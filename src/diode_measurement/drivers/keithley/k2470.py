from collections.abc import Mapping
from enum import StrEnum
from typing import Any

import msgspec
from comet.driver.keithley.k2470 import K2470

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K2470Adapter"]


class TerminalsLocation(StrEnum):
    FRONT = "FRON"
    REAR = "REAR"


class TControlMode(StrEnum):
    REP = "REP"
    MOV = "MOV"


class ProtectionSetting(StrEnum):
    AUTO = "AUTO"
    OFF = "OFF"
    ON = "ON"


class K2470Options(msgspec.Struct):
    route_terminals: TerminalsLocation = msgspec.field(
        name="route.terminals",
        default=TerminalsLocation.FRONT,
    )
    sense_range: float = msgspec.field(
        name="sense.range",
        default=1e-08,
    )
    sense_auto_range_lower_limit: float = msgspec.field(
        name="sense.auto_range.lower_limit",
        default=1e-08,
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
        default=1.0,
    )
    system_breakdown_protection: ProtectionSetting = msgspec.field(
        name="system.breakdown.protection",
        default=ProtectionSetting.AUTO,
    )
    source_delay_auto: bool = msgspec.field(
        name="source.delay.auto",
        default=True,
    )
    sense_azero: bool = msgspec.field(
        name="sense.azero",
        default=True,
    )


class K2470Adapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._driver: K2470 = K2470(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return parse_scpi_error(self._query(":SYST:ERR?"))

    def configure(self, options: Mapping[str, Any]) -> None:
        self._configure(msgspec.convert(options, type=K2470Options))

    def _configure(self, options: K2470Options) -> None:
        self.set_route_terminals(options.route_terminals)

        self.set_source_function("VOLT")
        self.set_sense_function("CURR")

        self.set_sense_current_range(options.sense_range)
        self.set_sense_current_range_auto_lower_limit(
            options.sense_auto_range_lower_limit
        )
        self.set_sense_current_range_auto(options.sense_auto_range)

        self.set_sense_current_average_tcontrol(options.filter_mode)
        self.set_sense_current_average_count(options.filter_count)
        self.set_sense_current_average_enable(options.filter_enable)

        self.set_sense_current_nplc(options.nplc)

        self.set_system_breakdown_protection(options.system_breakdown_protection)
        self.set_source_voltage_delay_auto(options.source_delay_auto)
        self.set_sense_current_azero(options.sense_azero)

    def get_output_enabled(self) -> bool:
        return self._query(":OUTP:STAT?") == "1"

    def set_output_enabled(self, enabled: bool) -> None:
        value = {False: "0", True: "1"}[enabled]
        self._write(f":OUTP:STAT {value}")

    def get_voltage_level(self) -> float:
        return float(self._query(":SOUR:VOLT:LEV?"))

    def set_voltage_level(self, level: float) -> None:
        self._write(f":SOUR:VOLT:LEV {level:.3E}")

    def set_voltage_range(self, level: float) -> None:
        self._write(f":SOUR:VOLT:RANG {level:.3E}")

    def set_current_compliance_level(self, level: float) -> None:
        self._write(f":SOUR:VOLT:ILIM:LEV {level:.3E}")

    def compliance_tripped(self) -> bool:
        return self._query(":SOUR:VOLT:ILIM:LEV:TRIP?") == "1"

    def measure_i(self) -> float:
        i, _ = self.measure_iv()
        return i

    def measure_v(self) -> float:
        _, v = self.measure_iv()
        return v

    def measure_iv(self) -> tuple[float, float]:
        """Measure I and V at once using READ?."""
        result = self._query(':READ? "defbuffer1", SOUR, READ')
        try:
            source, reading = result.split(",", 1)
            return float(reading), float(source)
        except Exception as exc:
            raise ValueError(
                f"Unexpected instrument response for READ?: {result!r}"
            ) from exc

    def set_route_terminals(self, location: TerminalsLocation) -> None:
        self._write(f":ROUT:TERM {location}")

    def set_source_function(self, function: str) -> None:
        self._write(f":SOUR:FUNC {function}")

    def set_sense_function(self, function: str) -> None:
        if function not in {"CURR", "RES", "VOLT"}:
            raise ValueError(f"Invalid sense function: {function}")
        self._write(f':SENS:FUNC "{function}"')

    def set_sense_current_range(self, level: float) -> None:
        self._write(f":SENS:CURR:RANG {level:E}")

    def set_sense_current_range_auto(self, enabled: bool) -> None:
        self._write(f":SENS:CURR:RANG:AUTO {enabled:d}")

    def set_sense_current_range_auto_lower_limit(self, limit: float) -> None:
        self._write(f":SENS:CURR:RANG:AUTO:LLIM {limit:E}")

    def set_sense_current_average_tcontrol(self, mode: TControlMode) -> None:
        self._write(f":SENS:CURR:AVER:TCON {mode}")

    def set_sense_current_average_count(self, count: int) -> None:
        self._write(f":SENS:CURR:AVER:COUN {count:d}")

    def set_sense_current_average_enable(self, state: bool) -> None:
        self._write(f":SENS:CURR:AVER:STAT {state:d}")

    def set_sense_current_nplc(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    def set_system_breakdown_protection(self, setting: ProtectionSetting) -> None:
        self._write(f":SYST:BRE:PROT {setting}")

    def is_interlock(self) -> bool:
        """Return status of the interlock."""
        return bool(int(self._query(":OUTP:INT:TRIP?")))

    def set_source_voltage_delay_auto(self, enabled: bool) -> None:
        self._write(f":SOUR:VOLT:DEL:AUTO {enabled:d}")

    def set_sense_current_azero(self, enabled: bool) -> None:
        self._write(f":SENS:CURR:AZER {enabled:d}")

    @handle_exception
    def _write(self, message: str) -> None:
        _ = self._resource.write(message)
        _ = self._resource.query("*OPC?")

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()
