from threading import Thread, Event
import docker
from docker.errors import NotFound
from sqlalchemy.orm import Session
from app.services.docker.container_watcher import watch_single_container
from app.db.model.containers_model import Container

docker_client = docker.from_env()

# container_name -> {thread, stop_event}
running_watchers: dict[str, dict] = {}


def start_enabled_container_watchers(db: Session):
    """
    Start watchers ONLY for enabled containers
    Call this ONCE at app startup (optional)
    """
    containers = (
        db.query(Container)
        .filter(Container.enabled == 1)
        .all()
    )

    for container in containers:
        start_watcher(container.name)


def start_watcher(container_name: str):
    """
    Start watching ONE container explicitly
    """
    if container_name in running_watchers:
        print(f"⚠️ Already watching: {container_name}")
        return

    try:
        container = docker_client.containers.get(container_name)

        # 🔒 SAFETY: do not attach to stopped containers
        if container.status != "running":
            print(f"⚠️ Container not running: {container_name}")
            return

    except NotFound:
        print(f"❌ Container not found: {container_name}")
        return

    stop_event = Event()


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
    """
    Stop watcher by name
    """
    watcher = running_watchers.get(container_name)
    if not watcher:
        print(f"⚠️ No watcher running for: {container_name}")
        return

    watcher["stop_event"].set()
    del running_watchers[container_name]

    print(f"🛑 Watcher stopped: {container_name}")


def stop_watchers_by_filter(name_contains: str):
    """
    Stop watchers by partial name
    """
    to_stop = [
        name for name in running_watchers
        if name_contains in name
    ]

    for name in to_stop:
        stop_watcher(name)
