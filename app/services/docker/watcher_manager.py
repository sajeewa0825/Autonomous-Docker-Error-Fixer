from threading import Thread
import docker
from sqlalchemy.orm import Session
from docker.errors import NotFound, APIError
from app.db.model.containers_model import Container
from app.services.docker.container_watcher import watch_single_container

docker_client = docker.from_env()

# Keep track of running watchers
running_watchers: dict[str, Thread] = {}


def start_enabled_container_watchers(db: Session):
    containers = db.query(Container).filter(Container.enabled == 1).all()

    for container in containers:
        name = container.name

        # Skip if already watching
        if name in running_watchers:
            continue

        # 🔍 Validate container exists in Docker
        try:
            docker_container = docker_client.containers.get(name)

            # Optional: ensure container is running
            if docker_container.status != "running":
                print(f"⚠️ Container '{name}' exists but is not running. Skipped.")
                continue

        except NotFound:
            print(f"❌ Container '{name}' not found in Docker. DB entry ignored.")
            continue

        except APIError as e:
            print(f"❌ Docker API error for '{name}': {e}")
            continue

        except Exception as e:
            print(f"❌ Unexpected error for '{name}': {e}")
            continue

        # ✅ Start watcher thread ONLY after validation
        thread = Thread(
            target=watch_single_container,
            args=(name,),
            daemon=True
        )
        thread.start()

        running_watchers[name] = thread
        print(f"🧵 Watching started for container: {name}")
