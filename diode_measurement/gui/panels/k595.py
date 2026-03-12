from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel

__all__ = ["K595Panel"]


class K595Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K595", parent)
