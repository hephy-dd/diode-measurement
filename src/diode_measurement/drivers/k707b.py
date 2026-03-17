from typing import Any

from comet.driver.keithley.k707b import K707B as _K707B

__all__ = ["K707B"]


class K707B(_K707B):
    def configure(self, options: dict[str, Any]) -> None:
        self.open_all_channels()
        channels = options.get("channels", [])
        self.close_channels(channels)
