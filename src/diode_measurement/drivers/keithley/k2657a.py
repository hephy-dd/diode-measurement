from collections.abc import Mapping
from enum import StrEnum

import msgspec
from comet.driver.keithley.k2657a import K2657A

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource

__all__ = ["K2657AAdapter"]


class SourceFunction(StrEnum):
    DCAMPS = "DCAMPS"
    DCVOLTS = "DCVOLTS"


class MeasureFunction(StrEnum):
    DCAMPS = "DCAMPS"
    DCVOLTS = "DCVOLTS"
    OHMS = "OHMS"
    WATTS = "WATTS"


class FilterType(StrEnum):
    REPEAT_AVG = "REPEAT_AVG"
    MOVING_AVG = "MOVING_AVG"
    MEDIAN = "MEDIAN"


class K2657AConfig(msgspec.Struct, frozen=True):
    beeper_enable: bool = msgspec.field(
        default=False,
        name="beeper.enable",
    )
    filter_type: FilterType = msgspec.field(
        default=FilterType.REPEAT_AVG,
        name="filter.mode",  # sic!
    )
    filter_count: int = msgspec.field(
        default=10,
        name="filter.count",
    )
    filter_enable: bool = msgspec.field(
        default=False,
        name="filter.enable",
    )
    nplc: float = 1.0


class K2657AAdapter:
    def __init__(self, resource: Resource) -> None:
        self._resource = resource
        self._driver = K2657A(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._write("reset()")

    def clear(self) -> None:
        self._write("status.reset()", wait_for_completion=False)

        # Neither reset() nor status.reset() clears the error queue.
        # Clear it explicitly to prevent stale errors from affecting subsequent operations.
        self._write("errorqueue.clear()")

    def next_error(self) -> InstrumentError | None:
        error = self._driver.next_error()
        if error is None:
            return None
        return InstrumentError(error.code, error.message)

    def configure(self, options: Mapping[str, object]) -> None:
        config = msgspec.convert(options, type=K2657AConfig)

        self.set_beeper_enable(config.beeper_enable)

        self.set_source_function(SourceFunction.DCVOLTS)
        self.set_display_measure_function(MeasureFunction.DCAMPS)

        self.set_measure_filter_type(config.filter_type)
        self.set_measure_filter_count(config.filter_count)
        self.set_measure_filter_enable(config.filter_enable)
        self.set_measure_nplc(config.nplc)

    def get_output_enabled(self) -> bool:
        return self._print("smua.source.output") == "1"

    def set_output_enabled(self, enabled: bool) -> None:
        value = "ON" if enabled else "OFF"
        self._set("smua.source.output", f"smua.OUTPUT_{value}")

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
        value = "ON" if enabled else "OFF"
        self._set("beeper.enable", f"beeper.{value}")

    def set_source_function(self, function: SourceFunction) -> None:
        self._set("smua.source.func", f"smua.OUTPUT_{function}")

    def set_measure_filter_type(self, filter_type: FilterType) -> None:
        self._set("smua.measure.filter.type", f"smua.FILTER_{filter_type}")

    def set_measure_filter_count(self, count: int) -> None:
        self._set("smua.measure.filter.count", f"{count:d}")

    def set_measure_filter_enable(self, enabled: bool) -> None:
        self._set("smua.measure.filter.enable", f"{enabled:d}")

    def set_measure_nplc(self, nplc: float) -> None:
        self._set("smua.measure.nplc", f"{nplc:E}")

    def set_display_measure_function(self, function: MeasureFunction) -> None:
        self._set("display.smua.measure.func", f"display.MEASURE_{function}")

    @handle_exception
    def _write(self, message: str, wait_for_completion: bool = True) -> None:
        _ = self._resource.write(message)
        if wait_for_completion:
            _ = self._resource.query("*OPC?")

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()

    def _print(self, expression: str) -> str:
        return self._query(f"print({expression})")

    def _set(self, key: str, value: str) -> None:
        self._write(f"{key} = {value}")
