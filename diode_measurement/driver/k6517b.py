import time
from typing import List, Tuple

from .driver import Electrometer, handle_exception

__all__ = ["K6517B"]


class K6517B(Electrometer):

    def identity(self) -> str:
        return self._query("*IDN?").strip()

    def reset(self) -> None:
        self._write("*RST")

    def clear(self) -> None:
        self._write("*CLS")

    def next_error(self) -> Tuple[int, str]:
        code, message = self._query(":SYST:ERR?").split(",")
        code = int(code)
        message = message.strip().strip('"')
        return code, message

    def configure(self, options: dict) -> None:
        self.set_format_elements(["READ"])
        self.set_sense_function("CURR")

        sense_range = options.get("sense.range", 20e-3)
        self.set_sense_current_range(sense_range)

        sense_auto_range_lower_limit = options.get("sense.auto_range.lower_limit", 2e-12)
        self.set_sense_current_range_auto_lower_limit(sense_auto_range_lower_limit)

        sense_auto_range_upper_limit = options.get("sense.auto_range.upper_limit", 20e-3)
        self.set_sense_current_range_auto_upper_limit(sense_auto_range_upper_limit)

        sense_auto_range = options.get("sense.auto_range", True)
        self.set_sense_current_range_auto(sense_auto_range)

        source_meter_connect = options.get("source.meter_connect", False)
        self.set_source_voltage_mconnect(source_meter_connect)

        filter_mode = options.get("filter.mode", "MOV")
        self.set_sense_current_average_tcontrol(filter_mode)

        filter_count = options.get("filter.count", 10)
        self.set_sense_current_average_count(filter_count)

        filter_enable = options.get("filter.enable", False)
        self.set_sense_current_average_state(filter_enable)

        nplc = options.get("nplc", 1.0)
        self.set_sense_current_nplcycles(nplc)

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

    def set_current_compliance_level(self, level: float) -> None:
        ...  # fixed to 1 mA

    def compliance_tripped(self) -> bool:
        return bool(int(self._query(":SOUR:CURR:LIM?")))

    def measure_i(self, timeout=10.0, interval=0.250):
        # Request operation complete
        self._write("*CLS")
        self._write_nowait("*OPC")
        # Initiate measurement
        self._write_nowait(":INIT")
        threshold = time.time() + timeout
        interval = min(timeout, interval)
        while time.time() < threshold:
            # Read event status
            if int(self._query("*ESR?")) & 0x1:
                try:
                    result = self._query(":FETC?")
                    return float(result.split(",")[0])
                except Exception as exc:
                    raise RuntimeError(f"Failed to fetch ELM reading: {exc}") from exc
            time.sleep(interval)
        raise RuntimeError(f"Electrometer reading timeout, exceeded {timeout:G} s")

    def measure_iv(self) -> Tuple[float, float]:
        return self.measure_i(), float("nan")  # TODO

    def set_format_elements(self, elements: List[str]) -> None:
        value = ",".join(elements)
        self._write(f":FORM:ELEM {value}")

    def set_sense_function(self, function: str) -> None:
        self._write(f":SENS:FUNC '{function}'")

    def set_sense_current_range(self, level: float) -> None:
        self._write(f":SENS:CURR:RANG {level:E}")

    def set_sense_current_range_auto(self, enabled: bool) -> None:
        self._write(f":SENS:CURR:RANG:AUTO {enabled:d}")

    def set_sense_current_range_auto_lower_limit(self, limit: float) -> None:
        self._write(f":SENS:CURR:RANG:AUTO:LLIM {limit:E}")

    def set_sense_current_range_auto_upper_limit(self, limit: float) -> None:
        self._write(f":SENS:CURR:RANG:AUTO:ULIM {limit:E}")

    def set_sense_current_average_tcontrol(self, tcontrol: str) -> None:
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
    def _write(self, message):
        self.resource.write(message)
        self.resource.query("*OPC?")

    @handle_exception
    def _write_nowait(self, message):
        self.resource.write(message)

    @handle_exception
    def _query(self, message):
        return self.resource.query(message).strip()
