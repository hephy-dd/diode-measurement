import threading
from enum import Enum
from typing import Any, Optional

__all__ = ["State"]


class FSMState(str, Enum):
    IDLE = "idle"
    CONFIGURE = "configure"
    RAMPING = "ramping"
    CONTINUOUS = "continuous"
    STOPPING = "stopping"


class State:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.abort_event = threading.Event()

        self.tcu_poll_interval: float = 5.0
        self.auto_reconnect: bool = False
        self.is_continuous: bool = False

        self.start_timestamp: float = 0.0
        self.measurement_type: str = ""
        self.source_role: Optional[str] = None
        self.bias_source_role: Optional[str] = None
        self.sample: str = ""
        self.filename: str = ""

        self.voltage_begin: float = 0.0
        self.voltage_end: float = 0.0
        self.voltage_step: float = 1.0
        self.waiting_time: float = 1.0

        self.bias_voltage: float = 0.0

        self._source_voltage: float = 0.0
        self._bias_source_voltage: float = 0.0
        self._change_voltage_continuous: Optional[dict] = None

        self._current_compliance: float = 0.0
        self._continue_in_compliance: bool = False
        self._waiting_time_continuous: float = 1.0
        self.settle_waiting_time: float = 1.0

        self.roles: dict[str, Any] = {}

    @property
    def stop_requested(self) -> bool:
        return self.abort_event.is_set()

    @property
    def continue_in_compliance(self) -> bool:
        with self._lock:
            return self._continue_in_compliance

    @continue_in_compliance.setter
    def continue_in_compliance(self, value: bool) -> None:
        with self._lock:
            self._continue_in_compliance = value

    @property
    def waiting_time_continuous(self) -> float:
        with self._lock:
            return self._waiting_time_continuous

    @waiting_time_continuous.setter
    def waiting_time_continuous(self, value: float) -> None:
        with self._lock:
            self._waiting_time_continuous = value

    @property
    def source_voltage(self) -> float:
        with self._lock:
            return self._source_voltage

    @source_voltage.setter
    def source_voltage(self, value: float) -> None:
        with self._lock:
            self._source_voltage = value

    @property
    def bias_source_voltage(self) -> float:
        with self._lock:
            return self._bias_source_voltage

    @bias_source_voltage.setter
    def bias_source_voltage(self, value: float) -> None:
        with self._lock:
            self._bias_source_voltage = value

    @property
    def current_compliance(self) -> float:
        with self._lock:
            return self._current_compliance

    @current_compliance.setter
    def current_compliance(self, value: float) -> None:
        with self._lock:
            self._current_compliance = value

    @property
    def is_change_voltage_continuous(self) -> bool:
        with self._lock:
            return self._change_voltage_continuous is not None

    def put_change_voltage_continuous(self, end_voltage: float, step_voltage: float, waiting_time: float) -> None:
        with self._lock:
            self._change_voltage_continuous = {
                "end_voltage": end_voltage,
                "step_voltage": step_voltage,
                "waiting_time": waiting_time,
            }

    def pop_change_voltage_continuous(self) -> Optional[dict]:
        with self._lock:
            change_voltage_continuous = self._change_voltage_continuous
            self._change_voltage_continuous = None
            return change_voltage_continuous

    def find_role(self, name: str) -> dict:
        return self.roles.get(name, {})
