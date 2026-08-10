from PySide6 import QtCore, QtWidgets

from ..panel import InstrumentPanel, MethodParameter

__all__ = ["AC3Panel"]


class AC3Panel(InstrumentPanel):
    target_temperature_changed = QtCore.Signal(float)
    dewpoint_control_changed = QtCore.Signal(bool)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("AC3", "ERS AC3 Fusion", parent)

        self.setpoint_group_box = QtWidgets.QGroupBox("Setpoint")

        self.target_temperature_spin_box = QtWidgets.QDoubleSpinBox()
        self.target_temperature_spin_box.setRange(-70, 300)
        self.target_temperature_spin_box.setDecimals(1)
        self.target_temperature_spin_box.setSuffix(" °C")
        self.target_temperature_spin_box.setStatusTip("Target temperature setpoint.")
        self.target_temperature_spin_box.editingFinished.connect(
            self.on_target_temperature_edited
        )

        self.dewpoint_control_check_box = QtWidgets.QCheckBox("Dewpoint Control")
        self.dewpoint_control_check_box.setStatusTip(
            "Prevents condensation using dew point monitoring"
        )
        self.dewpoint_control_check_box.toggled.connect(
            self.on_dewpoint_control_toggled
        )

        setpoint_layout = QtWidgets.QGridLayout(self.setpoint_group_box)
        setpoint_layout.addWidget(QtWidgets.QLabel("Target Temperature"))
        setpoint_layout.addWidget(self.target_temperature_spin_box)
        setpoint_layout.addWidget(self.dewpoint_control_check_box)

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.setpoint_group_box)
        left_layout.addStretch()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        # Parameters

        self.bind_parameter(
            "setpoint.temperature",
            MethodParameter(self.target_temperature, self.set_target_temperature),
        )
        self.bind_parameter(
            "dewpoint_control.enabled",
            MethodParameter(self.dewpoint_control, self.set_dewpoint_control),
        )

        self.restore_defaults()

    @QtCore.Slot()
    def on_target_temperature_edited(self) -> None:
        value = self.target_temperature_spin_box.value()
        self.target_temperature_changed.emit(value)

    @QtCore.Slot(bool)
    def on_dewpoint_control_toggled(self, checked: bool) -> None:
        self.dewpoint_control_changed.emit(checked)

    def target_temperature(self) -> float:
        return self.target_temperature_spin_box.value()

    def set_target_temperature(self, temperature: float) -> None:
        self.target_temperature_spin_box.setValue(temperature)
        self.target_temperature_changed.emit(self.target_temperature_spin_box.value())

    def dewpoint_control(self) -> bool:
        return self.dewpoint_control_check_box.isChecked()

    def set_dewpoint_control(self, enabled: bool) -> None:
        self.dewpoint_control_check_box.setChecked(enabled)
        self.dewpoint_control_changed.emit(enabled)

    def restore_defaults(self) -> None:
        self.set_target_temperature(24.0)
        self.set_dewpoint_control(True)

    def set_locked(self, state: bool) -> None: ...
