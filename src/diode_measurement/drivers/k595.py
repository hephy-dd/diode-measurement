import math
import time
from collections.abc import Mapping
from typing import Any, Final

from ..core.driver import InstrumentError, Resource, handle_exception

__all__ = ["K595Adapter"]

ERROR_MESSAGES: Final[dict[int, str]] = {
    0: "IDDC",
    1: "IDDCO",
    2: "No Remote",
    3: "Conflict",
    4: "Trigger Overrun",
    5: "Number",
    6: "Self Test",
}


class K595Adapter:
    WRITE_DELAY = 0.250

    def __init__(self, resource: Resource) -> None:
        self.resource = resource
        self._write_timestamp: float = 0.0

    def identify(self) -> str:
        return self._query("U0X")[:3]

    def reset(self) -> None:
        self.resource.clear()

    def clear(self) -> None:
        self.resource.clear()

    def next_error(self) -> InstrumentError | None:
        result = self._query("U1X")[3:]
        for index, value in enumerate(result):
            if value == "1":
                code = index + 100
                message = ERROR_MESSAGES.get(index, "Unknown Error")
                return InstrumentError(code, message)
        return None

    def configure(self, options: Mapping[str, Any]) -> None:
        self._write("T0X")
        self._write("V0X")

    def get_output_enabled(self) -> bool:
        return self.get_voltage_level() != 0

    def set_output_enabled(self, enabled: bool) -> None: ...  # not available

    def get_voltage_level(self) -> float:
        self._write("F1X")
        self._write("G1X")
        return float(self._query("X").split(",")[1])

    def set_voltage_level(self, level: float) -> None:
        self._write(f"V{level:.2f}X")

    def set_voltage_range(self, level: float) -> None: ...  # TODO

    def set_current_compliance_level(self, level: float) -> None: ...  # not supported

    def compliance_tripped(self) -> bool:
        self._write("F1X")
        self._write("G1X")
        return self._query("X")[0] == "O"

    def measure_i(self) -> float:
        self._write("F1X")
        self._write("G1X")
        return float(self._query("X").split(",")[0])

    def measure_iv(self) -> tuple[float, float]:
        return self.measure_i(), float("nan")  # TODO

    def measure_impedance(self) -> tuple[float, float]:
        self._write("F0X")
        self._write("G1X")
        return float(self._query("X").split(",")[0]), math.nan

    @handle_exception
    def _write(self, message: str) -> None:
        offset = self._write_timestamp + abs(type(self).WRITE_DELAY)
        interval = max(0.025, abs(type(self).WRITE_DELAY / 100.0))
        while time.monotonic() < offset:
            time.sleep(interval)
        self.resource.write(message)
        self._write_timestamp = time.monotonic()

    @handle_exception
    def _query(self, message: str) -> str:
        return self.resource.query(message).strip()
