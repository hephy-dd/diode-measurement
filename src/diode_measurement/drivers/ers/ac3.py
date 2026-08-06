import math
from collections.abc import Mapping
from typing import Any

from comet.driver.ers.ac3 import AC3

from diode_measurement.core.driver import InstrumentError
from diode_measurement.core.resource import Resource

__all__ = ["AC3Adapter"]


class AC3Adapter:
    def __init__(self, resource: Resource) -> None:
        self.resource = resource
        self._ac3 = AC3(resource)

    def identify(self) -> str:
        return self._ac3.identify()

    def reset(self) -> None:
        """Not implemented"""

    def clear(self) -> None:
        """Not implemented"""

    def next_error(self) -> InstrumentError | None:
        return self._ac3.next_error()

    def configure(self, options: Mapping[str, Any]) -> None:
        target_temperature = options["setpoint.temperature"]
        self.set_target_temperature(target_temperature)
        dewpoint_control = options["dewpoint_control.enabled"]
        self._ac3.dewpoint_control = dewpoint_control
        self._ac3.operating_mode = self._ac3.MODE_NORMAL

    def get_temperature(self) -> float:
        return self._ac3.temperature

    def get_humidity(self) -> float:
        return math.nan

    def set_target_temperature(self, temperature: float) -> None:
        self._ac3.target_temperature = temperature

    def is_within_setpoint(self) -> bool:
        return self._ac3.control_status == self._ac3.STATUS_TEMPERATURE_REACHED

    def get_state(self) -> str:
        state = self._ac3.control_status
        if state == self._ac3.STATUS_TEMPERATURE_REACHED:
            return "TEMP_REACHED"
        if state == self._ac3.STATUS_HEATING:
            return "HEATING"
        if state == self._ac3.STATUS_COOLING:
            return "COOLING"
        if state == self._ac3.STATUS_ERROR:
            return "ERROR"
        return "UNKNOWN"
