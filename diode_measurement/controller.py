import contextlib
import logging
import math
import os
import pathlib
import threading
import time

from datetime import datetime
from typing import Any, Dict, List, Iterator, Optional

from PyQt5 import QtCore, QtWidgets

from . import __version__

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
from .view.panels import K4215Panel

# DMM
from .view.panels import K2700Panel

# Switches
from .view.panels import BrandBoxPanel

from .view.widgets import showException
from .view.dialogs import ChangeVoltageDialog

from .view.plots import CV2PlotWidget, CVPlotWidget, ItPlotWidget, IVPlotWidget

from .measurement import Measurement
from .measurement.iv import IVMeasurement
from .measurement.iv_bias import IVBiasMeasurement
from .measurement.cv import CVMeasurement

from .reader import Reader
from .writer import Writer

from .utils import get_resource
from .utils import safe_filename
from .utils import format_metric

from .cache import Cache
from .settings import DEFAULTS
from .state import State

__all__ = ["Controller"]

logger = logging.getLogger(__name__)

MEASUREMENTS = {
    "iv": IVMeasurement,
    "iv_bias": IVBiasMeasurement,
    "cv": CVMeasurement,
}


class MeasurementRunner:
    """Measurement runner.

    Accepted options:
     - `timestamp_format` set timestamp format of file writer.
     - `value_format` set value format of file writer.
    """

    def __init__(self, measurement: Measurement, options: dict = None) -> None:
        self.measurement = measurement
        self.options: dict = {}
        if options is not None:
            self.options.update(options)

    def create_writer(self, fp) -> Writer:
        writer: Writer = Writer(fp)
        # Configure writer
        timestamp_format = self.options.get("timestamp_format")
        if timestamp_format:
            writer.timestamp_format = timestamp_format
        value_format = self.options.get("value_format")
        if value_format:
            writer.value_format = value_format
        return writer

    def __call__(self) -> None:
        measurement = self.measurement
        filename = measurement.state.get("filename")
        with contextlib.ExitStack() as stack:
            if filename:
                logger.info("preparing output file: %s", filename)

                path = os.path.dirname(filename)
                if not os.path.exists(path):
                    logger.debug("create output dir: %s", path)
                    os.makedirs(path)

                fp = stack.enter_context(open(filename, "w", newline=""))
                writer = self.create_writer(fp)
                # TODO
                # Note: using signals executes slots in main thread, should be worker thread
                measurement.started_event.subscribe(lambda state=dict(measurement.state): writer.write_meta(state))
                if isinstance(measurement, IVMeasurement):
                    measurement.iv_reading_event.subscribe(lambda reading: writer.write_iv_row(reading))
                    measurement.it_reading_event.subscribe(lambda reading: writer.write_it_row(reading))
                if isinstance(measurement, IVBiasMeasurement):
                    measurement.iv_reading_event.subscribe(lambda reading: writer.write_iv_bias_row(reading))
                    measurement.it_reading_event.subscribe(lambda reading: writer.write_it_bias_row(reading))
                if isinstance(measurement, CVMeasurement):
                    measurement.cv_reading_event.subscribe(lambda reading: writer.write_cv_row(reading))
                measurement.finished_event.subscribe(lambda: writer.flush())
            measurement.run()


