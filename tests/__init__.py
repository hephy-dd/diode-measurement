import pytest


class FakeResource:
    def __init__(self) -> None:
        self.buffer: list[str] = []

    def write(self, message: str) -> int:
        self.buffer.append(message)
        return len(message)

    def query(self, message: str) -> str:
        self.buffer.append(message)
        return self.buffer.pop(0)

    def clear(self) -> None: ...


@pytest.fixture
def res():
    return FakeResource()
