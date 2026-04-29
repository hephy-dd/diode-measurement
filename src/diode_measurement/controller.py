import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Mapping
from queue import Queue, Empty
from typing import Any, Optional

from PySide6 import QtCore, QtWidgets, QtStateMachine

from comet.utils import safe_filename

from .core.cache import Cache
from .core.measurement import Measurement
from .core.resource import parse_resource, ResourceConfig

# Source meter units
from .gui.panels import K237Panel
from .gui.panels import K2410Panel
from .gui.panels import K2470Panel
from .gui.panels import K2657APanel

# Electrometers
from .gui.panels import K6514Panel
from .gui.panels import K6517BPanel

# LCR meters
from .gui.panels import K595Panel
from .gui.panels import E4980APanel
from .gui.panels import A4284APanel
from .gui.panels import K4215Panel
from .gui.panels.k4215 import K4215CorrectionDialog

# DMM
from .gui.panels import K2700Panel

# TCU
from .gui.panels import AC3Panel

# Switches
from .gui.panels import BrandBoxPanel
from .gui.panels import K707BPanel
from .gui.panels import K708BPanel

from .gui.mainwindow import MainWindow
from .gui.widgets import show_exception
from .gui.dialogs import ChangeVoltageDialog
from .gui.plots import IVPlotsDataWidget, CVPlotsDataWidget

from .reader import Reader

from .utils import format_metric
from .utils import get_bool, get_int, get_float, get_str, get_dict

from .jobs import Job, MeasurementJob, K4215PerformCorrectionJob
from .settings import MeasurementParameters, measurement_registry
from .state import FSMState, ChangeVoltageParameters, State

__all__ = ["Controller"]

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    state: FSMState
    measurement_type: Optional[str]
    sample: Optional[str]
    source_voltage: Optional[float]
    smu_voltage: Optional[float]
    smu_current: Optional[float]
    smu2_voltage: Optional[float]
    smu2_current: Optional[float]
    elm_current: Optional[float]
    elm2_current: Optional[float]
    lcr_capacity: Optional[float]
    temperature: Optional[float]


