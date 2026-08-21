from PySide6 import QtWidgets

from diode_measurement.drivers.keithley.k237 import FilterMode

from ..panel import FSMState, InstrumentPanel, WidgetParameter

__all__ = ["K237Panel"]


class K237Panel(InstrumentPanel):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("K237", "Keithley 237", parent)

        # Filter

        self.filter_group_box = QtWidgets.QGroupBox()
        self.filter_group_box.setTitle("Filter")

        self.filter_mode_label = QtWidgets.QLabel("Mode")

        self.filter_mode_combo_box = QtWidgets.QComboBox()
        self.filter_mode_combo_box.addItem("Disabled", FilterMode.DISABLED)
        self.filter_mode_combo_box.addItem("2-readings", FilterMode.READINGS_2)
        self.filter_mode_combo_box.addItem("4-readings", FilterMode.READINGS_4)
        self.filter_mode_combo_box.addItem("8-readings", FilterMode.READINGS_8)
        self.filter_mode_combo_box.addItem("16-readings", FilterMode.READINGS_16)
        self.filter_mode_combo_box.addItem("32-readings", FilterMode.READINGS_32)

        filter_layout = QtWidgets.QVBoxLayout(self.filter_group_box)
        filter_layout.addWidget(self.filter_mode_label)
        filter_layout.addWidget(self.filter_mode_combo_box)
        filter_layout.addStretch()

        # Layout

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.filter_group_box)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        # Parameters

        self.bind_parameter("filter.mode", WidgetParameter(self.filter_mode_combo_box))

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.filter_mode_combo_box.setCurrentIndex(0)

    def set_fsm_state(self, state: FSMState) -> None:
        enabled = state == FSMState.IDLE
        self.filter_mode_combo_box.setEnabled(enabled)
