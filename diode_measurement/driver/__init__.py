from typing import Dict

# Drivers
from .k237 import K237
from .k595 import K595
from .k2410 import K2410
from .k2470 import K2470
from .k2657a import K2657A
from .k2700 import K2700
from .k4215 import K4215
from .k6514 import K6514
from .k6517b import K6517B
from .e4980a import E4980A
from .a4284a import A4284A
from .brandbox import BrandBox

__all__ = ["driver_factory"]

DRIVERS: Dict[str, type] = {
    "K237": K237,
    "K595": K595,
    "K2410": K2410,
    "K2470": K2470,
    "K2657A": K2657A,
    "K2700": K2700,
    "K4215": K4215,
    "K6514": K6514,
    "K6517B": K6517B,
    "E4980A": E4980A,
    "A4284A": A4284A,
    "BrandBox": BrandBox,
}


def driver_factory(model: str) -> type:
    """Return driver class referenced by model."""
    driver = DRIVERS.get(model)
    if driver is None:
        raise ValueError(f"No such driver: {model}")
    return driver
