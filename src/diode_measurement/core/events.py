import logging
from collections.abc import Callable
from threading import RLock

__all__ = ["EventHandler", "EventBus"]

logger = logging.getLogger(__name__)


class EventHandler:
    def __init__(self) -> None:
        self._handlers: list[Callable] = []
        self._lock = RLock()

    def subscribe(self, handler: Callable) -> None:
        self._handlers.append(handler)

    def __call__(self, *args, **kwargs) -> None:
        with self._lock:
            for handler in self._handlers:
                try:
                    handler(*args, **kwargs)
                except Exception:
                    logger.exception("failed to handle event")


class EventBus:
    def __init__(self) -> None:
        self._lock = RLock()
        self._event_registry: dict[str, list[Callable]] = {}

    def register_callback(self, event_name: str, event_callback: Callable) -> None:
        with self._lock:
            self._event_registry.setdefault(event_name, []).append(event_callback)

    def submit(self, event_name: str, *args) -> None:
        with self._lock:
            callbacks = tuple(self._event_registry.get(event_name, ()))

        for callback in callbacks:
            try:
                callback(*args)
            except Exception:
                logger.exception("Failed to submit event: %r", event_name)