class Controller(QtCore.QObject):

    started = QtCore.pyqtSignal()
    aborted = QtCore.pyqtSignal()
    update = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(Exception)
    finished = QtCore.pyqtSignal()

    requestChangeVoltage = QtCore.pyqtSignal(float, float, float)
    changeVoltageReady = QtCore.pyqtSignal()

    def __init__(self, view, parent=None) -> None:
        super().__init__(parent)
        self.view = view

        self.isExceptionDialogActive: bool = False
        self.abortRequested = threading.Event()
        self.measurementThread: Optional[threading.Thread] = None
        self.state: State = State()
        self.cache: Cache = Cache()
        self.rpc_params: Cache = Cache()

        self.view.setProperty("contentsUrl", "https://github.com/hephy-dd/diode-measurement")
        self.view.setProperty("about", f"""
            <h3>Diode Measurement</h3>
            <p>IV/CV measurements for silicon sensors.</p>
            <p>Version {__version__}</p>
            <p>This software is licensed under the GNU General Public License Version 3.</p>
            <p>Copyright &copy; 2021-2025 <a href=\"https://oeaw.ac.at/mbi\">MBI</a></p>
        """)

        # Controller
        self.ivPlotsController = IVPlotsController(self)
        self.cvPlotsController = CVPlotsController(self)

        self.changeVoltageController = ChangeVoltageController(self.view, self.state, self)
        self.requestChangeVoltage.connect(self.changeVoltageController.onRequestChangeVoltage)
        self.changeVoltageReady.connect(self.changeVoltageController.onChangeVoltageReady)
        self.failed.connect(self.handleException)

        # Source meter unit
        role = self.view.addRole("SMU")
        role.addInstrumentPanel(K237Panel())
        role.addInstrumentPanel(K2410Panel())
        role.addInstrumentPanel(K2470Panel())
        role.addInstrumentPanel(K2657APanel())

        # Bias source meter unit
        role = self.view.addRole("SMU2")
        role.addInstrumentPanel(K237Panel())
        role.addInstrumentPanel(K2410Panel())
        role.addInstrumentPanel(K2470Panel())
        role.addInstrumentPanel(K2657APanel())

        # Electrometer
        role = self.view.addRole("ELM")
        role.addInstrumentPanel(K6514Panel())
        role.addInstrumentPanel(K6517BPanel())
        role.resourceWidget.modelChanged.connect(self.onInstrumentsChanged)  # HACK

        # Electrometer 2
        role = self.view.addRole("ELM2")
        role.addInstrumentPanel(K6514Panel())
        role.addInstrumentPanel(K6517BPanel())
        role.resourceWidget.modelChanged.connect(self.onInstrumentsChanged)  # HACK

        # LCR meter
        role = self.view.addRole("LCR")
        role.addInstrumentPanel(K595Panel())
        role.addInstrumentPanel(E4980APanel())
        role.addInstrumentPanel(A4284APanel())
        role.addInstrumentPanel(K4215Panel())

        # Temperatur
        role = self.view.addRole("DMM")
        role.addInstrumentPanel(K2700Panel())

        # Switch
        role = self.view.addRole("Switch")
        role.addInstrumentPanel(BrandBoxPanel())

        self.view.importAction.triggered.connect(lambda: self.onImportFile())

        self.view.startAction.triggered.connect(self.started)
        self.view.startButton.clicked.connect(self.view.startAction.trigger)

        self.view.stopAction.triggered.connect(self.aborted)
        self.view.stopButton.clicked.connect(self.view.stopAction.trigger)

        self.view.continuousAction.toggled.connect(self.onContinuousToggled)
        self.view.continuousCheckBox.stateChanged.connect(self.onContinuousChanged)

        for spec in DEFAULTS:
            self.view.generalWidget.addMeasurement(spec)
        self.view.generalWidget.measurementComboBox.currentIndexChanged.connect(self.onMeasurementChanged)

        self.view.generalWidget.outputLineEdit.editingFinished.connect(self.onOutputEditingFinished)
        self.view.generalWidget.currentComplianceChanged.connect(self.onCurrentComplianceChanged)
        self.view.generalWidget.continueInComplianceChanged.connect(self.onContinueInComplianceChanged)
        self.view.generalWidget.waitingTimeContinuousChanged.connect(self.onWaitingTimeContinuousChanged)

        self.onMeasurementChanged(0)

        self.update.connect(self.onUpdate)

        self.view.generalWidget.instrumentsChanged.connect(self.onInstrumentsChanged)

        self.onInstrumentsChanged()

        self.view.generalWidget.smuCheckBox.toggled.connect(self.onToggleSmu)
        self.view.generalWidget.smu2CheckBox.toggled.connect(self.onToggleSmu2)
        self.view.generalWidget.elmCheckBox.toggled.connect(self.onToggleElm)
        self.view.generalWidget.elm2CheckBox.toggled.connect(self.onToggleElm2)
        self.view.generalWidget.lcrCheckBox.toggled.connect(self.onToggleLcr)
        self.view.generalWidget.dmmCheckBox.toggled.connect(self.onToggleDmm)
        self.view.generalWidget.switchCheckBox.toggled.connect(self.onToggleSwitch)

        self.onToggleSmu2(False)
        self.onToggleElm(False)
        self.onToggleElm2(False)
        self.onToggleLcr(False)
        self.onToggleDmm(False)
        self.onToggleSwitch(False)

        self.view.messageLabel.hide()
        self.view.progressBar.hide()

        # States

        self.idleState = QtCore.QState()
        self.idleState.entered.connect(self.setIdleState)

        self.runningState = QtCore.QState()
        self.runningState.entered.connect(self.setRunningState)

        self.stoppingState = QtCore.QState()
        self.stoppingState.entered.connect(self.setStoppingState)

        # Transitions

        self.idleState.addTransition(self.started, self.runningState)

        self.runningState.addTransition(self.finished, self.idleState)
        self.runningState.addTransition(self.aborted, self.stoppingState)

        self.stoppingState.addTransition(self.finished, self.idleState)

        # State machine

        self.stateMachine = QtCore.QStateMachine()
        self.stateMachine.addState(self.idleState)
        self.stateMachine.addState(self.runningState)
        self.stateMachine.addState(self.stoppingState)
        self.stateMachine.setInitialState(self.idleState)
        self.stateMachine.start()

    def snapshot(self):
        """Return application state snapshot."""
        with self.cache:
            snapshot = {}
            snapshot["state"] = self.cache.get("rpc_state", "idle")
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

    def prepareState(self) -> Dict[str, Any]:
        state: Dict[str, Any] = {}

        state["sample"] = self.view.generalWidget.sampleName()
        state["measurement_type"] = self.view.generalWidget.currentMeasurement().get("type")
        state["timestamp"] = time.time()

        state["continuous"] = self.view.isContinuous()
        state["reset"] = self.view.isReset()
        state["auto_reconnect"] = self.view.isAutoReconnect()
        state["voltage_begin"] = self.view.generalWidget.beginVoltage()
        state["voltage_end"] = self.view.generalWidget.endVoltage()
        state["voltage_step"] = self.view.generalWidget.stepVoltage()
        state["waiting_time"] = self.view.generalWidget.waitingTime()
        state["bias_voltage"] = self.view.generalWidget.biasVoltage()
        state["current_compliance"] = self.view.generalWidget.currentCompliance()
        state["continue_in_compliance"] = self.view.generalWidget.isContinueInCompliance()
        state["waiting_time_continuous"] = self.view.generalWidget.waitingTimeContinuous()

        roles: Dict[str, Any] = state.setdefault("roles", {})

        for role in self.view.roles():
            key = role.name().lower()
            resource = role.resourceWidget.resourceName()
            resource_name, visa_library = get_resource(resource)
            config = roles.setdefault(key, {})
            config.update({
                "resource_name": resource_name,
                "visa_library": visa_library,
                "model": role.resourceWidget.model(),
                "termination": role.resourceWidget.termination(),
                "timeout": role.resourceWidget.timeout()
            })
            config.update({"options": role.currentConfig()})

        if self.view.generalWidget.isSMUEnabled():
            state["source_role"] = "smu"
        elif self.view.generalWidget.isELMEnabled():
            state["source_role"] = "elm"
        elif self.view.generalWidget.isLCREnabled():
            state["source_role"] = "lcr"

        if self.view.generalWidget.isSMU2Enabled():
            state["bias_source_role"] = "smu2"

        roles.setdefault("smu", {}).update({"enabled": self.view.generalWidget.isSMUEnabled()})
        roles.setdefault("smu2", {}).update({"enabled": self.view.generalWidget.isSMU2Enabled()})
        roles.setdefault("elm", {}).update({"enabled": self.view.generalWidget.isELMEnabled()})
        roles.setdefault("elm2", {}).update({"enabled": self.view.generalWidget.isELM2Enabled()})
        roles.setdefault("lcr", {}).update({"enabled": self.view.generalWidget.isLCREnabled()})
        roles.setdefault("dmm", {}).update({"enabled": self.view.generalWidget.isDMMEnabled()})
        roles.setdefault("switch", {}).update({"enabled": self.view.generalWidget.isSwitchEnabled()})

        for key, value in state.items():
            logger.info("> %s: %s", key, value)

        return state

    def shutdown(self):
        self.stateMachine.stop()
        self.abortRequested.set()

    def loadSettings(self):
        settings = QtCore.QSettings()

        geometry = settings.value("mainwindow/geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if geometry.isEmpty():
            self.view.resize(800, 600)
        else:
            self.view.restoreGeometry(geometry)

        state = settings.value("mainwindow/state", QtCore.QByteArray(), QtCore.QByteArray)
        self.view.restoreState(state)

        continuous = settings.value("continuous", False, bool)
        self.view.setContinuous(continuous)

        reset = settings.value("reset", False, bool)
        self.view.setReset(reset)

        autoReconnect = settings.value("autoReconnect", False, bool)
        self.view.setAutoReconnect(autoReconnect)

        settings.beginGroup("generalTab")

        index = settings.value("measurement/index", 0, int)
        self.view.generalWidget.measurementComboBox.setCurrentIndex(index)

        enabled = settings.value("smu/enabled", False, bool)
        self.view.generalWidget.setSMUEnabled(enabled)

        enabled = settings.value("smu2/enabled", False, bool)
        self.view.generalWidget.setSMU2Enabled(enabled)

        enabled = settings.value("elm/enabled", False, bool)
        self.view.generalWidget.setELMEnabled(enabled)

        enabled = settings.value("elm2/enabled", False, bool)
        self.view.generalWidget.setELM2Enabled(enabled)

        enabled = settings.value("lcr/enabled", False, bool)
        self.view.generalWidget.setLCREnabled(enabled)

        enabled = settings.value("dmm/enabled", False, bool)
        self.view.generalWidget.setDMMEnabled(enabled)

        enabled = settings.value("switch/enabled", False, bool)
        self.view.generalWidget.setSwitchEnabled(enabled)

        enabled = settings.value("outputEnabled", False, bool)
        self.view.generalWidget.setOutputEnabled(enabled)

        sample = settings.value("sampleName", "Unnamed")
        self.view.generalWidget.setSampleName(sample)

        path = settings.value("outputDir", os.path.expanduser("~"))
        self.view.generalWidget.setOutputDir(path)

        voltage = settings.value("beginVoltage", 1, float)
        self.view.generalWidget.setBeginVoltage(voltage)

        voltage = settings.value("endVoltage", 1, float)
        self.view.generalWidget.setEndVoltage(voltage)

        voltage = settings.value("stepVoltage", 1, float)
        self.view.generalWidget.setStepVoltage(voltage)

        waitingTime = settings.value("waitingTime", 1, float)
        self.view.generalWidget.setWaitingTime(waitingTime)

        voltage = settings.value("biasVoltage", 0, float)
        self.view.generalWidget.setBiasVoltage(voltage)

        currentCompliance = settings.value("currentCompliance", 1, float)
        self.view.generalWidget.setCurrentCompliance(currentCompliance)

        continueInCompliance = settings.value("continueInCompliance", False, bool)
        self.view.generalWidget.setContinueInCompliance(continueInCompliance)

        waitingTime = settings.value("waitingTimeContinuous", 1, float)
        self.view.generalWidget.setWaitingTimeContinuous(waitingTime)

        settings.endGroup()

        settings.beginGroup("roles")

        for role in self.view.roles():
            name = role.name().lower()
            settings.beginGroup(name)
            role.setModel(settings.value("model", ""))
            role.setResourceName(settings.value("resource", ""))
            role.setTermination(settings.value("termination", ""))
            role.setTimeout(settings.value("timeout", 4, int))
            role.setResources(settings.value("resources", {}, dict))
            role.setConfigs(settings.value("configs", {}, dict))
            settings.endGroup()

        settings.endGroup()

        self.onInstrumentsChanged()

    def storeSettings(self):
        settings = QtCore.QSettings()

        settings.setValue("mainwindow/geometry", self.view.saveGeometry())
        settings.setValue("mainwindow/state", self.view.saveState())

        continuous = self.view.isContinuous()
        settings.setValue("continuous", continuous)

        reset = self.view.isReset()
        settings.setValue("reset", reset)

        autoReconnect = self.view.isAutoReconnect()
        settings.setValue("autoReconnect", autoReconnect)

        settings.beginGroup("generalTab")

        measurement_index = self.view.generalWidget.measurementComboBox.currentIndex()
        settings.setValue("measurement/index", measurement_index)

        enabled = self.view.generalWidget.isSMUEnabled()
        settings.setValue("smu/enabled", enabled)

        enabled = self.view.generalWidget.isSMU2Enabled()
        settings.setValue("smu2/enabled", enabled)

        enabled = self.view.generalWidget.isELMEnabled()
        settings.setValue("elm/enabled", enabled)

        enabled = self.view.generalWidget.isELM2Enabled()
        settings.setValue("elm2/enabled", enabled)

        enabled = self.view.generalWidget.isLCREnabled()
        settings.setValue("lcr/enabled", enabled)

        enabled = self.view.generalWidget.isDMMEnabled()
        settings.setValue("dmm/enabled", enabled)

        enabled = self.view.generalWidget.isSwitchEnabled()
        settings.setValue("switch/enabled", enabled)

        enabled = self.view.generalWidget.isOutputEnabled()
        settings.setValue("outputEnabled", enabled)

        sample = self.view.generalWidget.sampleName()
        settings.setValue("sampleName", sample)

        path = self.view.generalWidget.outputDir()
        settings.setValue("outputDir", path)

        voltage = self.view.generalWidget.beginVoltage()
        settings.setValue("beginVoltage", voltage)

        voltage = self.view.generalWidget.endVoltage()
        settings.setValue("endVoltage", voltage)

        voltage = self.view.generalWidget.stepVoltage()
        settings.setValue("stepVoltage", voltage)

        waitingTime = self.view.generalWidget.waitingTime()
        settings.setValue("waitingTime", waitingTime)

        voltage = self.view.generalWidget.biasVoltage()
        settings.setValue("biasVoltage", voltage)

        currentCompliance = self.view.generalWidget.currentCompliance()
        settings.setValue("currentCompliance", currentCompliance)

        continueInCompliance = self.view.generalWidget.isContinueInCompliance()
        settings.setValue("continueInCompliance", continueInCompliance)

        waitingTime = self.view.generalWidget.waitingTimeContinuous()
        settings.setValue("waitingTimeContinuous", waitingTime)

        settings.endGroup()

        settings.beginGroup("roles")

        for role in self.view.roles():
            name = role.name().lower()
            settings.beginGroup(name)
            settings.setValue("model", role.model())
            settings.setValue("resource", role.resourceName())
            settings.setValue("termination", role.termination())
            settings.setValue("timeout", role.timeout())
            settings.setValue("resources", role.resources())
            settings.setValue("configs", role.configs())
            settings.endGroup()

        settings.endGroup()

    def onImportFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.view,
            "Select measurement file",
            self.view.generalWidget.outputDir(),
            "Text (*.txt);;All (*);;"
        )
        if filename:
            logger.info("Importing measurement file: %s", filename)
            self.view.setEnabled(False)
            self.view.clear()
            self.ivPlotsController.clear()
            self.cvPlotsController.clear()
            try:
                # Open in binary mode!
                with open(filename, "rb") as fp:
                    reader = Reader(fp)
                    meta = reader.read_meta()
                    data = reader.read_data()
                    continuousData = reader.read_data()

                # Meta
                self.view.generalWidget.measurementComboBox.setCurrentIndex(-1)
                if meta.get("measurement_type"):
                    for index in range(self.view.generalWidget.measurementComboBox.count()):
                        spec = self.view.generalWidget.measurementComboBox.itemData(index)
                        if spec["type"] == meta.get("measurement_type"):
                            self.view.generalWidget.measurementComboBox.setCurrentIndex(index)
                            break
                if meta.get("sample"):
                    self.view.generalWidget.setSampleName(meta.get("sample"))
                if meta.get("voltage_begin"):
                    self.view.generalWidget.setBeginVoltage(meta.get("voltage_begin"))
                if meta.get("voltage_end"):
                    self.view.generalWidget.setEndVoltage(meta.get("voltage_end"))
                if meta.get("voltage_step"):
                    self.view.generalWidget.setStepVoltage(meta.get("voltage_step"))
                if meta.get("waiting_time"):
                    self.view.generalWidget.setWaitingTime(meta.get("waiting_time"))
                if meta.get("waiting_time_continuous"):
                    self.view.generalWidget.setWaitingTimeContinuous(meta.get("waiting_time_continuous"))
                if meta.get("current_compliance"):
                    self.view.generalWidget.setCurrentCompliance(meta.get("current_compliance"))

                # Data
                if meta.get("measurement_type") in ["iv", "iv_bias"]:
                    self.ivPlotsController.onLoadIVReadings(data)
                    self.ivPlotsController.onLoadItReadings(continuousData)
                if meta.get("measurement_type") in ["cv"]:
                    self.cvPlotsController.onLoadCVReadings(data)
                    self.cvPlotsController.onLoadCV2Readings(data)
            finally:
                self.view.setEnabled(True)

    # State slots

    def setIdleState(self):
        self.view.setIdleState()
        self.view.clearMessage()
        self.view.clearProgress()
        self.updateContinuousOption()
        with self.cache:
            self.cache.clear()
        self.ivPlotsController.updateTimer.stop()
        self.cvPlotsController.updateTimer.stop()

    def setRunningState(self):
        self.view.setRunningState()
        self.view.clear()
        self.startMeasurement()
        self.ivPlotsController.clear()
        self.cvPlotsController.clear()
        self.ivPlotsController.updateTimer.start(500)
        self.cvPlotsController.updateTimer.start(500)

    def setStoppingState(self):
        self.view.setStoppingState()
        self.view.setMessage("Stop requested...")
        self.state.update({"stop_requested": True})

    # Slots

    def handleException(self, exc):
        """Shows up to one error message at a time."""
        if not self.isExceptionDialogActive:
            self.isExceptionDialogActive = True
            showException(exc, self.view)
            self.isExceptionDialogActive = False

    def onUpdate(self, data):
        cache = {}
        if "rpc_state" in data:
            cache.update({"rpc_state": data.get("rpc_state")})
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
            self.view.setMessage(data.get("message", ""))
        if "progress" in data:
            self.view.setProgress(*data.get("progress", (0, 0, 0)))
        with self.cache:
            self.cache.update(cache)

    def onContinuousToggled(self, checked):
        self.view.setContinuous(checked)
        self.ivPlotsController.setContinuous(checked)
        self.cvPlotsController.setContinuous(checked)
        self.view.generalWidget.continuousGroupBox.setEnabled(checked)

    def onContinuousChanged(self, state):
        self.onContinuousToggled(state == QtCore.Qt.Checked)

    def onMeasurementChanged(self, index):
        spec = DEFAULTS[index]

        if spec.get("type") == "iv":
            self.view.setDataWidget(self.ivPlotsController.dataWidget)
            self.view.continuousAction.setEnabled(True)
            self.view.generalWidget.biasGroupBox.setEnabled(False)
            self.view.generalWidget.continuousGroupBox.setEnabled(self.view.isContinuous())
        elif spec.get("type") == "iv_bias":
            self.view.setDataWidget(self.ivPlotsController.dataWidget)
            self.view.continuousAction.setEnabled(True)
            self.view.generalWidget.biasGroupBox.setEnabled(True)
            self.view.generalWidget.continuousGroupBox.setEnabled(self.view.isContinuous())
        elif spec.get("type") == "cv":
            self.view.setDataWidget(self.cvPlotsController.dataWidget)
            self.view.continuousAction.setEnabled(False)
            self.view.generalWidget.biasGroupBox.setEnabled(False)
            self.view.generalWidget.continuousGroupBox.setEnabled(False)
        self.updateContinuousOption()

        enabled = "SMU" in spec.get("instruments", [])
        self.view.generalWidget.smuCheckBox.setEnabled(enabled)
        self.view.generalWidget.smuCheckBox.setVisible(enabled)
        self.view.smuGroupBox.setEnabled(enabled)
        self.view.smuGroupBox.setVisible(enabled)

        enabled = "SMU2" in spec.get("instruments", [])
        self.view.generalWidget.smu2CheckBox.setEnabled(enabled)
        self.view.generalWidget.smu2CheckBox.setVisible(enabled)
        self.view.smu2GroupBox.setEnabled(enabled)
        self.view.smu2GroupBox.setVisible(enabled)

        enabled = "ELM" in spec.get("instruments", [])
        self.view.generalWidget.elmCheckBox.setEnabled(enabled)
        self.view.generalWidget.elmCheckBox.setVisible(enabled)
        self.view.elmGroupBox.setEnabled(enabled)
        self.view.elmGroupBox.setVisible(enabled)

        enabled = "ELM2" in spec.get("instruments", [])
        self.view.generalWidget.elm2CheckBox.setEnabled(enabled)
        self.view.generalWidget.elm2CheckBox.setVisible(enabled)
        self.view.elm2GroupBox.setEnabled(enabled)
        self.view.elm2GroupBox.setVisible(enabled)

        enabled = "LCR" in spec.get("instruments", [])
        self.view.generalWidget.lcrCheckBox.setEnabled(enabled)
        self.view.generalWidget.lcrCheckBox.setVisible(enabled)
        self.view.lcrGroupBox.setEnabled(enabled)
        self.view.lcrGroupBox.setVisible(enabled)

        enabled = "SMU" in spec.get("default_instruments", [])
        self.view.generalWidget.setSMUEnabled(enabled)

        enabled = "SMU2" in spec.get("default_instruments", [])
        self.view.generalWidget.setSMU2Enabled(enabled)

        enabled = "ELM" in spec.get("default_instruments", [])
        self.view.generalWidget.setELMEnabled(enabled)

        enabled = "ELM2" in spec.get("default_instruments", [])
        self.view.generalWidget.setELM2Enabled(enabled)

        enabled = "LCR" in spec.get("default_instruments", [])
        self.view.generalWidget.setLCREnabled(enabled)

        unit = spec.get("voltage_unit")
        self.view.generalWidget.setVoltageUnit(unit)

        voltage = spec.get("default_begin_voltage", 0.0)
        self.view.generalWidget.setBeginVoltage(voltage)

        voltage = spec.get("default_end_voltage", 0.0)
        self.view.generalWidget.setEndVoltage(voltage)

        voltage = spec.get("default_step_voltage", 0.0)
        self.view.generalWidget.setStepVoltage(voltage)

        value = spec.get("default_waiting_time", 1.0)
        self.view.generalWidget.setWaitingTime(value)

        value = spec.get("default_waiting_time_continuous", 1.0)
        self.view.generalWidget.setWaitingTimeContinuous(value)

        value = spec.get("current_compliance_unit")
        self.view.generalWidget.setCurrentComplianceUnit(value)

        value = spec.get("default_current_compliance", 0.0)
        self.view.generalWidget.setCurrentCompliance(value)

        self.onInstrumentsChanged()

    def onInstrumentsChanged(self) -> None:
        self.view.generalWidget.setCurrentComplianceLocked(False)
        #
        # HACK Not all instruments support compliance!
        # TODO Implement instrument capabilities to lock not supported inputs
        #
        if self.view.generalWidget.isSMUEnabled():
            ...
        elif self.view.generalWidget.isELMEnabled():
            role = self.view.findRole("ELM")
            if role.resourceWidget.model() in ["K6517B"]:
                self.view.generalWidget.setCurrentComplianceLocked(True)
                self.view.generalWidget.setCurrentCompliance(1.0e-3)  # fixed for K6517B
        elif self.view.generalWidget.isELM2Enabled():
            role = self.view.findRole("ELM2")
            if role.resourceWidget.model() in ["K6517B"]:
                self.view.generalWidget.setCurrentComplianceLocked(True)
                self.view.generalWidget.setCurrentCompliance(1.0e-3)  # fixed for K6517B
        elif self.view.generalWidget.isLCREnabled():
            role = self.view.findRole("LCR")
            if role.resourceWidget.model() in ["K595", "E4980A", "A4284A", "K4215"]:
                self.view.generalWidget.setCurrentComplianceLocked(True)

    def onToggleSmu(self, state: bool) -> None:
        self.ivPlotsController.toggleSmuSeries(state)
        self.cvPlotsController.toggleSmuSeries(state)
        self.view.smuGroupBox.setEnabled(state)
        self.view.smuGroupBox.setVisible(state)

    def onToggleSmu2(self, state: bool) -> None:
        self.ivPlotsController.toggleSmu2Series(state)
        self.cvPlotsController.toggleSmu2Series(state)
        self.view.smu2GroupBox.setEnabled(state)
        self.view.smu2GroupBox.setVisible(state)

    def onToggleElm(self, state: bool) -> None:
        self.ivPlotsController.toggleElmSeries(state)
        self.cvPlotsController.toggleElmSeries(state)
        self.view.elmGroupBox.setEnabled(state)
        self.view.elmGroupBox.setVisible(state)

    def onToggleElm2(self, state: bool) -> None:
        self.ivPlotsController.toggleElm2Series(state)
        self.cvPlotsController.toggleElm2Series(state)
        self.view.elm2GroupBox.setEnabled(state)
        self.view.elm2GroupBox.setVisible(state)

    def onToggleLcr(self, state: bool) -> None:
        self.ivPlotsController.toggleLcrSeries(state)
        self.cvPlotsController.toggleLcrSeries(state)
        self.view.lcrGroupBox.setEnabled(state)
        self.view.lcrGroupBox.setVisible(state)

    def onToggleDmm(self, state: bool) -> None:
        self.view.dmmGroupBox.setEnabled(state)
        self.view.dmmGroupBox.setVisible(state)

    def onToggleSwitch(self, state: bool) -> None:
        ...

    def onOutputEditingFinished(self):
        if not self.view.generalWidget.outputLineEdit.text().strip():
            self.view.generalWidget.outputLineEdit.setText(os.path.expanduser("~"))

    def onCurrentComplianceChanged(self, value):
        logger.info("updated current_compliance: %s", format_metric(value, "A"))
        self.state.update({"current_compliance": value})

    def onContinueInComplianceChanged(self, checked):
        logger.info("updated continue_in_compliance: %s", checked)
        self.state.update({"continue_in_compliance": checked})

    def onWaitingTimeContinuousChanged(self, value):
        logger.info("updated waiting_time_continuous: %s", format_metric(value, "s"))
        self.state.update({"waiting_time_continuous": value})

    def updateContinuousOption(self):
        # Tweak continuous option
        validTypes = ["iv", "iv_bias"]
        currentMeasurement = self.view.generalWidget.currentMeasurement()
        enabled = False
        if currentMeasurement:
            measurementType = currentMeasurement.get("type")
            enabled = measurementType in validTypes
        self.view.continuousCheckBox.setEnabled(enabled)

    def createFilename(self):
        path = self.view.generalWidget.outputDir()
        sample = self.state.sample
        timestamp = datetime.fromtimestamp(self.state.timestamp).strftime("%Y-%m-%dT%H-%M-%S")
        filename = safe_filename(f"{sample}-{timestamp}.txt")
        return os.path.join(path, filename)

    def connectIVPlots(self, measurement) -> None:
        measurement.ivReadingQueue = self.ivPlotsController.ivReadingQueue
        measurement.ivReadingLock = self.ivPlotsController.ivReadingLock
        measurement.itReadingQueue = self.ivPlotsController.itReadingQueue
        measurement.itReadingLock = self.ivPlotsController.itReadingLock
        measurement.it_change_voltage_ready_event.subscribe(self.changeVoltageReady.emit)

    def connectCVPlots(self, measurement) -> None:
        measurement.cvReadingQueue = self.cvPlotsController.cvReadingQueue
        measurement.cvReadingLock = self.cvPlotsController.cvReadingLock

    def createMeasurement(self):
        measurementType = self.state.measurement_type
        measurement = MEASUREMENTS.get(measurementType)(self.state)

        measurement.update_event.subscribe(self.update.emit)

        if isinstance(measurement, IVMeasurement):
            self.connectIVPlots(measurement)
        elif isinstance(measurement, IVBiasMeasurement):
            self.connectIVPlots(measurement)
        elif isinstance(measurement, CVMeasurement):
            self.connectCVPlots(measurement)

        # Prepare role drivers
        for role in self.view.roles():
            measurement.register_instrument(role.name().lower())

        measurement.failed_event.subscribe(self.failed.emit)

        return measurement

    def startMeasurement(self) -> None:
        try:
            logger.debug("handle RPC params...")
            with self.rpc_params:
                rpc_params = self.rpc_params
                if "reset" in rpc_params:
                    self.view.setReset(rpc_params.get("reset"))
                if "continuous" in rpc_params:
                    self.view.setContinuous(rpc_params.get("continuous"))
                if "auto_reconnect" in rpc_params:
                    self.view.setAutoReconnect(rpc_params.get("auto_reconnect"))
                if "end_voltage" in rpc_params:
                    self.view.generalWidget.setEndVoltage(rpc_params.get("end_voltage"))
                if "begin_voltage" in rpc_params:
                    self.view.generalWidget.setBeginVoltage(rpc_params.get("begin_voltage"))
                if "step_voltage" in rpc_params:
                    self.view.generalWidget.setStepVoltage(rpc_params.get("step_voltage"))
                if "waiting_time" in rpc_params:
                    self.view.generalWidget.setWaitingTime(rpc_params.get("waiting_time"))
                if "compliance" in rpc_params:
                    self.view.generalWidget.setCurrentCompliance(rpc_params.get("compliance"))
                if "waiting_time_continuous" in rpc_params:
                    self.view.generalWidget.setWaitingTimeContinuous(rpc_params.get("waiting_time_continuous"))
                self.rpc_params.clear()
            logger.debug("handle RPC params... done.")

            logger.debug("preparing state...")
            state = self.prepareState()
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
            outputEnabled = self.view.generalWidget.isOutputEnabled()
            filename = self.createFilename() if outputEnabled else None
            self.state.update({"filename": filename})

            # Create and run measurement
            measurement = self.createMeasurement()

            options = {}

            settings = QtCore.QSettings()
            timestampFormat = settings.value("writer/timestampFormat", ".6f", str)
            valueFormat = settings.value("writer/valueFormat", "+.3E", str)

            options.update({
                "timestamp_format": timestampFormat,
                "value_format": valueFormat,
            })

            self.abortRequested = threading.Event()
            self.measurementThread = threading.Thread(target=self.runMeasurement, args=[measurement, options])
            self.measurementThread.start()

        except Exception as exc:
            logger.exception(exc)
            self.failed.emit(exc)
            self.aborted.emit()
            self.finished.emit()

    def runMeasurement(self, measurement, options):
        try:
            MeasurementRunner(measurement, options)()
        except Exception as exc:
            logger.exception(exc)
            self.failed.emit(exc)
        finally:
            self.finished.emit()


