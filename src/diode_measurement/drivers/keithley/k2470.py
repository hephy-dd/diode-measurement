from collections.abc import Mapping
from typing import Any

from comet.driver.keithley.k2470 import K2470

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K2470Adapter"]


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
        route_terminals = options.get("route.terminals", "FRON")
        self.set_route_terminals(route_terminals)

        self.set_source_function("VOLT")

        self.set_sense_function("CURR")

        sense_range = options.get("sense.range", 1e-08)
        self.set_sense_current_range(sense_range)

        sense_auto_range_lower_limit = options.get(
            "sense.auto_range.lower_limit", 1e-08
        )
        self.set_sense_current_range_auto_lower_limit(sense_auto_range_lower_limit)

        sense_auto_range = options.get("sense.auto_range", True)
        self.set_sense_current_range_auto(sense_auto_range)

        filter_mode = options.get("filter.mode", "MOV")
        self.set_sense_current_average_tcontrol(filter_mode)

        filter_count = options.get("filter.count", 10)
        self.set_sense_current_average_count(filter_count)

        filter_enable = options.get("filter.enable", False)
        self.set_sense_current_average_enable(filter_enable)

        nplc = options.get("nplc", 1.0)
        self.set_sense_current_nplc(nplc)

        system_breakdown_protection = options.get("system.breakdown.protection", "AUTO")
        self.set_system_breakdown_protection(system_breakdown_protection)

        source_delay_auto = options.get("source.delay.auto", True)
        self.set_source_voltage_delay_auto(source_delay_auto)

        sense_azero = options.get("sense.azero", True)
        self.set_sense_current_azero(sense_azero)

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

    def set_route_terminals(self, terminal: str) -> None:
        self._write(f":ROUT:TERM {terminal}")

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

    def set_sense_current_average_tcontrol(self, tcontrol: str) -> None:
        self._write(f":SENS:CURR:AVER:TCON {tcontrol}")

    def set_sense_current_average_count(self, count: int) -> None:
        self._write(f":SENS:CURR:AVER:COUN {count:d}")

    def set_sense_current_average_enable(self, state: bool) -> None:
        self._write(f":SENS:CURR:AVER:STAT {state:d}")

    def set_sense_current_nplc(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    def set_system_breakdown_protection(self, value: str) -> None:
        if value not in ("AUTO", "OFF", "ON"):
            raise ValueError(
                "Breakdown protection must be one of: 'AUTO', 'OFF' or 'ON'"
            )
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
