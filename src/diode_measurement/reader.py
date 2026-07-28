import csv
import logging
import re
from collections.abc import Iterator
from typing import Any, TextIO

from comet.utils import ureg

logger = logging.getLogger(__name__)

__all__ = ["Reader"]


def read_block(fp: TextIO) -> Iterator[str]:
    """Return a continuous block of lines, stopping at an empty line."""
    for line in fp:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.strip()
        if not line:
            break
        yield line


class Reader:
    delimiter: str = "\t"

    def __init__(self, fp: TextIO) -> None:
        self._fp = fp

    def read_meta(self) -> dict[str, Any]:
        reader = csv.reader(read_block(self._fp))
        meta: dict[str, Any] = {}
        for row in reader:
            if not row:
                break
            m = re.match(r"(\w+)(?:\[(\w+)\])?\:\s*(.*)\s*", row[0])
            if not m:
                raise RuntimeError(f"Invalid meta entry: {row[0]!r}")
            key = m.group(1)
            if key in meta:
                raise RuntimeError(f"Duplicate meta entry: {key!r}")
            unit = m.group(2)
            value = m.group(3)
            if unit:
                value = (float(value) * ureg(unit)).m
            meta[key] = value
        return meta

    def read_data(self) -> list[dict[str, float]]:
        reader = csv.reader(read_block(self._fp), delimiter=self.delimiter)
        header_row = next(reader, None)

        if not header_row:
            return []

        header = [key.split("[")[0].strip() for key in header_row]

        data: list[dict[str, float]] = []
        for row in reader:
            if not row:
                break
            values = (float(value) for value in row)
            data.append(dict(zip(header, values)))

        return data