class Controller(QtCore.QObject):
    started = QtCore.Signal()
    aborted = QtCore.Signal()
    updated = QtCore.Signal(dict)
    failed = QtCore.Signal(Exception)
    finished = QtCore.Signal()

    change_voltage_ready = QtCore.Signal()

    measurement_finished = QtCore.Signal()
    message_changed = QtCore.Signal(str)
    progress_changed = QtCore.Signal(int, int, int)

    def __init__(
        self, main_window: MainWindow, parent: Optional[QtCore.QObject] = None
    ) -> None:
        super().__init__(parent)

        self._shutdown_event = threading.Event()
        self._background_inbox: Queue[Job] = Queue()
        self._background_thread = threading.Thread(target=self._handle_background_jobs)

        self.main_window = main_window

        self.is_exception_dialog_active: bool = False

        self.state: State = State()
        self.state.event_bus.register_callback("change_voltage_done", self.change_voltage_ready.emit)
        self.state.event_bus.register_callback("update", self.updated.emit)
        self.state.event_bus.register_callback("failed", self.failed.emit)

        self.cache: Cache = Cache()

        self.measurement_registry: list[MeasurementParameters] = measurement_registry

        # Plots
        iv_reading_queue = self.state.create_iv_reading_queue()
        it_reading_queue = self.state.create_iv_reading_queue()
        cv_reading_queue = self.state.create_cv_reading_queue()

        self.iv_plots_data_windget = IVPlotsDataWidget(iv_reading_queue, it_reading_queue)
        self.iv_plots_data_windget.start(500)
        self.cv_plots_data_windget = CVPlotsDataWidget(cv_reading_queue)
        self.cv_plots_data_windget.start(500)

        self.change_voltage_controller = ChangeVoltageController(
            self.main_window, self.state, self
        )
        self.change_voltage_ready.connect(
            self.change_voltage_controller.on_change_voltage_ready
        )
        self.updated.connect(self.on_update)
        self.failed.connect(self.handle_exception)

        # Source meter unit
        role = main_window.add_role("smu", "SMU")
        role.add_instrument_panel(K237Panel())
        role.add_instrument_panel(K2410Panel())
        role.add_instrument_panel(K2470Panel())
        role.add_instrument_panel(K2657APanel())

        # Bias source meter unit
        role = main_window.add_role("smu2", "SMU2")
        role.add_instrument_panel(K237Panel())
        role.add_instrument_panel(K2410Panel())
        role.add_instrument_panel(K2470Panel())
        role.add_instrument_panel(K2657APanel())

        # Electrometer
        role = main_window.add_role("elm", "ELM")
        role.add_instrument_panel(K6514Panel())
        role.add_instrument_panel(K6517BPanel())
        role.resource_widget.model_changed.connect(self.on_instruments_changed)  # HACK

        # Electrometer 2
        role = main_window.add_role("elm2", "ELM2")
        role.add_instrument_panel(K6514Panel())
        role.add_instrument_panel(K6517BPanel())
        role.resource_widget.model_changed.connect(self.on_instruments_changed)  # HACK

        # LCR meter
        role = main_window.add_role("lcr", "LCR")
        role.add_instrument_panel(K595Panel())
        role.add_instrument_panel(E4980APanel())
        role.add_instrument_panel(A4284APanel())
        panel = K4215Panel()
        panel.perform_correction_clicked.connect(self.on_lcr_perform_correction)
        role.add_instrument_panel(panel)

        # DMM
        role = main_window.add_role("dmm", "DMM")
        role.add_instrument_panel(K2700Panel())

        # TCU
        role = main_window.add_role("tcu", "TCU")
        role.add_instrument_panel(AC3Panel())

        # Switch
        role = main_window.add_role("switch", "Switch")
        role.add_instrument_panel(BrandBoxPanel())
        role.add_instrument_panel(K707BPanel())
        role.add_instrument_panel(K708BPanel())

        main_window.import_action.triggered.connect(self.on_import_file)

        main_window.start_action.triggered.connect(self.on_start_measurement)
        main_window.start_button.clicked.connect(main_window.start_action.trigger)

        main_window.stop_action.triggered.connect(self.aborted)
        main_window.stop_button.clicked.connect(main_window.stop_action.trigger)

        main_window.continuous_action.toggled.connect(self.on_continuous_toggled)
        main_window.continuous_check_box.checkStateChanged.connect(
            self.on_continuous_changed
        )

        general_widget = main_window.general_widget

        for spec in self.measurement_registry:
            general_widget.add_measurement(spec)

        general_widget.measurement_combo_box.currentIndexChanged.connect(
            self.on_measurement_changed
        )

        general_widget.output_line_edit.editingFinished.connect(
            self.on_output_editing_finished
        )
        general_widget.current_compliance_changed.connect(
            self.on_current_compliance_changed
        )
        general_widget.continue_in_compliance_changed.connect(
            self.on_continue_in_compliance_changed
        )
        general_widget.waiting_time_continuous_changed.connect(
            self.on_waiting_time_continuous_changed
        )

        self.on_measurement_changed(0)

        general_widget.instruments_changed.connect(self.on_instruments_changed)

        self.on_instruments_changed()

        general_widget.role_check_boxes["smu"].toggled.connect(self.on_toggle_smu)
        general_widget.role_check_boxes["smu2"].toggled.connect(self.on_toggle_smu2)
        general_widget.role_check_boxes["elm"].toggled.connect(self.on_toggle_elm)
        general_widget.role_check_boxes["elm2"].toggled.connect(self.on_toggle_elm2)
        general_widget.role_check_boxes["lcr"].toggled.connect(self.on_toggle_lcr)
        general_widget.role_check_boxes["dmm"].toggled.connect(self.on_toggle_dmm)
        general_widget.role_check_boxes["tcu"].toggled.connect(self.on_toggle_tcu)
        general_widget.role_check_boxes["switch"].toggled.connect(self.on_toggle_switch)

        self.on_toggle_smu2(False)
        self.on_toggle_elm(False)
        self.on_toggle_elm2(False)
        self.on_toggle_lcr(False)
        self.on_toggle_dmm(False)
        self.on_toggle_tcu(False)
        self.on_toggle_switch(False)

        main_window.clear_message()
        main_window.clear_progress()

        self.message_changed.connect(main_window.set_message)
        self.progress_changed.connect(main_window.set_progress)

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
                except Empty:
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

    def snapshot(self) -> Snapshot:
        """Return thread save application state snapshot."""
        with self.cache:
            return Snapshot(
                state=self.cache.get("fsm_state", FSMState.IDLE),  # TODO
                measurement_type=self.cache.get("measurement_type"),
                sample=self.cache.get("sample"),
                source_voltage=self.cache.get("source_voltage"),
                smu_voltage=self.cache.get("smu_voltage"),
                smu_current=self.cache.get("smu_current"),
                smu2_voltage=self.cache.get("smu2_voltage"),
                smu2_current=self.cache.get("smu2_current"),
                elm_current=self.cache.get("elm_current"),
                elm2_current=self.cache.get("elm2_current"),
                lcr_capacity=self.cache.get("lcr_capacity"),
                temperature=self.cache.get("dmm_temperature"),
            )

    def get_role_model(self, role: str) -> str:
        for role_ in self.main_window.roles():
            if role_.name() == role:
                return role_.model()
        raise KeyError("No such role: {role!r}")

    def get_role_config(self, role: str) -> dict[str, Any]:
        for role_ in self.main_window.roles():
            if role_.name() == role:
                return role_.current_config()
        raise KeyError("No such role: {role!r}")

    def update_role_config(self, role: str, options: Mapping[str, Any]) -> dict[str, Any]:
        for role_ in self.main_window.roles():
            if role_.name() == role:
                config = role_.current_config()
                for key in options:
                    if key not in config:
                        logger.warning("Ignoring invalid config key %r for role %r", key, role)
                for key in config:
                    if key in options:
                        config[key] = options[key]
                # Update models configs
                configs = role_.configs()
                configs[role_.model()] = config
                role_.set_configs(configs)
                return role_.current_config()
        raise KeyError("No such role: {role!r}")

    def prepare_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {}

        general_widget = self.main_window.general_widget
        current_measurement = general_widget.current_measurement()

        if current_measurement is None:
            raise ValueError("No measurement selected.")

        state["sample"] = general_widget.sample_name()
        state["measurement_type"] = current_measurement.type
        state["timestamp"] = time.time()

        state["continuous"] = self.main_window.is_continuous()
        state["auto_reconnect"] = self.main_window.is_auto_reconnect()
        state["voltage_begin"] = general_widget.begin_voltage()
        state["voltage_end"] = general_widget.end_voltage()
        state["voltage_step"] = general_widget.step_voltage()
        state["waiting_time"] = general_widget.waiting_time()
        state["bias_voltage"] = general_widget.bias_voltage()
        state["current_compliance"] = general_widget.current_compliance()
        state["continue_in_compliance"] = general_widget.is_continue_in_compliance()
        state["waiting_time_continuous"] = general_widget.waiting_time_continuous()

        roles: dict[str, Any] = state.setdefault("roles", {})

        for role in self.main_window.roles():
            key = role.name()
            resource = role.resource_widget.resource_name()
            resource_name, visa_library = parse_resource(resource)
            config = roles.setdefault(key, {})
            config.update(
                {
                    "resource_name": resource_name,
                    "visa_library": visa_library,
                    "model": role.resource_widget.model(),
                    "termination": role.resource_widget.termination(),
                    "timeout": role.resource_widget.timeout(),
                    "reset_instrument": role.resource_widget.is_reset_instrument(),
                }
            )
            config.update({"options": role.current_config()})

        if general_widget.is_role_checked("smu"):
            state["source_role"] = "smu"
        elif general_widget.is_role_checked("elm"):
            state["source_role"] = "elm"
        elif general_widget.is_role_checked("lcr"):
            state["source_role"] = "lcr"

        if general_widget.is_role_checked("smu2"):
            state["bias_source_role"] = "smu2"

        roles.setdefault("smu", {}).update({"enabled": general_widget.is_role_checked("smu")})
        roles.setdefault("smu2", {}).update(
            {"enabled": general_widget.is_role_checked("smu2")}
        )
        roles.setdefault("elm", {}).update({"enabled": general_widget.is_role_checked("elm")})
        roles.setdefault("elm2", {}).update(
            {"enabled": general_widget.is_role_checked("elm2")}
        )
        roles.setdefault("lcr", {}).update({"enabled": general_widget.is_role_checked("lcr")})
        roles.setdefault("dmm", {}).update({"enabled": general_widget.is_role_checked("dmm")})
        roles.setdefault("tcu", {}).update({"enabled": general_widget.is_role_checked("tcu")})
        roles.setdefault("switch", {}).update(
            {"enabled": general_widget.is_role_checked("switch")}
        )

        for key, value in state.items():
            logger.info("> %s: %s", key, value)

        return state

    def start(self) -> None:
        if self._background_thread.ident is not None:
            return
        self._background_thread.start()

    def shutdown(self) -> None:
        self._shutdown_event.set()
        self.iv_plots_data_windget.stop()
        self.cv_plots_data_windget.stop()
        self.state_machine.stop()
        if self._background_thread.is_alive():
            self._background_thread.join(timeout=10.0)
            if self._background_thread.is_alive():
                logger.warning("Background thread did not stop within timeout")

    def read_settings(self) -> None:
        settings = QtCore.QSettings()

        geometry = settings.value("mainwindow/geometry")
        if isinstance(geometry, QtCore.QByteArray) and not geometry.isEmpty():
            self.main_window.restoreGeometry(geometry)
        else:
            self.main_window.resize(800, 600)

        state = settings.value("mainwindow/state")
        if isinstance(state, QtCore.QByteArray) and not state.isEmpty():
            self.main_window.restoreState(state)

        continuous = get_bool(settings.value("continuous"), False)
        self.main_window.set_continuous(continuous)

        auto_reconnect = get_bool(settings.value("autoReconnect"), False)
        self.main_window.set_auto_reconnect(auto_reconnect)

        settings.beginGroup("generalTab")

        general_widget = self.main_window.general_widget

        index = get_int(settings.value("measurement/index"), 0)
        general_widget.measurement_combo_box.setCurrentIndex(index)

        enabled = get_bool(settings.value("smu/enabled"), False)
        general_widget.set_role_checked("smu", enabled)

        enabled = get_bool(settings.value("smu2/enabled"), False)
        general_widget.set_role_checked("smu2", enabled)

        enabled = get_bool(settings.value("elm/enabled"), False)
        general_widget.set_role_checked("elm", enabled)

        enabled = get_bool(settings.value("elm2/enabled"), False)
        general_widget.set_role_checked("elm2", enabled)

        enabled = get_bool(settings.value("lcr/enabled"), False)
        general_widget.set_role_checked("lcr", enabled)

        enabled = get_bool(settings.value("dmm/enabled"), False)
        general_widget.set_role_checked("dmm", enabled)

        enabled = get_bool(settings.value("tcu/enabled"), False)
        general_widget.set_role_checked("tcu", enabled)

        enabled = get_bool(settings.value("switch/enabled"), False)
        general_widget.set_role_checked("switch", enabled)

        output_enabled = get_bool(settings.value("outputEnabled"), False)
        general_widget.set_output_enabled(output_enabled)

        sample_name = get_str(settings.value("sampleName"), "Unnamed")
        general_widget.set_sample_name(sample_name)

        output_dir = get_str(settings.value("outputDir"), os.path.expanduser("~"))
        general_widget.set_output_dir(output_dir)

        begin_voltage = get_float(settings.value("beginVoltage"), 1.0)
        general_widget.set_begin_voltage(begin_voltage)

        end_voltage = get_float(settings.value("endVoltage"), 1.0)
        general_widget.set_end_voltage(end_voltage)

        step_voltage = get_float(settings.value("stepVoltage"), 1.0)
        general_widget.set_step_voltage(step_voltage)

        waiting_time = get_float(settings.value("waitingTime"), 1.0)
        general_widget.set_waiting_time(waiting_time)

        bias_voltage = get_float(settings.value("biasVoltage"), 0.0)
        general_widget.set_bias_voltage(bias_voltage)

        current_compliance = get_float(settings.value("currentCompliance"), 1.0)
        general_widget.set_current_compliance(current_compliance)

        continue_in_compliance = get_bool(settings.value("continueInCompliance"), False)
        general_widget.set_continue_in_compliance(continue_in_compliance)

        waiting_time_continuous = get_float(settings.value("waitingTimeContinuous"), 1)
        general_widget.set_waiting_time_continuous(waiting_time_continuous)

        settings.endGroup()

        settings.beginGroup("roles")

        for role in self.main_window.roles():
            name = role.name()
            settings.beginGroup(name)
            role.set_model(get_str(settings.value("model"), ""))
            role.set_resource_name(get_str(settings.value("resource"), ""))
            role.set_termination(get_str(settings.value("termination"), ""))
            role.set_timeout(get_float(settings.value("timeout"), 4.0))
            role.set_reset_instrument(get_bool(settings.value("reset_instrument"), False))
            role.set_resources(get_dict(settings.value("resources"), {}))
            role.set_configs(get_dict(settings.value("configs"), {}))
            settings.endGroup()

        settings.endGroup()

        self.on_instruments_changed()

    def write_settings(self) -> None:
        settings = QtCore.QSettings()

        settings.setValue("mainwindow/geometry", self.main_window.saveGeometry())
        settings.setValue("mainwindow/state", self.main_window.saveState())

        continuous = self.main_window.is_continuous()
        settings.setValue("continuous", continuous)

        auto_reconnect = self.main_window.is_auto_reconnect()
        settings.setValue("autoReconnect", auto_reconnect)

        settings.beginGroup("generalTab")

        general_widget = self.main_window.general_widget

        measurement_index = general_widget.measurement_combo_box.currentIndex()
        settings.setValue("measurement/index", measurement_index)

        enabled = general_widget.is_role_checked("smu")
        settings.setValue("smu/enabled", enabled)

        enabled = general_widget.is_role_checked("smu2")
        settings.setValue("smu2/enabled", enabled)

        enabled = general_widget.is_role_checked("elm")
        settings.setValue("elm/enabled", enabled)

        enabled = general_widget.is_role_checked("elm2")
        settings.setValue("elm2/enabled", enabled)

        enabled = general_widget.is_role_checked("lcr")
        settings.setValue("lcr/enabled", enabled)

        enabled = general_widget.is_role_checked("dmm")
        settings.setValue("dmm/enabled", enabled)

        enabled = general_widget.is_role_checked("tcu")
        settings.setValue("tcu/enabled", enabled)

        enabled = general_widget.is_role_checked("switch")
        settings.setValue("switch/enabled", enabled)

        output_enabled = general_widget.is_output_enabled()
        settings.setValue("outputEnabled", output_enabled)

        sample_name = general_widget.sample_name()
        settings.setValue("sampleName", sample_name)

        output_dir = general_widget.output_dir()
        settings.setValue("outputDir", output_dir)

        begin_voltage = general_widget.begin_voltage()
        settings.setValue("beginVoltage", begin_voltage)

        end_voltage = general_widget.end_voltage()
        settings.setValue("endVoltage", end_voltage)

        step_voltage = general_widget.step_voltage()
        settings.setValue("stepVoltage", step_voltage)

        waiting_time = general_widget.waiting_time()
        settings.setValue("waitingTime", waiting_time)

        bias_voltage = general_widget.bias_voltage()
        settings.setValue("biasVoltage", bias_voltage)

        current_compliance = general_widget.current_compliance()
        settings.setValue("currentCompliance", current_compliance)

        continueInCompliance = general_widget.is_continue_in_compliance()
        settings.setValue("continueInCompliance", continueInCompliance)

        waiting_time_continuous = general_widget.waiting_time_continuous()
        settings.setValue("waitingTimeContinuous", waiting_time_continuous)

        settings.endGroup()

        settings.beginGroup("roles")

        for role in self.main_window.roles():
            name = role.name()
            settings.beginGroup(name)
            settings.setValue("model", role.model())
            settings.setValue("resource", role.resource_name())
            settings.setValue("termination", role.termination())
            settings.setValue("timeout", role.timeout())
            settings.setValue("reset_instrument", role.is_reset_instrument())
            settings.setValue("resources", role.resources())
            settings.setValue("configs", role.configs())
            settings.endGroup()

        settings.endGroup()

    @QtCore.Slot()
    def on_import_file(self) -> None:
        general_widget = self.main_window.general_widget
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.main_window,
            "Select measurement file",
            general_widget.output_dir(),
            "Text (*.txt);;All (*);;",
        )
        if filename:
            logger.info("Importing measurement file: %s", filename)
            self.main_window.setEnabled(False)
            self.main_window.clear()
            self.iv_plots_data_windget.clear()
            self.cv_plots_data_windget.clear()
            try:
                with open(filename, "r", newline="") as fp:
                    reader = Reader(fp)
                    meta = reader.read_meta()
                    data = reader.read_data()
                    continuous_data = reader.read_data()

                # Meta
                general_widget.measurement_combo_box.setCurrentIndex(-1)
                measurement_type = meta.get("measurement_type")
                if measurement_type:
                    for index in range(general_widget.measurement_combo_box.count()):
                        spec = general_widget.measurement_combo_box.itemData(index)
                        if spec.type == measurement_type:
                            general_widget.measurement_combo_box.setCurrentIndex(index)
                            break

                if (sample := meta.get("sample")) is not None:
                    general_widget.set_sample_name(sample)

                if (voltage_begin := meta.get("voltage_begin")) is not None:
                    general_widget.set_begin_voltage(voltage_begin)

                if (voltage_end := meta.get("voltage_end")) is not None:
                    general_widget.set_end_voltage(voltage_end)

                if (voltage_step := meta.get("voltage_step")) is not None:
                    general_widget.set_step_voltage(voltage_step)

                if (waiting_time := meta.get("waiting_time")) is not None:
                    general_widget.set_waiting_time(waiting_time)

                if (waiting_time_continuous := meta.get("waiting_time_continuous")) is not None:
                    general_widget.set_waiting_time_continuous(waiting_time_continuous)

                if (current_compliance := meta.get("current_compliance")) is not None:
                    general_widget.set_current_compliance(current_compliance)

                # Data
                if measurement_type == "iv":
                    self.iv_plots_data_windget.on_load_iv_readings(data)
                    self.iv_plots_data_windget.on_load_it_readings(continuous_data)
                    self.on_toggle_smu(True)
                    self.on_toggle_smu2(False)
                    self.on_toggle_elm(bool(self.iv_plots_data_windget.iv_plot_widget.elm_series.count()))
                    self.on_toggle_elm2(bool(self.iv_plots_data_windget.iv_plot_widget.elm2_series.count()))
                if measurement_type == "iv_bias":
                    self.iv_plots_data_windget.on_load_iv_readings(data)
                    self.iv_plots_data_windget.on_load_it_readings(continuous_data)
                    self.on_toggle_smu(True)
                    self.on_toggle_smu2(True)
                    self.on_toggle_elm(bool(self.iv_plots_data_windget.iv_plot_widget.elm_series.count()))
                    self.on_toggle_elm2(bool(self.iv_plots_data_windget.iv_plot_widget.elm2_series.count()))
                if measurement_type == "cv":
                    self.cv_plots_data_windget.load_cv_readings(data)
                    self.cv_plots_data_windget.load_cv2_readings(data)
            finally:
                self.main_window.setEnabled(True)

    # State slots

    def set_idle_state(self) -> None:
        self.main_window.control_tab_widget.setEnabled(True)
        self.main_window.set_idle_state()
        self.main_window.clear_message()
        self.main_window.clear_progress()
        self.update_continuous_option()
        with self.cache:
            self.cache.clear()

    def set_running_state(self) -> None:
        self.main_window.set_running_state()

    def set_stopping_state(self) -> None:
        self.main_window.set_stopping_state()
        self.main_window.set_message("Stop requested...")
        self.state.abort_event.set()

    # Slots

    def handle_exception(self, exc: Exception) -> None:
        """Shows up to one error message at a time."""
        if not self.is_exception_dialog_active:
            self.is_exception_dialog_active = True
            show_exception(exc, self.main_window)
            self.is_exception_dialog_active = False

    @QtCore.Slot(dict)
    def on_update(self, data: Mapping[str, Any]) -> None:
        cache = {}

        if (fsm_state := data.get("fsm_state")) is not None:
            cache.update({"fsm_state": fsm_state})

        if (source_voltage := data.get("source_voltage")) is not None:
            self.main_window.updateSourceVoltage(source_voltage)
            cache.update({"source_voltage": source_voltage})

        if (bias_source_voltage := data.get("bias_source_voltage")) is not None:
            self.main_window.updateBiasSourceVoltage(bias_source_voltage)
            cache.update({"bias_source_voltage": bias_source_voltage})

        if (smu_voltage := data.get("smu_voltage")) is not None:
            self.main_window.updateSMUVoltage(smu_voltage)
            cache.update({"smu_voltage": smu_voltage})

        if (smu_current := data.get("smu_current")) is not None:
            self.main_window.updateSMUCurrent(smu_current)
            cache.update({"smu_current": smu_current})

        if (smu2_voltage := data.get("smu2_voltage")) is not None:
            self.main_window.updateSMU2Voltage(smu2_voltage)
            cache.update({"smu2_voltage": smu2_voltage})

        if (smu2_current := data.get("smu2_current")) is not None:
            self.main_window.updateSMU2Current(smu2_current)
            cache.update({"smu2_current": smu2_current})

        if (elm_current := data.get("elm_current")) is not None:
            self.main_window.updateELMCurrent(elm_current)
            cache.update({"elm_current": elm_current})

        if (elm2_current := data.get("elm2_current")) is not None:
            self.main_window.updateELM2Current(elm2_current)
            cache.update({"elm2_current": elm2_current})

        if (lcr_capacity := data.get("lcr_capacity")) is not None:
            self.main_window.updateLCRCapacity(lcr_capacity)
            cache.update({"lcr_capacity": lcr_capacity})

        if (dmm_temperature := data.get("dmm_temperature")) is not None:
            self.main_window.updateDMMTemperature(dmm_temperature)
            cache.update({"dmm_temperature": dmm_temperature})

        if (tcu_temperature := data.get("tcu_temperature")) is not None:
            self.main_window.updateTCUTemperature(tcu_temperature)
            cache.update({"tcu_temperature": tcu_temperature})

        if (tcu_state := data.get("tcu_state")) is not None:
            self.main_window.updateTCUState(tcu_state)
            cache.update({"tcu_state": tcu_state})

        if (source_output_state := data.get("source_output_state")) is not None:
            self.main_window.updateSourceOutputState(source_output_state)

        if (bias_source_output_state := data.get("bias_source_output_state")) is not None:
            self.main_window.updateBiasSourceOutputState(bias_source_output_state)

        if (message := data.get("message")) is not None:
            self.main_window.set_message(message)

        if (progress := data.get("progress")) is not None:
            minimum, maximum, value = progress
            self.main_window.set_progress(minimum, maximum, value)

        with self.cache:
            self.cache.update(cache)

    @QtCore.Slot(bool)
    def on_continuous_toggled(self, checked: bool) -> None:
        self.main_window.set_continuous(checked)
        self.iv_plots_data_windget.set_continuous(checked)
        self.cv_plots_data_windget.set_continuous(checked)
        self.main_window.general_widget.continuous_group_box.setEnabled(checked)

    @QtCore.Slot(int)
    def on_continuous_changed(self, state: int) -> None:
        self.on_continuous_toggled(state == QtCore.Qt.CheckState.Checked)

    @QtCore.Slot(int)
    def on_measurement_changed(self, index: int) -> None:
        if index >= len(self.measurement_registry):
            logger.error("Invalid measurement spec index: %d", index)
            return

        spec: MeasurementParameters = self.measurement_registry[index]

        if spec.type == "iv":
            self.main_window.set_data_widget(self.iv_plots_data_windget)
            self.main_window.continuous_action.setEnabled(spec.provides_continuous)
            self.main_window.general_widget.bias_group_box.setEnabled(False)
            self.main_window.general_widget.continuous_group_box.setEnabled(
                self.main_window.is_continuous()
            )
        elif spec.type == "iv_bias":
            self.main_window.set_data_widget(self.iv_plots_data_windget)
            self.main_window.continuous_action.setEnabled(spec.provides_continuous)
            self.main_window.general_widget.bias_group_box.setEnabled(True)
            self.main_window.general_widget.continuous_group_box.setEnabled(
                self.main_window.is_continuous()
            )
        elif spec.type == "cv":
            self.main_window.set_data_widget(self.cv_plots_data_windget)
            self.main_window.continuous_action.setEnabled(spec.provides_continuous)
            self.main_window.general_widget.bias_group_box.setEnabled(False)
            self.main_window.general_widget.continuous_group_box.setEnabled(False)
        self.update_continuous_option()

        enabled = "smu" in spec.supported_roles
        self.main_window.set_role_enabled("smu", enabled)

        enabled = "smu2" in spec.supported_roles
        self.main_window.set_role_enabled("smu2", enabled)

        enabled = "elm" in spec.supported_roles
        self.main_window.set_role_enabled("elm", enabled)

        enabled = "elm2" in spec.supported_roles
        self.main_window.set_role_enabled("elm2", enabled)

        enabled = "lcr" in spec.supported_roles
        self.main_window.set_role_enabled("lcr", enabled)

        general_widget = self.main_window.general_widget

        enabled = "smu" in spec.default_roles
        general_widget.set_role_checked("smu", enabled)

        enabled = "smu2" in spec.default_roles
        general_widget.set_role_checked("smu2", enabled)

        enabled = "elm" in spec.default_roles
        general_widget.set_role_checked("elm", enabled)

        enabled = "elm2" in spec.default_roles
        general_widget.set_role_checked("elm2", enabled)

        enabled = "lcr" in spec.default_roles
        general_widget.set_role_checked("lcr", enabled)

        general_widget.set_voltage_unit(spec.voltage_unit)
        general_widget.set_begin_voltage(spec.default_begin_voltage)
        general_widget.set_end_voltage(spec.default_end_voltage)
        general_widget.set_step_voltage(spec.default_step_voltage)
        general_widget.set_waiting_time(spec.default_waiting_time)
        general_widget.set_waiting_time_continuous(spec.default_waiting_time_continuous)
        general_widget.set_current_compliance_unit(spec.current_compliance_unit)
        general_widget.set_current_compliance(spec.default_current_compliance)

        self.on_instruments_changed()

    @QtCore.Slot()
    def on_instruments_changed(self) -> None:
        general_widget = self.main_window.general_widget
        general_widget.set_current_compliance_locked(False)
        #
        # HACK Not all instruments support compliance!
        # TODO Implement instrument capabilities to lock not supported inputs
        #
        if general_widget.is_role_checked("smu"):
            ...
        elif general_widget.is_role_checked("elm"):
            role = self.main_window.find_role("elm")
            if role and role.resource_widget.model() in ["K6517B"]:
                general_widget.set_current_compliance_locked(True)
                general_widget.set_current_compliance(1.0e-3)  # fixed for K6517B
        elif general_widget.is_role_checked("elm2"):
            role = self.main_window.find_role("elm2")
            if role and role.resource_widget.model() in ["K6517B"]:
                general_widget.set_current_compliance_locked(True)
                general_widget.set_current_compliance(1.0e-3)  # fixed for K6517B
        elif general_widget.is_role_checked("lcr"):
            role = self.main_window.find_role("lcr")
            if role and role.resource_widget.model() in [
                "K595",
                "E4980A",
                "A4284A",
                "K4215",
            ]:
                general_widget.set_current_compliance_locked(True)

    @QtCore.Slot(bool)
    def on_toggle_smu(self, enabled: bool) -> None:
        self.iv_plots_data_windget.set_series_visible("smu", enabled)
        self.cv_plots_data_windget.set_series_visible("smu", enabled)
        self.main_window.smu_group_box.setEnabled(enabled)
        self.main_window.smu_group_box.setVisible(enabled)

    @QtCore.Slot(bool)
    def on_toggle_smu2(self, enabled: bool) -> None:
        self.iv_plots_data_windget.set_series_visible("smu2", enabled)
        self.cv_plots_data_windget.set_series_visible("smu2", enabled)
        self.main_window.smu2_group_box.setEnabled(enabled)
        self.main_window.smu2_group_box.setVisible(enabled)

    @QtCore.Slot(bool)
    def on_toggle_elm(self, enabled: bool) -> None:
        self.iv_plots_data_windget.set_series_visible("elm", enabled)
        self.cv_plots_data_windget.set_series_visible("elm", enabled)
        self.main_window.elm_group_box.setEnabled(enabled)
        self.main_window.elm_group_box.setVisible(enabled)

    @QtCore.Slot(bool)
    def on_toggle_elm2(self, enabled: bool) -> None:
        self.iv_plots_data_windget.set_series_visible("elm2", enabled)
        self.cv_plots_data_windget.set_series_visible("elm2", enabled)
        self.main_window.elm2_group_box.setEnabled(enabled)
        self.main_window.elm2_group_box.setVisible(enabled)

    @QtCore.Slot(bool)
    def on_toggle_lcr(self, enabled: bool) -> None:
        self.iv_plots_data_windget.set_series_visible("lcr", enabled)
        self.cv_plots_data_windget.set_series_visible("lcr", enabled)
        self.main_window.lcr_group_box.setEnabled(enabled)
        self.main_window.lcr_group_box.setVisible(enabled)

    @QtCore.Slot(bool)
    def on_toggle_dmm(self, enabled: bool) -> None:
        self.main_window.dmm_group_box.setEnabled(enabled)
        self.main_window.dmm_group_box.setVisible(enabled)

    @QtCore.Slot(bool)
    def on_toggle_tcu(self, enabled: bool) -> None:
        self.main_window.tcu_group_box.setEnabled(enabled)
        self.main_window.tcu_group_box.setVisible(enabled)

    @QtCore.Slot(bool)
    def on_toggle_switch(self, state: bool) -> None: ...

    @QtCore.Slot()
    def on_output_editing_finished(self) -> None:
        general_widget = self.main_window.general_widget
        if not general_widget.output_line_edit.text().strip():
            general_widget.output_line_edit.setText(os.path.expanduser("~"))

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
        measurement = self.main_window.general_widget.current_measurement()
        enabled = False
        if measurement is not None:
            enabled = measurement.provides_continuous
        self.main_window.continuous_check_box.setEnabled(enabled)

    def create_filename(self) -> str:
        path = self.main_window.general_widget.output_dir()
        sample = self.state.sample
        timestamp = datetime.fromtimestamp(self.state.timestamp).strftime(
            "%Y-%m-%dT%H-%M-%S"
        )
        filename = safe_filename(f"{sample}-{timestamp}.txt")
        return os.path.join(path, filename)

    def configure(self, params: Mapping[str, Any]) -> None:
        general_widget = self.main_window.general_widget
        for key, value in params.items():
            if key == "continuous":
                self.main_window.set_continuous(value)
            elif key == "auto_reconnect":
                self.main_window.set_auto_reconnect(value)
            elif key == "measurement_type":
                general_widget.set_current_measurement(value)
            elif key == "measurement_roles":
                general_widget.set_measurement_roles(value)
            elif key == "end_voltage":
                general_widget.set_end_voltage(value)
            elif key == "begin_voltage":
                general_widget.set_begin_voltage(value)
            elif key == "step_voltage":
                general_widget.set_step_voltage(value)
            elif key == "waiting_time":
                general_widget.set_waiting_time(value)
            elif key == "bias_voltage":
                general_widget.set_bias_voltage(value)
            elif key == "compliance":
                general_widget.set_current_compliance(value)
            elif key == "waiting_time_continuous":
                general_widget.set_waiting_time_continuous(value)
            else:
                raise KeyError(f"Invalid configuration key: {key}")

    def request_start(self) -> None:
        self.main_window.start_action.trigger()

    def request_stop(self) -> None:
        self.aborted.emit()

    def create_measurement(self, state: State) -> Measurement:
        measurement_type = state.measurement_type
        for spec in self.measurement_registry:  # TODO
            if spec.type == measurement_type:
                measurement = spec.measurement_cls(state)

                # Prepare role drivers
                for role in self.main_window.roles():
                    measurement.register_instrument(role.name())

                return measurement

        raise ValueError(f"No such measurement type: {measurement_type}")

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
            self.state.abort_event.clear()

            with self.cache:
                self.cache.update(
                    {
                        "measurement_type": state.get("measurement_type"),
                        "sample": state.get("sample"),
                    }
                )

            # Filename
            output_enabled = self.main_window.general_widget.is_output_enabled()
            filename = self.create_filename() if output_enabled else None
            self.state.update({"filename": filename})

            # Create and run measurement
            measurement = self.create_measurement(self.state)

            settings = QtCore.QSettings()
            timestamp_format = get_str(settings.value("writer/timestampFormat"), ".6f")
            value_format = get_str(settings.value("writer/valueFormat"), "+.3E")

            # discharge guard
            discharge_timeout = get_float(settings.value("misc/discharge_timeout"), 60.0)
            discharge_threshold = get_float(settings.value("misc/discharge_threshold"), 0.5)
            self.state.update({
                "discharge_timeout": discharge_timeout,
                "discharge_threshold": discharge_threshold,
            })

            self.main_window.clear()
            self.iv_plots_data_windget.clear()
            self.cv_plots_data_windget.clear()

            job = MeasurementJob(
                measurement,
                timestamp_format=timestamp_format,
                value_format=value_format,
                has_finished=self.measurement_finished.emit,
            )
            self.submit_background_job(job)

        except Exception as exc:
            logger.exception(exc)
            self.failed.emit(exc)
            self.aborted.emit()

    def request_change_voltage(self, parameters: ChangeVoltageParameters) -> None:
        state = self.snapshot().state
        if state != FSMState.CONTINUOUS:
            raise RuntimeError(
                f"Cannot change voltage in state '{state.value}'. Expected 'continuous'."
            )
        self.change_voltage_controller.request_change_voltage(parameters)

    def on_lcr_perform_correction(self) -> None:
        role = self.main_window.find_role("lcr")
        if role is None:
            return
        model = role.model()
        config = role.configs().get(model, {})
        if model == "K4215":
            dialog = K4215CorrectionDialog(self.main_window)
            external_bias_tee = config.get("external_bias_tee.enabled", False)
            if external_bias_tee:
                dialog.set_hint("<b>With</b> external Bias Tee (applying -10V DC)")
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            self.main_window.control_tab_widget.setEnabled(False)

            resource_name, visa_library = parse_resource(role.resource_name())
            resource_config = ResourceConfig(
                resource_name=resource_name,
                visa_library=visa_library,
                termination=role.termination(),
                timeout=role.timeout(),
            )

            self.submit_background_job(
                K4215PerformCorrectionJob(
                    resource_config=resource_config,
                    cable_length=config.get("correction.length"),
                    open_correction=dialog.is_open_correction(),
                    short_correction=dialog.is_short_correction(),
                    load_correction=dialog.get_load_correction(),
                    external_bias_tee=external_bias_tee,
                    progress=self.progress_changed.emit,
                    message=self.message_changed.emit,
                )
            )