class IVPlotsController(QtCore.QObject):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.ivPlotWidget = IVPlotWidget()
        self.itPlotWidget = ItPlotWidget()
        self.itPlotWidget.setVisible(False)
        self.dataWidget = QtWidgets.QWidget()
        self.ivLayout = QtWidgets.QHBoxLayout(self.dataWidget)
        self.ivLayout.addWidget(self.ivPlotWidget)
        self.ivLayout.addWidget(self.itPlotWidget)
        self.ivLayout.setStretch(0, 1)
        self.ivLayout.setStretch(1, 1)
        self.ivLayout.setContentsMargins(0, 0, 0, 0)

        self.ivReadingQueue = []
        self.ivReadingLock = threading.RLock()
        self.itReadingQueue = []
        self.itReadingLock = threading.RLock()

        self.updateTimer = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.onFlushIVReadings)
        self.updateTimer.timeout.connect(self.onFlushItReadings)

    def clear(self):
        self.ivReadingQueue.clear()
        self.itReadingQueue.clear()
        self.ivPlotWidget.clear()
        self.ivPlotWidget.reset()
        self.itPlotWidget.clear()
        self.itPlotWidget.reset()

    def toggleSmuSeries(self, state):
        self.ivPlotWidget.smuSeries.setVisible(state)
        self.itPlotWidget.smuSeries.setVisible(state)

    def toggleSmu2Series(self, state):
        self.ivPlotWidget.smu2Series.setVisible(state)
        self.itPlotWidget.smu2Series.setVisible(state)

    def toggleElmSeries(self, state):
        self.ivPlotWidget.elmSeries.setVisible(state)
        self.itPlotWidget.elmSeries.setVisible(state)

    def toggleElm2Series(self, state):
        self.ivPlotWidget.elm2Series.setVisible(state)
        self.itPlotWidget.elm2Series.setVisible(state)

    def toggleLcrSeries(self, state):
        ...

    def setContinuous(self, enabled):
        self.itPlotWidget.setVisible(enabled)

    def onFlushIVReadings(self) -> None:
        with self.ivReadingLock:
            readings = self.ivReadingQueue.copy()
            self.ivReadingQueue.clear()
        for reading in readings:
            self.onIVReading(reading, fit=False)
        if len(readings):
            self.ivPlotWidget.fit()

    def onIVReading(self, reading: dict, fit: bool = True) -> None:
        voltage: float = reading.get("voltage", math.nan)
        i_smu: float = reading.get("i_smu", math.nan)
        i_smu2: float = reading.get("i_smu2", math.nan)
        i_elm: float = reading.get("i_elm", math.nan)
        i_elm2: float = reading.get("i_elm2", math.nan)
        if math.isfinite(voltage) and math.isfinite(i_smu):
            self.ivPlotWidget.append("smu", voltage, i_smu)
        if math.isfinite(voltage) and math.isfinite(i_smu2):
            self.ivPlotWidget.append("smu2", voltage, i_smu2)
        if math.isfinite(voltage) and math.isfinite(i_elm):
            self.ivPlotWidget.append("elm", voltage, i_elm)
        if math.isfinite(voltage) and math.isfinite(i_elm2):
            self.ivPlotWidget.append("elm2", voltage, i_elm2)
        if fit:
            self.ivPlotWidget.fit()

    def onLoadIVReadings(self, readings: List[dict]) -> None:
        smuPoints = []
        smu2Points = []
        elmPoints = []
        elm2Points = []
        widget = self.ivPlotWidget
        widget.clear()
        for reading in readings:
            voltage: float = reading.get("voltage", math.nan)
            i_smu: float = reading.get("i_smu", math.nan)
            i_smu2: float = reading.get("i_smu2", math.nan)
            i_elm: float = reading.get("i_elm", math.nan)
            i_elm2: float = reading.get("i_elm2", math.nan)
            if math.isfinite(voltage) and math.isfinite(i_smu):
                smuPoints.append(QtCore.QPointF(voltage, i_smu))
                widget.iLimits.append(i_smu)
                widget.vLimits.append(voltage)
            if math.isfinite(voltage) and math.isfinite(i_smu2):
                smu2Points.append(QtCore.QPointF(voltage, i_smu2))
                widget.iLimits.append(i_smu2)
                widget.vLimits.append(voltage)
            if math.isfinite(voltage) and math.isfinite(i_elm):
                elmPoints.append(QtCore.QPointF(voltage, i_elm))
                widget.iLimits.append(i_elm)
                widget.vLimits.append(voltage)
            if math.isfinite(voltage) and math.isfinite(i_elm2):
                elm2Points.append(QtCore.QPointF(voltage, i_elm2))
                widget.iLimits.append(i_elm2)
                widget.vLimits.append(voltage)
        widget.series.get("smu").replace(smuPoints)
        widget.series.get("smu2").replace(smu2Points)
        widget.series.get("elm").replace(elmPoints)
        widget.series.get("elm2").replace(elm2Points)
        if self.parent():
            self.parent().onToggleSmu(True)
            self.parent().onToggleSmu2(bool(len(smu2Points)))
            self.parent().onToggleElm(bool(len(elmPoints)))
            self.parent().onToggleElm2(bool(len(elm2Points)))
        widget.fit()

    def onFlushItReadings(self) -> None:
        with self.itReadingLock:
            readings = self.itReadingQueue.copy()
            self.itReadingQueue.clear()
        for reading in readings:
            self.onItReading(reading, fit=False)
        if len(readings):
            self.itPlotWidget.fit()

    def onItReading(self, reading: dict, fit: bool = True) -> None:
        timestamp: float = reading.get("timestamp", math.nan)
        i_smu: float = reading.get("i_smu", math.nan)
        i_smu2: float = reading.get("i_smu2", math.nan)
        i_elm: float = reading.get("i_elm", math.nan)
        i_elm2: float = reading.get("i_elm2", math.nan)
        if math.isfinite(timestamp) and math.isfinite(i_smu):
            self.itPlotWidget.append("smu", timestamp, i_smu)
        if math.isfinite(timestamp) and math.isfinite(i_smu2):
            self.itPlotWidget.append("smu2", timestamp, i_smu2)
        if math.isfinite(timestamp) and math.isfinite(i_elm):
            self.itPlotWidget.append("elm", timestamp, i_elm)
        if math.isfinite(timestamp) and math.isfinite(i_elm2):
            self.itPlotWidget.append("elm2", timestamp, i_elm2)
        if fit:
            self.itPlotWidget.fit()

    def onLoadItReadings(self, readings: List[dict]) -> None:
        smuPoints: List[QtCore.QPointF] = []
        smu2Points: List[QtCore.QPointF] = []
        elmPoints: List[QtCore.QPointF] = []
        elm2Points: List[QtCore.QPointF] = []
        widget = self.itPlotWidget
        widget.clear()
        for reading in readings:
            timestamp: float = reading.get("timestamp", math.nan)
            i_smu: float = reading.get("i_smu", math.nan)
            i_smu2: float = reading.get("i_smu2", math.nan)
            i_elm: float = reading.get("i_elm", math.nan)
            i_elm2: float = reading.get("i_elm2", math.nan)
            if math.isfinite(timestamp) and math.isfinite(i_smu):
                smuPoints.append(QtCore.QPointF(timestamp * 1e3, i_smu))
                widget.iLimits.append(i_smu)
                widget.tLimits.append(timestamp)
            if math.isfinite(timestamp) and math.isfinite(i_smu2):
                smu2Points.append(QtCore.QPointF(timestamp * 1e3, i_smu2))
                widget.iLimits.append(i_smu2)
                widget.tLimits.append(timestamp)
            if math.isfinite(timestamp) and math.isfinite(i_elm):
                elmPoints.append(QtCore.QPointF(timestamp * 1e3, i_elm))
                widget.iLimits.append(i_elm)
                widget.tLimits.append(timestamp)
        widget.series.get("smu").replace(smuPoints)
        widget.series.get("smu2").replace(smu2Points)
        widget.series.get("elm").replace(elmPoints)
        widget.series.get("elm2").replace(elm2Points)
        widget.fit()


