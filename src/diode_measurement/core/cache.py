import threading
from collections.abc import Iterator, Mapping
from typing import Any, Self

__all__ = ["Cache"]


class Cache:
    """Lockable value cache."""

    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._items: dict[str, Any] = {}

    def __enter__(self) -> Self:
        self._lock.acquire()
        return self

    def __exit__(self, *exc):
        self._lock.release()
        return False

    def __iter__(self) -> Iterator:
        return iter(self._items)

    def get(self, key: str, default: Any = None) -> Any:
        return self._items.get(key, default)

    def update(self, items: Mapping[str, Any]) -> None:
        self._items.update(items)

    def clear(self) -> None:
        self._items.clear()
