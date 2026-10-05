from collections.abc import Iterable, Mapping

import msgspec
from comet.driver.hephy.brandbox import BrandBox

from diode_measurement.core.driver import InstrumentError
from diode_measurement.core.resource import Resource

__all__ = ["BrandBoxAdapter"]


class BrandBoxConfig(msgspec.Struct, frozen=True):
    channels: list[str] = msgspec.field(default_factory=list)


class BrandBoxAdapter:
    def __init__(self, resource: Resource) -> None:
        self._driver: BrandBox = BrandBox(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return self._driver.next_error()

    def configure(self, options: Mapping[str, object]) -> None:
        config = msgspec.convert(options, type=BrandBoxConfig)

        self.open_all_channels()
        self.close_channels(config.channels)

    def open_all_channels(self) -> None:
        self._driver.open_all_channels()

    def close_channels(self, channels: Iterable[str]) -> None:
        self._driver.close_channels(list(channels))
