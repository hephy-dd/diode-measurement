import threading
from collections.abc import Iterator
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
        self._state: dict[str, Any] = {}
        self.abort_event = threading.Event()
        self.tcu_poll_interval: float = 5.0

    @property
    def measurement_type(self) -> str:
        with self._lock:
            return self._state.get("measurement_type", "")

    @property
    def timestamp(self) -> float:
        with self._lock:
            return self._state.get("timestamp", 0.0)

    @property
    def sample(self) -> str:
        with self._lock:
            return self._state.get("sample", "")

    @property
    def stop_requested(self) -> bool:
        with self._lock:
            return self.abort_event.is_set()

    @property
    def auto_reconnect(self) -> bool:
        with self._lock:
            return self._state.get("auto_reconnect", False)

    @property
    def is_continuous(self) -> bool:
        with self._lock:
            return self._state.get("continuous", False)

    @property
    def continue_in_compliance(self) -> bool:
        with self._lock:
            return self._state.get("continue_in_compliance", False)

    @property
    def waiting_time(self) -> float:
        with self._lock:
            return self._state.get("waiting_time", 1.0)

    @property
    def waiting_time_continuous(self) -> float:
        with self._lock:
            return self._state.get("waiting_time_continuous", 1.0)

    @property
    def source_voltage(self) -> Optional[float]:
        with self._lock:
            return self._state.get("source_voltage")

    @property
    def bias_source_voltage(self) -> Optional[float]:
        with self._lock:
            return self._state.get("bias_source_voltage")

    @property
    def bias_voltage(self) -> float:
        with self._lock:
            return self._state.get("bias_voltage", 0.0)

    @property
    def voltage_begin(self) -> float:
        with self._lock:
            return self._state.get("voltage_begin", 0.0)

    @property
    def voltage_end(self) -> float:
        with self._lock:
            return self._state.get("voltage_end", 0.0)

    @property
    def voltage_step(self) -> float:
        with self._lock:
            return self._state.get("voltage_step", 1.0)

    @property
    def current_compliance(self) -> float:
        with self._lock:
            return self._state.get("current_compliance", 0.0)

    @property
    def source_role(self) -> Optional[str]:
        with self._lock:
            return self._state.get("source_role")

    @property
    def bias_source_role(self) -> Optional[str]:
        with self._lock:
            return self._state.get("bias_source_role")

    @property
    def change_voltage_continuous(self) -> Optional[float]:
        with self._lock:
            return self._state.get("change_voltage_continuous")

    def pop_change_voltage_continuous(self) -> Optional[float]:
        with self._lock:
            return self._state.pop("change_voltage_continuous", None)

    def find_role(self, name: str) -> dict:
        with self._lock:
            return self._state.get("roles", {}).get(name, {})

    def update(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._state.update(data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def __iter__(self) -> Iterator:
        with self._lock:
            return iter(self._state.items())