class CVPlotsController(QtCore.QObject):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.cvPlotWidget = CVPlotWidget()
        self.cv2PlotWidget = CV2PlotWidget()
        self.dataWidget = QtWidgets.QWidget()
        self.cvLayout = QtWidgets.QHBoxLayout(self.dataWidget)
        self.cvLayout.addWidget(self.cvPlotWidget)
        self.cvLayout.addWidget(self.cv2PlotWidget)
        self.cvLayout.setStretch(0, 1)
        self.cvLayout.setStretch(1, 1)
        self.cvLayout.setContentsMargins(0, 0, 0, 0)

        self.cvReadingQueue = []
        self.cvReadingLock = threading.RLock()

        self.updateTimer = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.onFlushCvReadings)

    def clear(self):
        self.cvReadingQueue.clear()
        self.cvPlotWidget.clear()
        self.cvPlotWidget.reset()
        self.cv2PlotWidget.clear()
        self.cv2PlotWidget.reset()

    def toggleSmuSeries(self, state):
        ...

    def toggleSmu2Series(self, state):
        ...

    def toggleElmSeries(self, state):
        ...

    def toggleElm2Series(self, state):
        ...

    def toggleLcrSeries(self, state):
        ...

    def setContinuous(self, enabled):
        ...

    def onFlushCvReadings(self) -> None:
        with self.cvReadingLock:
            readings = self.cvReadingQueue.copy()
            self.cvReadingQueue.clear()
        for reading in readings:
            self.onCVReading(reading, fit=False)
        if len(readings):
            self.cvPlotWidget.fit()

    def onCVReading(self, reading: dict, fit: bool = True) -> None:
        voltage: float = reading.get("voltage", math.nan)
        c_lcr: float = reading.get("c_lcr", math.nan)
        c2_lcr: float = reading.get("c2_lcr", math.nan)
        if math.isfinite(voltage) and math.isfinite(c_lcr):
            self.cvPlotWidget.append("lcr", voltage, c_lcr)
        if math.isfinite(voltage) and math.isfinite(c2_lcr):
            self.cv2PlotWidget.append("lcr", voltage, c2_lcr)

    def onLoadCVReadings(self, readings: List[dict]) -> None:
        lcrPoints: List[QtCore.QPointF] = []
        widget = self.cvPlotWidget
        widget.clear()
        for reading in readings:
            voltage: float = reading.get("voltage", math.nan)
            c_lcr: float = reading.get("c_lcr", math.nan)
            if math.isfinite(voltage) and math.isfinite(c_lcr):
                lcrPoints.append(QtCore.QPointF(voltage, c_lcr))
                widget.cLimits.append(c_lcr)
                widget.vLimits.append(voltage)
        widget.series.get("lcr").replace(lcrPoints)
        widget.fit()

    def onLoadCV2Readings(self, readings: List[dict]) -> None:
        lcr2Points: List[QtCore.QPointF] = []
        widget = self.cv2PlotWidget
        widget.clear()
        for reading in readings:
            voltage: float = reading.get("voltage", math.nan)
            c2_lcr: float = reading.get("c2_lcr", math.nan)
            if math.isfinite(voltage) and math.isfinite(c2_lcr):
                lcr2Points.append(QtCore.QPointF(voltage, c2_lcr))
                widget.cLimits.append(c2_lcr)
                widget.vLimits.append(voltage)
        widget.series.get("lcr").replace(lcr2Points)
        widget.fit()


