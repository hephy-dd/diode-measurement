from typing import Any, Callable, Mapping, Optional, Protocol

from PySide6 import QtCore, QtWidgets

from .metric import MetricWidget

__all__ = [
    "K237Panel",
    "K595Panel",
    "K2410Panel",
    "K2470Panel",
    "K2657APanel",
    "K2700Panel",
    "K4215Panel",
    "K6514Panel",
    "K6517BPanel",
    "A4284APanel",
    "E4980APanel",
    "BrandBoxPanel",
    "K707BPanel",
    "K708BPanel",
]


class K4215CorrectionDialog(QtWidgets.QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Perform Cable Correction")

        self.type_label = QtWidgets.QLabel("Type", self)

        self.combo_box = QtWidgets.QComboBox(self)
        self.combo_box.addItem("OPEN", "open")
        self.combo_box.addItem("SHORT", "short")
        self.combo_box.addItem("LOAD", "load")

        self.load_label = QtWidgets.QLabel("Load", self)

        self.load_spin_box = QtWidgets.QSpinBox(self)
        self.load_spin_box.setRange(1, 1_000_000)
        self.load_spin_box.setValue(50)
        self.load_spin_box.setSuffix(" Ω")

        self.hint_label = QtWidgets.QLabel(self)
        self.hint_label.setVisible(False)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addWidget(self.hint_label)
        form_layout.addRow(self.type_label, self.combo_box)
        form_layout.addRow(self.load_label, self.load_spin_box)

        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        self.dialog_button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.dialog_button_box.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.dialog_button_box.accepted.connect(self.accept)
        self.dialog_button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(self.dialog_button_box)

        self.combo_box.currentIndexChanged.connect(self._update_load_spin_box)
        self._update_load_spin_box(self.combo_box.currentIndex())

    def _update_load_spin_box(self, index: int) -> None:
        data = self.combo_box.itemData(index)
        enabled = data == "load"
        self.load_label.setEnabled(enabled)
        self.load_spin_box.setEnabled(enabled)

    def is_open_correction(self) -> bool:
        data = self.combo_box.currentData()
        return data == "open"

    def is_short_correction(self) -> bool:
        data = self.combo_box.currentData()
        return data == "short"

    def get_load_correction(self) -> Optional[int]:
        data = self.combo_box.currentData()
        if data == "load":
            return self.load_spin_box.value()
        return None

    def set_hint(self, text: str) -> None:
        self.hint_label.setText(text)
        self.hint_label.setVisible(True)


class Parameter(Protocol):
    def value(self) -> Any: ...
    def setValue(self, value: Any) -> None: ...


class WidgetParameter:
    def __init__(self, widget: QtWidgets.QWidget) -> None:
        self._widget = widget

    def value(self) -> Any:
        widget = self._widget
        if isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        elif isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QComboBox):
            return widget.currentData()
        elif isinstance(widget, MetricWidget):
            return widget.value()
        raise TypeError(f"Invalid widget type: {widget!r}")

    def setValue(self, value: Any) -> None:
        widget = self._widget
        if isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(value)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(value)
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(value)
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(value)
        elif isinstance(widget, QtWidgets.QComboBox):
            index = widget.findData(value)
            widget.setCurrentIndex(index)
        elif isinstance(widget, MetricWidget):
            widget.setValue(value)
        else:
            raise TypeError(f"Invalid widget type: {widget!r}")


class MethodParameter:
    def __init__(
        self, getter: Callable[[], Any], setter: Callable[[Any], None]
    ) -> None:
        self._getter = getter
        self._setter = setter

    def value(self) -> Any:
        return self._getter()

    def setValue(self, value: Any) -> None:
        self._setter(value)


