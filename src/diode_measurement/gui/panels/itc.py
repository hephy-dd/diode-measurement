from PySide6 import QtCore, QtWidgets

from ..panel import FSMState, InstrumentPanel, MethodParameter

__all__ = ["ITCPanel"]


class ITCPanel(InstrumentPanel):
    setpoint_enabled_changed = QtCore.Signal(bool)
    target_temperature_changed = QtCore.Signal(float)
    setpoint_tolerance_changed = QtCore.Signal(float)
    wait_for_setpoint_changed = QtCore.Signal(bool)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("ITC", "CTS ITC", parent)

        self._fsm_state = FSMState.IDLE

        self.setpoint_group_box = QtWidgets.QGroupBox("Setpoint")

        self.setpoint_enabled_check_box = QtWidgets.QCheckBox("Enabled")
        self.setpoint_enabled_check_box.toggled.connect(
            self.on_setpoint_enabled_toggled
        )

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

        self.wait_for_setpoint_check_box = QtWidgets.QCheckBox("Wait for Setpoint")
        self.wait_for_setpoint_check_box.setStatusTip(
            "Halt measurements until setpoint is reached"
        )
        self.wait_for_setpoint_check_box.toggled.connect(
            self.on_wait_for_setpoint_toggled
        )

        setpoint_layout = QtWidgets.QVBoxLayout(self.setpoint_group_box)
        setpoint_layout.addWidget(self.setpoint_enabled_check_box)
        setpoint_layout.addWidget(self.target_temperature_label)
        setpoint_layout.addWidget(self.target_temperature_spin_box)
        setpoint_layout.addWidget(self.setpoint_tolerance_label)
        setpoint_layout.addWidget(self.setpoint_tolerance_spin_box)
        setpoint_layout.addWidget(self.wait_for_setpoint_check_box)

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
            "setpoint.enabled",
            MethodParameter(self.is_setpoint_enabled, self.set_setpoint_enabled),
        )
        self.bind_parameter(
            "setpoint.temperature",
            MethodParameter(self.target_temperature, self.set_target_temperature),
        )
        self.bind_parameter(
            "setpoint.tolerance",
            MethodParameter(self.setpoint_tolerance, self.set_setpoint_tolerance),
        )
        self.bind_parameter(
            "setpoint.wait_for_setpoint",
            MethodParameter(self.is_wait_for_setpoint, self.set_wait_for_setpoint),
        )

        self.restore_defaults()

    @QtCore.Slot(bool)
    def on_setpoint_enabled_toggled(self, checked: bool) -> None:
        self.setpoint_enabled_changed.emit(checked)
        self._update_inputs()
        if checked:
            self.target_temperature_changed.emit(self.target_temperature())
            self.setpoint_tolerance_changed.emit(self.setpoint_tolerance())
            self.wait_for_setpoint_changed.emit(self.is_wait_for_setpoint())

    @QtCore.Slot()
    def on_target_temperature_edited(self) -> None:
        value = self.target_temperature_spin_box.value()
        self.target_temperature_changed.emit(value)

    @QtCore.Slot()
    def on_setpoint_tolerance_edited(self) -> None:
        value = self.setpoint_tolerance_spin_box.value()
        self.setpoint_tolerance_changed.emit(value)

    @QtCore.Slot()
    def on_wait_for_setpoint_toggled(self) -> None:
        value = self.wait_for_setpoint_check_box.isChecked()
        self.wait_for_setpoint_changed.emit(value)

    def is_setpoint_enabled(self) -> bool:
        return self.setpoint_enabled_check_box.isChecked()

    def set_setpoint_enabled(self, enabled: bool) -> None:
        with QtCore.QSignalBlocker(self.setpoint_enabled_check_box):
            self.setpoint_enabled_check_box.setChecked(enabled)
        self.setpoint_enabled_changed.emit(enabled)
        self._update_inputs()

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

    def is_wait_for_setpoint(self) -> bool:
        return self.wait_for_setpoint_check_box.isChecked()

    def set_wait_for_setpoint(self, enabled: bool) -> None:
        with QtCore.QSignalBlocker(self.wait_for_setpoint_check_box):
            self.wait_for_setpoint_check_box.setChecked(enabled)
        self.wait_for_setpoint_changed.emit(enabled)

    def restore_defaults(self) -> None:
        self.set_setpoint_enabled(False)
        self.set_target_temperature(24.0)
        self.set_setpoint_tolerance(0.2)
        self.set_wait_for_setpoint(False)

    def set_fsm_state(self, state: FSMState) -> None:
        self._fsm_state = state
        self._update_inputs()

    def _update_inputs(self) -> None:
        enabled = self._fsm_state in (FSMState.IDLE, FSMState.CONTINUOUS)
        self.setpoint_enabled_check_box.setEnabled(enabled)
        enabled = enabled and self.is_setpoint_enabled()
        self.target_temperature_spin_box.setEnabled(enabled)
        self.setpoint_tolerance_spin_box.setEnabled(enabled)
        self.wait_for_setpoint_check_box.setEnabled(enabled)
