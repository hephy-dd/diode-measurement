from typing import Any

from comet.driver.keithley.k708b import K708B as _K708B

__all__ = ["K708B"]


class K708B(_K708B):
    def configure(self, options: dict[str, Any]) -> None:
        self.open_all_channels()
        channels = options.get("channels", [])
        self.close_channels(channels)
