import traceback
from typing import Optional

from PySide6 import QtWidgets

__all__ = ["showException"]


def showException(exc: Exception, parent: Optional[QtWidgets.QWidget] = None) -> None:
    detailed_text = "".join(traceback.format_tb(exc.__traceback__))

    dialog = QtWidgets.QMessageBox(parent)
    dialog.setWindowTitle("Exception occured")
    dialog.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    dialog.setText(str(exc))
    dialog.setDetailedText(detailed_text)
    dialog.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
    dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)

    # Fix message box width
    layout: Optional[QtWidgets.QLayout] = dialog.layout()
    if isinstance(layout, QtWidgets.QGridLayout):
        spacer_item = QtWidgets.QSpacerItem(
            448,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addItem(spacer_item, layout.rowCount(), 0, 1, layout.columnCount())

    dialog.exec()
