import math
import time
from typing import Tuple

from .driver import LCRMeter, handle_exception

__all__ = ["K595"]

ERROR_MESSAGES = {
    0: "IDDC",
    1: "IDDCO",
    2: "No Remote",
    3: "Conflict",
    4: "Trigger Overrun",
    5: "Number",
    6: "Self Test"
}


class K595(LCRMeter):

    WRITE_DELAY = 0.250

    def identity(self) -> str:
        return self._query("U0X")[:3]

    def reset(self) -> None:
        self.resource.clear()

    def clear(self) -> None:
        self.resource.clear()

    def next_error(self) -> Tuple[int, str]:
        result = self._query("U1X")[3:]
        for index, value in enumerate(result):
            if value == "1":
                return index + 100, ERROR_MESSAGES.get(index, "Unknown Error")
        return 0, "No Error"

    def configure(self, options: dict) -> None:
        self._write("T0X")
        self._write("V0X")

    def get_output_enabled(self) -> bool:
        return self.get_voltage_level() != 0

    def set_output_enabled(self, enabled: bool) -> None:
        ...  # not available

    def get_voltage_level(self) -> float:
        self._write("F1X")
        self._write("G1X")
        return float(self._query("X").split(",")[1])

    def set_voltage_level(self, level: float) -> None:
        self._write(f"V{level:.2f}X")

    def set_voltage_range(self, level: float) -> None:
        ...  # TODO

    def set_current_compliance_level(self, level: float) -> None:
        ...  # not supported

    def compliance_tripped(self) -> bool:
        self._write("F1X")
        self._write("G1X")
        return self._query("X")[0] == "O"

    def measure_i(self) -> float:
        self._write("F1X")
        self._write("G1X")
        return float(self._query("X").split(",")[0])

    def measure_iv(self) -> Tuple[float, float]:
        return self.measure_i(), float("nan")  # TODO

    def measure_impedance(self) -> Tuple[float, float]:
        self._write("F0X")
        self._write("G1X")
        return float(self._query("X").split(",")[0]), math.nan

    @handle_exception
    def _write(self, message):
        if not hasattr(self, "_write_timestamp"):
            self._write_timestamp = 0
        offset = self._write_timestamp + abs(type(self).WRITE_DELAY)
        interval = max(0.025, abs(type(self).WRITE_DELAY / 100.))
        while time.time() < offset:
            time.sleep(interval)
        self.resource.write(message)
        self._write_timestamp = time.time()

    @handle_exception
    def _query(self, message):
        return self.resource.query(message).strip()
