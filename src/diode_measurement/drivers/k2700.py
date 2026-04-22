from collections.abc import Mapping
from typing import Any, Optional

from ..core.driver import BaseDriver, InstrumentError, handle_exception

__all__ = ["K2700"]


class K2700(BaseDriver):
    def identify(self) -> str:
        return self._query("*IDN?")

    def reset(self) -> None: ...  # prevent reset

    def clear(self) -> None:
        self._write("*CLS")

    def next_error(self) -> Optional[InstrumentError]:
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
