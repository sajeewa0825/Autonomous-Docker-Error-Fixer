from typing import Dict, List, Callable

# container_name -> list of callbacks
listeners: Dict[str, List[Callable[[str], None]]] = {}


def register_listener(container_name: str, callback: Callable[[str], None]):
    listeners.setdefault(container_name, []).append(callback)


def unregister_listener(container_name: str, callback: Callable):
    if container_name in listeners:
        listeners[container_name].remove(callback)


def broadcast_log(container_name: str, message: str):
    for cb in listeners.get(container_name, []):
        cb(message)