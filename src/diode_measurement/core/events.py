import logging
import threading
from collections.abc import Callable

__all__ = ["EventHandler"]

logger = logging.getLogger(__name__)


class EventHandler:
    def __init__(self) -> None:
        self._handlers: list[Callable] = []
        self._lock = threading.RLock()

    def subscribe(self, handler: Callable) -> None:
        self._handlers.append(handler)

    def __call__(self, *args, **kwargs) -> None:
        with self._lock:
            for handler in self._handlers:
                try:
                    handler(*args, **kwargs)
                except Exception:
                    logger.exception("failed to handle event")
