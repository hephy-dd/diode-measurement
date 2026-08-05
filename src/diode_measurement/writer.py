import csv
import math
from collections.abc import Iterable
from typing import Any, TextIO

from .core.events import Reading
from .core.role import Role

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
