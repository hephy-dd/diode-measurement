from .driver import DMM, handle_exception

__all__ = ['K2700']


class K2700(DMM):

    def identity(self) -> str:
        return self._query('*IDN?')

    def reset(self) -> None:
        pass  # prevent reset
        # self._write('*RST')

    def clear(self) -> None:
        pass  # prevent clear
        # self._write('*CLS')

    def error_state(self) -> tuple:
        code, message = self._query(':SYST:ERR?').split(',')
        code = int(code)
        message = message.strip().strip('"')
        return code, message

    def configure(self, **options) -> None:
        pass

    def read_temperature(self) -> float:
        self._write(":FORM:ELEM READ")  # select reading as return value
        return float(self._query(':FETC?'))

    @handle_exception
    def _write(self, message):
        self.resource.write(message)
        self.resource.query('*OPC?')

    @handle_exception
    def _query(self, message):
        return self.resource.query(message).strip()