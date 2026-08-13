from collections.abc import Iterable, Mapping
from typing import Any

from comet.driver.keithley.k708b import K708B

from ..core.driver import InstrumentError, Resource

__all__ = ["K708BAdapter"]


class K708BAdapter:
    def __init__(self, resource: Resource) -> None:
        self._driver = K708B(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None:
        self._driver.reset()

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return self._driver.next_error()

    def configure(self, options: Mapping[str, Any]) -> None:
        self.open_all_channels()
        channels = options.get("channels", [])
        self.close_channels(channels)

    def close_channels(self, channels: Iterable[str]) -> None:
        self._driver.close_channels(list(channels))

    def open_channels(self, channels: Iterable[str]) -> None:
        self._driver.open_channels(list(channels))

    def open_all_channels(self) -> None:
        self._driver.open_all_channels()

    def closed_channels(self) -> list[str]:
        return self._driver.closed_channels
