from collections.abc import Iterable, Mapping
from typing import Any

import msgspec
from comet.driver.keithley.k708b import K708B

from diode_measurement.core.driver import InstrumentError
from diode_measurement.core.resource import Resource

__all__ = ["K708B"]


class K708BOptions(msgspec.Struct):
    channels: list[str] = msgspec.field(
        name="channels",
        default=[],
    )


class K708BAdapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._driver: K708B = K708B(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return self._driver.next_error()

    def configure(self, options: Mapping[str, Any]) -> None:
        self._configure(msgspec.convert(options, type=K708BOptions))

    def _configure(self, options: K708BOptions) -> None:
        self.open_all_channels()
        self.close_channels(options.channels)

    def open_all_channels(self) -> None:
        self._driver.open_all_channels()

    def close_channels(self, channels: Iterable[str]) -> None:
        self._driver.close_channels(list(channels))
