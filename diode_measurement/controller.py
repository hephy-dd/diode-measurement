import logging
import math
import os
import threading
import time
import queue
from datetime import datetime
from typing import Any, Mapping, Optional

from PySide6 import QtCore, QtWidgets, QtStateMachine

# Source meter units
from .view.panels import K237Panel
from .view.panels import K2410Panel
from .view.panels import K2470Panel
from .view.panels import K2657APanel

# Electrometers
from .view.panels import K6514Panel
from .view.panels import K6517BPanel

# LCR meters
from .view.panels import K595Panel
from .view.panels import E4980APanel
from .view.panels import A4284APanel
from .view.panels import K4215Panel, K4215CorrectionDialog

# DMM
from .view.panels import K2700Panel

# Switches
from .view.panels import BrandBoxPanel

from .view.widgets import show_exception
from .view.dialogs import ChangeVoltageDialog

from .view.plots import CV2PlotWidget, CVPlotWidget, ItPlotWidget, IVPlotWidget

from .measurement import ReadingType, Measurement
from .measurement.iv import IVMeasurement
from .measurement.iv_bias import IVBiasMeasurement
from .measurement.cv import CVMeasurement

from .reader import Reader

from .utils import get_resource
from .utils import safe_filename
from .utils import format_metric

from .jobs import Job, MeasurementJob, K4215PerformCorrectionJob
from .cache import Cache
from .settings import DEFAULTS
from .state import State, FSMState

__all__ = ["Controller"]

logger = logging.getLogger(__name__)

MEASUREMENTS: dict = {
    "iv": IVMeasurement,
    "iv_bias": IVBiasMeasurement,
    "cv": CVMeasurement,
}


