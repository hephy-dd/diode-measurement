import csv
import logging
import re

from comet.utils import ureg

logger = logging.getLogger(__name__)

__all__ = ["Reader"]


def read_block(fp):
    """Return a continuous block of lines, stopping at an empty line."""
    for line in fp:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.strip()
        if not line:
            break
        yield line


class Reader:
    def __init__(self, fp):
        self.fp = fp

    def read_meta(self):
        reader = csv.reader(read_block(self.fp))
        meta = {}
        for row in reader:
            if not row:
                break
            m = re.match(r"(\w+)(?:\[(\w+)\])?\:\s*(.*)\s*", row[0])
            if not m:
                raise RuntimeError(f"Invalid meta entry: {repr(row[0])}")
            key = m.group(1)
            if key in meta:
                raise RuntimeError(f"Duplicate meta entry: {repr(key)}")
            unit = m.group(2)
            value = m.group(3)
            if unit:
                value = (float(value) * ureg(unit)).m
            meta[key] = value
        return meta

    def read_data(self):
        reader = csv.reader(read_block(self.fp), delimiter="\t")
        for row in reader:
            header = [key.split("[")[0].strip() for key in row]
            break
        data = []
        for row in reader:
            if not row:
                break
            values = (float(value) for value in row)
            data.append(dict(zip(header, values)))
        return data
