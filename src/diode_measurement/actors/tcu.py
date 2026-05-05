import logging
from threading import Event
from typing import Any

from ..core.actor import Actor
from ..core.driver import TCU
from ..core.timers import IntervalTimer

__all__ = ["TCUActor"]

logger = logging.getLogger(__name__)


class TCUActor(Actor):
    def __init__(self, tcu: TCU, event_bus, abort_event: Event) -> None:
        super().__init__(abort_event=abort_event)
        self.tcu = tcu
        self.event_bus = event_bus
        self.poll_interval: float = 5.0
        self.query_timeout: float = 10.0
        self._interval_timer = IntervalTimer(self.poll_interval)

    def on_idle(self) -> None:
        if not self._interval_timer.expired():
            return
        self._interval_timer.reset()
        try:
            temperature = self.tcu.get_temperature()
        except Exception:
            logger.exception("Failed to read TCU temperature")
        else:
            self.event_bus.submit("update", {"tcu_temperature": temperature})
        try:
            state = self.tcu.get_state()
        except Exception:
            logger.exception("Failed to read TCU state")
        else:
            self.event_bus.submit("update", {"tcu_state": state})

    def on_message(self, message: Any) -> Any:
        return message()

    def is_within_setpoint(self) -> bool:
        return self.ask(self.tcu.is_within_setpoint).result(timeout=self.query_timeout)

    def ensure_setpoint(self) -> None:
        while not self._abort_event.is_set():
            if self.is_within_setpoint():
                break
            self.sleep(self.poll_interval)