class Controller(QtCore.QObject):
    started = QtCore.Signal()
    aborted = QtCore.Signal()
    update = QtCore.Signal(dict)
    failed = QtCore.Signal(Exception)
    finished = QtCore.Signal()

    change_voltage_ready = QtCore.Signal()

    measurement_finished = QtCore.Signal()
    message_changed = QtCore.Signal(str)
    progress_changed = QtCore.Signal(int, int, int)

    def __init__(self, view, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)

        self._shutdown_event = threading.Event()
        self._background_inbox: queue.Queue[Job] = queue.Queue()
        self._background_thread = threading.Thread(target=self._handle_background_jobs)

        self.view = view

        self.is_exception_dialog_active: bool = False

        self.state: State = State()
        self.cache: Cache = Cache()

        # Controller
        self.iv_plots_controller = IVPlotsController(self)
        self.cv_plots_controller = CVPlotsController(self)

        self.change_voltage_controller = ChangeVoltageController(self.view, self.state, self)
        self.change_voltage_ready.connect(self.change_voltage_controller.on_change_voltage_ready)
        self.failed.connect(self.handle_exception)

        # Source meter unit
        role = self.view.add_role("SMU")
        role.add_instrument_panel(K237Panel())
        role.add_instrument_panel(K2410Panel())
        role.add_instrument_panel(K2470Panel())
        role.add_instrument_panel(K2657APanel())

        # Bias source meter unit
        role = self.view.add_role("SMU2")
        role.add_instrument_panel(K237Panel())
        role.add_instrument_panel(K2410Panel())
        role.add_instrument_panel(K2470Panel())
        role.add_instrument_panel(K2657APanel())

        # Electrometer
        role = self.view.add_role("ELM")
        role.add_instrument_panel(K6514Panel())
        role.add_instrument_panel(K6517BPanel())
        role.resource_widget.model_changed.connect(self.on_instruments_changed)  # HACK

        # Electrometer 2
        role = self.view.add_role("ELM2")
        role.add_instrument_panel(K6514Panel())
        role.add_instrument_panel(K6517BPanel())
        role.resource_widget.model_changed.connect(self.on_instruments_changed)  # HACK

        # LCR meter
        role = self.view.add_role("LCR")
        role.add_instrument_panel(K595Panel())
        role.add_instrument_panel(E4980APanel())
        role.add_instrument_panel(A4284APanel())
        panel = K4215Panel()
        panel.perform_correction_clicked.connect(self.on_lcr_perform_correction)
        role.add_instrument_panel(panel)

        # Temperatur
        role = self.view.add_role("DMM")
        role.add_instrument_panel(K2700Panel())

        # Switch
        role = self.view.add_role("Switch")
        role.add_instrument_panel(BrandBoxPanel())

        self.view.import_action.triggered.connect(lambda: self.on_import_file())

        self.view.start_action.triggered.connect(self.on_start_measurement)
        self.view.start_button.clicked.connect(self.view.start_action.trigger)

        self.view.stop_action.triggered.connect(self.aborted)
        self.view.stop_button.clicked.connect(self.view.stop_action.trigger)

        self.view.continuous_action.toggled.connect(self.on_continuous_toggled)
        self.view.continuous_check_box.checkStateChanged.connect(self.on_continuous_changed)

        for spec in DEFAULTS:
            self.view.general_widget.add_measurement(spec)
        self.view.general_widget.measurement_combo_box.currentIndexChanged.connect(self.on_measurement_changed)

        self.view.general_widget.output_line_edit.editingFinished.connect(self.on_output_editing_finished)
        self.view.general_widget.current_compliance_changed.connect(self.on_current_compliance_changed)
        self.view.general_widget.continue_in_compliance_changed.connect(self.on_continue_in_compliance_changed)
        self.view.general_widget.waiting_time_continuous_changed.connect(self.on_waiting_time_continuous_changed)

        self.on_measurement_changed(0)

        self.update.connect(self.on_update)

        self.view.general_widget.instruments_changed.connect(self.on_instruments_changed)

        self.on_instruments_changed()

        self.view.general_widget.smu_check_box.toggled.connect(self.on_toggle_smu)
        self.view.general_widget.smu2_check_box.toggled.connect(self.on_toggle_smu2)
        self.view.general_widget.elm_check_box.toggled.connect(self.on_toggle_elm)
        self.view.general_widget.elm2_check_box.toggled.connect(self.on_toggle_elm2)
        self.view.general_widget.lcr_check_box.toggled.connect(self.on_toggle_lcr)
        self.view.general_widget.dmm_check_box.toggled.connect(self.on_toggle_dmm)
        self.view.general_widget.switch_check_box.toggled.connect(self.on_toggle_switch)

        self.on_toggle_smu2(False)
        self.on_toggle_elm(False)
        self.on_toggle_elm2(False)
        self.on_toggle_lcr(False)
        self.on_toggle_dmm(False)
        self.on_toggle_switch(False)

        self.view.clear_message()
        self.view.clear_progress()

        self.message_changed.connect(self.view.set_message)
        self.progress_changed.connect(self.view.set_progress)

        # States

        self.idle_state = QtStateMachine.QState()
        self.idle_state.entered.connect(self.set_idle_state)

        self.running_state = QtStateMachine.QState()
        self.running_state.entered.connect(self.set_running_state)

        self.stopping_state = QtStateMachine.QState()
        self.stopping_state.entered.connect(self.set_stopping_state)

        # Transitions

        self.idle_state.addTransition(self.started, self.running_state)

        self.running_state.addTransition(self.finished, self.idle_state)
        self.running_state.addTransition(self.aborted, self.stopping_state)

        self.stopping_state.addTransition(self.finished, self.idle_state)

        # State machine

        self.state_machine = QtStateMachine.QStateMachine()
        self.state_machine.addState(self.idle_state)
        self.state_machine.addState(self.running_state)
        self.state_machine.addState(self.stopping_state)
        self.state_machine.setInitialState(self.idle_state)
        self.state_machine.start()

    def submit_background_job(self, job: Job) -> None:
        self._background_inbox.put_nowait(job)
        self.started.emit()

    def _handle_background_jobs(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                try:
                    job = self._background_inbox.get(timeout=0.25)
                except queue.Empty:
                    ...
                else:
                    try:
                        job()
                    except Exception as exc:
                        self.failed.emit(exc)
                    finally:
                        self.finished.emit()
            except Exception as exc:
                logger.exception(exc)

    def snapshot(self):
        """Return application state snapshot."""
        with self.cache:
            snapshot = {}
            snapshot["state"] = self.cache.get("fsm_state", FSMState.IDLE)  # TODO
            snapshot["measurement_type"] = self.cache.get("measurement_type")
            snapshot["sample"] = self.cache.get("sample")
            snapshot["source_voltage"] = self.cache.get("source_voltage")
            snapshot["smu_voltage"] = self.cache.get("smu_voltage")
            snapshot["smu_current"] = self.cache.get("smu_current")
            snapshot["smu2_voltage"] = self.cache.get("smu2_voltage")
            snapshot["smu2_current"] = self.cache.get("smu2_current")
            snapshot["elm_current"] = self.cache.get("elm_current")
            snapshot["elm2_current"] = self.cache.get("elm2_current")
            snapshot["lcr_capacity"] = self.cache.get("lcr_capacity")
            snapshot["temperature"] = self.cache.get("dmm_temperature")
            return snapshot

    def prepare_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {}

        current_measurement = self.view.general_widget.current_measurement() or {}

        state["sample"] = self.view.general_widget.sample_name()
        state["measurement_type"] = current_measurement.get("type")
        state["timestamp"] = time.time()

        state["continuous"] = self.view.is_continuous()
        state["reset_instruments"] = self.view.is_reset_instruments()
        state["auto_reconnect"] = self.view.is_auto_reconnect()
        state["voltage_begin"] = self.view.general_widget.begin_voltage()
        state["voltage_end"] = self.view.general_widget.end_voltage()
        state["voltage_step"] = self.view.general_widget.step_voltage()
        state["waiting_time"] = self.view.general_widget.waiting_time()
        state["bias_voltage"] = self.view.general_widget.bias_voltage()
        state["current_compliance"] = self.view.general_widget.current_compliance()
        state["continue_in_compliance"] = self.view.general_widget.is_continue_in_compliance()
        state["waiting_time_continuous"] = self.view.general_widget.waiting_time_continuous()

        roles: dict[str, Any] = state.setdefault("roles", {})

        for role in self.view.roles():
            key = role.name().lower()
            resource = role.resource_widget.resource_name()
            resource_name, visa_library = get_resource(resource)
            config = roles.setdefault(key, {})
            config.update({
                "resource_name": resource_name,
                "visa_library": visa_library,
                "model": role.resource_widget.model(),
                "termination": role.resource_widget.termination(),
                "timeout": role.resource_widget.timeout()
            })
            config.update({"options": role.current_config()})

        if self.view.general_widget.is_smu_enabled():
            state["source_role"] = "smu"
        elif self.view.general_widget.is_elm_enabled():
            state["source_role"] = "elm"
        elif self.view.general_widget.is_lcr_enabled():
            state["source_role"] = "lcr"

        if self.view.general_widget.is_smu2_enabled():
            state["bias_source_role"] = "smu2"

        roles.setdefault("smu", {}).update({"enabled": self.view.general_widget.is_smu_enabled()})
        roles.setdefault("smu2", {}).update({"enabled": self.view.general_widget.is_smu2_enabled()})
        roles.setdefault("elm", {}).update({"enabled": self.view.general_widget.is_elm_enabled()})
        roles.setdefault("elm2", {}).update({"enabled": self.view.general_widget.is_elm2_enabled()})
        roles.setdefault("lcr", {}).update({"enabled": self.view.general_widget.is_lcr_enabled()})
        roles.setdefault("dmm", {}).update({"enabled": self.view.general_widget.is_dmm_enabled()})
        roles.setdefault("switch", {}).update({"enabled": self.view.general_widget.is_switch_enabled()})

        for key, value in state.items():
            logger.info("> %s: %s", key, value)

        return state

    def start(self) -> None:
        if self._background_thread.ident is not None:
            return
        self._background_thread.start()

    def shutdown(self) -> None:
        self._shutdown_event.set()
        self.state_machine.stop()
        if self._background_thread.is_alive():
            self._background_thread.join(timeout=10.0)
            if self._background_thread.is_alive():
                logger.warning("Background thread did not stop within timeout")

    def read_settings(self) -> None:
        settings = QtCore.QSettings()

        geometry = settings.value("mainwindow/geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if geometry.isEmpty():  # type: ignore
            self.view.resize(800, 600)
        else:
            self.view.restoreGeometry(geometry)

        state = settings.value("mainwindow/state", QtCore.QByteArray(), QtCore.QByteArray)
        self.view.restoreState(state)

        continuous = settings.value("continuous", False, bool)
        self.view.set_continuous(continuous)

        reset = settings.value("reset", False, bool)
        self.view.set_reset_instruments(reset)

        auto_reconnect = settings.value("autoReconnect", False, bool)
        self.view.set_auto_reconnect(auto_reconnect)

        settings.beginGroup("generalTab")

        index = settings.value("measurement/index", 0, int)
        self.view.general_widget.measurement_combo_box.setCurrentIndex(index)

        enabled = settings.value("smu/enabled", False, bool)
        self.view.general_widget.set_smu_enabled(enabled)

        enabled = settings.value("smu2/enabled", False, bool)
        self.view.general_widget.set_smu2_enabled(enabled)

        enabled = settings.value("elm/enabled", False, bool)
        self.view.general_widget.set_elm_enabled(enabled)

        enabled = settings.value("elm2/enabled", False, bool)
        self.view.general_widget.set_elm2_enabled(enabled)

        enabled = settings.value("lcr/enabled", False, bool)
        self.view.general_widget.set_lcr_enabled(enabled)

        enabled = settings.value("dmm/enabled", False, bool)
        self.view.general_widget.set_dmm_enabled(enabled)

        enabled = settings.value("switch/enabled", False, bool)
        self.view.general_widget.set_switch_enabled(enabled)

        output_enabled = settings.value("outputEnabled", False, bool)
        self.view.general_widget.set_output_enabled(output_enabled)

        sample_name = settings.value("sampleName", "Unnamed")
        self.view.general_widget.set_sample_name(sample_name)

        output_dir = settings.value("outputDir", os.path.expanduser("~"))
        self.view.general_widget.set_output_dir(output_dir)

        begin_voltage = settings.value("beginVoltage", 1, float)
        self.view.general_widget.set_begin_voltage(begin_voltage)

        end_voltage = settings.value("endVoltage", 1, float)
        self.view.general_widget.set_end_voltage(end_voltage)

        step_voltage = settings.value("stepVoltage", 1, float)
        self.view.general_widget.set_step_voltage(step_voltage)

        waiting_time = settings.value("waitingTime", 1, float)
        self.view.general_widget.set_waiting_time(waiting_time)

        bias_voltage = settings.value("biasVoltage", 0, float)
        self.view.general_widget.set_bias_voltage(bias_voltage)

        current_compliance = settings.value("currentCompliance", 1, float)
        self.view.general_widget.set_current_compliance(current_compliance)

        continue_in_compliance = settings.value("continueInCompliance", False, bool)
        self.view.general_widget.set_continue_in_compliance(continue_in_compliance)

        waiting_time_continuous = settings.value("waitingTimeContinuous", 1, float)
        self.view.general_widget.set_waiting_time_continuous(waiting_time_continuous)

        settings.endGroup()

        settings.beginGroup("roles")

        for role in self.view.roles():
            name = role.name().lower()
            settings.beginGroup(name)
            role.set_model(settings.value("model", ""))
            role.set_resource_name(settings.value("resource", ""))
            role.set_termination(settings.value("termination", ""))
            role.set_timeout(settings.value("timeout", 4, int))
            role.set_resources(settings.value("resources", {}))
            role.set_configs(settings.value("configs", {}))
            settings.endGroup()

        settings.endGroup()

        self.on_instruments_changed()

    def write_settings(self) -> None:
        settings = QtCore.QSettings()

        settings.setValue("mainwindow/geometry", self.view.saveGeometry())
        settings.setValue("mainwindow/state", self.view.saveState())

        continuous = self.view.is_continuous()
        settings.setValue("continuous", continuous)

        reset = self.view.is_reset_instruments()
        settings.setValue("reset", reset)

        auto_reconnect = self.view.is_auto_reconnect()
        settings.setValue("autoReconnect", auto_reconnect)

        settings.beginGroup("generalTab")

        measurement_index = self.view.general_widget.measurement_combo_box.currentIndex()
        settings.setValue("measurement/index", measurement_index)

        enabled = self.view.general_widget.is_smu_enabled()
        settings.setValue("smu/enabled", enabled)

        enabled = self.view.general_widget.is_smu2_enabled()
        settings.setValue("smu2/enabled", enabled)

        enabled = self.view.general_widget.is_elm_enabled()
        settings.setValue("elm/enabled", enabled)

        enabled = self.view.general_widget.is_elm2_enabled()
        settings.setValue("elm2/enabled", enabled)

        enabled = self.view.general_widget.is_lcr_enabled()
        settings.setValue("lcr/enabled", enabled)

        enabled = self.view.general_widget.is_dmm_enabled()
        settings.setValue("dmm/enabled", enabled)

        enabled = self.view.general_widget.is_switch_enabled()
        settings.setValue("switch/enabled", enabled)

        output_enabled = self.view.general_widget.is_output_enabled()
        settings.setValue("outputEnabled", output_enabled)

        sample_name = self.view.general_widget.sample_name()
        settings.setValue("sampleName", sample_name)

        output_dir = self.view.general_widget.output_dir()
        settings.setValue("outputDir", output_dir)

        begin_voltage = self.view.general_widget.begin_voltage()
        settings.setValue("beginVoltage", begin_voltage)

        end_voltage = self.view.general_widget.end_voltage()
        settings.setValue("endVoltage", end_voltage)

        step_voltage = self.view.general_widget.step_voltage()
        settings.setValue("stepVoltage", step_voltage)

        waiting_time = self.view.general_widget.waiting_time()
        settings.setValue("waitingTime", waiting_time)

        bias_voltage = self.view.general_widget.bias_voltage()
        settings.setValue("biasVoltage", bias_voltage)

        current_compliance = self.view.general_widget.current_compliance()
        settings.setValue("currentCompliance", current_compliance)

        continueInCompliance = self.view.general_widget.is_continue_in_compliance()
        settings.setValue("continueInCompliance", continueInCompliance)

        waiting_time_continuous = self.view.general_widget.waiting_time_continuous()
        settings.setValue("waitingTimeContinuous", waiting_time_continuous)

        settings.endGroup()

        settings.beginGroup("roles")

        for role in self.view.roles():
            name = role.name().lower()
            settings.beginGroup(name)
            settings.setValue("model", role.model())
            settings.setValue("resource", role.resource_name())
            settings.setValue("termination", role.termination())
            settings.setValue("timeout", role.timeout())
            settings.setValue("resources", role.resources())
            settings.setValue("configs", role.configs())
            settings.endGroup()

        settings.endGroup()

    @QtCore.Slot()
    def on_import_file(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.view,
            "Select measurement file",
            self.view.general_widget.output_dir(),
            "Text (*.txt);;All (*);;"
        )
        if filename:
            logger.info("Importing measurement file: %s", filename)
            self.view.setEnabled(False)
            self.view.clear()
            self.iv_plots_controller.clear()
            self.cv_plots_controller.clear()
            try:
                # Open in binary mode!
                with open(filename, "rb") as fp:
                    reader = Reader(fp)
                    meta = reader.read_meta()
                    data = reader.read_data()
                    continuous_data = reader.read_data()

                # Meta
                self.view.general_widget.measurement_combo_box.setCurrentIndex(-1)
                if meta.get("measurement_type"):
                    for index in range(self.view.general_widget.measurement_combo_box.count()):
                        spec = self.view.general_widget.measurement_combo_box.itemData(index)
                        if spec["type"] == meta.get("measurement_type"):
                            self.view.general_widget.measurement_combo_box.setCurrentIndex(index)
                            break
                if meta.get("sample"):
                    self.view.general_widget.set_sample_name(meta.get("sample"))
                if meta.get("voltage_begin"):
                    self.view.general_widget.set_begin_voltage(meta.get("voltage_begin"))
                if meta.get("voltage_end"):
                    self.view.general_widget.set_end_voltage(meta.get("voltage_end"))
                if meta.get("voltage_step"):
                    self.view.general_widget.set_step_voltage(meta.get("voltage_step"))
                if meta.get("waiting_time"):
                    self.view.general_widget.set_waiting_time(meta.get("waiting_time"))
                if meta.get("waiting_time_continuous"):
                    self.view.general_widget.set_waiting_time_continuous(meta.get("waiting_time_continuous"))
                if meta.get("current_compliance"):
                    self.view.general_widget.set_current_compliance(meta.get("current_compliance"))

                # Data
                if meta.get("measurement_type") in ["iv", "iv_bias"]:
                    self.iv_plots_controller.on_load_iv_readings(data)
                    self.iv_plots_controller.on_load_it_readings(continuous_data)
                if meta.get("measurement_type") in ["cv"]:
                    self.cv_plots_controller.load_cv_readings(data)
                    self.cv_plots_controller.load_cv2_readings(data)
            finally:
                self.view.setEnabled(True)

    # State slots

    def set_idle_state(self) -> None:
        self.view.control_tab_widget.setEnabled(True)
        self.view.set_idle_state()
        self.view.clear_message()
        self.view.clear_progress()
        self.update_continuous_option()
        with self.cache:
            self.cache.clear()
        self.iv_plots_controller.update_timer.stop()
        self.cv_plots_controller.update_timer.stop()

    def set_running_state(self) -> None:
        self.view.set_running_state()

    def set_stopping_state(self) -> None:
        self.view.set_stopping_state()
        self.view.set_message("Stop requested...")
        self.state.update({"stop_requested": True})

    # Slots

    def handle_exception(self, exc: Exception) -> None:
        """Shows up to one error message at a time."""
        if not self.is_exception_dialog_active:
            self.is_exception_dialog_active = True
            show_exception(exc, self.view)
            self.is_exception_dialog_active = False

    @QtCore.Slot(dict)
    def on_update(self, data: dict) -> None:
        cache = {}
        if "fsm_state" in data:
            cache.update({"fsm_state": data.get("fsm_state")})
        if "source_voltage" in data:
            self.view.updateSourceVoltage(data.get("source_voltage"))
            cache.update({"source_voltage": data.get("source_voltage")})
        if "bias_source_voltage" in data:
            self.view.updateBiasSourceVoltage(data.get("bias_source_voltage"))
            cache.update({"bias_source_voltage": data.get("bias_source_voltage")})
        if "smu_voltage" in data:
            self.view.updateSMUVoltage(data.get("smu_voltage"))
            cache.update({"smu_voltage": data.get("smu_voltage")})
        if "smu_current" in data:
            self.view.updateSMUCurrent(data.get("smu_current"))
            cache.update({"smu_current": data.get("smu_current")})
        if "smu2_voltage" in data:
            self.view.updateSMU2Voltage(data.get("smu2_voltage"))
            cache.update({"smu2_voltage": data.get("smu2_voltage")})
        if "smu2_current" in data:
            self.view.updateSMU2Current(data.get("smu2_current"))
            cache.update({"smu2_current": data.get("smu2_current")})
        if "elm_current" in data:
            self.view.updateELMCurrent(data.get("elm_current"))
            cache.update({"elm_current": data.get("elm_current")})
        if "elm2_current" in data:
            self.view.updateELM2Current(data.get("elm2_current"))
            cache.update({"elm2_current": data.get("elm2_current")})
        if "lcr_capacity" in data:
            self.view.updateLCRCapacity(data.get("lcr_capacity"))
            cache.update({"lcr_capacity": data.get("lcr_capacity")})
        if "dmm_temperature" in data:
            self.view.updateDMMTemperature(data.get("dmm_temperature"))
            cache.update({"dmm_temperature": data.get("dmm_temperature")})
        if "source_output_state" in data:
            self.view.updateSourceOutputState(data.get("source_output_state"))
        if "bias_source_output_state" in data:
            self.view.updateBiasSourceOutputState(data.get("bias_source_output_state"))
        if "message" in data:
            self.view.set_message(data.get("message", ""))
        if "progress" in data:
            self.view.set_progress(*data.get("progress", (0, 0, 0)))
        with self.cache:
            self.cache.update(cache)

    @QtCore.Slot(bool)
    def on_continuous_toggled(self, checked: bool) -> None:
        self.view.set_continuous(checked)
        self.iv_plots_controller.set_continuous(checked)
        self.cv_plots_controller.set_continuous(checked)
        self.view.general_widget.continuous_group_box.setEnabled(checked)

    @QtCore.Slot(int)
    def on_continuous_changed(self, state: int) -> None:
        self.on_continuous_toggled(state == QtCore.Qt.CheckState.Checked)

    @QtCore.Slot(int)
    def on_measurement_changed(self, index: int) -> None:
        spec: dict[str, Any] = DEFAULTS[index]

        if spec.get("type") == "iv":
            self.view.set_data_widget(self.iv_plots_controller.data_widget)
            self.view.continuous_action.setEnabled(True)
            self.view.general_widget.bias_group_box.setEnabled(False)
            self.view.general_widget.continuous_group_box.setEnabled(self.view.is_continuous())
        elif spec.get("type") == "iv_bias":
            self.view.set_data_widget(self.iv_plots_controller.data_widget)
            self.view.continuous_action.setEnabled(True)
            self.view.general_widget.bias_group_box.setEnabled(True)
            self.view.general_widget.continuous_group_box.setEnabled(self.view.is_continuous())
        elif spec.get("type") == "cv":
            self.view.set_data_widget(self.cv_plots_controller.data_widget)
            self.view.continuous_action.setEnabled(False)
            self.view.general_widget.bias_group_box.setEnabled(False)
            self.view.general_widget.continuous_group_box.setEnabled(False)
        self.update_continuous_option()

        enabled = "SMU" in spec.get("instruments", [])
        self.view.general_widget.smu_check_box.setEnabled(enabled)
        self.view.general_widget.smu_check_box.setVisible(enabled)
        self.view.smu_group_box.setEnabled(enabled)
        self.view.smu_group_box.setVisible(enabled)

        enabled = "SMU2" in spec.get("instruments", [])
        self.view.general_widget.smu2_check_box.setEnabled(enabled)
        self.view.general_widget.smu2_check_box.setVisible(enabled)
        self.view.smu2_group_box.setEnabled(enabled)
        self.view.smu2_group_box.setVisible(enabled)

        enabled = "ELM" in spec.get("instruments", [])
        self.view.general_widget.elm_check_box.setEnabled(enabled)
        self.view.general_widget.elm_check_box.setVisible(enabled)
        self.view.elm_group_box.setEnabled(enabled)
        self.view.elm_group_box.setVisible(enabled)

        enabled = "ELM2" in spec.get("instruments", [])
        self.view.general_widget.elm2_check_box.setEnabled(enabled)
        self.view.general_widget.elm2_check_box.setVisible(enabled)
        self.view.elm2_group_box.setEnabled(enabled)
        self.view.elm2_group_box.setVisible(enabled)

        enabled = "LCR" in spec.get("instruments", [])
        self.view.general_widget.lcr_check_box.setEnabled(enabled)
        self.view.general_widget.lcr_check_box.setVisible(enabled)
        self.view.lcr_group_box.setEnabled(enabled)
        self.view.lcr_group_box.setVisible(enabled)

        default_instruments: list[str] = spec.get("default_instruments") or []

        enabled = "SMU" in default_instruments
        self.view.general_widget.set_smu_enabled(enabled)

        enabled = "SMU2" in default_instruments
        self.view.general_widget.set_smu2_enabled(enabled)

        enabled = "ELM" in default_instruments
        self.view.general_widget.set_elm_enabled(enabled)

        enabled = "ELM2" in default_instruments
        self.view.general_widget.set_elm2_enabled(enabled)

        enabled = "LCR" in default_instruments
        self.view.general_widget.set_lcr_enabled(enabled)

        voltage_unit = spec.get("voltage_unit")
        self.view.general_widget.set_voltage_unit(voltage_unit)

        begin_voltage = spec.get("default_begin_voltage", 0.0)
        self.view.general_widget.set_begin_voltage(begin_voltage)

        end_voltage = spec.get("default_end_voltage", 0.0)
        self.view.general_widget.set_end_voltage(end_voltage)

        step_voltage = spec.get("default_step_voltage", 0.0)
        self.view.general_widget.set_step_voltage(step_voltage)

        waiting_time = spec.get("default_waiting_time", 1.0)
        self.view.general_widget.set_waiting_time(waiting_time)

        waiting_time_continuous = spec.get("default_waiting_time_continuous", 1.0)
        self.view.general_widget.set_waiting_time_continuous(waiting_time_continuous)

        current_compliance_unit = spec.get("current_compliance_unit")
        self.view.general_widget.set_current_compliance_unit(current_compliance_unit)

        current_compliance = spec.get("default_current_compliance", 0.0)
        self.view.general_widget.set_current_compliance(current_compliance)

        self.on_instruments_changed()

    @QtCore.Slot()
    def on_instruments_changed(self) -> None:
        self.view.general_widget.set_current_compliance_locked(False)
        #
        # HACK Not all instruments support compliance!
        # TODO Implement instrument capabilities to lock not supported inputs
        #
        if self.view.general_widget.is_smu_enabled():
            ...
        elif self.view.general_widget.is_elm_enabled():
            role = self.view.find_role("ELM")
            if role.resource_widget.model() in ["K6517B"]:
                self.view.general_widget.set_current_compliance_locked(True)
                self.view.general_widget.set_current_compliance(1.0e-3)  # fixed for K6517B
        elif self.view.general_widget.is_elm2_enabled():
            role = self.view.find_role("ELM2")
            if role.resource_widget.model() in ["K6517B"]:
                self.view.general_widget.set_current_compliance_locked(True)
                self.view.general_widget.set_current_compliance(1.0e-3)  # fixed for K6517B
        elif self.view.general_widget.is_lcr_enabled():
            role = self.view.find_role("LCR")
            if role.resource_widget.model() in ["K595", "E4980A", "A4284A", "K4215"]:
                self.view.general_widget.set_current_compliance_locked(True)

    @QtCore.Slot(bool)
    def on_toggle_smu(self, state: bool) -> None:
        self.iv_plots_controller.toggle_smu_series(state)
        self.cv_plots_controller.toggle_smu_series(state)
        self.view.smu_group_box.setEnabled(state)
        self.view.smu_group_box.setVisible(state)

    @QtCore.Slot(bool)
    def on_toggle_smu2(self, state: bool) -> None:
        self.iv_plots_controller.toggle_smu2_series(state)
        self.cv_plots_controller.toggle_smu2_series(state)
        self.view.smu2_group_box.setEnabled(state)
        self.view.smu2_group_box.setVisible(state)

    @QtCore.Slot(bool)
    def on_toggle_elm(self, state: bool) -> None:
        self.iv_plots_controller.toggle_elm_series(state)
        self.cv_plots_controller.toggle_elm_series(state)
        self.view.elm_group_box.setEnabled(state)
        self.view.elm_group_box.setVisible(state)

    @QtCore.Slot(bool)
    def on_toggle_elm2(self, state: bool) -> None:
        self.iv_plots_controller.toggle_elm2_series(state)
        self.cv_plots_controller.toggle_elm2_series(state)
        self.view.elm2_group_box.setEnabled(state)
        self.view.elm2_group_box.setVisible(state)

    @QtCore.Slot(bool)
    def on_toggle_lcr(self, state: bool) -> None:
        self.iv_plots_controller.toggle_lcr_series(state)
        self.cv_plots_controller.toggle_lcr_series(state)
        self.view.lcr_group_box.setEnabled(state)
        self.view.lcr_group_box.setVisible(state)

    @QtCore.Slot(bool)
    def on_toggle_dmm(self, state: bool) -> None:
        self.view.dmm_group_box.setEnabled(state)
        self.view.dmm_group_box.setVisible(state)

    @QtCore.Slot(bool)
    def on_toggle_switch(self, state: bool) -> None:
        ...

    @QtCore.Slot()
    def on_output_editing_finished(self) -> None:
        if not self.view.general_widget.output_line_edit.text().strip():
            self.view.general_widget.output_line_edit.setText(os.path.expanduser("~"))

    @QtCore.Slot(float)
    def on_current_compliance_changed(self, value: float) -> None:
        logger.info("updated current_compliance: %s", format_metric(value, "A"))
        self.state.update({"current_compliance": value})

    @QtCore.Slot(bool)
    def on_continue_in_compliance_changed(self, checked: bool) -> None:
        logger.info("updated continue_in_compliance: %s", checked)
        self.state.update({"continue_in_compliance": checked})

    @QtCore.Slot(float)
    def on_waiting_time_continuous_changed(self, value: float) -> None:
        logger.info("updated waiting_time_continuous: %s", format_metric(value, "s"))
        self.state.update({"waiting_time_continuous": value})

    def update_continuous_option(self) -> None:
        # Tweak continuous option
        validTypes = ["iv", "iv_bias"]
        measurement = self.view.general_widget.current_measurement()
        enabled = False
        if measurement:
            measurementType = measurement.get("type")
            enabled = measurementType in validTypes
        self.view.continuous_check_box.setEnabled(enabled)

    def create_filename(self) -> str:
        path = self.view.general_widget.output_dir()
        sample = self.state.sample
        timestamp = datetime.fromtimestamp(self.state.timestamp).strftime("%Y-%m-%dT%H-%M-%S")
        filename = safe_filename(f"{sample}-{timestamp}.txt")
        return os.path.join(path, filename)

    def connect_iv_plots(self, measurement) -> None:
        measurement.iv_reading_queue = self.iv_plots_controller.iv_reading_queue
        measurement.iv_reading_lock = self.iv_plots_controller.iv_reading_lock
        measurement.it_reading_queue = self.iv_plots_controller.it_reading_queue
        measurement.it_reading_lock = self.iv_plots_controller.it_reading_lock
        measurement.it_change_voltage_ready_event.subscribe(self.change_voltage_ready.emit)

    def connect_cv_plots(self, measurement) -> None:
        measurement.cv_reading_queue = self.cv_plots_controller.cv_reading_queue
        measurement.cv_reading_lock = self.cv_plots_controller.cv_reading_lock

    def configure(self, params: Mapping[str, Any]) -> None:
        for key, value in params.items():
            if key == "reset":
                self.view.set_reset_instruments(value)
            elif key == "continuous":
                self.view.set_continuous(value)
            elif key == "auto_reconnect":
                self.view.set_auto_reconnect(value)
            elif key == "measurement_type":
                self.view.general_widget.set_current_measurement(value)
            elif key == "measurement_roles":
                self.view.general_widget.set_measurement_roles(value)
            elif key == "end_voltage":
                self.view.general_widget.set_end_voltage(value)
            elif key == "begin_voltage":
                self.view.general_widget.set_begin_voltage(value)
            elif key == "step_voltage":
                self.view.general_widget.set_step_voltage(value)
            elif key == "waiting_time":
                self.view.general_widget.set_waiting_time(value)
            elif key == "bias_voltage":
                self.view.general_widget.set_bias_voltage(value)
            elif key == "compliance":
                self.view.general_widget.set_current_compliance(value)
            elif key == "waiting_time_continuous":
                self.view.general_widget.set_waiting_time_continuous(value)
            else:
                raise KeyError(f"Invalid configuration key: {key}")

    def create_measurement(self) -> Measurement:
        measurement_type = self.state.measurement_type
        measurement_cls = MEASUREMENTS.get(measurement_type)
        if measurement_cls is None:
            raise ValueError(f"No such measurement type: {measurement_type}")
        measurement = measurement_cls(self.state)

        measurement.update_event.subscribe(self.update.emit)

        if isinstance(measurement, IVMeasurement):
            self.connect_iv_plots(measurement)
        elif isinstance(measurement, IVBiasMeasurement):
            self.connect_iv_plots(measurement)
        elif isinstance(measurement, CVMeasurement):
            self.connect_cv_plots(measurement)

        # Prepare role drivers
        for role in self.view.roles():
            measurement.register_instrument(role.name().lower())

        measurement.failed_event.subscribe(self.failed.emit)

        return measurement

    @QtCore.Slot()
    def on_start_measurement(self) -> None:
        try:
            logger.debug("preparing state...")
            state = self.prepare_state()
            logger.debug("preparing state... done.")

            if not state.get("source_role"):
                raise RuntimeError("No source instrument selected.")

            # Update state
            self.state.update(state)
            self.state.update({"stop_requested": False})

            with self.cache:
                self.cache.update({
                    "measurement_type": state.get("measurement_type"),
                    "sample": state.get("sample")
                })

            # Filename
            output_enabled = self.view.general_widget.is_output_enabled()
            filename = self.create_filename() if output_enabled else None
            self.state.update({"filename": filename})

            # Create and run measurement
            measurement = self.create_measurement()

            options: dict[str, Any] = {}

            settings = QtCore.QSettings()
            timestamp_format = settings.value("writer/timestampFormat", ".6f", str)
            valueFormat = settings.value("writer/valueFormat", "+.3E", str)

            options.update({
                "timestamp_format": timestamp_format,
                "value_format": valueFormat,
            })

            self.view.clear()
            self.iv_plots_controller.clear()
            self.cv_plots_controller.clear()
            self.iv_plots_controller.update_timer.start(500)
            self.cv_plots_controller.update_timer.start(500)

            job = MeasurementJob(measurement, options, has_finished=self.measurement_finished.emit)
            self.submit_background_job(job)

        except Exception as exc:
            logger.exception(exc)
            self.failed.emit(exc)
            self.aborted.emit()

    def request_change_voltage(self, end_voltage: float, step_voltage: float, waiting_time: float) -> None:
        state = self.snapshot().get("state")
        if state != FSMState.CONTINUOUS:
            raise RuntimeError(
                f"Cannot change voltage in state '{state.value}'. Expected 'continuous'."
            )
        self.change_voltage_controller.request_change_voltage(end_voltage, step_voltage, waiting_time)

    def on_lcr_perform_correction(self) -> None:
        role = self.view.find_role("LCR")
        if role:
            model = role.model()
            config = role.configs().get(model, {})
            if model == "K4215":
                dialog = K4215CorrectionDialog(self.view)
                external_bias_tee = config.get("external_bias_tee.enabled", False)
                if external_bias_tee:
                    dialog.set_hint("<b>With</b> external Bias Tee (applying -10V DC)")
                if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return
                self.view.control_tab_widget.setEnabled(False)
                self.submit_background_job(K4215PerformCorrectionJob(
                    model=model,
                    resource_name=role.resource_name(),
                    termination=role.termination(),
                    timeout=role.timeout(),
                    cable_length=config.get("correction.length"),
                    open_correction=dialog.is_open_correction(),
                    short_correction=dialog.is_short_correction(),
                    load_correction=dialog.get_load_correction(),
                    external_bias_tee=external_bias_tee,
                    progress=self.progress_changed.emit,
                    message=self.message_changed.emit,
                ))


class IVPlotsController(QtCore.QObject):
    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)

        self.iv_plot_widget = IVPlotWidget()
        self.it_plot_widget = ItPlotWidget()
        self.it_plot_widget.setVisible(False)
        self.data_widget = QtWidgets.QWidget()
        self.iv_layout = QtWidgets.QHBoxLayout(self.data_widget)
        self.iv_layout.addWidget(self.iv_plot_widget)
        self.iv_layout.addWidget(self.it_plot_widget)
        self.iv_layout.setStretch(0, 1)
        self.iv_layout.setStretch(1, 1)
        self.iv_layout.setContentsMargins(0, 0, 0, 0)

        self.iv_reading_queue: list[ReadingType] = []
        self.iv_reading_lock = threading.RLock()
        self.it_reading_queue: list[ReadingType] = []
        self.it_reading_lock = threading.RLock()

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.on_flush_iv_readings)
        self.update_timer.timeout.connect(self.on_flush_it_readings)

    def clear(self):
        self.iv_reading_queue.clear()
        self.it_reading_queue.clear()
        self.iv_plot_widget.clear()
        self.iv_plot_widget.reset()
        self.it_plot_widget.clear()
        self.it_plot_widget.reset()

    def toggle_smu_series(self, state):
        self.iv_plot_widget.smuSeries.setVisible(state)
        self.it_plot_widget.smuSeries.setVisible(state)

    def toggle_smu2_series(self, state):
        self.iv_plot_widget.smu2Series.setVisible(state)
        self.it_plot_widget.smu2Series.setVisible(state)

    def toggle_elm_series(self, state):
        self.iv_plot_widget.elmSeries.setVisible(state)
        self.it_plot_widget.elmSeries.setVisible(state)

    def toggle_elm2_series(self, state):
        self.iv_plot_widget.elm2Series.setVisible(state)
        self.it_plot_widget.elm2Series.setVisible(state)

    def toggle_lcr_series(self, state):
        ...

    def set_continuous(self, enabled):
        self.it_plot_widget.setVisible(enabled)

    def on_flush_iv_readings(self) -> None:
        with self.iv_reading_lock:
            readings = self.iv_reading_queue.copy()
            self.iv_reading_queue.clear()
        for reading in readings:
            self.append_iv_reading(reading, fit=False)
        if len(readings):
            self.iv_plot_widget.fit()

    def append_iv_reading(self, reading: dict, fit: bool = True) -> None:
        voltage: float = reading.get("voltage", math.nan)
        i_smu: float = reading.get("i_smu", math.nan)
        i_smu2: float = reading.get("i_smu2", math.nan)
        i_elm: float = reading.get("i_elm", math.nan)
        i_elm2: float = reading.get("i_elm2", math.nan)
        if math.isfinite(voltage) and math.isfinite(i_smu):
            self.iv_plot_widget.append("smu", voltage, i_smu)
        if math.isfinite(voltage) and math.isfinite(i_smu2):
            self.iv_plot_widget.append("smu2", voltage, i_smu2)
        if math.isfinite(voltage) and math.isfinite(i_elm):
            self.iv_plot_widget.append("elm", voltage, i_elm)
        if math.isfinite(voltage) and math.isfinite(i_elm2):
            self.iv_plot_widget.append("elm2", voltage, i_elm2)
        if fit:
            self.iv_plot_widget.fit()

    def on_load_iv_readings(self, readings: list[dict]) -> None:
        smu_points: list[QtCore.QPointF] = []
        smu2_points: list[QtCore.QPointF] = []
        elm_points: list[QtCore.QPointF] = []
        elm2_points: list[QtCore.QPointF] = []
        widget = self.iv_plot_widget
        widget.clear()
        for reading in readings:
            voltage: float = reading.get("voltage", math.nan)
            i_smu: float = reading.get("i_smu", math.nan)
            i_smu2: float = reading.get("i_smu2", math.nan)
            i_elm: float = reading.get("i_elm", math.nan)
            i_elm2: float = reading.get("i_elm2", math.nan)
            if math.isfinite(voltage) and math.isfinite(i_smu):
                smu_points.append(QtCore.QPointF(voltage, i_smu))
                widget.iLimits.append(i_smu)
                widget.vLimits.append(voltage)
            if math.isfinite(voltage) and math.isfinite(i_smu2):
                smu2_points.append(QtCore.QPointF(voltage, i_smu2))
                widget.iLimits.append(i_smu2)
                widget.vLimits.append(voltage)
            if math.isfinite(voltage) and math.isfinite(i_elm):
                elm_points.append(QtCore.QPointF(voltage, i_elm))
                widget.iLimits.append(i_elm)
                widget.vLimits.append(voltage)
            if math.isfinite(voltage) and math.isfinite(i_elm2):
                elm2_points.append(QtCore.QPointF(voltage, i_elm2))
                widget.iLimits.append(i_elm2)
                widget.vLimits.append(voltage)
        widget.replace_series("smu", smu_points)
        widget.replace_series("smu2", smu2_points)
        widget.replace_series("elm", elm_points)
        widget.replace_series("elm2", elm2_points)
        parent = self.parent()  # TODO!
        if isinstance(parent, Controller):
            parent.on_toggle_smu(True)
            parent.on_toggle_smu2(bool(len(smu2_points)))
            parent.on_toggle_elm(bool(len(elm_points)))
            parent.on_toggle_elm2(bool(len(elm2_points)))
        widget.fit()

    def on_flush_it_readings(self) -> None:
        with self.it_reading_lock:
            readings = self.it_reading_queue.copy()
            self.it_reading_queue.clear()
        for reading in readings:
            self.append_it_reading(reading, fit=False)
        if len(readings):
            self.it_plot_widget.fit()

    def append_it_reading(self, reading: dict, fit: bool = True) -> None:
        timestamp: float = reading.get("timestamp", math.nan)
        i_smu: float = reading.get("i_smu", math.nan)
        i_smu2: float = reading.get("i_smu2", math.nan)
        i_elm: float = reading.get("i_elm", math.nan)
        i_elm2: float = reading.get("i_elm2", math.nan)
        if math.isfinite(timestamp) and math.isfinite(i_smu):
            self.it_plot_widget.append("smu", timestamp, i_smu)
        if math.isfinite(timestamp) and math.isfinite(i_smu2):
            self.it_plot_widget.append("smu2", timestamp, i_smu2)
        if math.isfinite(timestamp) and math.isfinite(i_elm):
            self.it_plot_widget.append("elm", timestamp, i_elm)
        if math.isfinite(timestamp) and math.isfinite(i_elm2):
            self.it_plot_widget.append("elm2", timestamp, i_elm2)
        if fit:
            self.it_plot_widget.fit()

    def on_load_it_readings(self, readings: list[dict]) -> None:
        smu_points: list[QtCore.QPointF] = []
        smu2_points: list[QtCore.QPointF] = []
        elm_points: list[QtCore.QPointF] = []
        elm2_points: list[QtCore.QPointF] = []
        widget = self.it_plot_widget
        widget.clear()
        for reading in readings:
            timestamp: float = reading.get("timestamp", math.nan)
            i_smu: float = reading.get("i_smu", math.nan)
            i_smu2: float = reading.get("i_smu2", math.nan)
            i_elm: float = reading.get("i_elm", math.nan)
            i_elm2: float = reading.get("i_elm2", math.nan)
            if math.isfinite(timestamp) and math.isfinite(i_smu):
                smu_points.append(QtCore.QPointF(timestamp * 1e3, i_smu))
                widget.iLimits.append(i_smu)
                widget.tLimits.append(timestamp)
            if math.isfinite(timestamp) and math.isfinite(i_smu2):
                smu2_points.append(QtCore.QPointF(timestamp * 1e3, i_smu2))
                widget.iLimits.append(i_smu2)
                widget.tLimits.append(timestamp)
            if math.isfinite(timestamp) and math.isfinite(i_elm):
                elm_points.append(QtCore.QPointF(timestamp * 1e3, i_elm))
                widget.iLimits.append(i_elm)
                widget.tLimits.append(timestamp)
            if math.isfinite(timestamp) and math.isfinite(i_elm2):
                elm2_points.append(QtCore.QPointF(timestamp * 1e3, i_elm2))
                widget.iLimits.append(i_elm2)
                widget.tLimits.append(timestamp)
        widget.replace_series("smu", smu_points)
        widget.replace_series("smu2", smu2_points)
        widget.replace_series("elm", elm_points)
        widget.replace_series("elm2", elm2_points)
        widget.fit()


