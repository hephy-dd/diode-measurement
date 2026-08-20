from collections.abc import Mapping
from enum import IntEnum
from typing import Any

from comet.driver.cts.itc import ITC

from diode_measurement.core.driver import InstrumentError
from diode_measurement.core.events import (
    ChangeSetpointEnabled,
    ChangeSetpointTolerance,
    ChangeTargetTemperature,
)
from diode_measurement.core.resource import Resource

__all__ = ["ITCAdapter"]


class AnalogChannel(IntEnum):
    TEMPERATURE = 1
    HUMIDITY = 2


class ITCAdapter:
    def __init__(self, resource: Resource) -> None:
        self._itc: ITC = ITC(resource.resource)  # requires PyVISA resource
        self._setpoint_enabled: bool = False
        self._is_within_setpoint: bool = False
        self._setpoint_tolerance: float = 0.2
        self._setpoint_hysteresis: float = 0.1

    def identify(self) -> str:
        return self._itc.identify()

    def reset(self) -> None:
        self._is_within_setpoint = False

    def clear(self) -> None:
        self._is_within_setpoint = False

    def next_error(self) -> InstrumentError | None:
        status = self._itc.query_bytes("S", 10)  # read status register
        is_error = status[2] == "1"
        if is_error:
            code = status[9]
            message = self._itc.ERROR_MESSAGES.get(code)
            if message is not None:  # ignore warnings get only errors
                return InstrumentError(ord(code), message)
        return None

    def configure(self, options: Mapping[str, Any]) -> None:
        setpoint_enabled = options.get("setpoint.enabled", False)
        self.set_setpoint_enabled(setpoint_enabled)
        tolerance = options.get("setpoint.tolerance", 0.2)
        self.set_temperature_tolerance(tolerance)

        if self.is_setpoint_enabled():
            target_temperature = options["setpoint.temperature"]
            self.set_target_temperature(target_temperature)

    def get_temperature(self) -> float:
        return self._itc.analog_channel[AnalogChannel.TEMPERATURE][0]

    def get_target_temperature(self) -> float:
        return self._itc.analog_channel[AnalogChannel.TEMPERATURE][1]

    def get_humidity(self) -> float:
        return self._itc.analog_channel[AnalogChannel.HUMIDITY][0]

    def get_target_humidity(self) -> float:
        return self._itc.analog_channel[AnalogChannel.TEMPERATURE][1]

    def is_setpoint_enabled(self) -> bool:
        return self._setpoint_enabled

    def set_setpoint_enabled(self, enabled: bool) -> None:
        self._setpoint_enabled = enabled

    def set_target_temperature(self, temperature: float) -> None:
        self._itc.analog_channel[AnalogChannel.TEMPERATURE] = temperature

    def set_target_humidity(self, humidity: float) -> None:
        """Not implemented"""

    def set_temperature_tolerance(self, tolerance: float) -> None:
        self._setpoint_tolerance = tolerance

    def is_within_setpoint(self) -> bool:
        temperature, target_temperature = self._itc.analog_channel[
            AnalogChannel.TEMPERATURE
        ]

        temperature = round(temperature, 1)
        target_temperature = round(target_temperature, 1)

        tolerance = self._setpoint_tolerance
        if self._is_within_setpoint:
            tolerance += self._setpoint_hysteresis
        delta = abs(target_temperature - temperature)
        self._is_within_setpoint = delta <= tolerance
        return self._is_within_setpoint

    def get_state(self) -> str:
        status = self._itc.status
        program = self._itc.program
        if status.running:
            return f"RUNNING ({program})"
        return "HALTED"

    def handle_event(self, event: Any) -> None:
        match event:
            case ChangeSetpointEnabled(enabled):
                self.set_setpoint_enabled(enabled)
            case ChangeTargetTemperature(target_temperature):
                self.set_target_temperature(target_temperature)
            case ChangeSetpointTolerance(tolerance):
                self.set_temperature_tolerance(tolerance)
            case _:
                raise ValueError("Invalid event for ITC: %r", event)
