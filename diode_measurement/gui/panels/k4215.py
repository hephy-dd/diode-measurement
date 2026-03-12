from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..panel import InstrumentPanel, WidgetParameter, MethodParameter

__all__ = ["K4215Panel", "K4215CorrectionDialog"]


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
