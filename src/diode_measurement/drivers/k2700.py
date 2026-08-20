from collections.abc import Mapping
from typing import Any

from ..core.driver import BaseDriver, InstrumentError, handle_exception
from ..core.scpi import parse_scpi_error

__all__ = ["K2700"]


class K2700(BaseDriver):
    def identify(self) -> str:
        return self._query("*IDN?")

    def reset(self) -> None: ...  # prevent reset

    def clear(self) -> None:
        self._write("*CLS")

    def next_error(self) -> InstrumentError | None:
        return parse_scpi_error(self._query(":SYST:ERR?"))

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
