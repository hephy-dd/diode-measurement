import time
from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Any

import msgspec
from comet.driver.keithley.k6514 import K6514

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K6514Adapter"]


class SenseFunction(StrEnum):
    VOLTAGE = "VOLT"
    CURRENT = "CURR"
    RESISTANCE = "RES"
    CHARGE = "CHAR"


class TControlMode(StrEnum):
    MOV = "MOV"
    REP = "REP"


class K6514Options(msgspec.Struct):
    sense_range: float = msgspec.field(
        name="sense.range",
        default=200e-6,
    )
    sense_auto_range_lower_limit: float = msgspec.field(
        name="sense.auto_range.lower_limit",
        default=2e-12,
    )
    sense_auto_range_upper_limit: float = msgspec.field(
        name="sense.auto_range.upper_limit",
        default=20e-3,
    )
    sense_auto_range: bool = msgspec.field(
        name="sense.auto_range",
        default=True,
    )
    filter_mode: TControlMode = msgspec.field(
        name="filter.mode",
        default=TControlMode.REP,
    )
    filter_count: int = msgspec.field(
        name="filter.count",
        default=10,
    )
    filter_enable: bool = msgspec.field(
        name="filter.enable",
        default=False,
    )
    nplc: float = msgspec.field(
        name="nplc",
        default=5.0,
    )


class K6514Adapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._driver: K6514 = K6514(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return parse_scpi_error(self._query(":SYST:ERR?"))

    def configure(self, options: Mapping[str, Any]) -> None:
        self._configure(msgspec.convert(options, type=K6514Options))

    def _configure(self, options: K6514Options) -> None:
        self.set_format_elements(["READ"])
        self.set_sense_function(SenseFunction.CURRENT)

        self.set_sense_current_range(options.sense_range)
        self.set_sense_current_range_auto_lower_limit(
            options.sense_auto_range_lower_limit
        )
        self.set_sense_current_range_auto_upper_limit(
            options.sense_auto_range_upper_limit
        )
        self.set_sense_current_range_auto(options.sense_auto_range)

        self.set_sense_average_tcontrol(options.filter_mode)
        self.set_sense_average_count(options.filter_count)
        self.set_sense_average_state(options.filter_enable)

        self.set_sense_current_nplcycles(options.nplc)

    def get_output_enabled(self) -> bool:
        return False

    def set_output_enabled(self, enabled: bool) -> None: ...

    def get_voltage_level(self) -> float:
        return 0

    def set_voltage_level(self, level: float) -> None: ...

    def set_voltage_range(self, level: float) -> None: ...

    def set_current_compliance_level(self, level: float) -> None: ...  # not supported

    def compliance_tripped(self) -> bool:
        return False

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

    def set_sense_average_tcontrol(self, mode: TControlMode) -> None:
        self._write(f":SENS:AVER:TCON {mode}")

    def set_sense_average_count(self, count: int) -> None:
        self._write(f":SENS:AVER:COUN {count:d}")

    def set_sense_average_state(self, state: bool) -> None:
        self._write(f":SENS:AVER:STAT {state:d}")

    def set_sense_current_nplcycles(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    def set_zero_check_enabled(self, enabled: bool) -> None:
        self._write(f":SYST:ZCH {enabled:d}")

    @handle_exception
    def _write(self, message: str) -> None:
        _ = self._resource.write(message)
        _ = self._resource.query("*OPC?")

    @handle_exception
    def _write_nowait(self, message: str):
        _ = self._resource.write(message)

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()
