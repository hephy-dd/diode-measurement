import traceback
from typing import Optional

from PySide6 import QtWidgets

__all__ = ["show_exception"]


def show_exception(exc: Exception, parent: Optional[QtWidgets.QWidget] = None) -> None:
    detailed_text = "".join(traceback.format_tb(exc.__traceback__))

    messag_box = QtWidgets.QMessageBox(parent)
    messag_box.setWindowTitle("Exception occured")
    messag_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    messag_box.setText(str(exc))
    messag_box.setDetailedText(detailed_text)
    messag_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
    messag_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)

    # Fix message box width
    layout: Optional[QtWidgets.QLayout] = messag_box.layout()
    if isinstance(layout, QtWidgets.QGridLayout):
        spacer_item = QtWidgets.QSpacerItem(
            448,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addItem(spacer_item, layout.rowCount(), 0, 1, layout.columnCount())

    messag_box.exec()
