from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, WidgetParameter

__all__ = ["K2410Panel"]


class K2410Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K2410", parent)

        # Filter

        self.filter_group_box = QtWidgets.QGroupBox()
        self.filter_group_box.setTitle("Filter")
        self.filter_enable_check_box = QtWidgets.QCheckBox("Enabled")

        self.filter_count_label = QtWidgets.QLabel("Count")

        self.filter_count_spin_box = QtWidgets.QSpinBox()
        self.filter_count_spin_box.setSingleStep(1)
        self.filter_count_spin_box.setRange(2, 100)

        self.filter_mode_label = QtWidgets.QLabel("Mode")

        self.filter_mode_combo_box = QtWidgets.QComboBox()
        self.filter_mode_combo_box.addItem("Repeat", "REP")
        self.filter_mode_combo_box.addItem("Moving", "MOV")

        filter_layout = QtWidgets.QVBoxLayout(self.filter_group_box)
        filter_layout.addWidget(self.filter_enable_check_box)
        filter_layout.addWidget(self.filter_count_label)
        filter_layout.addWidget(self.filter_count_spin_box)
        filter_layout.addWidget(self.filter_mode_label)
        filter_layout.addWidget(self.filter_mode_combo_box)
        filter_layout.addStretch()

        # Integration Time

        self.integration_time_group_box = QtWidgets.QGroupBox()
        self.integration_time_group_box.setTitle("Integration Time")

        self.nplc_label = QtWidgets.QLabel("NPLC")

        self.nplc_spin_box = QtWidgets.QDoubleSpinBox()
        self.nplc_spin_box.setStatusTip("Number of Power Line Cycles (0.01 to 10)")
        self.nplc_spin_box.setRange(0.01, 10.0)
        self.nplc_spin_box.setDecimals(2)
        self.nplc_spin_box.setSingleStep(0.1)
        self.nplc_spin_box.setStepType(
            QtWidgets.QDoubleSpinBox.StepType.AdaptiveDecimalStepType
        )

        integration_time_layout = QtWidgets.QVBoxLayout(self.integration_time_group_box)
        integration_time_layout.addWidget(self.nplc_label)
        integration_time_layout.addWidget(self.nplc_spin_box)

        # Route terminals

        self.route_terminals_group_box = QtWidgets.QGroupBox()
        self.route_terminals_group_box.setTitle("Route Terminals")

        self.route_terminals_combo_box = QtWidgets.QComboBox()
        self.route_terminals_combo_box.addItem("Front", "FRON")
        self.route_terminals_combo_box.addItem("Rear", "REAR")

        route_terminals_layout = QtWidgets.QVBoxLayout(self.route_terminals_group_box)
        route_terminals_layout.addWidget(self.route_terminals_combo_box)
        route_terminals_layout.addStretch()

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.filter_group_box)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.integration_time_group_box)
        right_layout.addWidget(self.route_terminals_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        # Parameters

        self.bind_parameter(
            "filter.enable", WidgetParameter(self.filter_enable_check_box)
        )
        self.bind_parameter("filter.count", WidgetParameter(self.filter_count_spin_box))
        self.bind_parameter("filter.mode", WidgetParameter(self.filter_mode_combo_box))
        self.bind_parameter("nplc", WidgetParameter(self.nplc_spin_box))
        self.bind_parameter(
            "route.terminals", WidgetParameter(self.route_terminals_combo_box)
        )

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.filter_enable_check_box.setChecked(False)
        self.filter_count_spin_box.setValue(10)
        self.filter_mode_combo_box.setCurrentIndex(0)
        self.nplc_spin_box.setValue(1.0)
        self.route_terminals_combo_box.setCurrentIndex(0)

    def set_locked(self, state: bool) -> None:
        self.filter_enable_check_box.setEnabled(not state)
        self.filter_count_spin_box.setEnabled(not state)
        self.filter_mode_combo_box.setEnabled(not state)
        self.nplc_spin_box.setEnabled(not state)
        self.route_terminals_combo_box.setEnabled(not state)
