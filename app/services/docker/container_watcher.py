import time
import docker
import asyncio
from threading import Event
from langchain_groq import ChatGroq

from app.services.ai_agent.graph import build_agentic_rag_graph
from app.core.loadenv import Settings
from app.services.docker.log_broadcaster import broadcast_log

docker_client = docker.from_env()

llm_instance = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY
)

graph = build_agentic_rag_graph()


def watch_single_container(container_name: str, stop_event: Event):
    """
    Watch logs ONLY from watcher start time
    + broadcast to WebSocket clients
    """
    try:
        container = docker_client.containers.get(container_name)
        start_time = int(time.time())

        print(f"🟢 Started watching container: {container_name}")

        logs = container.logs(
            stream=True,
            follow=True,
            since=start_time
        )

        for line in logs:
            if stop_event.is_set():
                print(f"🛑 Stopped watching: {container_name}")
                break

            log_line = line.decode("utf-8", errors="ignore").strip()
            if not log_line:
                continue

            # 🔥 SEND TO UI
            asyncio.run(
                broadcast_log(container_name, log_line)
            )

            # 🧠 AI processing (optional)
            try:
                graph.invoke({
                    "log_line": log_line,
                    "llm": llm_instance,
                    "container_name": container_name,
                })
            except Exception as e:
                print(f"⚠️ AI error [{container_name}]: {e}")

    except Exception as e:
        print(f"❌ Watcher failed [{container_name}]: {e}")
