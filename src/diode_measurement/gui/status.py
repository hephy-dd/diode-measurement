import math
from typing import Any

from PySide6 import QtCore, QtWidgets

from ..utils import format_metric, format_switch


def stylesheet_switch(state: Any | None) -> str:
    if state is None:
        return ""
    return (
        "QLineEdit:enabled{ background-color: #339933; color: white; }" if state else ""
    )


class SMUStatusGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.voltage_line_edit = QtWidgets.QLineEdit(self)
        self.voltage_line_edit.setReadOnly(True)
        self.voltage_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.current_line_edit = QtWidgets.QLineEdit(self)
        self.current_line_edit.setReadOnly(True)
        self.current_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.output_state_line_edit = QtWidgets.QLineEdit(self)
        self.output_state_line_edit.setReadOnly(True)
        self.output_state_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout = QtWidgets.QHBoxLayout(self)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Voltage"))
        vbox_layout.addWidget(self.voltage_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Current"))
        vbox_layout.addWidget(self.current_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Output"))
        vbox_layout.addWidget(self.output_state_line_edit)
        layout.addLayout(vbox_layout)

        layout.setStretch(0, 3)
        layout.setStretch(1, 3)
        layout.setStretch(2, 1)

    def clear(self) -> None:
        self.voltage_line_edit.setText("---")
        self.current_line_edit.setText("---")
        self.output_state_line_edit.setText("---")

    def set_voltage(self, voltage: float) -> None:
        self.voltage_line_edit.setText(format_metric(voltage, "V"))

    def set_current(self, current: float) -> None:
        self.current_line_edit.setText(format_metric(current, "A"))

    def set_output_state(self, state: bool) -> None:
        self.output_state_line_edit.setText(
            format_switch(state) if state is not None else "---"
        )
        self.output_state_line_edit.setStyleSheet(stylesheet_switch(state))


class ELMStatusGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.voltage_line_edit = QtWidgets.QLineEdit(self)
        self.voltage_line_edit.setReadOnly(True)
        self.voltage_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.current_line_edit = QtWidgets.QLineEdit(self)
        self.current_line_edit.setReadOnly(True)
        self.current_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.output_state_line_edit = QtWidgets.QLineEdit(self)
        self.output_state_line_edit.setReadOnly(True)
        self.output_state_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout = QtWidgets.QHBoxLayout(self)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Voltage"))
        vbox_layout.addWidget(self.voltage_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Current"))
        vbox_layout.addWidget(self.current_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Output"))
        vbox_layout.addWidget(self.output_state_line_edit)
        layout.addLayout(vbox_layout)

        layout.setStretch(0, 3)
        layout.setStretch(1, 3)
        layout.setStretch(2, 1)

        self.clear()

    def clear(self) -> None:
        self.voltage_line_edit.setText("---")
        self.current_line_edit.setText("---")
        self.output_state_line_edit.setText("---")

    def set_voltage(self, voltage: float) -> None:
        self.voltage_line_edit.setText(format_metric(voltage, "V"))

    def set_current(self, current: float) -> None:
        self.current_line_edit.setText(format_metric(current, "A"))

    def set_output_state(self, state: bool) -> None:
        self.output_state_line_edit.setText(
            format_switch(state) if state is not None else "---"
        )
        self.output_state_line_edit.setStyleSheet(stylesheet_switch(state))


class LCRStatusGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.voltage_line_edit = QtWidgets.QLineEdit(self)
        self.voltage_line_edit.setReadOnly(True)
        self.voltage_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.capacity_line_edit = QtWidgets.QLineEdit(self)
        self.capacity_line_edit.setReadOnly(True)
        self.capacity_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.output_state_line_edit = QtWidgets.QLineEdit(self)
        self.output_state_line_edit.setReadOnly(True)
        self.output_state_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout = QtWidgets.QHBoxLayout(self)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Voltage"))
        vbox_layout.addWidget(self.voltage_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Capacity"))
        vbox_layout.addWidget(self.capacity_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Output"))
        vbox_layout.addWidget(self.output_state_line_edit)
        layout.addLayout(vbox_layout)

        layout.setStretch(0, 3)
        layout.setStretch(1, 3)
        layout.setStretch(2, 1)

        self.clear()

    def clear(self) -> None:
        self.voltage_line_edit.setText("---")
        self.capacity_line_edit.setText("---")
        self.output_state_line_edit.setText("---")

    def set_voltage(self, voltage: float) -> None:
        self.voltage_line_edit.setText(format_metric(voltage, "V"))

    def set_capacity(self, capacity: float) -> None:
        self.capacity_line_edit.setText(format_metric(capacity, "F"))

    def set_output_state(self, state: bool) -> None:
        self.output_state_line_edit.setText(
            format_switch(state) if state is not None else "---"
        )
        self.output_state_line_edit.setStyleSheet(stylesheet_switch(state))


class DMMStatusGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.temperature_line_edit = QtWidgets.QLineEdit(self)
        self.temperature_line_edit.setReadOnly(True)
        self.temperature_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout = QtWidgets.QHBoxLayout(self)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Temperature"))
        vbox_layout.addWidget(self.temperature_line_edit)
        layout.addLayout(vbox_layout)

        layout.addStretch()
        layout.setStretch(0, 2)
        layout.setStretch(1, 3)

        self.clear()

    def clear(self) -> None:
        self.temperature_line_edit.setText("---")

    def set_temperature(self, temperature: float) -> None:
        self.temperature_line_edit.setText(format_metric(temperature, "°C", 1))


class TCUStatusGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.temperature_line_edit = QtWidgets.QLineEdit(self)
        self.temperature_line_edit.setReadOnly(True)
        self.temperature_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.humidity_line_edit = QtWidgets.QLineEdit(self)
        self.humidity_line_edit.setReadOnly(True)
        self.humidity_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.state_line_edit = QtWidgets.QLineEdit(self)
        self.state_line_edit.setReadOnly(True)
        self.state_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout = QtWidgets.QHBoxLayout(self)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Temperature"))
        vbox_layout.addWidget(self.temperature_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("Humidity"))
        vbox_layout.addWidget(self.humidity_line_edit)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(QtWidgets.QLabel("State"))
        vbox_layout.addWidget(self.state_line_edit)
        layout.addLayout(vbox_layout)

        self.clear()

    def clear(self) -> None:
        self.temperature_line_edit.setText("---")
        self.humidity_line_edit.setText("---")
        self.state_line_edit.setText("---")

    def set_temperature(self, temperature: float) -> None:
        if math.isfinite(temperature):
            self.temperature_line_edit.setText(format_metric(temperature, "°C", 1))
        else:
            self.temperature_line_edit.setText("---")

    def set_humidity(self, humidity: float) -> None:
        if math.isfinite(humidity):
            self.humidity_line_edit.setText(format_metric(humidity, "%rH", 1))
        else:
            self.humidity_line_edit.setText("---")

    def set_state(self, state: str) -> None:
        self.state_line_edit.setText(str(state))
