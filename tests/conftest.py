from dataclasses import dataclass
from typing import Self

import pytest


@dataclass(slots=True)
class MockResource:
    buffer: list[str]

    def write(self, message: str) -> int:
        self.buffer.append(message)
        return len(message)

    def query(self, message: str) -> str:
        self.buffer.append(message)
        return self.buffer.pop(0)

    def clear(self) -> None: ...


@dataclass(slots=True)
class MockRawResource:
    in_buffer: bytes
    out_buffer: bytes

    def write_raw(self, message: bytes) -> int:
        self.in_buffer += message
        return len(message)

    def read_bytes(self, count: int) -> bytes:
        result = self.out_buffer[:count]
        self.out_buffer = self.out_buffer[count:]
        return result

    def clear(self) -> None: ...

    @property
    def resource(self) -> Self:
        return self


@pytest.fixture
def res():
    return MockResource([])


@pytest.fixture
def raw_res():
    return MockRawResource(b"", b"")