class InstrumentPanel(QtWidgets.QWidget):
    def __init__(self, model: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._parameters: dict[str, Parameter] = {}
        self._model = model

    def model(self) -> str:
        return self._model

    def restore_defaults(self) -> None: ...

    def set_locked(self, state: bool) -> None: ...

    def bind_parameter(self, key: str, parameter: Parameter) -> None:
        if key in self._parameters:
            raise KeyError(f"Parameter already exists: {key!r}")
        self._parameters[key] = parameter

    def config(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        for key, parameter in self._parameters.items():
            config[key] = parameter.value()
        return config

    def apply_config(self, config: Mapping[str, Any]) -> None:
        for key, value in config.items():
            parameter = self._parameters.get(key)
            if parameter is None:
                raise KeyError(f"No such parameter: {key!r}")
            parameter.setValue(value)


class K237Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K237", parent)

        # Filter

        self.filter_group_box = QtWidgets.QGroupBox()
        self.filter_group_box.setTitle("Filter")

        self.filter_mode_label = QtWidgets.QLabel("Mode")

        self.filter_mode_combo_box = QtWidgets.QComboBox()
        self.filter_mode_combo_box.addItem("Disabled", 0)
        self.filter_mode_combo_box.addItem("2-readings", 1)
        self.filter_mode_combo_box.addItem("4-readings", 2)
        self.filter_mode_combo_box.addItem("8-readings", 3)
        self.filter_mode_combo_box.addItem("16-readings", 4)
        self.filter_mode_combo_box.addItem("32-readings", 5)

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

    def set_locked(self, state: bool) -> None:
        self.filter_mode_combo_box.setEnabled(not state)


class K595Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K595", parent)


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


class K2470Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K2470", parent)

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

        self.breakdown_protection_check_box = QtWidgets.QCheckBox(
            "Breakdown Protection"
        )

        system_layout = QtWidgets.QVBoxLayout(self.system_group_box)
        system_layout.addWidget(self.breakdown_protection_check_box)
        system_layout.addStretch()

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
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
            WidgetParameter(self.breakdown_protection_check_box),
        )

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.filter_enable_check_box.setChecked(False)
        self.filter_count_spin_box.setValue(10)
        self.filter_mode_combo_box.setCurrentIndex(0)
        self.nplc_spin_box.setValue(1.0)
        self.route_terminals_combo_box.setCurrentIndex(0)
        self.breakdown_protection_check_box.setChecked(False)

    def set_locked(self, state: bool) -> None:
        self.filter_enable_check_box.setEnabled(not state)
        self.filter_count_spin_box.setEnabled(not state)
        self.filter_mode_combo_box.setEnabled(not state)
        self.nplc_spin_box.setEnabled(not state)
        self.route_terminals_combo_box.setEnabled(not state)
        self.breakdown_protection_check_box.setEnabled(not state)


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


class K2700Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K2700", parent)


class K4215Panel(InstrumentPanel):
    perform_correction_clicked = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K4215", parent)

        # AC amplitude

        self.amplitude_group_box = QtWidgets.QGroupBox()
        self.amplitude_group_box.setTitle("AC Amplitude")

        self.amplitude_voltage_time_label = QtWidgets.QLabel("Voltage")

        self.amplitude_voltage_spin_box = QtWidgets.QDoubleSpinBox()
        self.amplitude_voltage_spin_box.setSuffix(" mV")
        self.amplitude_voltage_spin_box.setDecimals(0)
        self.amplitude_voltage_spin_box.setRange(5, 20e3)
        self.amplitude_voltage_spin_box.setValue(100.0)

        self.amplitude_frequency_time_label = QtWidgets.QLabel("Frequency")

        self.amplitude_frequency_spin_box = QtWidgets.QDoubleSpinBox()
        self.amplitude_frequency_spin_box.setSuffix(" kHz")
        self.amplitude_frequency_spin_box.setDecimals(3)
        self.amplitude_frequency_spin_box.setRange(0.020, 2e6)
        self.amplitude_frequency_spin_box.setValue(1e5)

        self.amplitude_alc_check_box = QtWidgets.QCheckBox("Auto Level Control (ALC)")

        amplitude_layout = QtWidgets.QVBoxLayout(self.amplitude_group_box)
        amplitude_layout.addWidget(self.amplitude_voltage_time_label)
        amplitude_layout.addWidget(self.amplitude_voltage_spin_box)
        amplitude_layout.addWidget(self.amplitude_frequency_time_label)
        amplitude_layout.addWidget(self.amplitude_frequency_spin_box)
        # amplitude_layout.addWidget(self.amplitude_alc_check_box)
        amplitude_layout.addStretch()

        # External Bias Tee section
        self.external_bias_tee_group_box = QtWidgets.QGroupBox()
        self.external_bias_tee_group_box.setTitle("External Bias Tee")

        self.external_bias_tee_check_box = QtWidgets.QCheckBox(
            "-10V DC Bias (only for P3 Bias Tee)"
        )
        self.external_bias_tee_check_box.setStatusTip(
            "Use external bias tee for DC bias voltage. When enabled, internal bias voltage control is disabled."
        )

        external_bias_tee_layout = QtWidgets.QVBoxLayout(
            self.external_bias_tee_group_box
        )
        external_bias_tee_layout.addWidget(self.external_bias_tee_check_box)
        external_bias_tee_layout.addStretch()

        # Aperture

        self.aperture_group_box = QtWidgets.QGroupBox()
        self.aperture_group_box.setTitle("Aperture")

        self.integration_time_label = QtWidgets.QLabel("Integration Time")

        self.integration_time_combo_box = QtWidgets.QComboBox()
        self.integration_time_combo_box.addItem("Fast", "SHOR")
        self.integration_time_combo_box.addItem("Normal", "MED")
        self.integration_time_combo_box.addItem("Quiet", "LONG")
        self.integration_time_combo_box.addItem("Custom", "CUSTOM")

        self.averaging_rate_label = QtWidgets.QLabel("Aperture (PLC)")

        self.averaging_rate_spin_box = QtWidgets.QDoubleSpinBox()
        self.averaging_rate_spin_box.setRange(0.006, 10.002)
        self.averaging_rate_spin_box.setDecimals(4)
        self.averaging_rate_spin_box.setValue(10.0)

        self.filter_factor_label = QtWidgets.QLabel("Filter Factor")

        self.filter_factor_spin_box = QtWidgets.QDoubleSpinBox()
        self.filter_factor_spin_box.setRange(0, 707.0)
        self.filter_factor_spin_box.setDecimals(1)
        self.filter_factor_spin_box.setValue(2.0)
        self.filter_factor_spin_box.setStatusTip("Filter factor for noise reduction")

        self.delay_factor_label = QtWidgets.QLabel("Delay Factor")

        self.delay_factor_spin_box = QtWidgets.QDoubleSpinBox()
        self.delay_factor_spin_box.setRange(0.1, 100.0)
        self.delay_factor_spin_box.setDecimals(1)
        self.delay_factor_spin_box.setValue(1.0)
        self.delay_factor_spin_box.setStatusTip("Delay factor for measurement timing")

        aperture_layout = QtWidgets.QVBoxLayout(self.aperture_group_box)
        aperture_layout.addWidget(self.integration_time_label)
        aperture_layout.addWidget(self.integration_time_combo_box)
        aperture_layout.addWidget(self.averaging_rate_label)
        aperture_layout.addWidget(self.averaging_rate_spin_box)
        aperture_layout.addWidget(self.filter_factor_label)
        aperture_layout.addWidget(self.filter_factor_spin_box)
        aperture_layout.addWidget(self.delay_factor_label)
        aperture_layout.addWidget(self.delay_factor_spin_box)
        aperture_layout.addStretch()

        # Correction

        self.correction_group_box = QtWidgets.QGroupBox()
        self.correction_group_box.setTitle("Correction")

        self.length_label = QtWidgets.QLabel("Cable Length")

        self.length_combo_box = QtWidgets.QComboBox()
        self.length_combo_box.addItem("0 m", 0.0)
        self.length_combo_box.addItem("1.5 m", 1.5)
        self.length_combo_box.addItem("3.0 m", 3.0)
        self.length_combo_box.addItem("Custom", 4.0)
        self.length_combo_box.addItem("CVIV 2W 1.5 m", 5.0)
        self.length_combo_box.addItem("CVIV 4W black 0.75 m", 6.0)
        self.length_combo_box.addItem("CVIV 4W blue 0.61 m", 7.0)

        self.open_enabled_check_box = QtWidgets.QCheckBox("OPEN")
        self.open_enabled_check_box.setStatusTip("Enable OPEN correction")

        self.short_enabled_check_box = QtWidgets.QCheckBox("SHORT")
        self.short_enabled_check_box.setStatusTip("Enable SHORT correction")

        self.load_enabled_check_box = QtWidgets.QCheckBox("LOAD")
        self.load_enabled_check_box.setStatusTip("Enable LOAD correction")

        self.performCorrectionButton = QtWidgets.QPushButton("Perform Cable Correction")
        self.performCorrectionButton.clicked.connect(
            self.perform_correction_clicked.emit
        )

        modes_layout = QtWidgets.QHBoxLayout()
        modes_layout.addWidget(self.open_enabled_check_box)
        modes_layout.addWidget(self.short_enabled_check_box)
        modes_layout.addWidget(self.load_enabled_check_box)
        modes_layout.addStretch()

        correction_layout = QtWidgets.QVBoxLayout(self.correction_group_box)
        correction_layout.addWidget(self.length_label)
        correction_layout.addWidget(self.length_combo_box)
        correction_layout.addLayout(modes_layout)
        correction_layout.addWidget(self.performCorrectionButton)
        correction_layout.addStretch()

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.amplitude_group_box)
        left_layout.addWidget(self.external_bias_tee_group_box)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.aperture_group_box)
        right_layout.addWidget(self.correction_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        self.bind_parameter(
            "voltage",
            MethodParameter(self.amplitude_voltage, self.set_amplitude_voltage),
        )
        self.bind_parameter(
            "frequency",
            MethodParameter(self.amplitude_frequency, self.set_amplitude_frequency),
        )
        self.bind_parameter(
            "amplitude.alc", WidgetParameter(self.amplitude_alc_check_box)
        )
        self.bind_parameter(
            "aperture.integration_time",
            WidgetParameter(self.integration_time_combo_box),
        )
        self.bind_parameter(
            "aperture.aperture", WidgetParameter(self.averaging_rate_spin_box)
        )
        self.bind_parameter(
            "aperture.filter_count", WidgetParameter(self.filter_factor_spin_box)
        )
        self.bind_parameter(
            "aperture.delay_factor", WidgetParameter(self.delay_factor_spin_box)
        )
        self.bind_parameter("correction.length", WidgetParameter(self.length_combo_box))
        self.bind_parameter(
            "correction.open.enabled", WidgetParameter(self.open_enabled_check_box)
        )
        self.bind_parameter(
            "correction.short.enabled", WidgetParameter(self.short_enabled_check_box)
        )
        self.bind_parameter(
            "correction.load.enabled", WidgetParameter(self.load_enabled_check_box)
        )
        self.bind_parameter(
            "external_bias_tee.enabled",
            WidgetParameter(self.external_bias_tee_check_box),
        )

        # Connect signal to handle bias voltage control state
        self.external_bias_tee_check_box.toggled.connect(self.onExternalBiasTeeCToggled)

        # Connect signal to handle integration time preset changes
        self.integration_time_combo_box.currentTextChanged.connect(
            self.on_integration_time_changed
        )

        # Connect signals to switch to Custom when manual changes are made
        self.averaging_rate_spin_box.valueChanged.connect(
            self.on_manual_parameter_change
        )
        self.filter_factor_spin_box.valueChanged.connect(
            self.on_manual_parameter_change
        )
        self.delay_factor_spin_box.valueChanged.connect(self.on_manual_parameter_change)

        self.restore_defaults()

    def onExternalBiasTeeCToggled(self, checked: bool) -> None:
        """Handle external bias tee checkbox toggle."""
        # When external bias tee is enabled, warn user that bias voltage control is disabled
        if checked:
            self.setStatusTip(
                "External bias tee enabled - internal bias voltage control is disabled"
            )
        else:
            self.setStatusTip(
                "External bias tee disabled - internal bias voltage control is available"
            )

    def on_integration_time_changed(self, text: str) -> None:
        """Handle integration time preset changes."""
        # Define presets based on K4215 manual
        presets = {
            "Fast": {
                "delay_factor": 0.7,
                "filter_factor": 0.2,
                "aperture_time": 1,
            },
            "Normal": {
                "delay_factor": 1.0,
                "filter_factor": 1.0,
                "aperture_time": 10,
            },
            "Quiet": {
                "delay_factor": 0.7,
                "filter_factor": 1.3,
                "aperture_time": 10,
            },
        }

        # Only update if it's a preset (not Custom)
        if text in presets:
            preset = presets[text]

            # Update delay factor (already scaled for display)
            self.delay_factor_spin_box.setValue(preset["delay_factor"])

            # Update filter count
            self.filter_factor_spin_box.setValue(preset["filter_factor"])

            # Set aperture time from preset
            self.averaging_rate_spin_box.setValue(preset["aperture_time"])

    def on_manual_parameter_change(self) -> None:
        """Switch to Custom mode when user manually changes parameters."""
        # Only switch to Custom if currently on a preset
        current_text = self.integration_time_combo_box.currentText()
        if current_text != "Custom":
            # Temporarily disconnect the signal to avoid recursion
            self.integration_time_combo_box.currentTextChanged.disconnect()
            self.integration_time_combo_box.setCurrentText("Custom")
            self.integration_time_combo_box.currentTextChanged.connect(
                self.on_integration_time_changed
            )

    def amplitude_voltage(self) -> float:
        return self.amplitude_voltage_spin_box.value() / 1e3  # mV to V

    def set_amplitude_voltage(self, voltage: float) -> None:
        self.amplitude_voltage_spin_box.setValue(voltage * 1e3)  # V to mV

    def amplitude_frequency(self) -> float:
        return self.amplitude_frequency_spin_box.value() * 1e3  # kHz to Hz

    def set_amplitude_frequency(self, frequency: float) -> None:
        self.amplitude_frequency_spin_box.setValue(frequency / 1e3)  # Hz to kHz

    def restore_defaults(self) -> None:
        self.set_amplitude_voltage(1e-1)
        self.set_amplitude_frequency(100e3)
        self.amplitude_alc_check_box.setChecked(False)
        self.integration_time_combo_box.setCurrentIndex(1)
        self.averaging_rate_spin_box.setValue(10.0)
        self.length_combo_box.setCurrentIndex(0)
        self.open_enabled_check_box.setChecked(False)
        self.short_enabled_check_box.setChecked(False)
        self.external_bias_tee_check_box.setChecked(False)

    def set_locked(self, state: bool) -> None:
        self.amplitude_voltage_spin_box.setEnabled(not state)
        self.amplitude_frequency_spin_box.setEnabled(not state)
        self.amplitude_alc_check_box.setEnabled(not state)
        self.integration_time_combo_box.setEnabled(not state)
        self.averaging_rate_spin_box.setEnabled(not state)
        self.length_combo_box.setEnabled(not state)
        self.open_enabled_check_box.setEnabled(not state)
        self.short_enabled_check_box.setEnabled(not state)
        self.load_enabled_check_box.setEnabled(not state)
        self.performCorrectionButton.setEnabled(not state)
        self.external_bias_tee_check_box.setEnabled(not state)


class K6514Panel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K6514", parent)

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
        range_layout.addStretch()

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
            "filter.enable", WidgetParameter(self.filter_enable_check_box)
        )
        self.bind_parameter("filter.count", WidgetParameter(self.filter_count_spin_box))
        self.bind_parameter("filter.mode", WidgetParameter(self.filter_mode_combo_box))
        self.bind_parameter("nplc", WidgetParameter(self.nplc_spin_box))

        self.restore_defaults()

    def restore_defaults(self) -> None:
        self.sense_range_metric.setValue(200e-6)
        self.auto_range_check_box.setChecked(True)
        self.auto_range_llimit_metric.setValue(2e-12)
        self.auto_range_ulimit_metric.setValue(20e-3)
        self.filter_enable_check_box.setChecked(False)
        self.filter_count_spin_box.setValue(10)
        self.filter_mode_combo_box.setCurrentIndex(0)
        self.nplc_spin_box.setValue(5.0)
        self.on_auto_range_check_changed(self.auto_range_check_box.isChecked())

    def set_locked(self, state: bool) -> None:
        self.sense_range_metric.setEnabled(not state)
        self.auto_range_check_box.setEnabled(not state)
        self.auto_range_llimit_metric.setEnabled(not state)
        self.auto_range_ulimit_metric.setEnabled(not state)
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


