from collections.abc import Mapping
from typing import Any

from comet.driver.keithley.k2657a import K2657A

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource

__all__ = ["K2657AAdapter"]


class K2657AAdapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._driver: K2657A = K2657A(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._write("reset()")

    def clear(self) -> None:
        self._write("status.reset()")

    def next_error(self) -> InstrumentError | None:
        error = self._driver.next_error()
        if error is None:
            return None
        return InstrumentError(error.code, error.message)

    def configure(self, options: Mapping[str, Any]) -> None:
        beeper_enable = options.get("beeper.enable", False)
        self.set_beeper_enable(beeper_enable)

        self.set_source_function("DCVOLTS")
        self.set_display_measure_function("DCAMPS")

        filter_mode = options.get("filter.mode", "REPEAT_AVG")
        self.set_measure_filter_type(filter_mode)

        filter_count = options.get("filter.count", 10)
        self.set_measure_filter_count(filter_count)

        filter_enable = options.get("filter.enable", False)
        self.set_measure_filter_enable(filter_enable)

        nplc = options.get("nplc", 1.0)
        self.set_measure_nplc(nplc)

    def get_output_enabled(self) -> bool:
        return self._print("smua.source.output") == "1"

    def set_output_enabled(self, enabled: bool) -> None:
        value = {False: "OFF", True: "ON"}[enabled]
        self._write(f"smua.source.output = smua.OUTPUT_{value}")

    def get_voltage_level(self) -> float:
        return self._driver.voltage_level

    def set_voltage_level(self, level: float) -> None:
        self._driver.voltage_level = level

    def set_voltage_range(self, level: float) -> None:
        self._driver.voltage_range = level

    def set_current_compliance_level(self, level: float) -> None:
        self._driver.current_compliance = level

    def compliance_tripped(self) -> bool:
        return self._driver.compliance_tripped

    def measure_i(self) -> float:
        return self._driver.measure_current()

    def measure_v(self) -> float:
        return self._driver.measure_voltage()

    def measure_iv(self) -> tuple[float, float]:
        i = self.measure_i()  # TODO print(smua.measure.iv())
        v = self.measure_v()
        return i, v

    def set_beeper_enable(self, enabled: bool) -> None:
        value = {True: "ON", False: "OFF"}[enabled]
        self._write(f"beeper.enable = beeper.{value}")

    def set_source_function(self, function: str) -> None:
        self._write(f"smua.source.func = smua.OUTPUT_{function}")

    def set_measure_filter_type(self, filter_type: str) -> None:
        self._write(f"smua.measure.filter.type = smua.FILTER_{filter_type}")

    def set_measure_filter_count(self, count: int) -> None:
        self._write(f"smua.measure.filter.count = {count:d}")

    def set_measure_filter_enable(self, enabled: bool) -> None:
        self._write(f"smua.measure.filter.enable = {enabled:d}")

    def set_measure_nplc(self, nplc: float) -> None:
        self._write(f"smua.measure.nplc = {nplc:E}")

    def set_display_measure_function(self, function: str) -> None:
        if function not in ("DCAMPS", "DCVOLTS", "OHMS", "WATTS"):
            raise ValueError(f"Invalid display measure function: {function}")
        self._write(f"display.smua.measure.func = display.MEASURE_{function}")

    @handle_exception
    def _write(self, message: str) -> None:
        _ = self._resource.write(message)
        _ = self._resource.query("*OPC?")

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()

    def _print(self, message: str):
        return self._query(f"print({message})")
