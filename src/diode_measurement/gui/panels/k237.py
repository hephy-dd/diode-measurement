from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, WidgetParameter

__all__ = ["K237Panel"]


class K237Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K237", parent)

        # Filter

        self.filter_group_box = QtWidgets.QGroupBox()
        self.filter_group_box.setTitle("Filter")

        self.filter_mode_label = QtWidgets.QLabel("Mode")

        self.filter_mode_combo_box = QtWidgets.QComboBox()
        self.filter_mode_combo_box.addItem("Disabled", 0)
        self.filter_mode_combo_box.addItem("2-readings", 1)
        self.filter_mode_combo_box.addItem("4-readings", 2)
        self.filter_mode_combo_box.addItem("8-readings", 3)
        self.filter_mode_combo_box.addItem("16-readings", 4)
        self.filter_mode_combo_box.addItem("32-readings", 5)

        filter_layout = QtWidgets.QVBoxLayout(self.filter_group_box)
        filter_layout.addWidget(self.filter_mode_label)
        filter_layout.addWidget(self.filter_mode_combo_box)
        filter_layout.addStretch()

        # Layout

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.filter_group_box)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        # Parameters

        self.bind_parameter("filter.mode", WidgetParameter(self.filter_mode_combo_box))

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.filter_mode_combo_box.setCurrentIndex(0)

    def set_locked(self, state: bool) -> None:
        self.filter_mode_combo_box.setEnabled(not state)