class A4284APanel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("A4284A", parent)

        # AC amplitude

        self.amplitude_group_box = QtWidgets.QGroupBox()
        self.amplitude_group_box.setTitle("AC Amplitude")

        self.amplitude_voltage_time_label = QtWidgets.QLabel("Voltage")

        self.amplitude_voltage_spin_box = QtWidgets.QDoubleSpinBox()
        self.amplitude_voltage_spin_box.setSuffix(" mV")
        self.amplitude_voltage_spin_box.setDecimals(0)
        self.amplitude_voltage_spin_box.setRange(5, 20e3)

        self.amplitude_frequency_time_label = QtWidgets.QLabel("Frequency")

        self.amplitude_frequency_spin_box = QtWidgets.QDoubleSpinBox()
        self.amplitude_frequency_spin_box.setSuffix(" kHz")
        self.amplitude_frequency_spin_box.setDecimals(3)
        self.amplitude_frequency_spin_box.setRange(0.020, 2e6)

        self.amplitude_alc_check_box = QtWidgets.QCheckBox("Auto Level Control (ALC)")

        amplitude_layout = QtWidgets.QVBoxLayout(self.amplitude_group_box)
        amplitude_layout.addWidget(self.amplitude_voltage_time_label)
        amplitude_layout.addWidget(self.amplitude_voltage_spin_box)
        amplitude_layout.addWidget(self.amplitude_frequency_time_label)
        amplitude_layout.addWidget(self.amplitude_frequency_spin_box)
        amplitude_layout.addWidget(self.amplitude_alc_check_box)
        amplitude_layout.addStretch()

        # Aperture

        self.aperture_group_box = QtWidgets.QGroupBox()
        self.aperture_group_box.setTitle("Aperture")

        self.integration_time_label = QtWidgets.QLabel("Integration Time")

        self.integration_time_combo_box = QtWidgets.QComboBox()
        self.integration_time_combo_box.addItem("Short", "SHOR")
        self.integration_time_combo_box.addItem("Medium", "MED")
        self.integration_time_combo_box.addItem("Long", "LONG")

        self.averaging_rate_label = QtWidgets.QLabel("Averaging Rate")

        self.averaging_rate_spin_box = QtWidgets.QSpinBox()
        self.averaging_rate_spin_box.setRange(1, 128)

        aperture_layout = QtWidgets.QVBoxLayout(self.aperture_group_box)
        aperture_layout.addWidget(self.integration_time_label)
        aperture_layout.addWidget(self.integration_time_combo_box)
        aperture_layout.addWidget(self.averaging_rate_label)
        aperture_layout.addWidget(self.averaging_rate_spin_box)

        # Correction

        self.correction_group_box = QtWidgets.QGroupBox()
        self.correction_group_box.setTitle("Correction")

        self.length_label = QtWidgets.QLabel("Cable Length")

        self.length_combo_box = QtWidgets.QComboBox()
        self.length_combo_box.addItem("0 m", 0)
        self.length_combo_box.addItem("1 m", 1)
        self.length_combo_box.addItem("2 m", 2)

        self.open_enabled_check_box = QtWidgets.QCheckBox("Enable OPEN correction")
        self.open_enabled_check_box.setStatusTip("Enable OPEN correction")

        self.short_enabled_check_box = QtWidgets.QCheckBox("Enable SHORT correction")
        self.short_enabled_check_box.setStatusTip("Enable SHORT correction")

        correction_layout = QtWidgets.QVBoxLayout(self.correction_group_box)
        correction_layout.addWidget(self.length_label)
        correction_layout.addWidget(self.length_combo_box)
        correction_layout.addWidget(self.open_enabled_check_box)
        correction_layout.addWidget(self.short_enabled_check_box)
        correction_layout.addStretch()

        # Layout

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.aperture_group_box)
        right_layout.addWidget(self.correction_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.amplitude_group_box)
        layout.addLayout(right_layout)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        self.bind_parameter(
            "voltage",
            MethodParameter(self.amplitude_voltage, self.set_amplitude_voltage),
        )
        self.bind_parameter(
            "frequency",
            MethodParameter(self.amplitude_frequency, self.set_amplitude_frequency),
        )
        self.bind_parameter(
            "amplitude.alc", WidgetParameter(self.amplitude_alc_check_box)
        )
        self.bind_parameter(
            "aperture.integration_time",
            WidgetParameter(self.integration_time_combo_box),
        )
        self.bind_parameter(
            "aperture.averaging_rate", WidgetParameter(self.averaging_rate_spin_box)
        )
        self.bind_parameter("correction.length", WidgetParameter(self.length_combo_box))
        self.bind_parameter(
            "correction.open.enabled", WidgetParameter(self.open_enabled_check_box)
        )
        self.bind_parameter(
            "correction.short.enabled", WidgetParameter(self.short_enabled_check_box)
        )

        self.restore_defaults()

    def amplitude_voltage(self) -> float:
        return self.amplitude_voltage_spin_box.value() / 1e3  # mV to V

    def set_amplitude_voltage(self, voltage: float) -> None:
        self.amplitude_voltage_spin_box.setValue(voltage * 1e3)  # V to mV

    def amplitude_frequency(self) -> float:
        return self.amplitude_frequency_spin_box.value() * 1e3  # kHz to Hz

    def set_amplitude_frequency(self, frequency: float) -> None:
        self.amplitude_frequency_spin_box.setValue(frequency / 1e3)  # Hz to kHz

    def restore_defaults(self) -> None:
        self.set_amplitude_voltage(1e0)
        self.set_amplitude_frequency(1e3)
        self.amplitude_alc_check_box.setChecked(False)
        self.integration_time_combo_box.setCurrentIndex(1)
        self.averaging_rate_spin_box.setValue(1)
        self.length_combo_box.setCurrentIndex(0)
        self.open_enabled_check_box.setChecked(False)
        self.short_enabled_check_box.setChecked(False)

    def set_locked(self, state: bool) -> None:
        self.amplitude_voltage_spin_box.setEnabled(not state)
        self.amplitude_frequency_spin_box.setEnabled(not state)
        self.amplitude_alc_check_box.setEnabled(not state)
        self.integration_time_combo_box.setEnabled(not state)
        self.averaging_rate_spin_box.setEnabled(not state)
        self.length_combo_box.setEnabled(not state)
        self.open_enabled_check_box.setEnabled(not state)
        self.short_enabled_check_box.setEnabled(not state)


