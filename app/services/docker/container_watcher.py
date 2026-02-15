import time
import docker
import asyncio
import json
from threading import Event

from langchain_groq import ChatGroq
from app.services.ai_agent.graph import build_agentic_rag_graph
from app.core.loadenv import Settings

from app.services.docker.log_broadcaster import broadcast_event
from app.services.actions.action_manager import (
    create_action, should_auto_execute, needs_human_approval, approve_and_execute
)

docker_client = docker.from_env()

llm_instance = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY
)

graph = build_agentic_rag_graph()

def _safe_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        return {}

def watch_single_container(container_name: str, stop_event: Event):
    try:
        container = docker_client.containers.get(container_name)
        start_time = int(time.time())

        print(f"🟢 Started watching container: {container_name}")

        logs = container.logs(stream=True, follow=True, since=start_time)

        for line in logs:
            if stop_event.is_set():
                print(f"🛑 Stopped watching: {container_name}")
                break

            log_line = line.decode("utf-8", errors="ignore").strip()
            if not log_line:
                continue

            # 1) stream raw log
            asyncio.run(broadcast_event(container_name, {"type": "log", "line": log_line}))

            # 2) analyze + propose fix if error
            try:
                result = graph.invoke({
                    "log_line": log_line,
                    "llm": llm_instance,
                    "container_name": container_name,
                })

                # analyzer info is in result["analysis"]
                analysis = _safe_json(result.get("analysis", "{}"))
                status = analysis.get("status", "ok")
                summary = analysis.get("summary", "")
                aconf = float(analysis.get("confidence", 0.5))

                asyncio.run(broadcast_event(container_name, {
                    "type": "analysis",
                    "status": status,
                    "summary": summary,
                    "confidence": aconf,
                }))

                if status != "error":
                    continue

                # agent response is JSON string in result["response"]
                agent_data = _safe_json(result.get("response", "{}"))
                command = (agent_data.get("command") or "NO_ACTION_RECOMMENDED").strip()
                conf = float(agent_data.get("confidence", 0.5))
                source = (agent_data.get("source") or "unknown").strip()
                reason = (agent_data.get("reason") or "").strip()

                asyncio.run(broadcast_event(container_name, {
                    "type": "fix_suggestion",
                    "command": command,
                    "confidence": conf,
                    "source": source,
                    "reason": reason,
                }))

                # 3) approval gate
                if command == "NO_ACTION_RECOMMENDED":
                    continue

                if should_auto_execute(conf):
                    # auto-exec
                    action = create_action(container_name, command, conf, source, reason)
                    updated = approve_and_execute(action.action_id)
                    asyncio.run(broadcast_event(container_name, {
                        "type": "action_result",
                        "action_id": updated.action_id,
                        "status": updated.status,
                        "message": updated.result_message,
                        "command": updated.command,
                        "confidence": updated.confidence,
                    }))
                else:
                    # needs approval
                    action = create_action(container_name, command, conf, source, reason)
                    asyncio.run(broadcast_event(container_name, {
                        "type": "approval_required",
                        "action_id": action.action_id,
                        "command": action.command,
                        "confidence": action.confidence,
                        "source": action.source,
                        "reason": action.reason,
                        "threshold": float(Settings.APPROVAL_MIN_CONFIDENCE),
                    }))

            except Exception as e:
                print(f"⚠️ Graph error [{container_name}]: {e}")
                asyncio.run(broadcast_event(container_name, {
                    "type": "system_error",
                    "message": str(e),
                }))

    except Exception as e:
        print(f"❌ Watcher failed [{container_name}]: {e}")
        try:
            asyncio.run(broadcast_event(container_name, {"type": "system_error", "message": str(e)}))
        except Exception:
            pass
