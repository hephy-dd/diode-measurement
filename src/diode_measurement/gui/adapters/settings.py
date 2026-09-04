from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TypeVar, cast

from PySide6 import QtCore

__all__ = ["SettingsAdapter"]

T = TypeVar("T")


class SettingsAdapter:
    def __init__(self, settings: QtCore.QSettings) -> None:
        self._settings: QtCore.QSettings = settings

    def get(self, key: str, default: T) -> T:
        return cast(
            T,
            self._settings.value(
                key,
                default,
                type(default),
            ),
        )

    def set(self, key: str, value: object) -> None:
        self._settings.setValue(key, value)

    @contextmanager
    def group(self, prefix: str) -> Generator[None]:
        self._settings.beginGroup(prefix)
        try:
            yield
        finally:
            self._settings.endGroup()