class E4980APanel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("E4980A", parent)

        # AC amplitude

        self.amplitude_group_box = QtWidgets.QGroupBox()
        self.amplitude_group_box.setTitle("AC Amplitude")

        self.amplitude_voltage_time_label = QtWidgets.QLabel("Voltage")

        self.amplitude_voltage_spin_box = QtWidgets.QDoubleSpinBox()
        self.amplitude_voltage_spin_box.setSuffix(" mV")
        self.amplitude_voltage_spin_box.setDecimals(0)
        self.amplitude_voltage_spin_box.setRange(0, 20e3)

        self.amplitude_frequency_time_label = QtWidgets.QLabel("Frequency")

        self.amplitude_frequency_spin_box = QtWidgets.QDoubleSpinBox()
        self.amplitude_frequency_spin_box.setSuffix(" kHz")
        self.amplitude_frequency_spin_box.setDecimals(3)
        self.amplitude_frequency_spin_box.setRange(0.020, 2e6)

        self.amplitude_alc_check_box = QtWidgets.QCheckBox("Auto Level Control (ALC)")

        amplitude_layout = QtWidgets.QVBoxLayout(self.amplitude_group_box)
        amplitude_layout.addWidget(self.amplitude_voltage_time_label)
        amplitude_layout.addWidget(self.amplitude_voltage_spin_box)
        amplitude_layout.addWidget(self.amplitude_frequency_time_label)
        amplitude_layout.addWidget(self.amplitude_frequency_spin_box)
        amplitude_layout.addWidget(self.amplitude_alc_check_box)
        amplitude_layout.addStretch()

        # Aperture

        self.aperture_group_box = QtWidgets.QGroupBox()
        self.aperture_group_box.setTitle("Aperture")

        self.integration_time_label = QtWidgets.QLabel("Integration Time")

        self.integration_time_combo_box = QtWidgets.QComboBox()
        self.integration_time_combo_box.addItem("Short", "SHOR")
        self.integration_time_combo_box.addItem("Medium", "MED")
        self.integration_time_combo_box.addItem("Long", "LONG")

        self.averaging_rate_label = QtWidgets.QLabel("Averaging Rate")

        self.averaging_rate_spin_box = QtWidgets.QSpinBox()
        self.averaging_rate_spin_box.setRange(1, 128)

        aperture_layout = QtWidgets.QVBoxLayout(self.aperture_group_box)
        aperture_layout.addWidget(self.integration_time_label)
        aperture_layout.addWidget(self.integration_time_combo_box)
        aperture_layout.addWidget(self.averaging_rate_label)
        aperture_layout.addWidget(self.averaging_rate_spin_box)

        # Correction

        self.correction_group_box = QtWidgets.QGroupBox()
        self.correction_group_box.setTitle("Correction")

        self.length_label = QtWidgets.QLabel("Cable Length")

        self.length_combo_box = QtWidgets.QComboBox()
        self.length_combo_box.addItem("0 m", 0)
        self.length_combo_box.addItem("1 m", 1)
        self.length_combo_box.addItem("2 m", 2)
        self.length_combo_box.addItem("4 m", 4)

        self.open_enabled_check_box = QtWidgets.QCheckBox("Enable OPEN correction")
        self.open_enabled_check_box.setStatusTip("Enable OPEN correction")

        self.short_enabled_check_box = QtWidgets.QCheckBox("Enable SHORT correction")
        self.short_enabled_check_box.setStatusTip("Enable SHORT correction")

        correction_layout = QtWidgets.QVBoxLayout(self.correction_group_box)
        correction_layout.addWidget(self.length_label)
        correction_layout.addWidget(self.length_combo_box)
        correction_layout.addWidget(self.open_enabled_check_box)
        correction_layout.addWidget(self.short_enabled_check_box)
        correction_layout.addStretch()

        # Layout

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.aperture_group_box)
        right_layout.addWidget(self.correction_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.amplitude_group_box)
        layout.addLayout(right_layout)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        self.bind_parameter(
            "voltage",
            MethodParameter(self.amplitude_voltage, self.set_amplitude_voltage),
        )
        self.bind_parameter(
            "frequency",
            MethodParameter(self.amplitude_frequency, self.set_amplitude_frequency),
        )
        self.bind_parameter(
            "amplitude.alc", WidgetParameter(self.amplitude_alc_check_box)
        )
        self.bind_parameter(
            "aperture.integration_time",
            WidgetParameter(self.integration_time_combo_box),
        )
        self.bind_parameter(
            "aperture.averaging_rate", WidgetParameter(self.averaging_rate_spin_box)
        )
        self.bind_parameter("correction.length", WidgetParameter(self.length_combo_box))
        self.bind_parameter(
            "correction.open.enabled", WidgetParameter(self.open_enabled_check_box)
        )
        self.bind_parameter(
            "correction.short.enabled", WidgetParameter(self.short_enabled_check_box)
        )

        self.restore_defaults()

    def amplitude_voltage(self) -> float:
        return self.amplitude_voltage_spin_box.value() / 1e3  # mV to V

    def set_amplitude_voltage(self, voltage: float) -> None:
        self.amplitude_voltage_spin_box.setValue(voltage * 1e3)  # V to mV

    def amplitude_frequency(self) -> float:
        return self.amplitude_frequency_spin_box.value() * 1e3  # kHz to Hz

    def set_amplitude_frequency(self, frequency: float) -> None:
        self.amplitude_frequency_spin_box.setValue(frequency / 1e3)  # Hz to kHz

    def restore_defaults(self) -> None:
        self.set_amplitude_voltage(1e0)
        self.set_amplitude_frequency(1e3)
        self.amplitude_alc_check_box.setChecked(False)
        self.integration_time_combo_box.setCurrentIndex(1)
        self.averaging_rate_spin_box.setValue(1)
        self.length_combo_box.setCurrentIndex(0)
        self.open_enabled_check_box.setChecked(False)
        self.short_enabled_check_box.setChecked(False)

    def set_locked(self, state: bool) -> None:
        self.amplitude_voltage_spin_box.setEnabled(not state)
        self.amplitude_frequency_spin_box.setEnabled(not state)
        self.amplitude_alc_check_box.setEnabled(not state)
        self.integration_time_combo_box.setEnabled(not state)
        self.averaging_rate_spin_box.setEnabled(not state)
        self.length_combo_box.setEnabled(not state)
        self.open_enabled_check_box.setEnabled(not state)
        self.short_enabled_check_box.setEnabled(not state)


