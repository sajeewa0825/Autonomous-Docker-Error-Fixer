import time
import docker
import asyncio
import json
from threading import Event
from docker.errors import NotFound, APIError

from langchain_groq import ChatGroq

from app.services.ai_agent.graph import build_agentic_rag_graph
from app.core.loadenv import Settings
from app.core.config import SessionLocal

from app.services.docker.log_broadcaster import broadcast_event
from app.services.actions.action_manager import (
    create_action,
    should_auto_execute,
    approve_and_execute,
)
from app.services.docker.error_log_service import save_error_log

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


def _emit(container_name: str, payload: dict):
    try:
        asyncio.run(broadcast_event(container_name, payload))
    except Exception as e:
        print(f"⚠️ Broadcast failed [{container_name}]: {e}")


def _save_error_record(
    container_name: str,
    raw_error_log_line: str,
    suggested_command: str,
    confidence: float,
):
    """
    Save one error suggestion row into DB.
    Uses a fresh DB session because watcher runs in a background thread.
    """
    db = SessionLocal()
    try:
        save_error_log(
            db=db,
            container_name=container_name,
            raw_error_log_line=raw_error_log_line,
            suggested_command=suggested_command,
            confidence=confidence,
        )
    except Exception as e:
        print(f"⚠️ Failed to save error log [{container_name}]: {e}")
        db.rollback()
    finally:
        db.close()


def _process_log_line(container_name: str, log_line: str):
    _emit(container_name, {"type": "log", "line": log_line})

    try:
        result = graph.invoke({
            "log_line": log_line,
            "llm": llm_instance,
            "container_name": container_name,
        })

        analysis = _safe_json(result.get("analysis", "{}"))
        status = analysis.get("status", "ok")
        summary = analysis.get("summary", "")
        aconf = float(analysis.get("confidence", 0.5))

        _emit(container_name, {
            "type": "analysis",
            "status": status,
            "summary": summary,
            "confidence": aconf,
        })

        if status != "error":
            return

        agent_data = _safe_json(result.get("response", "{}"))
        command = (agent_data.get("command") or "NO_ACTION_RECOMMENDED").strip()
        conf = float(agent_data.get("confidence", 0.5))
        source = (agent_data.get("source") or "unknown").strip()
        reason = (agent_data.get("reason") or "").strip()

        _emit(container_name, {
            "type": "fix_suggestion",
            "command": command,
            "confidence": conf,
            "source": source,
            "reason": reason,
        })

        # save only when there is a real suggested command
        if command != "NO_ACTION_RECOMMENDED":
            _save_error_record(
                container_name=container_name,
                raw_error_log_line=log_line,
                suggested_command=command,
                confidence=conf,
            )

        if command == "NO_ACTION_RECOMMENDED":
            return

        action = create_action(container_name, command, conf, source, reason)

        if should_auto_execute(conf):
            updated = approve_and_execute(action.action_id)
            _emit(container_name, {
                "type": "action_result",
                "action_id": updated.action_id,
                "status": updated.status,
                "message": updated.result_message,
                "command": updated.command,
                "confidence": updated.confidence,
                "source": updated.source,
                "reason": updated.reason,
            })
        else:
            _emit(container_name, {
                "type": "approval_required",
                "action_id": action.action_id,
                "command": action.command,
                "confidence": action.confidence,
                "source": action.source,
                "reason": action.reason,
                "threshold": float(Settings.APPROVAL_MIN_CONFIDENCE),
            })

    except Exception as e:
        print(f"⚠️ Graph error [{container_name}]: {e}")
        _emit(container_name, {
            "type": "system_error",
            "message": f"Graph error: {str(e)}",
        })


def watch_single_container(container_name: str, stop_event: Event):
    last_since = int(time.time())

    print(f"🟢 Watch loop started for container: {container_name}")

    while not stop_event.is_set():
        try:
            container = docker_client.containers.get(container_name)
            container.reload()
            status = container.status

            if status != "running":
                print(f"⏸️ Container not running [{container_name}] (status={status}). Waiting...")
                time.sleep(2)
                continue

            print(f"📡 Attaching to logs: {container_name} (since={last_since})")

            logs = container.logs(
                stream=True,
                follow=True,
                since=last_since,
            )

            for line in logs:
                if stop_event.is_set():
                    print(f"🛑 Stopped watching: {container_name}")
                    return

                log_line = line.decode("utf-8", errors="ignore").strip()
                if not log_line:
                    continue

                last_since = int(time.time())
                _process_log_line(container_name, log_line)

            if not stop_event.is_set():
                print(f"🔁 Log stream ended for [{container_name}], reconnecting...")
                time.sleep(1)

        except NotFound:
            print(f"❌ Container not found [{container_name}], retrying...")
            _emit(container_name, {
                "type": "system_error",
                "message": f"Container not found: {container_name}",
            })
            time.sleep(3)

        except APIError as e:
            print(f"⚠️ Docker API error [{container_name}]: {e}")
            _emit(container_name, {
                "type": "system_error",
                "message": f"Docker API error: {str(e)}",
            })
            time.sleep(2)

        except Exception as e:
            print(f"⚠️ Watcher error [{container_name}]: {e}")
            _emit(container_name, {
                "type": "system_error",
                "message": str(e),
            })
            time.sleep(2)

    print(f"🛑 Watch loop exited for container: {container_name}")