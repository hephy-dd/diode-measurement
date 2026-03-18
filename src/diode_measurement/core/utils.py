import logging
import time
import threading
from typing import Callable

__all__ = ["EventHandler", "IntervalTimer"]


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


class IntervalTimer:
    def __init__(self, interval: float) -> None:
        if interval < 0:
            raise ValueError("interval must be >= 0")
        self.interval = float(interval)
        self._clock: Callable[[], float] = time.monotonic
        self._last_reset: float = self._clock()

    def expired(self) -> bool:
        return (self._clock() - self._last_reset) >= self.interval

    def reset(self) -> None:
        self._last_reset = self._clock()

    def remaining(self) -> float:
        return max(0.0, self.interval - (self._clock() - self._last_reset))

    def __bool__(self) -> bool:
        return self.expired()
