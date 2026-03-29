from threading import Thread, Event, Lock
import docker
from docker.errors import NotFound
from sqlalchemy.orm import Session

from app.services.docker.container_watcher import watch_single_container
from app.db.model.containers_model import Container

docker_client = docker.from_env()

# container_name -> {thread, stop_event}
running_watchers: dict[str, dict] = {}
watchers_lock = Lock()


def _watcher_runner(container_name: str, stop_event: Event):
    """
    Wrapper so we can always clean registry when thread exits.
    """
    try:
        watch_single_container(container_name, stop_event)
    finally:
        with watchers_lock:
            watcher = running_watchers.get(container_name)
            if watcher and watcher["stop_event"] is stop_event:
                del running_watchers[container_name]
        print(f"🧹 Watcher cleaned up: {container_name}")


def start_enabled_container_watchers(db: Session):
    """
    Start watchers ONLY for enabled containers.
    Call this ONCE at app startup.
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
    Start watching ONE container explicitly.
    Safe for repeated calls.
    """
    with watchers_lock:
        existing = running_watchers.get(container_name)

        if existing:
            thread = existing["thread"]

            # If old thread died unexpectedly, clean it first
            if not thread.is_alive():
                del running_watchers[container_name]
            else:
                print(f"⚠️ Already watching: {container_name}")
                return

    try:
        container = docker_client.containers.get(container_name)

        # Optional: allow watcher even if not running yet.
        # The watcher will reconnect when container comes up.
        print(f"🔎 Found container: {container_name} (status={container.status})")

    except NotFound:
        print(f"❌ Container not found: {container_name}")
        return
    except Exception as e:
        print(f"❌ Failed to inspect container {container_name}: {e}")
        return

    stop_event = Event()

    thread = Thread(
        target=_watcher_runner,
        args=(container_name, stop_event),
        daemon=True,
        name=f"watcher-{container_name}"
    )

    with watchers_lock:
        running_watchers[container_name] = {
            "thread": thread,
            "stop_event": stop_event
        }

    thread.start()
    print(f"🧵 Watcher started: {container_name}")


def stop_watcher(container_name: str):
    """
    Stop watcher by name.
    """
    with watchers_lock:
        watcher = running_watchers.get(container_name)
        if not watcher:
            print(f"⚠️ No watcher running for: {container_name}")
            return

        stop_event = watcher["stop_event"]
        thread = watcher["thread"]

    stop_event.set()

    # Give thread a moment to exit gracefully
    thread.join(timeout=3)

    with watchers_lock:
        current = running_watchers.get(container_name)
        if current and current["stop_event"] is stop_event:
            del running_watchers[container_name]

    print(f"🛑 Watcher stopped: {container_name}")


def stop_watchers_by_filter(name_contains: str):
    """
    Stop watchers by partial name.
    """
    with watchers_lock:
        to_stop = [
            name for name in running_watchers
            if name_contains in name
        ]

    for name in to_stop:
        stop_watcher(name)


def list_running_watchers():
    """
    Optional helper for debugging/API usage.
    """
    with watchers_lock:
        return {
            name: {
                "alive": data["thread"].is_alive(),
                "thread_name": data["thread"].name,
            }
            for name, data in running_watchers.items()
        }