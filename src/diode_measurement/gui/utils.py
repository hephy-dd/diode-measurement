from comet.utils import auto_scale

__all__ = [
    "format_metric",
    "format_switch",
]


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
