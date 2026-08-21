from collections.abc import Mapping
from typing import Any

import msgspec
from comet.driver.keithley.k2700 import K2700

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K2700Adapter"]


class K2700Options(msgspec.Struct): ...


class K2700Adapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._driver: K2700 = K2700(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None: ...  # TODO prevent reset

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        return parse_scpi_error(self._query(":SYST:ERR?"))

    def configure(self, options: Mapping[str, Any]) -> None:
        self._configure(msgspec.convert(options, type=K2700Options))

    def _configure(self, options: K2700Options) -> None: ...

    def measure_temperature(self) -> float:
        self._write(":FORM:ELEM READ")  # select reading as return value
        return float(self._query(":FETC?"))

    @handle_exception
    def _write(self, message: str) -> None:
        _ = self._resource.write(message)
        _ = self._resource.query("*OPC?")

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()
