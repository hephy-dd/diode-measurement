from typing import Any

from comet.driver.ers.ac3 import AC3 as _AC3

__all__ = ["AC3"]


class AC3(_AC3):
    def configure(self, options: dict[str, Any]) -> None:
        target_temperature = options["setpoint.temperature"]
        self.target_temperature = target_temperature
        dewpoint_control = options["dewpoint_control.enabled"]
        self.dewpoint_control = dewpoint_control
        self.operating_mode = self.MODE_NORMAL

    def is_within_setpoint(self) -> bool:
        return self.control_status == self.STATUS_TEMPERATURE_REACHED
