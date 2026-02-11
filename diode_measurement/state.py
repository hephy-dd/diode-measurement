from typing import Any, Iterator, Optional

__all__ = ["State"]


class State:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {}

    @property
    def measurement_type(self) -> str:
        return self._state.get("measurement_type", "")

    @property
    def timestamp(self) -> float:
        return self._state.get("timestamp", 0.0)

    @property
    def sample(self) -> str:
        return self._state.get("sample", "")

    @property
    def stop_requested(self) -> bool:
        return self._state.get("stop_requested", False)

    @property
    def auto_reconnect(self) -> bool:
        return self._state.get("auto_reconnect", False)

    @property
    def is_continuous(self) -> bool:
        return self._state.get("continuous", False)

    @property
    def is_reset(self) -> bool:
        return self._state.get("reset", False)

    @property
    def continue_in_compliance(self) -> bool:
        return self._state.get("continue_in_compliance", False)

    @property
    def waiting_time(self) -> float:
        return self._state.get("waiting_time", 1.0)

    @property
    def waiting_time_continuous(self) -> float:
        return self._state.get("waiting_time_continuous", 1.0)

    @property
    def source_voltage(self) -> Optional[float]:
        return self._state.get("source_voltage")

    @property
    def bias_source_voltage(self) -> Optional[float]:
        return self._state.get("bias_source_voltage")

    @property
    def bias_voltage(self) -> float:
        return self._state.get("bias_voltage", 0.0)

    @property
    def voltage_begin(self) -> float:
        return self._state.get("voltage_begin", 0.0)

    @property
    def voltage_end(self) -> float:
        return self._state.get("voltage_end", 0.0)

    @property
    def voltage_step(self) -> float:
        return self._state.get("voltage_step", 1.0)

    @property
    def current_compliance(self) -> float:
        return self._state.get("current_compliance", 0.0)

    @property
    def source_role(self) -> Optional[str]:
        return self._state.get("source_role")

    @property
    def bias_source_role(self) -> Optional[str]:
        return self._state.get("bias_source_role")

    @property
    def change_voltage_continuous(self) -> Optional[float]:
        return self._state.get("change_voltage_continuous")

    def pop_change_voltage_continuous(self) -> Optional[float]:
        return self._state.pop("change_voltage_continuous", None)

    def find_role(self, name: str) -> dict:
        return self._state.get("roles", {}).get(name, {})

    def update(self, data: dict[str, Any]) -> None:
        self._state.update(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def __iter__(self) -> Iterator:
        return iter(self._state.items())
