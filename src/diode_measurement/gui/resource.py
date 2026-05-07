from typing import Optional

from PySide6 import QtCore, QtWidgets


__all__ = ["ResourceWidget"]

BAUD_RATES: list[int] = [
    1200,
    2400,
    4800,
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
    921600,
]


class BrowseResourcesDialog(QtWidgets.QDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Browse VISA Resources")
        self.resize(360, 260)

        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self.accept)

        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        self.dialog_button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.dialog_button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.dialog_button_box.accepted.connect(self.accept)
        self.dialog_button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.dialog_button_box)

    def add_resource_name(self, name: str) -> None:
        self.list_widget.addItem(name)
        if self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

    def current_resource_name(self) -> str:
        item = self.list_widget.currentItem()
        if item is None:
            return ""
        return item.text()


class ResourceWidget(QtWidgets.QGroupBox):
    model_changed = QtCore.Signal(str)
    browse_resources = QtCore.Signal()
    test_connection = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Instrument")

        self.model_label = QtWidgets.QLabel("Model", self)

        self.model_combo_box = QtWidgets.QComboBox(self)
        self.model_combo_box.setStatusTip("Instrument model.")
        self.model_combo_box.currentTextChanged.connect(self.on_model_text_changed)

        self.resource_label = QtWidgets.QLabel("Resource", self)

        self.resource_line_edit = QtWidgets.QLineEdit(self)
        self.resource_line_edit.setStatusTip(
            "Instrument resource GPIB number, IP and port or any valid VISA resource name."
        )
        self.resource_line_edit.textChanged.connect(
            self.on_update_baud_rate_visibility
        )

        self.resource_browse_button = QtWidgets.QToolButton(self)
        self.resource_browse_button.setStatusTip("Browse connected VISA resources...")
        self.resource_browse_button.setText("...")
        self.resource_browse_button.clicked.connect(self.browse_resources.emit)

        self.baud_rate_label = QtWidgets.QLabel("Baud Rate", self)

        self.baud_rate_combo_box = QtWidgets.QComboBox(self)
        self.baud_rate_combo_box.setStatusTip("Baud rate for serial connections.")
        for baud_rate in BAUD_RATES:
            self.baud_rate_combo_box.addItem(str(baud_rate), baud_rate)

        self.termination_label = QtWidgets.QLabel("Termination", self)

        self.termination_combo_box = QtWidgets.QComboBox(self)
        self.termination_combo_box.setStatusTip("Read and write termination characters.")
        self.termination_combo_box.addItem("CR+LF", "\r\n")
        self.termination_combo_box.addItem("CR", "\r")
        self.termination_combo_box.addItem("LF", "\n")

        self.timeout_label = QtWidgets.QLabel("Timeout", self)

        self.timeout_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.timeout_spin_box.setStatusTip("Timeout for communication in seconds.")
        self.timeout_spin_box.setSuffix(" s")
        self.timeout_spin_box.setRange(1, 60)
        self.timeout_spin_box.setValue(4)
        self.timeout_spin_box.setDecimals(2)

        self.test_connection_button = QtWidgets.QPushButton(self)
        self.test_connection_button.setText("&Test")
        self.test_connection_button.setStatusTip("Test instrument connection.")
        self.test_connection_button.setMaximumWidth(48)
        self.test_connection_button.clicked.connect(self.test_connection.emit)

        self.reset_instrument_check_box = QtWidgets.QCheckBox(self)
        self.reset_instrument_check_box.setText("Reset Instrument")
        self.reset_instrument_check_box.setStatusTip("Reset instrument on start measurement")

        layout = QtWidgets.QGridLayout(self)

        layout.addWidget(self.model_label, 0, 0, 1, 3)
        layout.addWidget(self.model_combo_box, 1, 0, 1, 3)

        layout.addWidget(self.resource_label, 2, 0, 1, 3)

        resource_layout = QtWidgets.QHBoxLayout()
        resource_layout.addWidget(self.resource_line_edit)
        resource_layout.addWidget(self.resource_browse_button)

        layout.addLayout(resource_layout, 3, 0, 1, 3)

        layout.addWidget(self.baud_rate_label, 4, 0, 1, 3)
        layout.addWidget(self.baud_rate_combo_box, 5, 0, 1, 3)

        layout.addWidget(self.termination_label, 6, 0, 1, 1)
        layout.addWidget(self.timeout_label, 6, 1, 1, 1)

        layout.addWidget(self.termination_combo_box, 7, 0, 1, 1)
        layout.addWidget(self.timeout_spin_box, 7, 1, 1, 1)
        layout.addWidget(self.test_connection_button, 7, 2, 1, 1)

        layout.addWidget(self.reset_instrument_check_box, 8, 0, 1, 3)

        layout.setRowStretch(9, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)

        self.on_update_baud_rate_visibility()

    def set_locked(self, state: bool) -> None:
        self.model_combo_box.setEnabled(not state)
        self.resource_line_edit.setEnabled(not state)
        self.resource_browse_button.setEnabled(not state)
        self.baud_rate_combo_box.setEnabled(not state)
        self.termination_combo_box.setEnabled(not state)
        self.timeout_spin_box.setEnabled(not state)
        self.test_connection_button.setEnabled(not state)
        self.reset_instrument_check_box.setEnabled(not state)

    def model(self) -> str:
        return self.model_combo_box.currentText()

    def set_model(self, model: str) -> None:
        index = self.model_combo_box.findText(model)
        self.model_combo_box.setCurrentIndex(max(0, index))
        self.model_changed.emit(self.model_combo_box.itemText(max(0, index)))

    def add_model(self, model: str) -> None:
        self.model_combo_box.addItem(model)

    def resource_name(self) -> str:
        return self.resource_line_edit.text().strip()

    def set_resource_name(self, resource_name: str) -> None:
        self.resource_line_edit.setText(resource_name)

    def termination(self) -> str:
        return self.termination_combo_box.currentData()

    def set_termination(self, termination: str) -> None:
        index = self.termination_combo_box.findData(termination)
        self.termination_combo_box.setCurrentIndex(max(0, index))

    def timeout(self) -> float:
        return self.timeout_spin_box.value()

    def set_timeout(self, timeout: float) -> None:
        self.timeout_spin_box.setValue(timeout)

    def baud_rate(self) -> int:
        return self.baud_rate_combo_box.currentData()

    def set_baud_rate(self, baud_rate: int) -> None:
        index = self.baud_rate_combo_box.findData(baud_rate)
        self.baud_rate_combo_box.setCurrentIndex(max(0, index))

    def is_reset_instrument(self) -> bool:
        return self.reset_instrument_check_box.isChecked()

    def set_reset_instrument(self, enabled: bool) -> None:
        self.reset_instrument_check_box.setChecked(enabled)

    def show_browse_resources(self, resource_names: list[str]) -> None:
        dialog = BrowseResourcesDialog(self)
        for resource_name in resource_names:
            dialog.add_resource_name(resource_name)

        result = dialog.exec()

        if result == QtWidgets.QDialog.DialogCode.Accepted:
            selected_resource = dialog.current_resource_name()
            if selected_resource:
                self.resource_line_edit.setText(selected_resource)

    @QtCore.Slot(str)
    def on_model_text_changed(self, text: str) -> None:
        self.model_changed.emit(text)

    @QtCore.Slot()
    def on_update_baud_rate_visibility(self) -> None:
        text = self.resource_line_edit.text().strip().upper()
        is_serial = (
            text.startswith("ASRL")
            or text.startswith("COM")
        )
        self.baud_rate_label.setVisible(is_serial)
        self.baud_rate_combo_box.setVisible(is_serial)
