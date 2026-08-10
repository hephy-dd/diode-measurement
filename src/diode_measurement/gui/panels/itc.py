from PySide6 import QtCore, QtWidgets

from ..panel import FSMState, InstrumentPanel, MethodParameter

__all__ = ["ITCPanel"]


class ITCPanel(InstrumentPanel):
    target_temperature_changed = QtCore.Signal(float)
    setpoint_tolerance_changed = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("ITC", "CTS ITC", parent)

        self.setpoint_group_box = QtWidgets.QGroupBox("Setpoint")

        self.target_temperature_label = QtWidgets.QLabel("Target Temperature")

        self.target_temperature_spin_box = QtWidgets.QDoubleSpinBox()
        self.target_temperature_spin_box.setRange(-70, 300)
        self.target_temperature_spin_box.setDecimals(1)
        self.target_temperature_spin_box.setSuffix(" °C")
        self.target_temperature_spin_box.setStatusTip("Target temperature setpoint.")
        self.target_temperature_spin_box.editingFinished.connect(
            self.on_target_temperature_edited
        )

        self.setpoint_tolerance_label = QtWidgets.QLabel("Tolerance")

        self.setpoint_tolerance_spin_box = QtWidgets.QDoubleSpinBox()
        self.setpoint_tolerance_spin_box.setRange(0, 10)
        self.setpoint_tolerance_spin_box.setDecimals(1)
        self.setpoint_tolerance_spin_box.setSingleStep(0.1)
        self.setpoint_tolerance_spin_box.setSuffix(" °C")
        self.setpoint_tolerance_spin_box.setStatusTip("Setpoint tolerance.")
        self.setpoint_tolerance_spin_box.editingFinished.connect(
            self.on_setpoint_tolerance_edited
        )

        setpoint_layout = QtWidgets.QGridLayout(self.setpoint_group_box)
        setpoint_layout.addWidget(self.target_temperature_label)
        setpoint_layout.addWidget(self.target_temperature_spin_box)
        setpoint_layout.addWidget(self.setpoint_tolerance_label)
        setpoint_layout.addWidget(self.setpoint_tolerance_spin_box)

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
            "setpoint.tolerance",
            MethodParameter(self.setpoint_tolerance, self.set_setpoint_tolerance),
        )

        self.restore_defaults()

    @QtCore.Slot(bool)
    def on_setpoint_enabled_toggled(self, checked: bool) -> None:
        self.target_temperature_spin_box.setEnabled(checked)
        self.setpoint_tolerance_spin_box.setEnabled(checked)

    @QtCore.Slot()
    def on_target_temperature_edited(self) -> None:
        value = self.target_temperature_spin_box.value()
        self.target_temperature_changed.emit(value)

    @QtCore.Slot()
    def on_setpoint_tolerance_edited(self) -> None:
        value = self.setpoint_tolerance_spin_box.value()
        self.setpoint_tolerance_changed.emit(value)

    def target_temperature(self) -> float:
        return self.target_temperature_spin_box.value()

    def set_target_temperature(self, temperature: float) -> None:
        self.target_temperature_spin_box.setValue(temperature)
        self.target_temperature_changed.emit(self.target_temperature_spin_box.value())

    def setpoint_tolerance(self) -> float:
        return self.setpoint_tolerance_spin_box.value()

    def set_setpoint_tolerance(self, tolerance: float) -> None:
        self.setpoint_tolerance_spin_box.setValue(tolerance)
        self.setpoint_tolerance_changed.emit(self.setpoint_tolerance_spin_box.value())

    def restore_defaults(self) -> None:
        self.set_target_temperature(24.0)
        self.set_setpoint_tolerance(0.2)

    def set_fsm_state(self, state: FSMState) -> None:
        enabled = state in (FSMState.IDLE, FSMState.CONTINUOUS)
        self.target_temperature_spin_box.setEnabled(enabled)
        self.setpoint_tolerance_spin_box.setEnabled(enabled)
