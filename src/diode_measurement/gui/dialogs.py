from typing import Optional

from PySide6 import QtWidgets

__all__ = ["ChangeVoltageDialog"]


class ChangeVoltageDialog(QtWidgets.QDialog):
    """Change voltage dialog for continuous It measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Change Voltage")

        self.end_voltage_label = QtWidgets.QLabel("End Voltage", self)

        self.end_voltage_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.end_voltage_spin_box.setRange(-3030, +3030)
        self.end_voltage_spin_box.setDecimals(3)
        self.end_voltage_spin_box.setSuffix(" V")

        self.step_voltage_label = QtWidgets.QLabel("Step Voltage", self)

        self.step_voltage_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.step_voltage_spin_box.setRange(0, +110)
        self.step_voltage_spin_box.setDecimals(3)
        self.step_voltage_spin_box.setSuffix(" V")

        self.waiting_time_label = QtWidgets.QLabel("Waiting Time", self)

        self.waiting_time_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time_spin_box.setRange(0, 60)
        self.waiting_time_spin_box.setDecimals(2)
        self.waiting_time_spin_box.setSuffix(" s")

        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        self.dialog_button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.dialog_button_box.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.dialog_button_box.accepted.connect(self.accept)
        self.dialog_button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.end_voltage_label)
        layout.addWidget(self.end_voltage_spin_box)
        layout.addWidget(self.step_voltage_label)
        layout.addWidget(self.step_voltage_spin_box)
        layout.addWidget(self.waiting_time_label)
        layout.addWidget(self.waiting_time_spin_box)
        layout.addWidget(self.dialog_button_box)

    def end_voltage(self) -> float:
        """Return end voltage in volts."""
        return self.end_voltage_spin_box.value()

    def set_end_voltage(self, voltage: float) -> None:
        """Set end voltage in volts."""
        self.end_voltage_spin_box.setValue(voltage)

    def step_voltage(self) -> float:
        """Return step voltage in volts."""
        return self.step_voltage_spin_box.value()

    def set_step_voltage(self, voltage: float) -> None:
        """Set step voltage in volts."""
        self.step_voltage_spin_box.setValue(voltage)

    def waiting_time(self) -> float:
        """Return waiting time in seconds or fractions of seconds."""
        return self.waiting_time_spin_box.value()

    def set_waiting_time(self, seconds: float) -> None:
        """Set waiting time in seconds or fractions of seconds."""
        self.waiting_time_spin_box.setValue(seconds)
