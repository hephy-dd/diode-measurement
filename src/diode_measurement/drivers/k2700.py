from collections.abc import Mapping
from typing import Any

from comet.driver.keithley.k2700 import K2700

from ..core.driver import InstrumentError, Resource, handle_exception

__all__ = ["K2700Adapter"]


class K2700Adapter:
    def __init__(self, resource: Resource) -> None:
        self.resource = resource
        self._driver = K2700(resource)

    def identify(self) -> str:
        return self._driver.identify()

    def reset(self) -> None: ...  # prevent reset

    def clear(self) -> None:
        self._driver.clear()

    def next_error(self) -> InstrumentError | None:
        code, message = self._query(":SYST:ERR?").split(",")
        code = int(code)
        if code == 0:
            return None
        message = message.strip().strip('"')
        return InstrumentError(code, message)

    def configure(self, options: Mapping[str, Any]) -> None: ...

    def measure_temperature(self) -> float:
        self._write(":FORM:ELEM READ")  # select reading as return value
        return float(self._query(":FETC?"))

    @handle_exception
    def _write(self, message: str) -> None:
        self.resource.write(message)
        self.resource.query("*OPC?")

    @handle_exception
    def _query(self, message: str) -> str:
        return self.resource.query(message).strip()