class BrandBoxPanel(InstrumentPanel):
    CHANNELS: list[str] = [
        "A1", "B1", "C1",
        "A2", "B2", "C2",
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("BrandBox", parent)

        # Channels

        self.channel_check_boxes: dict[str, QtWidgets.QCheckBox] = {}

        self.channels_group_box = QtWidgets.QGroupBox("Channels")

        channels_layout = QtWidgets.QGridLayout(self.channels_group_box)

        # Create and place checkboxes in the grid
        for i, channel in enumerate(self.CHANNELS):
            check_box = QtWidgets.QCheckBox()
            check_box.setText(channel)
            check_box.setStatusTip(channel)
            self.channel_check_boxes[channel] = check_box

            row = i // 3   # 3 per row
            col = i % 3
            channels_layout.addWidget(check_box, row, col)

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.channels_group_box)
        left_layout.addStretch()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        # Parameters

        self.bind_parameter(
            "channels", MethodParameter(self.closed_channels, self.set_closed_channels)
        )

        self.restore_defaults()

    def closed_channels(self) -> list[str]:
        channels: list[str] = []
        for channel, check_box in self.channel_check_boxes.items():
            if check_box.isChecked():
                channels.append(channel)
        return channels

    def set_closed_channels(self, channels: list[str]) -> None:
        selected = set(channels)
        for channel, check_box in self.channel_check_boxes.items():
            check_box.setChecked(channel in selected)

    def restore_defaults(self) -> None:
        self.set_closed_channels([])

    def set_locked(self, state: bool) -> None:
        for check_box in self.channel_check_boxes.values():
            check_box.setEnabled(not state)


