import time
from collections.abc import Iterable, Mapping
from enum import StrEnum

import msgspec
from comet.driver.keithley.k6517b import K6517B

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K6517BAdapter"]


class SenseFunction(StrEnum):
    CURRENT = "CURR"
    VOLTAGE = "VOLT"


class FilterType(StrEnum):
    MOVING = "MOV"
    REPEAT = "REP"


class K6517BConfig(msgspec.Struct, frozen=True):
    sense_range: float = msgspec.field(
        default=20e-3,
        name="sense.range",
    )
    sense_auto_range_lower_limit: float = msgspec.field(
        default=2e-12,
        name="sense.auto_range.lower_limit",
    )
    sense_auto_range_upper_limit: float = msgspec.field(
        default=20e-3,
        name="sense.auto_range.upper_limit",
    )
    sense_auto_range: bool = msgspec.field(
        default=True,
        name="sense.auto_range",
    )
    source_meter_connect: bool = msgspec.field(
        default=False,
        name="source.meter_connect",
    )
    filter_type: FilterType = msgspec.field(
        default=FilterType.MOVING,
        name="filter.mode",
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


class K6517BAdapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._driver: K6517B = K6517B(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return parse_scpi_error(self._query(":SYST:ERR?"))

    def configure(self, options: Mapping[str, object]) -> None:
        config = msgspec.convert(options, type=K6517BConfig)

        self.set_format_elements(["READ"])
        self.set_sense_function(SenseFunction.CURRENT)

        self.set_sense_current_range(config.sense_range)
        self.set_sense_current_range_auto_lower_limit(
            config.sense_auto_range_lower_limit
        )
        self.set_sense_current_range_auto_upper_limit(
            config.sense_auto_range_upper_limit
        )
        self.set_sense_current_range_auto(config.sense_auto_range)

        self.set_source_voltage_mconnect(config.source_meter_connect)

        self.set_sense_current_average_tcontrol(config.filter_type)
        self.set_sense_current_average_count(config.filter_count)
        self.set_sense_current_average_state(config.filter_enable)
        self.set_sense_current_nplcycles(config.nplc)

    def get_output_enabled(self) -> bool:
        return bool(int(self._query(":OUTP:STAT?")))

    def set_output_enabled(self, enabled: bool) -> None:
        self._write(f":OUTP:STAT {enabled:d}")

    def get_voltage_level(self) -> float:
        return float(self._query(":SOUR:VOLT:LEV?"))

    def set_voltage_level(self, level: float) -> None:
        self._write(f":SOUR:VOLT:LEV {level:E}")

    def set_voltage_range(self, level: float) -> None:
        self._write(f":SOUR:VOLT:RANG {level:E}")

    def set_current_compliance_level(self, level: float) -> None: ...  # fixed to 1 mA

    def compliance_tripped(self) -> bool:
        return bool(int(self._query(":SOUR:CURR:LIM?")))

    def measure_i(self, timeout: float = 10.0, interval: float = 0.250) -> float:
        # Request operation complete
        self._write("*CLS")
        self._write_nowait("*OPC")
        # Initiate measurement
        self._write_nowait(":INIT")
        threshold = time.monotonic() + timeout
        interval = min(timeout, interval)
        while time.monotonic() < threshold:
            # Read event status
            if int(self._query("*ESR?")) & 0x1:
                try:
                    result = self._query(":FETC?")
                    return float(result.split(",")[0])
                except Exception as exc:
                    raise RuntimeError(f"Failed to fetch ELM reading: {exc}") from exc
            time.sleep(interval)
        raise RuntimeError(f"Electrometer reading timeout, exceeded {timeout:G} s")

    def measure_iv(self) -> tuple[float, float]:
        return self.measure_i(), float("nan")  # TODO

    def set_format_elements(self, elements: Iterable[str]) -> None:
        value = ",".join(elements)
        self._write(f":FORM:ELEM {value}")

    def set_sense_function(self, function: SenseFunction) -> None:
        self._write(f":SENS:FUNC '{function}'")

    def set_sense_current_range(self, level: float) -> None:
        self._write(f":SENS:CURR:RANG {level:E}")

    def set_sense_current_range_auto(self, enabled: bool) -> None:
        self._write(f":SENS:CURR:RANG:AUTO {enabled:d}")

    def set_sense_current_range_auto_lower_limit(self, limit: float) -> None:
        self._write(f":SENS:CURR:RANG:AUTO:LLIM {limit:E}")

    def set_sense_current_range_auto_upper_limit(self, limit: float) -> None:
        self._write(f":SENS:CURR:RANG:AUTO:ULIM {limit:E}")

    def set_sense_current_average_tcontrol(self, tcontrol: FilterType) -> None:
        self._write(f":SENS:CURR:AVER:TCON {tcontrol}")

    def set_sense_current_average_count(self, count: int) -> None:
        self._write(f":SENS:CURR:AVER:COUN {count:d}")

    def set_sense_current_average_state(self, state: bool) -> None:
        self._write(f":SENS:CURR:AVER:STAT {state:d}")

    def set_sense_current_nplcycles(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    def set_source_voltage_mconnect(self, enabled: bool) -> None:
        self._write(f":SOUR:VOLT:MCON {enabled:d}")

    def set_zero_check_enabled(self, enabled: bool) -> None:
        self._write(f":SYST:ZCH {enabled:d}")

    @handle_exception
    def _write(self, message: str) -> None:
        _ = self._resource.write(message)
        _ = self._resource.query("*OPC?")

    @handle_exception
    def _write_nowait(self, message: str) -> None:
        _ = self._resource.write(message)

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()
