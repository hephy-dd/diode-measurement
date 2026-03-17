from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, WidgetParameter
from ..metric import MetricWidget

__all__ = ["K6517BPanel"]


class K6517BPanel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K6517B", parent)

        # Range

        self.range_group_box = QtWidgets.QGroupBox()
        self.range_group_box.setTitle("Sense Range")

        self.sense_range_metric = MetricWidget()
        self.sense_range_metric.setDecimals(3)
        self.sense_range_metric.setRange(0, 999)  # TODO
        self.sense_range_metric.setUnit("A")
        self.sense_range_metric.setPrefixes("munp")

        self.auto_range_llimit_label = QtWidgets.QLabel("Lower Limit")

        self.auto_range_llimit_metric = MetricWidget()
        self.auto_range_llimit_metric.setDecimals(3)
        self.auto_range_llimit_metric.setRange(0, 999)  # TODO
        self.auto_range_llimit_metric.setUnit("A")
        self.auto_range_llimit_metric.setPrefixes("munp")

        self.auto_range_ulimit_label = QtWidgets.QLabel("Upper Limit")

        self.auto_range_ulimit_metric = MetricWidget()
        self.auto_range_ulimit_metric.setDecimals(3)
        self.auto_range_ulimit_metric.setRange(0, 999)  # TODO
        self.auto_range_ulimit_metric.setUnit("A")
        self.auto_range_ulimit_metric.setPrefixes("munp")

        self.auto_range_check_box = QtWidgets.QCheckBox("Auto Range")
        self.auto_range_check_box.toggled.connect(self.on_auto_range_check_changed)

        range_layout = QtWidgets.QVBoxLayout(self.range_group_box)
        range_layout.addWidget(self.sense_range_metric)
        range_layout.addWidget(self.auto_range_check_box)
        range_layout.addWidget(self.auto_range_llimit_label)
        range_layout.addWidget(self.auto_range_llimit_metric)
        range_layout.addWidget(self.auto_range_ulimit_label)
        range_layout.addWidget(self.auto_range_ulimit_metric)

        # Source

        self.source_group_box = QtWidgets.QGroupBox()
        self.source_group_box.setTitle("Source")

        self.meter_connect_check_box = QtWidgets.QCheckBox("Meter Connect")
        self.meter_connect_check_box.setStatusTip(
            "Enable or disable V-source LO to ammeter LO connection."
        )

        source_layout = QtWidgets.QVBoxLayout(self.source_group_box)
        source_layout.addWidget(self.meter_connect_check_box)
        source_layout.addStretch()

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
        # filter_layout.addStretch()

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
        integration_time_layout.addStretch()

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.range_group_box)
        left_layout.addWidget(self.source_group_box)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.filter_group_box)
        right_layout.addWidget(self.integration_time_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        # Parameters

        self.bind_parameter("sense.range", WidgetParameter(self.sense_range_metric))
        self.bind_parameter(
            "sense.auto_range", WidgetParameter(self.auto_range_check_box)
        )
        self.bind_parameter(
            "sense.auto_range.lower_limit",
            WidgetParameter(self.auto_range_llimit_metric),
        )
        self.bind_parameter(
            "sense.auto_range.upper_limit",
            WidgetParameter(self.auto_range_ulimit_metric),
        )
        self.bind_parameter(
            "source.meter_connect", WidgetParameter(self.meter_connect_check_box)
        )
        self.bind_parameter(
            "filter.enable", WidgetParameter(self.filter_enable_check_box)
        )
        self.bind_parameter("filter.count", WidgetParameter(self.filter_count_spin_box))
        self.bind_parameter("filter.mode", WidgetParameter(self.filter_mode_combo_box))
        self.bind_parameter("nplc", WidgetParameter(self.nplc_spin_box))

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.sense_range_metric.setValue(20e-3)
        self.auto_range_check_box.setChecked(True)
        self.auto_range_llimit_metric.setValue(2e-12)
        self.auto_range_ulimit_metric.setValue(20e-3)
        self.meter_connect_check_box.setChecked(False)
        self.filter_enable_check_box.setChecked(False)
        self.filter_count_spin_box.setValue(10)
        self.filter_mode_combo_box.setCurrentIndex(0)
        self.nplc_spin_box.setValue(1.0)

    def set_locked(self, state: bool) -> None:
        self.sense_range_metric.setEnabled(not state)
        self.auto_range_check_box.setEnabled(not state)
        self.auto_range_llimit_metric.setEnabled(not state)
        self.auto_range_ulimit_metric.setEnabled(not state)
        self.meter_connect_check_box.setEnabled(not state)
        self.filter_enable_check_box.setEnabled(not state)
        self.filter_count_spin_box.setEnabled(not state)
        self.filter_mode_combo_box.setEnabled(not state)
        self.nplc_spin_box.setEnabled(not state)
        self.on_auto_range_check_changed(self.auto_range_check_box.isChecked())

    def on_auto_range_check_changed(self, checked) -> None:
        enabled = self.auto_range_check_box.isEnabled()
        self.sense_range_metric.setEnabled(enabled and not checked)
        self.auto_range_llimit_label.setEnabled(enabled and checked)
        self.auto_range_llimit_metric.setEnabled(enabled and checked)
        self.auto_range_ulimit_label.setEnabled(enabled and checked)
        self.auto_range_ulimit_metric.setEnabled(enabled and checked)
