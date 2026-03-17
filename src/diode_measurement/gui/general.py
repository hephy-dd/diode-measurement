from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..utils import convert

__all__ = ["GeneralWidget"]


class GeneralWidget(QtWidgets.QWidget):
    instruments_changed = QtCore.Signal()
    current_compliance_changed = QtCore.Signal(float)
    continue_in_compliance_changed = QtCore.Signal(bool)
    waiting_time_continuous_changed = QtCore.Signal(float)
    change_voltage_clicked = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("General")

        self._current_compliance_locked: bool = False

        self._create_widgets()
        self._create_layout()

    def _create_widgets(self) -> None:
        self.measurement_combo_box = QtWidgets.QComboBox(self)

        self.smu_check_box = QtWidgets.QCheckBox("SMU", self)
        self.smu_check_box.checkStateChanged.connect(self.instruments_changed)

        self.smu2_check_box = QtWidgets.QCheckBox("SMU2", self)
        self.smu2_check_box.checkStateChanged.connect(self.instruments_changed)

        self.elm_check_box = QtWidgets.QCheckBox("ELM", self)
        self.elm_check_box.checkStateChanged.connect(self.instruments_changed)

        self.elm2_check_box = QtWidgets.QCheckBox("ELM2", self)
        self.elm2_check_box.checkStateChanged.connect(self.instruments_changed)

        self.lcr_check_box = QtWidgets.QCheckBox("LCR", self)
        self.lcr_check_box.checkStateChanged.connect(self.instruments_changed)

        self.dmm_check_box = QtWidgets.QCheckBox("DMM", self)
        self.dmm_check_box.checkStateChanged.connect(self.instruments_changed)

        self.tcu_check_box = QtWidgets.QCheckBox("TCU", self)
        self.tcu_check_box.checkStateChanged.connect(self.instruments_changed)

        self.switch_check_box = QtWidgets.QCheckBox("Switch", self)
        self.switch_check_box.checkStateChanged.connect(self.instruments_changed)

        self.begin_voltage_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.begin_voltage_spin_box.setDecimals(3)
        self.begin_voltage_spin_box.setRange(-3030.0, +3030.0)
        self.begin_voltage_spin_box.setSuffix(" V")

        self.end_voltage_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.end_voltage_spin_box.setDecimals(3)
        self.end_voltage_spin_box.setRange(-3030.0, +3030.0)
        self.end_voltage_spin_box.setSuffix(" V")

        self.step_voltage_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.step_voltage_spin_box.setDecimals(3)
        self.step_voltage_spin_box.setRange(0, +3030.0)
        self.step_voltage_spin_box.setSuffix(" V")

        self.waiting_time_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time_spin_box.setSuffix(" s")

        self.bias_voltage_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.bias_voltage_spin_box.setDecimals(3)
        self.bias_voltage_spin_box.setRange(-3030.0, +3030.0)
        self.bias_voltage_spin_box.setSuffix(" V")

        self.current_compliance_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.current_compliance_spin_box.setDecimals(3)
        self.current_compliance_spin_box.setRange(0.0, +2000.0)
        self.current_compliance_spin_box.setSuffix(" uA")
        self.current_compliance_spin_box.editingFinished.connect(
            lambda: self.current_compliance_changed.emit(self.current_compliance())
        )

        self.continue_in_compliance_check_box = QtWidgets.QCheckBox(self)
        self.continue_in_compliance_check_box.setText("Continue in Compliance")
        self.continue_in_compliance_check_box.setStatusTip(
            "Continue measurement when source in compliance."
        )
        self.continue_in_compliance_check_box.setChecked(False)
        self.continue_in_compliance_check_box.toggled.connect(
            lambda checked: self.continue_in_compliance_changed.emit(checked)
        )

        self.sample_line_edit = QtWidgets.QLineEdit(self)

        completer = QtWidgets.QCompleter()
        completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)

        model = QtWidgets.QFileSystemModel(completer)
        model.setFilter(
            QtCore.QDir.Filter.Dirs
            | QtCore.QDir.Filter.Drives
            | QtCore.QDir.Filter.NoDotAndDotDot
            | QtCore.QDir.Filter.AllDirs
        )
        model.setRootPath(QtCore.QDir.rootPath())
        completer.setModel(model)

        self.output_line_edit = QtWidgets.QLineEdit(self)
        self.output_line_edit.setCompleter(completer)

        self.output_tool_button = QtWidgets.QToolButton(self)
        self.output_tool_button.setText("...")
        self.output_tool_button.setStatusTip("Select output directory")
        self.output_tool_button.clicked.connect(self.on_select_output)

        self.waiting_time_continuous_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time_continuous_spin_box.setSuffix(" s")
        self.waiting_time_continuous_spin_box.setDecimals(2)
        self.waiting_time_continuous_spin_box.setStatusTip(
            "Waiting time for continuous measurement"
        )
        self.waiting_time_continuous_spin_box.editingFinished.connect(
            lambda: self.waiting_time_continuous_changed.emit(
                self.waiting_time_continuous()
            )
        )

        self.change_voltage_button = QtWidgets.QToolButton(self)
        self.change_voltage_button.setText("&Change Voltage...")
        self.change_voltage_button.setStatusTip(
            "Change voltage in continuous measurement"
        )
        self.change_voltage_button.setEnabled(False)
        self.change_voltage_button.clicked.connect(self.change_voltage_clicked)

        self.measurement_group_box = QtWidgets.QGroupBox(self)
        self.measurement_group_box.setTitle("Measurement")

        self.output_group_box = QtWidgets.QGroupBox(self)
        self.output_group_box.setTitle("Output")
        self.output_group_box.setCheckable(True)
        self.output_group_box.setChecked(False)

        self.ramp_group_box = QtWidgets.QGroupBox(self)
        self.ramp_group_box.setTitle("Ramp")

        self.bias_group_box = QtWidgets.QGroupBox(self)
        self.bias_group_box.setTitle("Bias Voltage (SMU2)")

        self.compliance_group_box = QtWidgets.QGroupBox(self)
        self.compliance_group_box.setTitle("Compliance")

        self.continuous_group_box = QtWidgets.QGroupBox(self)
        self.continuous_group_box.setTitle("Continuous Meas.")

    def _create_layout(self) -> None:
        vbox_layout = QtWidgets.QVBoxLayout(self.measurement_group_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Type"))
        vbox_layout.addWidget(self.measurement_combo_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Instruments"))
        self.instrument_widget = QtWidgets.QWidget()
        vbox_layout.addWidget(self.instrument_widget)
        self.instrument_layout = QtWidgets.QHBoxLayout(self.instrument_widget)
        self.instrument_layout.addWidget(self.smu_check_box)
        self.instrument_layout.addWidget(self.smu2_check_box)
        self.instrument_layout.addWidget(self.elm_check_box)
        self.instrument_layout.addWidget(self.elm2_check_box)
        self.instrument_layout.addWidget(self.lcr_check_box)
        self.instrument_layout.addWidget(self.dmm_check_box)
        self.instrument_layout.addWidget(self.tcu_check_box)
        self.instrument_layout.addWidget(self.switch_check_box)
        self.instrument_layout.addStretch()
        self.instrument_layout.setContentsMargins(0, 0, 0, 0)

        vbox_layout = QtWidgets.QVBoxLayout(self.output_group_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Sample Name"))
        vbox_layout.addWidget(self.sample_line_edit)
        vbox_layout.addWidget(QtWidgets.QLabel("Output Path"))
        output_layout = QtWidgets.QHBoxLayout()
        output_layout.addWidget(self.output_line_edit)
        output_layout.addWidget(self.output_tool_button)
        vbox_layout.addLayout(output_layout)
        vbox_layout.addStretch()

        vbox_layout = QtWidgets.QVBoxLayout(self.ramp_group_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Begin"))
        vbox_layout.addWidget(self.begin_voltage_spin_box)
        vbox_layout.addWidget(QtWidgets.QLabel("End"))
        vbox_layout.addWidget(self.end_voltage_spin_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Step"))
        vbox_layout.addWidget(self.step_voltage_spin_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Waiting Time"))
        vbox_layout.addWidget(self.waiting_time_spin_box)

        vbox_layout = QtWidgets.QVBoxLayout(self.bias_group_box)
        vbox_layout.addWidget(self.bias_voltage_spin_box)
        vbox_layout.addStretch()

        vbox_layout = QtWidgets.QVBoxLayout(self.compliance_group_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Current"))
        vbox_layout.addWidget(self.current_compliance_spin_box)
        vbox_layout.addWidget(self.continue_in_compliance_check_box)
        vbox_layout.addStretch()

        waiting_time_layout = QtWidgets.QHBoxLayout()
        waiting_time_layout.addWidget(self.waiting_time_continuous_spin_box)

        vbox_layout = QtWidgets.QVBoxLayout(self.continuous_group_box)
        vbox_layout.addWidget(QtWidgets.QLabel("Waiting Time"))
        vbox_layout.addLayout(waiting_time_layout)
        vbox_layout.addWidget(self.change_voltage_button)
        vbox_layout.addStretch()

        layout = QtWidgets.QHBoxLayout(self)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(self.measurement_group_box)
        vbox_layout.addWidget(self.output_group_box)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(self.ramp_group_box)
        vbox_layout.addWidget(self.bias_group_box)
        layout.addLayout(vbox_layout)

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(self.compliance_group_box)
        vbox_layout.addWidget(self.continuous_group_box)
        layout.addLayout(vbox_layout)

        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)
        layout.setStretch(2, 1)

    def set_idle_state(self) -> None:
        self.measurement_combo_box.setEnabled(True)
        self.instrument_widget.setEnabled(True)
        self.output_group_box.setEnabled(True)
        self.begin_voltage_spin_box.setEnabled(True)
        self.end_voltage_spin_box.setEnabled(True)
        self.step_voltage_spin_box.setEnabled(True)
        self.waiting_time_spin_box.setEnabled(True)
        self.bias_voltage_spin_box.setEnabled(True)
        self.change_voltage_button.setEnabled(False)
        self.current_compliance_spin_box.setEnabled(not self._current_compliance_locked)
        self.continue_in_compliance_check_box.setEnabled(True)

    def set_running_state(self) -> None:
        self.measurement_combo_box.setEnabled(False)
        self.instrument_widget.setEnabled(False)
        self.output_group_box.setEnabled(False)
        self.begin_voltage_spin_box.setEnabled(False)
        self.end_voltage_spin_box.setEnabled(False)
        self.step_voltage_spin_box.setEnabled(False)
        self.waiting_time_spin_box.setEnabled(False)
        self.bias_voltage_spin_box.setEnabled(False)

    def set_stopping_state(self):
        self.change_voltage_button.setEnabled(False)
        self.current_compliance_spin_box.setEnabled(False)
        self.continue_in_compliance_check_box.setEnabled(False)

    def add_measurement(self, spec: dict) -> None:
        self.measurement_combo_box.addItem(spec.get("title", ""), spec)

    def current_measurement(self) -> Optional[dict]:
        return self.measurement_combo_box.currentData()

    def set_current_measurement(self, measurement_id: str) -> None:
        for index in range(self.measurement_combo_box.count()):
            data = self.measurement_combo_box.itemData(index)
            if isinstance(data, dict):
                if data.get("id") == measurement_id:
                    self.measurement_combo_box.setCurrentIndex(index)
                    return

    def set_measurement_roles(self, roles: list[str]) -> None:
        self.set_smu_enabled("smu" in roles)
        self.set_smu2_enabled("smu2" in roles)
        self.set_elm_enabled("elm" in roles)
        self.set_elm2_enabled("elm2" in roles)
        self.set_lcr_enabled("lcr" in roles)
        self.set_dmm_enabled("dmm" in roles)
        self.set_switch_enabled("switch" in roles)

    def is_smu_enabled(self):
        return self.smu_check_box.isChecked()

    def set_smu_enabled(self, enabled):
        return self.smu_check_box.setChecked(enabled)

    def is_smu2_enabled(self):
        return self.smu2_check_box.isChecked()

    def set_smu2_enabled(self, enabled):
        return self.smu2_check_box.setChecked(enabled)

    def is_elm_enabled(self):
        return self.elm_check_box.isChecked()

    def set_elm_enabled(self, enabled):
        return self.elm_check_box.setChecked(enabled)

    def is_elm2_enabled(self):
        return self.elm2_check_box.isChecked()

    def set_elm2_enabled(self, enabled):
        return self.elm2_check_box.setChecked(enabled)

    def is_lcr_enabled(self):
        return self.lcr_check_box.isChecked()

    def set_lcr_enabled(self, enabled):
        return self.lcr_check_box.setChecked(enabled)

    def is_dmm_enabled(self):
        return self.dmm_check_box.isChecked()

    def set_dmm_enabled(self, enabled):
        return self.dmm_check_box.setChecked(enabled)

    def is_tcu_enabled(self):
        return self.tcu_check_box.isChecked()

    def set_tcu_enabled(self, enabled):
        return self.tcu_check_box.setChecked(enabled)

    def is_switch_enabled(self):
        return self.switch_check_box.isChecked()

    def set_switch_enabled(self, enabled):
        return self.switch_check_box.setChecked(enabled)

    def is_output_enabled(self):
        return self.output_group_box.isChecked()

    def set_output_enabled(self, enabled: bool) -> None:
        self.output_group_box.setChecked(enabled)

    def sample_name(self) -> str:
        return self.sample_line_edit.text().strip()

    def set_sample_name(self, text: str) -> None:
        self.sample_line_edit.setText(text)

    def output_dir(self) -> str:
        return self.output_line_edit.text().strip()

    def set_output_dir(self, text: str) -> None:
        self.output_line_edit.setText(text)

    @QtCore.Slot()
    def on_select_output(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select ouput path", self.output_dir()
        )
        if path:
            self.set_output_dir(path)

    def set_voltage_unit(self, unit: str) -> None:
        self.begin_voltage_spin_box.setSuffix(f" {unit}")
        self.end_voltage_spin_box.setSuffix(f" {unit}")
        self.step_voltage_spin_box.setSuffix(f" {unit}")

    def begin_voltage(self) -> float:
        value = self.begin_voltage_spin_box.value()
        unit = self.begin_voltage_spin_box.suffix().strip()
        return convert(value, unit, "V")

    def set_begin_voltage(self, begin_voltage: float) -> None:
        unit = self.begin_voltage_spin_box.suffix().strip()
        self.begin_voltage_spin_box.setValue(convert(begin_voltage, "V", unit))

    def end_voltage(self) -> float:
        value = self.end_voltage_spin_box.value()
        unit = self.end_voltage_spin_box.suffix().strip()
        return convert(value, unit, "V")

    def set_end_voltage(self, end_voltage: float) -> None:
        unit = self.end_voltage_spin_box.suffix().strip()
        self.end_voltage_spin_box.setValue(convert(end_voltage, "V", unit))

    def step_voltage(self) -> float:
        value = self.step_voltage_spin_box.value()
        unit = self.step_voltage_spin_box.suffix().strip()
        return convert(value, unit, "V")

    def set_step_voltage(self, step_voltage: float):
        unit = self.step_voltage_spin_box.suffix().strip()
        self.step_voltage_spin_box.setValue(convert(step_voltage, "V", unit))

    def waiting_time(self) -> float:
        return self.waiting_time_spin_box.value()

    def set_waiting_time(self, waiting_time: float) -> None:
        self.waiting_time_spin_box.setValue(waiting_time)

    def bias_voltage(self) -> float:
        value = self.bias_voltage_spin_box.value()
        unit = self.bias_voltage_spin_box.suffix().strip()
        return convert(value, unit, "V")

    def set_bias_voltage(self, bias_voltage: float) -> None:
        unit = self.bias_voltage_spin_box.suffix().strip()
        self.bias_voltage_spin_box.setValue(convert(bias_voltage, "V", unit))

    def set_current_compliance_unit(self, unit: str) -> None:
        self.current_compliance_spin_box.setSuffix(f" {unit}")

    def current_compliance(self) -> float:
        value = self.current_compliance_spin_box.value()
        unit = self.current_compliance_spin_box.suffix().strip()
        return convert(value, unit, "A")

    def set_current_compliance(self, compliance: float) -> None:
        unit = self.current_compliance_spin_box.suffix().strip()
        return self.current_compliance_spin_box.setValue(convert(compliance, "A", unit))

    def set_current_compliance_locked(self, state: bool) -> None:
        self._current_compliance_locked = state
        self.current_compliance_spin_box.setEnabled(not state)

    def is_continue_in_compliance(self) -> bool:
        return self.continue_in_compliance_check_box.isChecked()

    def set_continue_in_compliance(self, enabled: bool) -> None:
        self.continue_in_compliance_check_box.setChecked(enabled)

    def waiting_time_continuous(self) -> float:
        return self.waiting_time_continuous_spin_box.value()

    def set_waiting_time_continuous(self, waiting_time: float) -> None:
        self.waiting_time_continuous_spin_box.setValue(waiting_time)

    def set_change_voltage_enabled(self, enabled: bool) -> None:
        self.change_voltage_button.setEnabled(enabled)
