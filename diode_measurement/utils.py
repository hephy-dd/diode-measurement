import re
import pint

__all__ = [
    'ureg',
    'safe_filename',
    'auto_scale',
    'format_metric',
    'format_switch',
    'limits'
]

ureg = pint.UnitRegistry()

def get_resource(resource_name):
    """Create valid VISA resource name for short descriptors."""
    resource_name = resource_name.strip()

    m = re.match(r'^(\d+)$', resource_name)
    if m:
        resource_name = f"GPIB0::{m.group(1)}::INSTR"

    m = re.match(r'^(\d+\.\d+\.\d+\.\d+)\:(\d+)$', resource_name)
    if m:
        resource_name = f"TCPIP0::{m.group(1)}::{m.group(2)}::SOCKET"

    m = re.match(r'^(\w+)\:(\d+)$', resource_name)
    if m:
        resource_name = f"TCPIP0::{m.group(1)}::{m.group(2)}::SOCKET"

    visa_library = ''
    if resource_name.startswith("TCPIP"):
        visa_library = '@py'

    return resource_name, visa_library

def safe_filename(filename):
    return re.sub(r'[^a-zA-Z0-9\_\/\.\-]+', '_', filename)

def auto_scale(value):
    scales = (
        (1e+24, 'Y', 'yotta'),
        (1e+21, 'Z', 'zetta'),
        (1e+18, 'E', 'exa'),
        (1e+15, 'P', 'peta'),
        (1e+12, 'T', 'tera'),
        (1e+9, 'G', 'giga'),
        (1e+6, 'M', 'mega'),
        (1e+3, 'k', 'kilo'),
        (1e+0, '', ''),
        (1e-3, 'm', 'milli'),
        (1e-6, 'u', 'micro'),
        (1e-9, 'n', 'nano'),
        (1e-12, 'p', 'pico'),
        (1e-15, 'f', 'femto'),
        (1e-18, 'a', 'atto'),
        (1e-21, 'z', 'zepto'),
        (1e-24, 'y', 'yocto')
    )
    for scale, prefix, name in scales:
        if abs(value) >= scale:
            return scale, prefix, name
    return 1e0, '', ''

def format_metric(value, unit, decimals=3):
    """Pretty format metric units.
    >>> format_metric(.0042, 'A')
    '4.200 mA'
    """
    if value is None:
        return "---"
    scale, prefix, _ = auto_scale(value)
    return f"{value * (1 / scale):.{decimals}f} {prefix}{unit}"

def format_switch(value, default=None):
    """Pretty format for instrument output states.
    >>> format_switch(False)
    'OFF'
    """
    return {False: "OFF", True: "ON"}.get(value) or default

def limits(iterable) -> tuple:
    """Calculate limits of 2D point series."""
    limits = tuple()
    for x, y in iterable:
        if not limits:
            limits = (x, x, y, y)
        else:
            limits = (
                min(x, limits[0]),
                max(x, limits[1]),
                min(y, limits[2]),
                max(y, limits[3])
            )
    return limits
