from typing import Optional, Tuple

from .driver import SourceMeter, handle_exception

__all__ = ["K2400"]


class K2400(SourceMeter):

    def __init__(self, resource) -> None:
        super().__init__(resource)
        self._format_element: Optional[str] = None

    def identity(self) -> str:
        return self._query("*IDN?")

    def reset(self) -> None:
        self._write("*RST")

    def clear(self) -> None:
        self._write("*CLS")

    def next_error(self) -> Tuple[int, str]:
        result = self._query(":SYST:ERR?")
        try:
            code, message = result.split(",")
            code = int(code)
            message = message.strip().strip('"')
            return code, message
        except Exception as exc:
            raise RuntimeError(f"Failed to parse error message: {result!r}") from exc

    def configure(self, options: dict) -> None:
        beeper_state = options.get("beeper.state", False)
        self.set_system_beeper_state(beeper_state)

        route_terminals = options.get("route.terminals", "FRON")
        self.set_route_terminals(route_terminals)

        self.set_source_function("VOLT")

        self._write(":SENS:FUNC:CONC ON")  # enable concurrent measurements
        self._write(":SENS:FUNC:ON 'VOLT','CURR'")
        self._write(":FORM:ELEM VOLT,CURR")

        filter_mode = options.get("filter.mode", "MOV")
        self.set_sense_average_tcontrol(filter_mode)

        filter_count = options.get("filter.count", 10)
        self.set_sense_average_count(filter_count)

        filter_enable = options.get("filter.enable", False)
        self.set_sense_average_state(filter_enable)

        nplc = options.get("nplc", 1.0)
        self.set_sense_current_nplc(nplc)

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

    def measure_iv(self) -> Tuple[float, float]:
        if self._format_element != "VOLT,CURR":
            self._write(":FORM:ELEM VOLT,CURR")
            self._format_element = "VOLT,CURR"
        v, i = self._query(":READ?").split(",")[:2]
        return float(i), float(v)

    def set_system_beeper_state(self, state: bool) -> None:
        self._write(f":SYST:BEEP:STAT {state:d}")

    def set_route_terminals(self, terminal: str) -> None:
        self._write(f":ROUT:TERM {terminal}")

    def set_source_function(self, function: str) -> None:
        self._write(f":SOUR:FUNC {function}")

    def set_sense_average_tcontrol(self, tcontrol: str) -> None:
        self._write(f":SENS:AVER:TCON {tcontrol}")

    def set_sense_average_count(self, count: int) -> None:
        self._write(f":SENS:AVER:COUN {count:d}")

    def set_sense_average_state(self, state: bool) -> None:
        self._write(f":SENS:AVER:STAT {state:d}")

    def set_sense_current_nplc(self, nplc: float) -> None:
        self._write(f":SENS:CURR:NPLC {nplc:E}")

    @handle_exception
    def _write(self, message):
        self.resource.write(message)
        self.resource.query("*OPC?")

    @handle_exception
    def _query(self, message):
        return self.resource.query(message).strip()
