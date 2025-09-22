from .driver import DMM, handle_exception

__all__ = ["K2700"]


class K2700(DMM):

    def identity(self) -> str:
        return self._query("*IDN?")

    def reset(self) -> None:
        ...  # prevent reset

    def clear(self) -> None:
        self._write("*CLS")

    def next_error(self) -> tuple[int, str]:
        code, message = self._query(":SYST:ERR?").split(",")
        code = int(code)
        message = message.strip().strip('"')
        return code, message

    def configure(self, options: dict) -> None:
        ...

    def measure_temperature(self) -> float:
        self._write(":FORM:ELEM READ")  # select reading as return value
        return float(self._query(":FETC?"))

    @handle_exception
    def _write(self, message):
        self.resource.write(message)
        self.resource.query("*OPC?")

    @handle_exception
    def _query(self, message):
        return self.resource.query(message).strip()
