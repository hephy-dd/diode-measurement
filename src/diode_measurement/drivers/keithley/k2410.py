from collections.abc import Mapping
from enum import StrEnum
from typing import Any

import msgspec
from comet.driver.keithley.k2410 import K2410

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K2410Adapter"]


class TerminalsLocation(StrEnum):
    FRONT = "FRON"
    REAR = "REAR"


class TControlMode(StrEnum):
    REP = "REP"
    MOV = "MOV"


class SourceFunction(StrEnum):
    VOLTAGE = "VOLT"
    CURRENT = "CURR"


class K2410Options(msgspec.Struct):
    beeper_state: bool = msgspec.field(
        name="beeper.state",
        default=False,
    )
    route_terminals: TerminalsLocation = msgspec.field(
        name="route.terminals",
        default=TerminalsLocation.FRONT,
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


class K2410Adapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._driver: K2410 = K2410(resource)
        self._format_element: str | None = None

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return parse_scpi_error(self._query(":SYST:ERR?"))

    def configure(self, options: Mapping[str, Any]) -> None:
        self._configure(msgspec.convert(options, type=K2410Options))

    def _configure(self, options: K2410Options) -> None:
        self.set_system_beeper_state(options.beeper_state)
        self.set_route_terminals(options.route_terminals)

        self.set_source_function(SourceFunction.VOLTAGE)

        self._write(":SENS:FUNC:CONC ON")  # enable concurrent measurements
        self._write(":SENS:FUNC:ON 'VOLT','CURR'")
        self._write(":FORM:ELEM VOLT,CURR")

        self.set_sense_average_tcontrol(options.filter_mode)
        self.set_sense_average_count(options.filter_count)
        self.set_sense_average_state(options.filter_enable)
        self.set_sense_current_nplc(options.nplc)

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
        self._write(f":SENS:CURR:PROT:LEV {level:.3E}")

    def compliance_tripped(self) -> bool:
        return self._query(":SENS:CURR:PROT:TRIP?") == "1"

    def measure_i(self) -> float:
        i, _ = self.measure_iv()
        return i

    def measure_v(self) -> float:
        _, v = self.measure_iv()
        return v

    def measure_iv(self) -> tuple[float, float]:
        if self._format_element != "VOLT,CURR":
            self._write(":FORM:ELEM VOLT,CURR")
            self._format_element = "VOLT,CURR"
        v, i = self._query(":READ?").split(",")[:2]
        return float(i), float(v)

    def set_system_beeper_state(self, state: bool) -> None:
        self._write(f":SYST:BEEP:STAT {state:d}")

    def set_route_terminals(self, location: TerminalsLocation) -> None:
        self._write(f":ROUT:TERM {location}")

    def set_source_function(self, function: SourceFunction) -> None:
        self._write(f":SOUR:FUNC {function}")

    def set_sense_average_tcontrol(self, mode: TControlMode) -> None:
        self._write(f":SENS:AVER:TCON {mode}")

    def set_sense_average_count(self, count: int) -> None:
        self._write(f":SENS:AVER:COUN {count:d}")

    def set_sense_average_state(self, state: bool) -> None:
        self._write(f":SENS:AVER:STAT {state:d}")

    def set_sense_current_nplc(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    @handle_exception
    def _write(self, message: str) -> None:
        _ = self._resource.write(message)
        _ = self._resource.query("*OPC?")

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()