class CVPlotsController(QtCore.QObject):
    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)

        self.cv_plot_widget = CVPlotWidget()
        self.cv2_plot_widget = CV2PlotWidget()
        self.data_widget = QtWidgets.QWidget()
        self.cv_layout = QtWidgets.QHBoxLayout(self.data_widget)
        self.cv_layout.addWidget(self.cv_plot_widget)
        self.cv_layout.addWidget(self.cv2_plot_widget)
        self.cv_layout.setStretch(0, 1)
        self.cv_layout.setStretch(1, 1)
        self.cv_layout.setContentsMargins(0, 0, 0, 0)

        self.cv_reading_queue: list[ReadingType] = []
        self.cv_reading_lock = threading.RLock()

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.flush_cv_readings)

    def clear(self) -> None:
        self.cv_reading_queue.clear()
        self.cv_plot_widget.clear()
        self.cv_plot_widget.reset()
        self.cv2_plot_widget.clear()
        self.cv2_plot_widget.reset()

    def toggle_smu_series(self, state):
        ...

    def toggle_smu2_series(self, state):
        ...

    def toggle_elm_series(self, state):
        ...

    def toggle_elm2_series(self, state):
        ...

    def toggle_lcr_series(self, state):
        ...

    def set_continuous(self, enabled):
        ...

    def flush_cv_readings(self) -> None:
        with self.cv_reading_lock:
            readings = self.cv_reading_queue.copy()
            self.cv_reading_queue.clear()
        for reading in readings:
            self.append_cv_reading(reading, fit=False)
        if len(readings):
            self.cv_plot_widget.fit()

    def append_cv_reading(self, reading: dict, fit: bool = True) -> None:
        voltage: float = reading.get("voltage", math.nan)
        c_lcr: float = reading.get("c_lcr", math.nan)
        c2_lcr: float = reading.get("c2_lcr", math.nan)
        if math.isfinite(voltage) and math.isfinite(c_lcr):
            self.cv_plot_widget.append("lcr", voltage, c_lcr)
        if math.isfinite(voltage) and math.isfinite(c2_lcr):
            self.cv2_plot_widget.append("lcr", voltage, c2_lcr)

    def load_cv_readings(self, readings: list[dict]) -> None:
        lcr_points: list[QtCore.QPointF] = []
        widget = self.cv_plot_widget
        widget.clear()
        for reading in readings:
            voltage: float = reading.get("voltage", math.nan)
            c_lcr: float = reading.get("c_lcr", math.nan)
            if math.isfinite(voltage) and math.isfinite(c_lcr):
                lcr_points.append(QtCore.QPointF(voltage, c_lcr))
                widget.cLimits.append(c_lcr)
                widget.vLimits.append(voltage)
        widget.replace_series("lcr", lcr_points)
        widget.fit()

    def load_cv2_readings(self, readings: list[dict]) -> None:
        lcr2_points: list[QtCore.QPointF] = []
        widget = self.cv2_plot_widget
        widget.clear()
        for reading in readings:
            voltage: float = reading.get("voltage", math.nan)
            c2_lcr: float = reading.get("c2_lcr", math.nan)
            if math.isfinite(voltage) and math.isfinite(c2_lcr):
                lcr2_points.append(QtCore.QPointF(voltage, c2_lcr))
                widget.cLimits.append(c2_lcr)
                widget.vLimits.append(voltage)
        widget.replace_series("lcr", lcr2_points)
        widget.fit()


