import time
import docker
from threading import Thread

from app.services.ai_agent.graph import build_agentic_rag_graph
from app.core.loadenv import Settings
from langchain_groq import ChatGroq

llm_instance = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY
)

graph = build_agentic_rag_graph()
docker_client = docker.from_env()


def watch_single_container(container_name: str):
    """Watch logs of ONE container (blocking)."""
    try:
        container = docker_client.containers.get(container_name)
        print(f"🟢 Started watching: {container_name}")

        since_time = int(time.time())

        for line in container.logs(
            stream=True,
            follow=True,
            since=since_time
        ):
            log_line = line.decode("utf-8").strip()
            if not log_line:
                continue

            print(f"[{container_name}] {log_line}")

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
