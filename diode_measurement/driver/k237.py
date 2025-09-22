import time
import logging

from .driver import SourceMeter, handle_exception

__all__ = ["K237"]

ERROR_MESSAGES = {
    0: "Trigger Overrun",
    1: "IDDC",
    2: "IDDCO",
    3: "Interlock Present",
    4: "Illegal Measure Range",
    5: "Illegal Source Range",
    6: "Invalid Sweep Mix",
    7: "Log Cannot Cross Zero",
    8: "Autoranging Source With Pulse Sweep",
    9: "In Calibration",
    10: "In Standby",
    11: "Unit is a 236",
    12: "IOU DPRAM Failed",
    13: "IOU EEPROM Failed",
    14: "IOU Cal Checksum Error",
    15: "DPRAM Lockup",
    16: "DPRAM Link Error",
    17: "Cal ADC Zero Error",
    18: "Cal ADC Gain Error",
    19: "Cal SRC Zero Error",
    20: "Cal SRC Gain Error",
    21: "Cal Common Mode Error",
    22: "Cal Compliance Error",
    23: "Cal Value Error",
    24: "Cal Constants Error",
    25: "Cal Invalid Error"
}

logger = logging.getLogger(__name__)


class K237(SourceMeter):

    WRITE_DELAY = 0.250

    def identity(self) -> str:
        return self._query("U0X")

    def reset(self) -> None:
        self.resource.clear()

    def clear(self) -> None:
        self.resource.clear()

    def next_error(self) -> tuple[int, str]:
        result = self._query("U1X").strip()[3:]
        for index, value in enumerate(result):
            if value == "1":
                return index + 100, ERROR_MESSAGES.get(index, "Unknown Error")
        return 0, "No Error"

    def configure(self, options: dict) -> None:
        self._write("F0,0X")  # function VOLT
        self._write("B0,0,0X")  # bias to auto
        filter_mode = options.get("filter.mode", 0)
        self._write(f"P{filter_mode:d}X")

    def get_output_enabled(self) -> bool:
        return self._query("U3X")[18:20] == "N1"

    def set_output_enabled(self, enabled: bool) -> None:
        value = {False: "N0X", True: "N1X"}[enabled]
        self._write(value)

    def get_voltage_level(self) -> float:
        self._write("G1,2,0X")
        return float(self._query("X"))

    def set_voltage_level(self, level: float) -> None:
        self._write(f"B{level:.3E},,X")

    def set_voltage_range(self, level: float) -> None:
        index = self._voltage_range(level)
        self._write(f"B,{index:d},X")

    def set_current_compliance_level(self, level: float) -> None:
        self._write(f"L{level:.3E},0X")

    def compliance_tripped(self) -> bool:
        self._write("G1,0,0X")
        return self._query("X")[0:2] == "OS"

    def measure_i(self) -> float:
        self._write("G4,2,0X")
        return float(self._query("X"))

    def measure_iv(self) -> tuple[float, float]:
        i = self.measure_i()
        v = self.get_voltage_level()  # not possible in function VOLT
        return i, v

    @handle_exception
    def _write(self, message):
        if not hasattr(self, "_write_timestamp"):
            self._write_timestamp = 0
        offset = self._write_timestamp + abs(type(self).WRITE_DELAY)
        interval = 0.025
        while time.time() < offset:
            time.sleep(interval)
        self.resource.write(message)
        self._write_timestamp = time.time()

    @handle_exception
    def _query(self, message):
        result = self.resource.query(message)
        return result.strip()

    def _voltage_range(self, level):
        level = abs(level)
        if level <= 1.1:
            return 1
        elif level <= 11.:
            return 2
        elif level <= 110.:
            return 3
        elif level <= 1100.:
            return 4
        return 0  # Auto
