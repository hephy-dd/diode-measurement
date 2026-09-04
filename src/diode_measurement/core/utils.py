from pint import UnitRegistry

__all__ = ["convert"]

ureg = UnitRegistry()


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a numeric value from one unit to another."""
    return (value * ureg(from_unit)).to(to_unit).magnitude
