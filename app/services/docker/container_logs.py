import time
import docker
from app.core.loadenv import Settings
from app.services.ai_agent.graph import build_agentic_rag_graph
from langchain_groq import ChatGroq


llm_instance = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY
)

# Build your full RAG + log analyzer graph once
graph = build_agentic_rag_graph()

def watch_docker_logs():
    """Watch logs from a container and analyze them in real time."""
    try:
        client = docker.from_env()
        print("🔵 Connected to Docker daemon.")
    except Exception as e:
        print(f"❌ Error connecting to Docker daemon: {e}")
        return

    try:
        container = client.containers.get(Settings.DOCKER_CONTAINER_NAME)
        print(f"🟢 Watching logs from container: {Settings.DOCKER_CONTAINER_NAME}")

        since_time = int(time.time())

        for line in container.logs(stream=True, follow=True , since=since_time):
            log_line = line.decode("utf-8").strip()
            if not log_line:
                continue

            print(f"[LOG] {log_line}")

            # 🔍 Send log line to your LangGraph workflow
            try:
                # print(f"[LOG] {log_line}")
                print("🧠 Graph input started")
                result = graph.invoke({
                    "log_line": log_line,
                    "llm": llm_instance,
                    "container_name": Settings.DOCKER_CONTAINER_NAME,
                })
                # print("🧠 Graph result:", result)

            except Exception as e:
                print(f"⚠️ Error analyzing (Container) log: {e}")

    except Exception as e:
        print(f"❌ Error watching container logs: {e}")
        time.sleep(10)