class ChangeVoltageController(QtCore.QObject):
    def __init__(
        self, main_window, context: State, parent: Optional[QtCore.QObject] = None
    ) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.context: State = context
        # Connect signals
        self.main_window.prepare_change_voltage.connect(self.on_prepare_change_voltage)

    def source_voltage(self) -> float:
        source_voltage = self.context.source_voltage
        if source_voltage is not None:
            return source_voltage
        return self.main_window.general_widget.end_voltage()

    @QtCore.Slot()
    def on_prepare_change_voltage(self) -> None:
        general_widget = self.main_window.general_widget
        dialog = ChangeVoltageDialog(self.main_window)
        dialog.set_end_voltage(self.source_voltage())
        dialog.set_step_voltage(general_widget.step_voltage())
        dialog.set_waiting_time(general_widget.waiting_time())
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            parameters = ChangeVoltageParameters(
                end_voltage=dialog.end_voltage(),
                step_voltage=dialog.step_voltage(),
                waiting_time=dialog.waiting_time(),
            )
            self.request_change_voltage(parameters)

    def request_change_voltage(self, parameters: ChangeVoltageParameters) -> None:
        if self.main_window.is_change_voltage_enabled():
            logger.info(
                "request change voltage: end_voltage=%s, step_voltage=%s, waiting_time=%s",
                format_metric(parameters.end_voltage, "V"),
                format_metric(parameters.step_voltage, "V"),
                format_metric(parameters.waiting_time, "s"),
            )
            self.context.request_change_voltage(parameters)
            self.main_window.set_change_voltage_enabled(False)

    @QtCore.Slot()
    def on_change_voltage_ready(self) -> None:
        self.main_window.set_change_voltage_enabled(True)
