from typing import Protocol


class Job(Protocol):
    def __call__(self) -> None: ...
