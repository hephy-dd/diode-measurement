from ..core.driver import driver_factory, driver_registry

# Instrument adapters
from .cts.itc import ITCAdapter
from .ers.ac3 import AC3Adapter
from .hephy.brandbox import BrandBoxAdapter
from .keithley.k237 import K237Adapter
from .keithley.k595 import K595Adapter
from .keithley.k707b import K707BAdapter
from .keithley.k708b import K708BAdapter
from .keithley.k2410 import K2410Adapter
from .keithley.k2470 import K2470Adapter
from .keithley.k2657a import K2657AAdapter
from .keithley.k2700 import K2700Adapter
from .keithley.k4215 import K4215Adapter
from .keithley.k6514 import K6514Adapter
from .keithley.k6517b import K6517BAdapter
from .keysight.a4284a import A4284AAdapter
from .keysight.e4980a import E4980AAdapter

__all__ = ["driver_factory"]

driver_registry.update(
    {
        "K237": K237Adapter,
        "K595": K595Adapter,
        "K2410": K2410Adapter,
        "K2470": K2470Adapter,
        "K2657A": K2657AAdapter,
        "K2700": K2700Adapter,
        "K4215": K4215Adapter,
        "K6514": K6514Adapter,
        "K6517B": K6517BAdapter,
        "E4980A": E4980AAdapter,
        "A4284A": A4284AAdapter,
        "AC3": AC3Adapter,
        "ITC": ITCAdapter,
        "BrandBox": BrandBoxAdapter,
        "K707B": K707BAdapter,
        "K708B": K708BAdapter,
    }
)
