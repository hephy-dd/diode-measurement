from PySide6 import QtWidgets

from ..panel import InstrumentPanel

__all__ = ["ITCPanel"]


class ITCPanel(InstrumentPanel):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("ITC", "CTS ITC", parent)

        self.restore_defaults()

    def restore_defaults(self) -> None: ...

    def set_locked(self, state: bool) -> None: ...
