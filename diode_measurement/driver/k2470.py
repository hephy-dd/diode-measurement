from typing import Optional

from .driver import SourceMeter, InstrumentError, handle_exception

__all__ = ["K2470"]


class K2470(SourceMeter):
    def identify(self) -> str:
        return self._query("*IDN?")

    def reset(self) -> None:
        self._write("*RST")

    def clear(self) -> None:
        self._write("*CLS")

    def next_error(self) -> Optional[InstrumentError]:
        code, message = self._query(":SYST:ERR?").split(",")
        code = int(code)
        if code == 0:
            return None
        message = message.strip().strip('"')
        return InstrumentError(code, message)

    def configure(self, options: dict) -> None:
        route_terminals = options.get("route.terminals", "FRON")
        self.set_route_terminals(route_terminals)

        self.set_source_function("VOLT")

        self.set_sense_function("CURR")

        filter_mode = options.get("filter.mode", "MOV")
        self.set_sense_current_average_tcontrol(filter_mode)

        filter_count = options.get("filter.count", 10)
        self.set_sense_current_average_count(filter_count)

        filter_enable = options.get("filter.enable", False)
        self.set_sense_current_average_enable(filter_enable)

        nplc = options.get("nplc", 1.0)
        self.set_sense_current_nplc(nplc)

        system_breakdown_protection = options.get("system.breakdown.protection", False)
        self.set_system_breakdown_protection(system_breakdown_protection)

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
        self._write(":TRAC:TRIG \"defbuffer1\"")
        result = self._query(":TRAC:DATA? 1, 1, \"defbuffer1\", SOUR, READ")
        try:
            source, reading = result.split(",", 1)
            return float(reading), float(source)
        except Exception as exc:
            raise ValueError(f"Unexpected instrument response: {result!r}") from exc

    def set_route_terminals(self, terminal: str) -> None:
        self._write(f":ROUT:TERM {terminal}")

    def set_source_function(self, function: str) -> None:
        self._write(f":SOUR:FUNC {function}")

    def set_sense_function(self, function: str) -> None:
        if function not in {"CURR", "RES", "VOLT"}:
            raise ValueError(f"Invalid sense function: {function}")
        self._write(f":SENS:FUNC \"{function}\"")

    def set_sense_current_average_tcontrol(self, tcontrol: str) -> None:
        self._write(f":SENS:CURR:AVER:TCON {tcontrol}")

    def set_sense_current_average_count(self, count: int) -> None:
        self._write(f":SENS:CURR:AVER:COUN {count:d}")

    def set_sense_current_average_enable(self, state: bool) -> None:
        self._write(f":SENS:CURR:AVER:STAT {state:d}")

    def set_sense_current_nplc(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    def set_system_breakdown_protection(self, state: bool) -> None:
        value = "ON" if state else "OFF"  # 0 and 1 not supported?
        self._write(f":SYST:BRE:PROT {value}")

    def is_interlock(self) -> bool:
        """Return status of the interlock."""
        return bool(int(self._query(":OUTP:INT:TRIP?")))

    @handle_exception
    def _write(self, message):
        self.resource.write(message)
        self.resource.query("*OPC?")

    @handle_exception
    def _query(self, message):
        return self.resource.query(message).strip()
