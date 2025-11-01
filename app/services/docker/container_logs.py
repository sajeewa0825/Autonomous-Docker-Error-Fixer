import time
import docker
from app.core.loadenv import Settings


def watch_docker_logs():
    client = docker.from_env()


    try:
        container = client.containers.get(Settings.DOCKER_CONTAINER_NAME)
        print(f"🟢 Watching logs from container: {Settings.DOCKER_CONTAINER_NAME}")

        for line in container.logs(stream=True, follow=True):
            log_line = line.decode("utf-8").strip()
            print(f"[LOG] {log_line}")

    except Exception as e:
        print(f"❌ Error watching container logs: {e}")
        time.sleep(10)