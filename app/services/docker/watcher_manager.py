from threading import Thread, Event
import docker
from docker.errors import NotFound
from sqlalchemy.orm import Session
from app.db.model.containers_model import Container

docker_client = docker.from_env()

# container_name -> {thread, stop_event}
running_watchers: dict[str, dict] = {}

def start_enabled_container_watchers(db: Session):
    containers = db.query(Container).filter(Container.enabled == 1).all()

    for container in containers:
        start_watcher(container.name)

def start_watcher(container_name: str):
    if container_name in running_watchers:
        return

    try:
        docker_client.containers.get(container_name)
    except NotFound:
        print(f"❌ Container not found: {container_name}")
        return

    stop_event = Event()

    from app.services.docker.container_watcher import watch_single_container

    thread = Thread(
        target=watch_single_container,
        args=(container_name, stop_event),
        daemon=True
    )
    thread.start()

    running_watchers[container_name] = {
        "thread": thread,
        "stop_event": stop_event
    }

    print(f"🧵 Watcher started: {container_name}")


def stop_watcher(container_name: str):
    watcher = running_watchers.get(container_name)
    if not watcher:
        return

    watcher["stop_event"].set()
    del running_watchers[container_name]

    print(f"🛑 Watcher stopped: {container_name}")
