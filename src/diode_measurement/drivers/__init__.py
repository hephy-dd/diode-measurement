from ..core.driver import adapter_factory, adapter_registry

# Instrument adapters
from .a4284a import A4284AAdapter
from .brandbox import BrandBoxAdapter
from .cts.itc import ITCAdapter
from .e4980a import E4980AAdapter
from .ers.ac3 import AC3Adapter
from .k237 import K237Adapter
from .k595 import K595Adapter
from .k707b import K707BAdapter
from .k708b import K708BAdapter
from .k2410 import K2410Adapter
from .k2470 import K2470Adapter
from .k2657a import K2657AAdapter
from .k2700 import K2700Adapter
from .k4215 import K4215Adapter
from .k6514 import K6514Adapter
from .k6517b import K6517BAdapter

__all__ = ["adapter_factory"]

adapter_registry.update(
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
