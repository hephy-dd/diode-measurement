import csv
import math

from typing import Any, Optional, TextIO

__all__ = ["Writer"]


def safe_format(value: Any, format_spec: Optional[str] = None) -> str:
    """Safe format any value, return `NAN` if format fails."""
    try:
        return format(value, format_spec or "")
    except Exception:
        return format(math.nan)


class Writer:
    delimiter: str = "\t"

    def __init__(self, fp: TextIO) -> None:
        self._fp: TextIO = fp
        self._writer = csv.writer(fp, delimiter=self.delimiter)
        self._current_table: Optional[str] = None
        self._timestamp_offset: float = 0.
        self.relative_timestamp: bool = False
        self.timestamp_format: str = ".6f"
        self.value_format: str = "+.3E"

    def get_timestamp(self, data: dict) -> Optional[float]:
        """Return absolute or relative timestamp based on configuration."""
        timestamp = data.get("timestamp")
        if timestamp is not None:
            if self.relative_timestamp:
                timestamp -= self._timestamp_offset
        return timestamp

    def reset_timestamp_offset(self, data: dict) -> None:
        """Reset timestamp offset for relative timestamps."""
        if self.relative_timestamp:
            self._timestamp_offset = data.get("timestamp", 0.)
        else:
            self._timestamp_offset = 0.

    def flush(self) -> None:
        self._fp.flush()

    def write_tag(self, key: str, value: Any) -> None:
        key = key.strip()
        value = format(value).strip()
        self._writer.writerow([f"{key}: {value}"])

    def write_table_header(self, columns: list) -> None:
        self._writer.writerow([])
        self._writer.writerow(columns)

    def write_table_row(self, columns: list) -> None:
        self._writer.writerow(columns)

    def write_meta(self, data: dict) -> None:
        self._current_table = None
        self.write_tag("sample", data.get("sample"))
        self.write_tag("measurement_type", data.get("measurement_type"))
        if "bias_voltage" in data:
            self.write_tag("bias_voltage[V]", safe_format(data.get("bias_voltage"), self.value_format))
        self.write_tag("voltage_begin[V]", safe_format(data.get("voltage_begin"), self.value_format))
        self.write_tag("voltage_end[V]", safe_format(data.get("voltage_end"), self.value_format))
        self.write_tag("voltage_step[V]", safe_format(data.get("voltage_step"), self.value_format))
        self.write_tag("waiting_time[s]", safe_format(data.get("waiting_time"), self.value_format))
        self.write_tag("current_compliance[A]", safe_format(data.get("current_compliance"), self.value_format))
        self.write_meta_lcr(data)
        self.flush()

    def write_meta_lcr(self, data: dict[str, Any]) -> None:
        lcr = data.get("roles", {}).get("lcr", {})
        if lcr.get("enabled"):
            lcr_options = lcr.get("options", {})
            # lcr.options.voltage
            voltage = lcr_options.get("voltage")
            if voltage is not None:
                self.write_tag("lcr_ac_amplitude[V]", safe_format(voltage, self.value_format))
            # lcr.options.frequency
            frequency = lcr_options.get("frequency")
            if frequency is not None:
                self.write_tag("lcr_ac_frequency[Hz]", safe_format(frequency, self.value_format))

    def write_iv_row(self, data: dict[str, Any]) -> None:
        if self._current_table != "iv":
            self._current_table = "iv"
            self.write_table_header([
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "i_elm[A]",
                "i_elm2[A]",
                "temperature[degC]",
            ])
            self.reset_timestamp_offset(data)
        self.write_table_row([
            safe_format(self.get_timestamp(data), self.timestamp_format),
            safe_format(data.get("voltage"), self.value_format),
            safe_format(data.get("v_smu"), self.value_format),
            safe_format(data.get("i_smu"), self.value_format),
            safe_format(data.get("i_elm"), self.value_format),
            safe_format(data.get("i_elm2"), self.value_format),
            safe_format(data.get("t_dmm"), self.value_format),
        ])
        self.flush()

    def write_iv_bias_row(self, data: dict[str, Any]) -> None:
        if self._current_table != "iv":
            self._current_table = "iv"
            self.write_table_header([
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "v_smu2[V]",
                "i_smu2[A]",
                "i_elm[A]",
                "i_elm2[A]",
                "temperature[degC]",
            ])
            self.reset_timestamp_offset(data)
        self.write_table_row([
            safe_format(self.get_timestamp(data), self.timestamp_format),
            safe_format(data.get("voltage"), self.value_format),
            safe_format(data.get("v_smu"), self.value_format),
            safe_format(data.get("i_smu"), self.value_format),
            safe_format(data.get("v_smu2"), self.value_format),
            safe_format(data.get("i_smu2"), self.value_format),
            safe_format(data.get("i_elm"), self.value_format),
            safe_format(data.get("i_elm2"), self.value_format),
            safe_format(data.get("t_dmm"), self.value_format),
        ])
        self.flush()

    def write_it_row(self, data: dict[str, Any]) -> None:
        if self._current_table != "it":
            self._current_table = "it"
            self.write_table_header([
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "i_elm[A]",
                "i_elm2[A]",
                "temperature[degC]",
            ])
            self.reset_timestamp_offset(data)
        self.write_table_row([
            safe_format(self.get_timestamp(data), self.timestamp_format),
            safe_format(data.get("voltage"), self.value_format),
            safe_format(data.get("v_smu"), self.value_format),
            safe_format(data.get("i_smu"), self.value_format),
            safe_format(data.get("i_elm"), self.value_format),
            safe_format(data.get("i_elm2"), self.value_format),
            safe_format(data.get("t_dmm"), self.value_format),
        ])
        self.flush()

    def write_it_bias_row(self, data: dict[str, Any]) -> None:
        if self._current_table != "it":
            self._current_table = "it"
            self.write_table_header([
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "v_smu2[V]",
                "i_smu2[A]",
                "i_elm[A]",
                "i_elm2[A]",
                "temperature[degC]"
            ])
            self.reset_timestamp_offset(data)
        self.write_table_row([
            safe_format(self.get_timestamp(data), self.timestamp_format),
            safe_format(data.get("voltage"), self.value_format),
            safe_format(data.get("v_smu"), self.value_format),
            safe_format(data.get("i_smu"), self.value_format),
            safe_format(data.get("v_smu2"), self.value_format),
            safe_format(data.get("i_smu2"), self.value_format),
            safe_format(data.get("i_elm"), self.value_format),
            safe_format(data.get("i_elm2"), self.value_format),
            safe_format(data.get("t_dmm"), self.value_format),
        ])
        self.flush()

    def write_cv_row(self, data: dict[str, Any]) -> None:
        if self._current_table != "cv":
            self._current_table = "cv"
            self.write_table_header([
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "c_lcr[F]",
                "c2_lcr[1/F^2]",
                "r_lcr[Ohm]",
                "temperature[degC]"
            ])
            self.reset_timestamp_offset(data)
        self.write_table_row([
            safe_format(self.get_timestamp(data), self.timestamp_format),
            safe_format(data.get("voltage"), self.value_format),
            safe_format(data.get("v_smu"), self.value_format),
            safe_format(data.get("i_smu"), self.value_format),
            safe_format(data.get("c_lcr"), self.value_format),
            safe_format(data.get("c2_lcr"), self.value_format),
            safe_format(data.get("r_lcr"), self.value_format),
            safe_format(data.get("t_dmm"), self.value_format)
        ])
        self.flush()