class ChangeVoltageController(QtCore.QObject):
    def __init__(self, view, state: State, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.view = view
        self.state: State = state
        # Connect signals
        self.view.prepare_change_voltage.connect(self.on_prepare_change_voltage)

    def source_voltage(self) -> float:
        source_voltage = self.state.source_voltage
        if source_voltage is not None:
            return source_voltage
        return self.view.general_widget.end_voltage()

    @QtCore.Slot()
    def on_prepare_change_voltage(self) -> None:
        dialog = ChangeVoltageDialog(self.view)
        dialog.set_end_voltage(self.source_voltage())
        dialog.set_step_voltage(self.view.general_widget.step_voltage())
        dialog.set_waiting_time(self.view.general_widget.waiting_time())
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.request_change_voltage(
                dialog.end_voltage(),
                dialog.step_voltage(),
                dialog.waiting_time()
            )

    def request_change_voltage(self, end_voltage: float, step_voltage: float, waiting_time: float) -> None:
        if self.view.is_change_voltage_enabled():
            logger.info(
                "updated change_voltage_continuous: end_voltage=%s, step_voltage=%s, waiting_time=%s",
                format_metric(end_voltage, "V"),
                format_metric(step_voltage, "V"),
                format_metric(waiting_time, "s")
            )
            self.state.update({"change_voltage_continuous": {
                "end_voltage": end_voltage,
                "step_voltage": step_voltage,
                "waiting_time": waiting_time,
            }})
            self.view.set_change_voltage_enabled(False)

    @QtCore.Slot()
    def on_change_voltage_ready(self) -> None:
        self.view.set_change_voltage_enabled(True)
