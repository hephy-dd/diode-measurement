import csv
import math
from collections.abc import Iterable
from typing import Any, TextIO

from .core.role import Role
from .state import CVReading, IVReading, Reading, State

__all__ = ["Writer"]


def safe_format(value: Any, format_spec: str | None = None) -> str:
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
        self._current_table: str | None = None
        self._timestamp_offset: float = 0.0
        self.relative_timestamp: bool = False
        self.timestamp_format: str = ".6f"
        self.value_format: str = "+.3E"
        self.optional_roles: list[Role] = []

    def get_timestamp(self, timestamp: float) -> float:
        """Return absolute or relative timestamp based on configuration."""
        if timestamp is not None and self.relative_timestamp:
            timestamp -= self._timestamp_offset
        return timestamp

    def reset_timestamp_offset(self, timestamp: float = 0.0) -> None:
        """Reset timestamp offset for relative timestamps."""
        if self.relative_timestamp:
            self._timestamp_offset = timestamp
        else:
            self._timestamp_offset = 0.0

    def dmm_header(self) -> list[str]:
        header = []
        if Role.DMM in self.optional_roles:
            header.extend(
                [
                    "dmm_temperature[degC]",
                ]
            )
        return header

    def dmm_data(self, reading: Reading) -> list[str]:
        row = []
        if Role.DMM in self.optional_roles:
            row.extend(
                [
                    safe_format(reading.t_dmm, self.value_format),
                ]
            )
        return row

    def tcu_header(self) -> list[str]:
        header = []
        if Role.TCU in self.optional_roles:
            header.extend(
                [
                    "tcu_temperature[degC]",
                    "tcu_humidity[%rH]",
                ]
            )
        return header

    def tcu_data(self, reading: Reading) -> list[str]:
        row = []
        if Role.TCU in self.optional_roles:
            row.extend(
                [
                    safe_format(reading.tcu_temperature, self.value_format),
                    safe_format(reading.tcu_humidity, self.value_format),
                ]
            )
        return row

    def flush(self) -> None:
        self._fp.flush()

    def write_tag(self, key: str, value: Any) -> None:
        key = key.strip()
        value = format(value).strip()
        self._writer.writerow([f"{key}: {value}"])

    def write_table_header(self, columns: Iterable[str]) -> None:
        self._writer.writerow([])
        self._writer.writerow(columns)

    def write_table_row(self, columns: Iterable[str]) -> None:
        self._writer.writerow(columns)

    def write_meta(self, state: State) -> None:
        self._current_table = None
        self.write_tag("sample", state.sample)
        self.write_tag("measurement_type", state.measurement_type)
        if state.bias_source_role is not None:
            self.write_tag(
                "bias_voltage[V]", safe_format(state.bias_voltage, self.value_format)
            )
        self.write_tag(
            "voltage_begin[V]", safe_format(state.voltage_begin, self.value_format)
        )
        self.write_tag(
            "voltage_end[V]", safe_format(state.voltage_end, self.value_format)
        )
        self.write_tag(
            "voltage_step[V]", safe_format(state.voltage_step, self.value_format)
        )
        self.write_tag(
            "waiting_time[s]", safe_format(state.waiting_time, self.value_format)
        )
        self.write_tag(
            "current_compliance[A]",
            safe_format(state.current_compliance, self.value_format),
        )
        self.write_meta_lcr(state)
        self.flush()

    def write_meta_lcr(self, state: State) -> None:
        lcr = state.roles.get(Role.LCR)
        if lcr and lcr.enabled:
            lcr_options = lcr.options
            # lcr.options.voltage
            voltage = lcr_options.get("voltage")
            if voltage is not None:
                self.write_tag(
                    "lcr_ac_amplitude[V]", safe_format(voltage, self.value_format)
                )
            # lcr.options.frequency
            frequency = lcr_options.get("frequency")
            if frequency is not None:
                self.write_tag(
                    "lcr_ac_frequency[Hz]", safe_format(frequency, self.value_format)
                )

    def write_iv_row(self, reading: IVReading) -> None:
        timestamp_utc = reading.timestamp
        if self._current_table != "iv":
            self._current_table = "iv"
            header = (
                [
                    "timestamp[s]",
                    "voltage[V]",
                    "v_smu[V]",
                    "i_smu[A]",
                    "i_elm[A]",
                    "i_elm2[A]",
                ]
                + self.dmm_header()
                + self.tcu_header()
            )
            self.write_table_header(header)
            self.reset_timestamp_offset(timestamp_utc)
        row = (
            [
                safe_format(self.get_timestamp(timestamp_utc), self.timestamp_format),
                safe_format(reading.voltage, self.value_format),
                safe_format(reading.v_smu, self.value_format),
                safe_format(reading.i_smu, self.value_format),
                safe_format(reading.i_elm, self.value_format),
                safe_format(reading.i_elm2, self.value_format),
            ]
            + self.dmm_data(reading)
            + self.tcu_data(reading)
        )
        self.write_table_row(row)
        self.flush()

    def write_iv_bias_row(self, reading: IVReading) -> None:
        timestamp_utc = reading.timestamp
        if self._current_table != "iv":
            self._current_table = "iv"
            header = (
                [
                    "timestamp[s]",
                    "voltage[V]",
                    "v_smu[V]",
                    "i_smu[A]",
                    "v_smu2[V]",
                    "i_smu2[A]",
                    "i_elm[A]",
                    "i_elm2[A]",
                ]
                + self.dmm_header()
                + self.tcu_header()
            )
            self.write_table_header(header)
            self.reset_timestamp_offset(timestamp_utc)
        row = (
            [
                safe_format(self.get_timestamp(timestamp_utc), self.timestamp_format),
                safe_format(reading.voltage, self.value_format),
                safe_format(reading.v_smu, self.value_format),
                safe_format(reading.i_smu, self.value_format),
                safe_format(reading.v_smu2, self.value_format),
                safe_format(reading.i_smu2, self.value_format),
                safe_format(reading.i_elm, self.value_format),
                safe_format(reading.i_elm2, self.value_format),
            ]
            + self.dmm_data(reading)
            + self.tcu_data(reading)
        )
        self.write_table_row(row)
        self.flush()

    def write_it_row(self, reading: IVReading) -> None:
        timestamp_utc = reading.timestamp
        if self._current_table != "it":
            self._current_table = "it"
            header = (
                [
                    "timestamp[s]",
                    "voltage[V]",
                    "v_smu[V]",
                    "i_smu[A]",
                    "i_elm[A]",
                    "i_elm2[A]",
                ]
                + self.dmm_header()
                + self.tcu_header()
            )
            self.write_table_header(header)
            self.reset_timestamp_offset(timestamp_utc)
        row = (
            [
                safe_format(self.get_timestamp(timestamp_utc), self.timestamp_format),
                safe_format(reading.voltage, self.value_format),
                safe_format(reading.v_smu, self.value_format),
                safe_format(reading.i_smu, self.value_format),
                safe_format(reading.i_elm, self.value_format),
                safe_format(reading.i_elm2, self.value_format),
            ]
            + self.dmm_data(reading)
            + self.tcu_data(reading)
        )
        self.write_table_row(row)
        self.flush()

    def write_it_bias_row(self, reading: IVReading) -> None:
        timestamp_utc = reading.timestamp
        if self._current_table != "it":
            self._current_table = "it"
            header = (
                [
                    "timestamp[s]",
                    "voltage[V]",
                    "v_smu[V]",
                    "i_smu[A]",
                    "v_smu2[V]",
                    "i_smu2[A]",
                    "i_elm[A]",
                    "i_elm2[A]",
                ]
                + self.dmm_header()
                + self.tcu_header()
            )
            self.write_table_header(header)
            self.reset_timestamp_offset(timestamp_utc)
        row = (
            [
                safe_format(self.get_timestamp(timestamp_utc), self.timestamp_format),
                safe_format(reading.voltage, self.value_format),
                safe_format(reading.v_smu, self.value_format),
                safe_format(reading.i_smu, self.value_format),
                safe_format(reading.v_smu2, self.value_format),
                safe_format(reading.i_smu2, self.value_format),
                safe_format(reading.i_elm, self.value_format),
                safe_format(reading.i_elm2, self.value_format),
            ]
            + self.dmm_data(reading)
            + self.tcu_data(reading)
        )
        self.write_table_row(row)
        self.flush()

    def write_cv_row(self, reading: CVReading) -> None:
        timestamp_utc = reading.timestamp
        if self._current_table != "cv":
            self._current_table = "cv"
            header = (
                [
                    "timestamp[s]",
                    "voltage[V]",
                    "v_smu[V]",
                    "i_smu[A]",
                    "c_lcr[F]",
                    "c2_lcr[1/F^2]",
                    "r_lcr[Ohm]",
                ]
                + self.dmm_header()
                + self.tcu_header()
            )
            self.write_table_header(header)
            self.reset_timestamp_offset(timestamp_utc)
        row = (
            [
                safe_format(self.get_timestamp(timestamp_utc), self.timestamp_format),
                safe_format(reading.voltage, self.value_format),
                safe_format(reading.v_smu, self.value_format),
                safe_format(reading.i_smu, self.value_format),
                safe_format(reading.c_lcr, self.value_format),
                safe_format(reading.c2_lcr, self.value_format),
                safe_format(reading.r_lcr, self.value_format),
            ]
            + self.dmm_data(reading)
            + self.tcu_data(reading)
        )
        self.write_table_row(row)
        self.flush()
