import traceback
from collections.abc import Callable

from PySide6 import QtWidgets

__all__ = ["show_exception"]


def show_exception(
    exc: Exception,
    parent: QtWidgets.QWidget | None = None,
    on_finished: Callable[[int], None] | None = None,
) -> None:
    detailed_text = "".join(traceback.format_tb(exc.__traceback__))

    message_box = QtWidgets.QMessageBox(parent)
    message_box.setWindowTitle("Exception occured")
    message_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    message_box.setText(str(exc))
    message_box.setDetailedText(detailed_text)
    message_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
    message_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)

    # Fix message box width
    layout: QtWidgets.QLayout | None = message_box.layout()
    if isinstance(layout, QtWidgets.QGridLayout):
        spacer_item = QtWidgets.QSpacerItem(
            448,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addItem(spacer_item, layout.rowCount(), 0, 1, layout.columnCount())

    message_box.finished.connect(message_box.deleteLater)
    if on_finished is not None:
        message_box.finished.connect(on_finished)
    message_box.open()
