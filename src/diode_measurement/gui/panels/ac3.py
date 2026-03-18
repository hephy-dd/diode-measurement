from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, MethodParameter

__all__ = ["AC3Panel"]


class AC3Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("AC3", parent)

        self.setpoint_group_box = QtWidgets.QGroupBox("Setpoint")

        self.target_temperature_spin_box = QtWidgets.QDoubleSpinBox()
        self.target_temperature_spin_box.setRange(-70, 300)
        self.target_temperature_spin_box.setDecimals(1)
        self.target_temperature_spin_box.setSuffix(" °C")
        self.target_temperature_spin_box.setStatusTip("Target temperature setpoint.")

        self.dewpoint_control_check_box = QtWidgets.QCheckBox("Dewpoint Control")
        self.dewpoint_control_check_box.setStatusTip(
            "Prevents condensation using dew point monitoring"
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

    def target_temperature(self) -> float:
        return self.target_temperature_spin_box.value()

    def set_target_temperature(self, temperature: float) -> None:
        self.target_temperature_spin_box.setValue(temperature)

    def dewpoint_control(self) -> bool:
        return self.dewpoint_control_check_box.isChecked()

    def set_dewpoint_control(self, enabled: bool) -> None:
        self.dewpoint_control_check_box.setChecked(enabled)

    def restore_defaults(self) -> None:
        self.set_target_temperature(24.0)
        self.set_dewpoint_control(True)

    def set_locked(self, state: bool) -> None:
        self.target_temperature_spin_box.setEnabled(not state)
        self.dewpoint_control_check_box.setEnabled(not state)
