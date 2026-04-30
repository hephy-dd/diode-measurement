from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..core.resource import parse_resource, ResourceConfig, Resource
from ..drivers import driver_factory

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
        self.resource_line_edit.textChanged.connect(
            self.on_update_baud_rate_visibility
        )

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
        self.test_connection_button.clicked.connect(self.on_test_conntection)

        self.reset_instrument_check_box = QtWidgets.QCheckBox(self)
        self.reset_instrument_check_box.setText("Reset Instrument")
        self.reset_instrument_check_box.setStatusTip("Reset instrument on start measurement")

        layout = QtWidgets.QGridLayout(self)

        layout.addWidget(self.model_label, 0, 0, 1, 3)
        layout.addWidget(self.model_combo_box, 1, 0, 1, 3)

        layout.addWidget(self.resource_label, 2, 0, 1, 3)
        layout.addWidget(self.resource_line_edit, 3, 0, 1, 3)

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

    @QtCore.Slot(str)
    def on_model_text_changed(self, text: str) -> None:
        self.model_changed.emit(text)

    def create_resource(self) -> Resource:
        resource_name, visa_library = parse_resource(self.resource_name())
        resource_config = ResourceConfig(
            resource_name=resource_name,
            visa_library=visa_library,
            termination=self.termination(),
            timeout=self.timeout(),
        )
        return Resource(resource_config)

    def read_identity(self) -> str:
        with self.create_resource() as res:
            instr = driver_factory(self.model())(res)
            return instr.identify()

    @QtCore.Slot()
    def on_update_baud_rate_visibility(self) -> None:
        text = self.resource_line_edit.text().strip().upper()
        is_serial = (
            text.startswith("ASRL")
            or text.startswith("COM")
        )
        self.baud_rate_label.setEnabled(is_serial)
        self.baud_rate_combo_box.setEnabled(is_serial)

    @QtCore.Slot()
    def on_test_conntection(self) -> None:
        try:
            identity = self.read_identity()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Connection Test", format(exc))
        else:
            QtWidgets.QMessageBox.information(self, "Connection Test", format(identity))
