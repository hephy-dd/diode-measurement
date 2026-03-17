from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel

__all__ = ["K2700Panel"]


class K2700Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K2700", parent)