class K707BPanel(InstrumentPanel):
    CHANNELS: list[str] = [
        "1A01", "1A02", "1A03", "1A04", "1A05", "1A06", "1A07", "1A08", "1A09", "1A11", "1A12",
        "1B01", "1B02", "1B03", "1B04", "1B05", "1B06", "1B07", "1B08", "1B09", "1B11", "1B12",
        "1C01", "1C02", "1C03", "1C04", "1C05", "1C06", "1C07", "1C08", "1C09", "1C11", "1C12",
        "1D01", "1D02", "1D03", "1D04", "1D05", "1D06", "1D07", "1D08", "1D09", "1D11", "1D12",
        "1E01", "1E02", "1E03", "1E04", "1E05", "1E06", "1E07", "1E08", "1E09", "1E11", "1E12",
        "1F01", "1F02", "1F03", "1F04", "1F05", "1F06", "1F07", "1F08", "1F09", "1F11", "1F12",
        "1G01", "1G02", "1G03", "1G04", "1G05", "1G06", "1G07", "1G08", "1G09", "1G11", "1G12",
        "2A01", "2A02", "2A03", "2A04", "2A05", "2A06", "2A07", "2A08", "2A09", "2A11", "2A12",
        "2B01", "2B02", "2B03", "2B04", "2B05", "2B06", "2B07", "2B08", "2B09", "2B11", "2B12",
        "2C01", "2C02", "2C03", "2C04", "2C05", "2C06", "2C07", "2C08", "2C09", "2C11", "2C12",
        "2D01", "2D02", "2D03", "2D04", "2D05", "2D06", "2D07", "2D08", "2D09", "2D11", "2D12",
        "2E01", "2E02", "2E03", "2E04", "2E05", "2E06", "2E07", "2E08", "2E09", "2E11", "2E12",
        "2F01", "2F02", "2F03", "2F04", "2F05", "2F06", "2F07", "2F08", "2F09", "2F11", "2F12",
        "2G01", "2G02", "2G03", "2G04", "2G05", "2G06", "2G07", "2G08", "2G09", "2G11", "2G12",
        "3A01", "3A02", "3A03", "3A04", "3A05", "3A06", "3A07", "3A08", "3A09", "3A11", "3A12",
        "3B01", "3B02", "3B03", "3B04", "3B05", "3B06", "3B07", "3B08", "3B09", "3B11", "3B12",
        "3C01", "3C02", "3C03", "3C04", "3C05", "3C06", "3C07", "3C08", "3C09", "3C11", "3C12",
        "3D01", "3D02", "3D03", "3D04", "3D05", "3D06", "3D07", "3D08", "3D09", "3D11", "3D12",
        "3E01", "3E02", "3E03", "3E04", "3E05", "3E06", "3E07", "3E08", "3E09", "3E11", "3E12",
        "3F01", "3F02", "3F03", "3F04", "3F05", "3F06", "3F07", "3F08", "3F09", "3F11", "3F12",
        "3G01", "3G02", "3G03", "3G04", "3G05", "3G06", "3G07", "3G08", "3G09", "3G11", "3G12",
        "4A01", "4A02", "4A03", "4A04", "4A05", "4A06", "4A07", "4A08", "4A09", "4A11", "4A12",
        "4B01", "4B02", "4B03", "4B04", "4B05", "4B06", "4B07", "4B08", "4B09", "4B11", "4B12",
        "4C01", "4C02", "4C03", "4C04", "4C05", "4C06", "4C07", "4C08", "4C09", "4C11", "4C12",
        "4D01", "4D02", "4D03", "4D04", "4D05", "4D06", "4D07", "4D08", "4D09", "4D11", "4D12",
        "4E01", "4E02", "4E03", "4E04", "4E05", "4E06", "4E07", "4E08", "4E09", "4E11", "4E12",
        "4F01", "4F02", "4F03", "4F04", "4F05", "4F06", "4F07", "4F08", "4F09", "4F11", "4F12",
        "4G01", "4G02", "4G03", "4G04", "4G05", "4G06", "4G07", "4G08", "4G09", "4G11", "4G12",
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K707B", parent)

        # Channels

        self.channel_check_boxes: dict[str, QtWidgets.QCheckBox] = {}

        self.scroll_container = QtWidgets.QWidget()
        channels_layout = QtWidgets.QGridLayout(self.scroll_container)

        # Create and place checkboxes in the grid
        for i, channel in enumerate(self.CHANNELS):
            check_box = QtWidgets.QCheckBox()
            check_box.setText(channel)
            check_box.setStatusTip(channel)
            self.channel_check_boxes[channel] = check_box

            row = i // 11  # 11 per row
            col = i % 11
            channels_layout.addWidget(check_box, row, col)

        self.scroll_area = QtWidgets.QScrollArea()
        # self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_container)

        self.channels_group_box = QtWidgets.QGroupBox("Channels")

        channels_group_box_layout = QtWidgets.QVBoxLayout(self.channels_group_box)
        channels_group_box_layout.addWidget(self.scroll_area)

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.channels_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.setStretch(0, 1)

        # Parameters

        self.bind_parameter(
            "channels", MethodParameter(self.closed_channels, self.set_closed_channels)
        )

        self.restore_defaults()

    def closed_channels(self) -> list[str]:
        channels: list[str] = []
        for channel, check_box in self.channel_check_boxes.items():
            if check_box.isChecked():
                channels.append(channel)
        return channels

    def set_closed_channels(self, channels: list[str]) -> None:
        selected = set(channels)
        for channel, check_box in self.channel_check_boxes.items():
            check_box.setChecked(channel in selected)

    def restore_defaults(self) -> None:
        self.set_closed_channels([])

    def set_locked(self, state: bool) -> None:
        self.scroll_container.setEnabled(not state)


class K708BPanel(InstrumentPanel):
    CHANNELS: list[str] = [
        "1A00", "1A01", "1A02", "1A03", "1A04", "1A05", "1A06", "1A07", "1A08",
        "1B00", "1B01", "1B02", "1B03", "1B04", "1B05", "1B06", "1B07", "1B08",
        "1C00", "1C01", "1C02", "1C03", "1C04", "1C05", "1C06", "1C07", "1C08",
        "1D00", "1D01", "1D02", "1D03", "1D04", "1D05", "1D06", "1D07", "1D08",
        "1E00", "1E01", "1E02", "1E03", "1E04", "1E05", "1E06", "1E07", "1E08",
        "1F00", "1F01", "1F02", "1F03", "1F04", "1F05", "1F06", "1F07", "1F08",
        "1G00", "1G01", "1G02", "1G03", "1G04", "1G05", "1G06", "1G07", "1G08",
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K708B", parent)

        # Channels

        self.channel_check_boxes: dict[str, QtWidgets.QCheckBox] = {}

        self.scroll_container = QtWidgets.QWidget()
        channels_layout = QtWidgets.QGridLayout(self.scroll_container)

        # Create and place checkboxes in the grid
        for i, channel in enumerate(self.CHANNELS):
            check_box = QtWidgets.QCheckBox()
            check_box.setText(channel)
            check_box.setStatusTip(channel)
            self.channel_check_boxes[channel] = check_box

            row = i // 9  # 9 per row
            col = i % 9
            channels_layout.addWidget(check_box, row, col)

        self.scroll_area = QtWidgets.QScrollArea()
        # self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_container)

        self.channels_group_box = QtWidgets.QGroupBox("Channels")

        channels_group_box_layout = QtWidgets.QVBoxLayout(self.channels_group_box)
        channels_group_box_layout.addWidget(self.scroll_area)

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.channels_group_box)
        left_layout.addStretch()
        left_layout.setStretch(0, 2)
        left_layout.setStretch(1, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.setStretch(0, 1)

        # Parameters

        self.bind_parameter(
            "channels", MethodParameter(self.closed_channels, self.set_closed_channels)
        )

        self.restore_defaults()

    def closed_channels(self) -> list[str]:
        channels: list[str] = []
        for channel, check_box in self.channel_check_boxes.items():
            if check_box.isChecked():
                channels.append(channel)
        return channels

    def set_closed_channels(self, channels: list[str]) -> None:
        selected = set(channels)
        for channel, check_box in self.channel_check_boxes.items():
            check_box.setChecked(channel in selected)

    def restore_defaults(self) -> None:
        self.set_closed_channels([])

    def set_locked(self, state: bool) -> None:
        self.scroll_container.setEnabled(not state)
