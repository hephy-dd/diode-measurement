from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..driver import driver_factory
from ..utils import open_resource

__all__ = ["ResourceWidget"]


class ResourceWidget(QtWidgets.QGroupBox):
    model_changed = QtCore.Signal(str)

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

        self.termination_label = QtWidgets.QLabel("Termination", self)

        self.termination_combo_box = QtWidgets.QComboBox(self)
        self.termination_combo_box.setStatusTip(
            "Read and write termination characters."
        )
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
        self.test_connection_button.clicked.connect(self.test_conntection)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.model_label, 0, 0, 1, 3)
        layout.addWidget(self.model_combo_box, 1, 0, 1, 3)
        layout.addWidget(self.resource_label, 2, 0, 1, 3)
        layout.addWidget(self.resource_line_edit, 3, 0, 1, 3)
        layout.addWidget(self.termination_label, 4, 0, 1, 1)
        layout.addWidget(self.timeout_label, 4, 1, 1, 1)
        layout.addWidget(self.termination_combo_box, 5, 0, 1, 1)
        layout.addWidget(self.timeout_spin_box, 5, 1, 1, 1)
        layout.addWidget(self.test_connection_button, 5, 2, 1, 1)
        layout.setRowStretch(6, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)

    def set_locked(self, state: bool) -> None:
        self.model_combo_box.setEnabled(not state)
        self.resource_line_edit.setEnabled(not state)
        self.termination_combo_box.setEnabled(not state)
        self.timeout_spin_box.setEnabled(not state)
        self.test_connection_button.setEnabled(not state)

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

    @QtCore.Slot(str)
    def on_model_text_changed(self, text: str) -> None:
        self.model_changed.emit(text)

    def open_resource(self):
        return open_resource(self.resource_name(), self.termination(), self.timeout())

    def read_identity(self) -> str:
        with self.open_resource() as res:
            instr = driver_factory(self.model())(res)
            return instr.identify()

    @QtCore.Slot()
    def test_conntection(self) -> None:
        try:
            identity = self.read_identity()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Connection Test", format(exc))
        else:
            QtWidgets.QMessageBox.information(self, "Connection Test", format(identity))
