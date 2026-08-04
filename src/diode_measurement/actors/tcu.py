import logging
import math
import time
from copy import copy
from dataclasses import dataclass
from threading import Event, RLock
from typing import Any

from ..core.actor import ThreadingActor
from ..core.driver import TCU

__all__ = ["TCUActor"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TCUMetrics:
    timestamp_utc: float
    temperature: float = math.nan
    humidity: float = math.nan
    state: str = ""


class TCUActor(ThreadingActor):
    def __init__(self, tcu: TCU, event_bus, abort_event: Event) -> None:
        super().__init__(abort_event=abort_event)
        self.tcu = tcu
        self.event_bus = event_bus
        self.poll_interval: float = 5.0
        self.query_timeout: float = 10.0
        self._next_poll_at: float = 0.0
        self._metrics = TCUMetrics(0)
        self._metrics_lock = RLock()

    def on_idle(self) -> None:
        now = time.monotonic()
        if now < self._next_poll_at:
            return

        self._next_poll_at = now + self.poll_interval

        timestamp_utc = time.time()
        temperature = math.nan
        humidity = math.nan
        state = ""

        try:
            temperature = self.tcu.get_temperature()
        except Exception:
            logger.exception("Failed to read TCU temperature")

        try:
            humidity = self.tcu.get_humidity()
        except Exception:
            logger.exception("Failed to read TCU humidity")

        try:
            state = self.tcu.get_state()
        except Exception:
            logger.exception("Failed to read TCU state")

        self.event_bus.submit(
            "update",
            {
                "tcu_temperature": temperature,
                "tcu_humidity": humidity,
                "tcu_state": state,
            },
        )

        with self._metrics_lock:
            self._metrics = TCUMetrics(
                timestamp_utc=timestamp_utc,
                temperature=temperature,
                humidity=humidity,
                state=state,
            )

    def on_message(self, message: Any) -> Any:
        return message()

    def is_within_setpoint(self) -> bool:
        return self.ask(self.tcu.is_within_setpoint).result(timeout=self.query_timeout)

    def ensure_setpoint(self) -> None:
        while not self._abort_event.is_set():
            if self.is_within_setpoint():
                break
            self.sleep(self.poll_interval)

    def cached_metrics(self) -> TCUMetrics:
        with self._metrics_lock:
            return copy(self._metrics)
