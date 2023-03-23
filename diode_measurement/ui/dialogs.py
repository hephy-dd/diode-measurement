from PyQt5 import QtWidgets

__all__ = ["ChangeVoltageDialog"]


class ChangeVoltageDialog(QtWidgets.QDialog):
    """Change voltage dialog for continuous It measurements."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Change Voltage")

        self.endVoltageLabel = QtWidgets.QLabel("End Voltage")

        self.endVoltageSpinBox = QtWidgets.QDoubleSpinBox()
        self.endVoltageSpinBox.setRange(-3030, +3030)
        self.endVoltageSpinBox.setDecimals(3)
        self.endVoltageSpinBox.setSuffix(" V")

        self.stepVoltageLabel = QtWidgets.QLabel("Step Voltage")

        self.stepVoltageSpinBox = QtWidgets.QDoubleSpinBox()
        self.stepVoltageSpinBox.setRange(0, +110)
        self.stepVoltageSpinBox.setDecimals(3)
        self.stepVoltageSpinBox.setSuffix(" V")

        self.waitingTimeLabel = QtWidgets.QLabel("Waiting Time")

        self.waitingTimeSpinBox = QtWidgets.QDoubleSpinBox()
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.addButton(self.buttonBox.Ok)
        self.buttonBox.addButton(self.buttonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.endVoltageLabel)
        layout.addWidget(self.endVoltageSpinBox)
        layout.addWidget(self.stepVoltageLabel)
        layout.addWidget(self.stepVoltageSpinBox)
        layout.addWidget(self.waitingTimeLabel)
        layout.addWidget(self.waitingTimeSpinBox)
        layout.addWidget(self.buttonBox)

    def endVoltage(self) -> float:
        """Return end voltage in volts."""
        return self.endVoltageSpinBox.value()

    def setEndVoltage(self, voltage: float) -> None:
        """Set end voltage in volts."""
        self.endVoltageSpinBox.setValue(voltage)

    def stepVoltage(self) -> float:
        """Return step voltage in volts."""
        return self.stepVoltageSpinBox.value()

    def setStepVoltage(self, voltage: float) -> None:
        """Set step voltage in volts."""
        self.stepVoltageSpinBox.setValue(voltage)

    def waitingTime(self) -> float:
        """Return waiting time in seconds or fractions of seconds."""
        return self.waitingTimeSpinBox.value()

    def setWaitingTime(self, seconds: float) -> None:
        """Set waiting time in seconds or fractions of seconds."""
        self.waitingTimeSpinBox.setValue(seconds)
