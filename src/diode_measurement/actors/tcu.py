import logging
import math
import time
from copy import copy
from dataclasses import dataclass
from functools import partial
from queue import Queue
from threading import Event, RLock
from typing import Any

from ..core.actor import ThreadingActor
from ..core.driver import TCUAdapter
from ..core.events import UpdateMetricsEvent

__all__ = ["TCUActor"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TCUMetrics:
    timestamp_utc: float
    temperature: float = math.nan
    humidity: float = math.nan
    state: str = ""


class TCUActor(ThreadingActor):
    def __init__(self, tcu: TCUAdapter, event_queue: Queue, abort_event: Event) -> None:
        super().__init__(abort_event=abort_event)
        self.tcu = tcu
        self.event_queue: Queue[Any] = event_queue
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
            humidity = self.tcu.get_humidity()  # AC3 driver returns NaN
        except Exception:
            logger.exception("Failed to read TCU humidity")

        try:
            state = self.tcu.get_state()
        except Exception:
            logger.exception("Failed to read TCU state")

        self.event_queue.put(
            UpdateMetricsEvent(
                {
                    "tcu_temperature": temperature,
                    "tcu_humidity": humidity,
                    "tcu_state": state,
                },
            )
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

    def is_setpoint_enabled(self) -> bool:
        return self.ask(self.tcu.is_setpoint_enabled).result(timeout=self.query_timeout)

    def set_setpoint_enabled(self, enabled: bool) -> None:
        self.ask(partial(self.tcu.set_setpoint_enabled, enabled)).result(
            timeout=self.query_timeout
        )

    def set_target_temperature(self, temperature_setpoint: float) -> None:
        self.ask(partial(self.tcu.set_target_temperature, temperature_setpoint)).result(
            timeout=self.query_timeout
        )

    def is_within_setpoint(self) -> bool:
        return self.ask(self.tcu.is_within_setpoint).result(timeout=self.query_timeout)

    def cached_metrics(self) -> TCUMetrics:
        with self._metrics_lock:
            return copy(self._metrics)

    def handle_event(self, event: Any) -> None:
        self.ask(partial(self.tcu.handle_event, event)).result(
            timeout=self.query_timeout
        )
