from collections.abc import Mapping
from enum import IntEnum
from typing import Any

from comet.driver.cts.itc import ITC

from diode_measurement.core.driver import InstrumentError
from diode_measurement.core.resource import Resource


class AnalogChannel(IntEnum):
    TEMPERATURE = 1
    HUMIDITY = 2


class ITCAdapter:
    def __init__(self, resource: Resource) -> None:
        self.resource = resource
        self._itc = ITC(resource.resource)

    def identify(self) -> str:
        return self._itc.identify()

    def reset(self) -> None:
        """Not implemented"""

    def clear(self) -> None:
        """Not implemented"""

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

    def set_target_temperature(self, temperature: float) -> None:
        self._itc.analog_channel[AnalogChannel.TEMPERATURE] = temperature

    def set_target_humidity(self, humidity: float) -> None:
        """Not implemented"""

    def is_within_setpoint(self) -> bool:
        temperature, target_temperature = self._itc.analog_channel[
            AnalogChannel.TEMPERATURE
        ]
        return round(temperature, 1) == round(target_temperature, 1)

    def get_state(self) -> str:
        status = self._itc.status
        program = self._itc.program
        if status.running:
            return f"RUNNING ({program})"
        return "HALTED"
