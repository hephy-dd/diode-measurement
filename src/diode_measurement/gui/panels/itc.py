from PySide6 import QtCore, QtWidgets

from ..panel import InstrumentPanel, MethodParameter

__all__ = ["ITCPanel"]


class ITCPanel(InstrumentPanel):
    target_temperature_changed = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("ITC", "CTS ITC", parent)

        self.setpoint_group_box = QtWidgets.QGroupBox("Setpoint")

        self.target_temperature_spin_box = QtWidgets.QDoubleSpinBox()
        self.target_temperature_spin_box.setRange(-70, 300)
        self.target_temperature_spin_box.setDecimals(1)
        self.target_temperature_spin_box.setSuffix(" °C")
        self.target_temperature_spin_box.setStatusTip("Target temperature setpoint.")
        self.target_temperature_spin_box.editingFinished.connect(
            self.on_target_temperature_edited
        )

        setpoint_layout = QtWidgets.QGridLayout(self.setpoint_group_box)
        setpoint_layout.addWidget(QtWidgets.QLabel("Target Temperature"))
        setpoint_layout.addWidget(self.target_temperature_spin_box)

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

        self.restore_defaults()

    @QtCore.Slot()
    def on_target_temperature_edited(self) -> None:
        value = self.target_temperature_spin_box.value()
        self.target_temperature_changed.emit(value)

    def target_temperature(self) -> float:
        return self.target_temperature_spin_box.value()

    def set_target_temperature(self, temperature: float) -> None:
        self.target_temperature_spin_box.setValue(temperature)

    def restore_defaults(self) -> None:
        self.set_target_temperature(24.0)

    def set_locked(self, state: bool) -> None:
        # self.target_temperature_spin_box.setEnabled(not state)
        ...
