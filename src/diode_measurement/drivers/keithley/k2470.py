from collections.abc import Mapping
from enum import StrEnum

import msgspec
from comet.driver.keithley.k2470 import K2470

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K2470Adapter"]


class RouteTerminals(StrEnum):
    FRONT = "FRON"
    REAR = "REAR"


class SourceFunction(StrEnum):
    CURRENT = "CURR"
    VOLTAGE = "VOLT"


class SenseFunction(StrEnum):
    CURRENT = "CURR"
    RESISTANCE = "RES"
    VOLTAGE = "VOLT"


class FilterType(StrEnum):
    MOVING = "MOV"
    REPEAT = "REP"


class BreakdownProtection(StrEnum):
    AUTO = "AUTO"
    OFF = "OFF"
    ON = "ON"


class K2470Config(msgspec.Struct, frozen=True):
    route_terminals: RouteTerminals = msgspec.field(
        default=RouteTerminals.FRONT,
        name="route.terminals",
    )
    sense_range: float = msgspec.field(
        default=1e-8,
        name="sense.range",
    )
    sense_auto_range_lower_limit: float = msgspec.field(
        default=1e-8,
        name="sense.auto_range.lower_limit",
    )
    sense_auto_range: bool = msgspec.field(
        default=True,
        name="sense.auto_range",
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
    breakdown_protection: BreakdownProtection = msgspec.field(
        default=BreakdownProtection.AUTO,
        name="system.breakdown.protection",
    )
    source_delay_auto: bool = msgspec.field(
        default=True,
        name="source.delay.auto",
    )
    sense_auto_zero: bool = msgspec.field(
        default=True,
        name="sense.azero",
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

    def configure(self, options: Mapping[str, object]) -> None:
        config = msgspec.convert(options, type=K2470Config)

        self.set_route_terminals(config.route_terminals)

        self.set_source_function(SourceFunction.VOLTAGE)
        self.set_sense_function(SenseFunction.CURRENT)

        self.set_sense_current_range(config.sense_range)
        self.set_sense_current_range_auto_lower_limit(
            config.sense_auto_range_lower_limit
        )
        self.set_sense_current_range_auto(config.sense_auto_range)

        self.set_sense_current_average_tcontrol(config.filter_type)
        self.set_sense_current_average_count(config.filter_count)
        self.set_sense_current_average_enable(config.filter_enable)

        self.set_sense_current_nplc(config.nplc)
        self.set_system_breakdown_protection(config.breakdown_protection)
        self.set_source_voltage_delay_auto(config.source_delay_auto)
        self.set_sense_current_azero(config.sense_auto_zero)

    def get_output_enabled(self) -> bool:
        return self._query(":OUTP:STAT?") == "1"

    def set_output_enabled(self, enabled: bool) -> None:
        value = "1" if enabled else "0"
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
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Unexpected instrument response for READ?: {result!r}"
            ) from exc

    def set_route_terminals(self, terminals: RouteTerminals) -> None:
        self._write(f":ROUT:TERM {terminals}")

    def set_source_function(self, function: SourceFunction) -> None:
        self._write(f":SOUR:FUNC {function}")

    def set_sense_function(self, function: SenseFunction) -> None:
        self._write(f':SENS:FUNC "{function}"')

    def set_sense_current_range(self, level: float) -> None:
        self._write(f":SENS:CURR:RANG {level:E}")

    def set_sense_current_range_auto(self, enabled: bool) -> None:
        self._write(f":SENS:CURR:RANG:AUTO {enabled:d}")

    def set_sense_current_range_auto_lower_limit(self, limit: float) -> None:
        self._write(f":SENS:CURR:RANG:AUTO:LLIM {limit:E}")

    def set_sense_current_average_tcontrol(self, filter_type: FilterType) -> None:
        self._write(f":SENS:CURR:AVER:TCON {filter_type}")

    def set_sense_current_average_count(self, count: int) -> None:
        self._write(f":SENS:CURR:AVER:COUN {count:d}")

    def set_sense_current_average_enable(self, state: bool) -> None:
        self._write(f":SENS:CURR:AVER:STAT {state:d}")

    def set_sense_current_nplc(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    def set_system_breakdown_protection(self, value: BreakdownProtection) -> None:
        self._write(f":SYST:BRE:PROT {value}")

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
