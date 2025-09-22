import re

from typing import Optional

from .driver import SwitchingMatrix, handle_exception

__all__ = ["BrandBox"]

ERROR_MESSAGES: dict[int, str] = {
    99: "Invalid command"
}


def split_channels(channels: str) -> list[str]:
    return [channel.strip() for channel in channels.split(',') if channel.strip()]


def join_channels(channels: list[str]) -> str:
    return ','.join([format(channel).strip() for channel in channels])


def parse_error(response: str) -> int:
    m = re.match(r'^err(\d+)', response.lower())
    if m:
        return int(m.group(1))
    return 0


class BrandBox(SwitchingMatrix):

    CHANNELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

    def __init__(self, resource):
        super().__init__(resource)
        self._error_queue = []

    def identity(self) -> str:
        return self._query("*IDN?")

    def reset(self) -> None:
        self._error_queue.clear()
        ...  # prevent reset

    def clear(self) -> None:
        self._error_queue.clear()
        self._write("*CLS")  # NOTE: closes IV-Mode channels!

    def next_error(self) -> tuple[int, str]:
        code = 0
        if self._error_queue:
            code = self._error_queue.pop(0)
        return code, ERROR_MESSAGES.get(code, "No Error")

    def configure(self, options: dict) -> None:
        self.open_all_channels()
        channels = options.get("channels", [])
        self.close_channels(channels)

    def close_channels(self, channels: list) -> None:
        channel_list = join_channels(sorted(channels))
        self._write(f':CLOS {channel_list}')

    def open_channels(self, channels: list) -> None:
        channel_list = join_channels(sorted(channels))
        self._write(f':OPEN {channel_list}')

    def open_all_channels(self) -> None:
        channel_list = join_channels(type(self).CHANNELS)
        self._write(f':OPEN {channel_list}')

    def closed_channels(self) -> list:
        channels = self._query(':CLOS:STAT?')
        return split_channels(channels)

    @handle_exception
    def _write(self, message):
        response = self._query(message)
        error = parse_error(response)
        if error:
            self._error_queue.append(error)

    @handle_exception
    def _query(self, message):
        response = self.resource.query(message).strip()
        error = parse_error(response)
        if error:
            self._error_queue.append(error)
            return ""
        return response
