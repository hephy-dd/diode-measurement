from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, WidgetParameter, MethodParameter

__all__ = ["A4284APanel"]


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
