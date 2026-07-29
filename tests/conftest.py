from dataclasses import dataclass

import pytest


@dataclass(slots=True)
class FakeResource:
    buffer: list[str]

    def write(self, message: str) -> int:
        self.buffer.append(message)
        return len(message)

    def query(self, message: str) -> str:
        self.buffer.append(message)
        return self.buffer.pop(0)

    def clear(self) -> None: ...


@pytest.fixture
def res():
    return FakeResource([])
