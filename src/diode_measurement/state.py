import logging
import threading
from dataclasses import dataclass
from collections.abc import Iterator
from enum import Enum
from queue import Queue
from typing import Any, Callable, Optional

from .core.role import Role

__all__ = ["State"]


class FSMState(str, Enum):
    IDLE = "idle"
    CONFIGURE = "configure"
    RAMPING = "ramping"
    CONTINUOUS = "continuous"
    STOPPING = "stopping"


@dataclass
class ChangeVoltageParameters:
    end_voltage: float
    step_voltage: float
    waiting_time: float


@dataclass
class Reading:
    timestamp: float
    t_dmm: float


@dataclass
class IVReading(Reading):
    voltage: float
    v_smu: float
    i_smu: float
    v_smu2: float
    i_smu2: float
    i_elm: float
    i_elm2: float


@dataclass
class CVReading(Reading):
    voltage: float
    v_smu: float
    i_smu: float
    c_lcr: float
    c2_lcr: float
    r_lcr: float


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
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
                logging.exception("Failed to submit event: %r", event_name)


class State:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {}
        self.abort_event = threading.Event()
        self.tcu_poll_interval: float = 5.0
        self._change_voltage_parameters: Optional[ChangeVoltageParameters] = None
        self._iv_reading_queues: list[Queue[IVReading]] = []
        self._it_reading_queues: list[Queue[IVReading]] = []
        self._cv_reading_queues: list[Queue[CVReading]] = []
        self.event_bus: EventBus = EventBus()

    @property
    def stop_requested(self) -> bool:
        return self.abort_event.is_set()

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
    def discharge_timeout(self) -> float:
        with self._lock:
            return self._state.get("discharge_timeout", 60.0)

    @property
    def discharge_threshold(self) -> float:
        with self._lock:
            return self._state.get("discharge_threshold", 0.5)

    @property
    def is_change_voltage_continuous(self) -> bool:
        with self._lock:
            return self._change_voltage_parameters is not None

    def pop_change_voltage_continuous(self) -> Optional[ChangeVoltageParameters]:
        with self._lock:
            parameters = self._change_voltage_parameters
            self._change_voltage_parameters = None
            return parameters

    def request_change_voltage(self, parameters: ChangeVoltageParameters) -> None:
        with self._lock:
            self._change_voltage_parameters = ChangeVoltageParameters(
                end_voltage=parameters.end_voltage,
                step_voltage=parameters.step_voltage,
                waiting_time=parameters.waiting_time,
            )

    def find_role(self, name: str) -> Optional[Role]:
        with self._lock:
            role_data = self._state.get("roles", {}).get(name)
            if role_data is None:
                return None
            return Role.from_dict(dict(role_data))

    def update(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._state.update(data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def items(self) -> tuple[tuple[str, Any], ...]:
        with self._lock:
            return tuple(self._state.items())

    def __iter__(self) -> Iterator:
        return iter(self._state.items())

    def create_iv_reading_queue(self) -> Queue[IVReading]:
        with self._lock:
            queue: Queue[IVReading] = Queue()
            self._iv_reading_queues.append(queue)
            return queue

    def create_it_reading_queue(self) -> Queue[IVReading]:
        with self._lock:
            queue: Queue[IVReading] = Queue()
            self._it_reading_queues.append(queue)
            return queue

    def create_cv_reading_queue(self) -> Queue[CVReading]:
        with self._lock:
            queue: Queue[CVReading] = Queue()
            self._cv_reading_queues.append(queue)
            return queue

    def append_iv_reading(self, reading: IVReading) -> None:
        for queue in self._iv_reading_queues:
            queue.put_nowait(reading)

    def append_it_reading(self, reading: IVReading) -> None:
        for queue in self._it_reading_queues:
            queue.put_nowait(reading)

    def append_cv_reading(self, reading: CVReading) -> None:
        for queue in self._cv_reading_queues:
            queue.put_nowait(reading)
