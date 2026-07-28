from PySide6 import QtWidgets

from ..panel import InstrumentPanel

__all__ = ["K2700Panel"]


class K2700Panel(InstrumentPanel):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("K2700", "Keithley 2700", parent)
