import re
from collections.abc import Iterable, Mapping
from typing import Any, Optional

import pyvisa

from comet.utils import ureg, auto_scale

__all__ = [
    "get_resource",
    "open_resource",
    "format_metric",
    "format_switch",
    "limits",
    "convert",
    "get_bool",
    "get_int",
    "get_float",
    "get_str",
    "get_dict",
]


def get_resource(resource_name: str) -> tuple[str, str]:
    """Create valid VISA resource name for short descriptors."""
    resource_name = resource_name.strip()

    m = re.match(r"^(\d+)$", resource_name)
    if m:
        resource_name = f"GPIB0::{m.group(1)}::INSTR"

    m = re.match(r"^(\d+\.\d+\.\d+\.\d+)\:(\d+)$", resource_name)
    if m:
        resource_name = f"TCPIP0::{m.group(1)}::{m.group(2)}::SOCKET"

    m = re.match(r"^(\w+)\:(\d+)$", resource_name)
    if m:
        resource_name = f"TCPIP0::{m.group(1)}::{m.group(2)}::SOCKET"

    visa_library = ""
    if resource_name.startswith("TCPIP"):
        visa_library = "@py"

    return resource_name, visa_library


def open_resource(resource_name: str, termination: str, timeout: float):
    resource_name, visa_library = get_resource(resource_name)
    timeout_millisecs = timeout * 1e3
    rm = pyvisa.ResourceManager(visa_library)
    return rm.open_resource(
        resource_name=resource_name,
        read_termination=termination,
        write_termination=termination,
        timeout=timeout_millisecs,
    )


def format_metric(value: float, unit: str, decimals: int = 3) -> str:
    """Pretty format metric units.
    >>> format_metric(.0042, "A")
    '4.200 mA'
    """
    if value is None:
        return "---"
    scale, prefix, _ = auto_scale(value)
    return f"{value * (1 / scale):.{decimals}f} {prefix}{unit}"


def format_switch(value: bool) -> str:
    """Pretty format for instrument output states.
    >>> format_switch(False)
    'OFF'
    """
    return {False: "OFF", True: "ON"}.get(value) or "---"


def limits(iterable: Iterable) -> tuple:
    """Calculate limits of 2D point series."""
    limits: tuple = tuple()
    for x, y in iterable:
        if not limits:
            limits = (x, x, y, y)
        else:
            limits = (
                min(x, limits[0]),
                max(x, limits[1]),
                min(y, limits[2]),
                max(y, limits[3]),
            )
    return limits


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a numeric value from one unit to another."""
    return (value * ureg(from_unit)).to(to_unit).m


def get_bool(value: Any, default: bool = False) -> bool:
    """Return a parsed boolean, or default if the value is not recognized."""
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, int):
        return value != 0

    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "on"}:
            return True
        if v in {"0", "false", "no", "off"}:
            return False
        return default

    return default


def get_int(value: Any, default: int = 0) -> int:
    """Return value converted to int, or default if conversion fails."""
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_float(value: Any, default: float = 0.0) -> float:
    """Return value converted to float, or default if conversion fails."""
    if isinstance(value, bool):
        return float(value)

    if isinstance(value, float):
        return value

    if isinstance(value, int):
        return float(value)

    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_str(value: Any, default: str = "") -> str:
    """Return value converted to str, or default if conversion fails or value is None."""
    if isinstance(value, str):
        return value

    if value is None:
        return default

    try:
        return str(value)
    except Exception:
        return default


def get_dict(value: Any, default: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Return a dict value, or default if the input is not mapping-like."""
    if isinstance(value, dict):
        return value

    if isinstance(value, Mapping):
        return dict(value)

    if default is None:
        return {}

    return default
