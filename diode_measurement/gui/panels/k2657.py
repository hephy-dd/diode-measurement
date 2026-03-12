from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, WidgetParameter

__all__ = ["K2657APanel"]


class K2657APanel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K2657A", parent)

        self.filter_group_box = QtWidgets.QGroupBox()
        self.filter_group_box.setTitle("Filter")
        self.filter_enable_check_box = QtWidgets.QCheckBox("Enabled")

        self.filter_count_label = QtWidgets.QLabel("Count")

        self.filter_count_spin_box = QtWidgets.QSpinBox()
        self.filter_count_spin_box.setSingleStep(1)
        self.filter_count_spin_box.setRange(2, 100)

        self.filter_mode_label = QtWidgets.QLabel("Mode")

        self.filter_mode_combo_box = QtWidgets.QComboBox()
        self.filter_mode_combo_box.addItem("Repeat", "REPEAT_AVG")
        self.filter_mode_combo_box.addItem("Moving", "MOVING_AVG")
        self.filter_mode_combo_box.addItem("Median", "MEDIAN")

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
        self.nplc_spin_box.setStatusTip("Number of Power Line Cycles (0.001 to 25)")
        self.nplc_spin_box.setRange(0.001, 25.0)
        self.nplc_spin_box.setDecimals(3)
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
        left_layout.addWidget(self.filter_group_box)
        left_layout.addWidget(self.integration_time_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        self.bind_parameter(
            "filter.enable", WidgetParameter(self.filter_enable_check_box)
        )
        self.bind_parameter("filter.count", WidgetParameter(self.filter_count_spin_box))
        self.bind_parameter("filter.mode", WidgetParameter(self.filter_mode_combo_box))
        self.bind_parameter("nplc", WidgetParameter(self.nplc_spin_box))

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.filter_enable_check_box.setChecked(False)
        self.filter_count_spin_box.setValue(10)
        self.filter_mode_combo_box.setCurrentIndex(0)
        self.nplc_spin_box.setValue(1.0)

    def set_locked(self, state: bool) -> None:
        self.filter_enable_check_box.setEnabled(not state)
        self.filter_count_spin_box.setEnabled(not state)
        self.filter_mode_combo_box.setEnabled(not state)
        self.nplc_spin_box.setEnabled(not state)
