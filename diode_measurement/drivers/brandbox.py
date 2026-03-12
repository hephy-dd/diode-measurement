from typing import Any

from comet.driver.hephy.brandbox import BrandBox as _BrandBox

__all__ = ["BrandBox"]


class BrandBox(_BrandBox):
    def configure(self, options: dict[str, Any]) -> None:
        self.open_all_channels()
        channels = options.get("channels", [])
        self.close_channels(channels)