class ChangeVoltageController(QtCore.QObject):

    def __init__(self, view, state, parent=None) -> None:
        super().__init__(parent)
        self.view = view
        self.state = state
        # Connect signals
        self.view.prepareChangeVoltage.connect(self.onPrepareChangeVoltage)

    def sourceVoltage(self):
        source_voltage = self.state.source_voltage
        if source_voltage is not None:
            return source_voltage
        return self.view.generalWidget.endVoltage()

    def onPrepareChangeVoltage(self) -> None:
        dialog = ChangeVoltageDialog(self.view)
        dialog.setEndVoltage(self.sourceVoltage())
        dialog.setStepVoltage(self.view.generalWidget.stepVoltage())
        dialog.setWaitingTime(self.view.generalWidget.waitingTime())
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            self.onRequestChangeVoltage(
                dialog.endVoltage(),
                dialog.stepVoltage(),
                dialog.waitingTime()
            )

    def onRequestChangeVoltage(self, endVoltage: float, stepVoltage: float, waitingTime: float) -> None:
        if self.view.isChangeVoltageEnabled():
            logger.info(
                "updated change_voltage_continuous: end_voltage=%s, step_voltage=%s, waiting_time=%s",
                format_metric(endVoltage, "V"),
                format_metric(stepVoltage, "V"),
                format_metric(waitingTime, "s")
            )
            self.state.update({"change_voltage_continuous": {
                "end_voltage": endVoltage,
                "step_voltage": stepVoltage,
                "waiting_time": waitingTime
            }})
            self.view.setChangeVoltageEnabled(False)

    def onChangeVoltageReady(self) -> None:
        self.view.setChangeVoltageEnabled(True)
