import logging
import threading
from typing import Callable

__all__ = ["EventHandler"]


class EventHandler:
    def __init__(self) -> None:
        self.handlers: list[Callable] = []
        self.lock = threading.RLock()

    def subscribe(self, handler: Callable) -> None:
        self.handlers.append(handler)

    def __call__(self, *args, **kwargs) -> None:
        with self.lock:
            for handler in self.handlers:
                try:
                    handler(*args, **kwargs)
                except Exception as exc:
                    logging.exception(exc)
