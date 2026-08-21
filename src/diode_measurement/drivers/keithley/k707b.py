from collections.abc import Iterable, Mapping
from typing import Any

import msgspec
from comet.driver.keithley.k707b import K707B

from diode_measurement.core.driver import InstrumentError
from diode_measurement.core.resource import Resource

__all__ = ["K707BAdapter"]


class K707BOptions(msgspec.Struct):
    channels: list[str] = msgspec.field(
        name="channels",
        default=[],
    )


class K707BAdapter:
    def __init__(self, resource: Resource) -> None:
        self._driver: K707B = K707B(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return self._driver.next_error()

    def configure(self, options: Mapping[str, Any]) -> None:
        self._configure(msgspec.convert(options, type=K707BOptions))

    def _configure(self, options: K707BOptions) -> None:
        self.open_all_channels()
        self.close_channels(options.channels)

    def open_all_channels(self) -> None:
        self._driver.open_all_channels()

    def close_channels(self, channels: Iterable[str]) -> None:
        self._driver.close_channels(list(channels))
