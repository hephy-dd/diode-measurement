from typing import Any

from PySide6 import QtCore, QtWidgets

from ..metric import MetricWidget
from ..panel import InstrumentPanel, WidgetParameter

__all__ = ["K2470Panel"]


class K2470Panel(InstrumentPanel):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("K2470", "Keithley 2470", parent)

        # Range

        self.range_group_box = QtWidgets.QGroupBox()
        self.range_group_box.setTitle("Sense Range")

        self.sense_range_metric = MetricWidget()
        self.sense_range_metric.setDecimals(3)
        self.sense_range_metric.setRange(10e-09, 1.0)
        self.sense_range_metric.setUnit("A")
        self.sense_range_metric.setPrefixes("mun")

        self.auto_range_check_box = QtWidgets.QCheckBox("Auto Range")
        self.auto_range_check_box.toggled.connect(self.on_auto_range_check_changed)

        self.auto_range_llimit_label = QtWidgets.QLabel("Lower Limit")

        self.auto_range_llimit_metric = MetricWidget()
        self.auto_range_llimit_metric.setDecimals(3)
        self.auto_range_llimit_metric.setRange(10e-09, 100e-03)
        self.auto_range_llimit_metric.setUnit("A")
        self.auto_range_llimit_metric.setPrefixes("mun")

        range_layout = QtWidgets.QVBoxLayout(self.range_group_box)
        range_layout.addWidget(self.sense_range_metric)
        range_layout.addWidget(self.auto_range_check_box)
        range_layout.addWidget(self.auto_range_llimit_label)
        range_layout.addWidget(self.auto_range_llimit_metric)

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

        # Route Terminals

        self.route_terminals_combo_box = QtWidgets.QComboBox()
        self.route_terminals_combo_box.addItem("Front", "FRON")
        self.route_terminals_combo_box.addItem("Rear", "REAR")

        self.route_terminals_group_box = QtWidgets.QGroupBox()
        self.route_terminals_group_box.setTitle("Route Terminals")

        route_terminals_layout = QtWidgets.QVBoxLayout(self.route_terminals_group_box)
        route_terminals_layout.addWidget(self.route_terminals_combo_box)

        # System

        self.system_group_box = QtWidgets.QGroupBox()
        self.system_group_box.setTitle("System")

        self.breakdown_protection_label = QtWidgets.QLabel("Breakdown Protection")

        self.breakdown_protection_combo_box = QtWidgets.QComboBox()
        self.breakdown_protection_combo_box.addItem("Auto", "AUTO")
        self.breakdown_protection_combo_box.addItem("On", "ON")
        self.breakdown_protection_combo_box.addItem("Off", "OFF")

        system_layout = QtWidgets.QVBoxLayout(self.system_group_box)
        system_layout.addWidget(self.breakdown_protection_label)
        system_layout.addWidget(self.breakdown_protection_combo_box)
        system_layout.addStretch()

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.range_group_box)
        left_layout.addWidget(self.filter_group_box)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.integration_time_group_box)
        right_layout.addWidget(self.route_terminals_group_box)
        right_layout.addWidget(self.system_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        self.bind_parameter("sense.range", WidgetParameter(self.sense_range_metric))
        self.bind_parameter(
            "sense.auto_range", WidgetParameter(self.auto_range_check_box)
        )
        self.bind_parameter(
            "sense.auto_range.lower_limit",
            WidgetParameter(self.auto_range_llimit_metric),
        )
        self.bind_parameter(
            "filter.enable", WidgetParameter(self.filter_enable_check_box)
        )
        self.bind_parameter("filter.count", WidgetParameter(self.filter_count_spin_box))
        self.bind_parameter("filter.mode", WidgetParameter(self.filter_mode_combo_box))
        self.bind_parameter("nplc", WidgetParameter(self.nplc_spin_box))
        self.bind_parameter(
            "route.terminals", WidgetParameter(self.route_terminals_combo_box)
        )
        self.bind_parameter(
            "system.breakdown.protection",
            WidgetParameter(self.breakdown_protection_combo_box),
        )

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.sense_range_metric.setValue(1e-08)
        self.auto_range_check_box.setChecked(True)
        self.auto_range_llimit_metric.setValue(1e-08)
        self.filter_enable_check_box.setChecked(False)
        self.filter_count_spin_box.setValue(10)
        self.filter_mode_combo_box.setCurrentIndex(0)
        self.nplc_spin_box.setValue(1.0)
        self.route_terminals_combo_box.setCurrentIndex(0)
        self.breakdown_protection_combo_box.setCurrentIndex(0)

    def set_locked(self, state: bool) -> None:
        self.sense_range_metric.setEnabled(not state)
        self.auto_range_check_box.setEnabled(not state)
        self.auto_range_llimit_metric.setEnabled(not state)
        self.filter_enable_check_box.setEnabled(not state)
        self.filter_count_spin_box.setEnabled(not state)
        self.filter_mode_combo_box.setEnabled(not state)
        self.nplc_spin_box.setEnabled(not state)
        self.route_terminals_combo_box.setEnabled(not state)
        self.breakdown_protection_combo_box.setEnabled(not state)
        self.on_auto_range_check_changed(self.auto_range_check_box.isChecked())

    @QtCore.Slot(bool)
    def on_auto_range_check_changed(self, checked: bool) -> None:
        enabled = self.auto_range_check_box.isEnabled()
        self.sense_range_metric.setEnabled(enabled and not checked)
        self.auto_range_llimit_label.setEnabled(enabled and checked)
        self.auto_range_llimit_metric.setEnabled(enabled and checked)

    def migrate_config_value(self, key: str, value: Any) -> Any:
        match key:
            case "system.breakdown.protection":
                if isinstance(value, bool):
                    return {True: "AUTO", False: "OFF"}.get(value, "AUTO")
        return value
