from PyQt5 import QtCore, QtWidgets

from ..utils import ureg

__all__ = ["GeneralWidget"]


class GeneralWidget(QtWidgets.QWidget):

    instrumentsChanged = QtCore.pyqtSignal()
    currentComplianceChanged = QtCore.pyqtSignal(float)
    continueInComplianceChanged = QtCore.pyqtSignal(bool)
    waitingTimeContinuousChanged = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("General")

        self._createWidgets()
        self._createLayout()

    def _createWidgets(self):
        self.measurementComboBox = QtWidgets.QComboBox()

        self.smuCheckBox = QtWidgets.QCheckBox("SMU")
        self.smuCheckBox.stateChanged.connect(self.instrumentsChanged)

        self.smu2CheckBox = QtWidgets.QCheckBox("SMU2")
        self.smu2CheckBox.stateChanged.connect(self.instrumentsChanged)

        self.elmCheckBox = QtWidgets.QCheckBox("ELM")
        self.elmCheckBox.stateChanged.connect(self.instrumentsChanged)

        self.elm2CheckBox = QtWidgets.QCheckBox("ELM2")
        self.elm2CheckBox.stateChanged.connect(self.instrumentsChanged)

        self.lcrCheckBox = QtWidgets.QCheckBox("LCR")
        self.lcrCheckBox.stateChanged.connect(self.instrumentsChanged)

        self.dmmCheckBox = QtWidgets.QCheckBox("DMM")
        self.dmmCheckBox.stateChanged.connect(self.instrumentsChanged)

        self.switchCheckBox = QtWidgets.QCheckBox("Switch")
        self.switchCheckBox.stateChanged.connect(self.instrumentsChanged)

        self.beginVoltageSpinBox = QtWidgets.QDoubleSpinBox()
        self.beginVoltageSpinBox.setDecimals(3)
        self.beginVoltageSpinBox.setRange(-3030.0, +3030.0)
        self.beginVoltageSpinBox.setSuffix(" V")

        self.endVoltageSpinBox = QtWidgets.QDoubleSpinBox()
        self.endVoltageSpinBox.setDecimals(3)
        self.endVoltageSpinBox.setRange(-3030.0, +3030.0)
        self.endVoltageSpinBox.setSuffix(" V")

        self.stepVoltageSpinBox = QtWidgets.QDoubleSpinBox()
        self.stepVoltageSpinBox.setDecimals(3)
        self.stepVoltageSpinBox.setRange(0, +3030.0)
        self.stepVoltageSpinBox.setSuffix(" V")

        self.waitingTimeSpinBox = QtWidgets.QDoubleSpinBox()
        self.waitingTimeSpinBox.setSuffix(" s")

        self.biasVoltageSpinBox = QtWidgets.QDoubleSpinBox()
        self.biasVoltageSpinBox.setDecimals(3)
        self.biasVoltageSpinBox.setRange(-3030.0, +3030.0)
        self.biasVoltageSpinBox.setSuffix(" V")

        self.currentComplianceSpinBox = QtWidgets.QDoubleSpinBox()
        self.currentComplianceSpinBox.setDecimals(3)
        self.currentComplianceSpinBox.setRange(0.0, +2000000.0)
        self.currentComplianceSpinBox.setSuffix(" uA")
        self.currentComplianceSpinBox.editingFinished.connect(
            lambda: self.currentComplianceChanged.emit(self.currentCompliance())
        )

        self.continueInComplianceCheckBox = QtWidgets.QCheckBox()
        self.continueInComplianceCheckBox.setText("Continue in Compliance")
        self.continueInComplianceCheckBox.setStatusTip("Continue measurement when source in compliance.""")
        self.continueInComplianceCheckBox.setChecked(False)
        self.continueInComplianceCheckBox.toggled.connect(
            lambda checked: self.continueInComplianceChanged.emit(checked)
        )

        self.sampleLineEdit = QtWidgets.QLineEdit()

        self.outputLineEdit = QtWidgets.QLineEdit()
        completer = QtWidgets.QCompleter(self)
        completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        model = QtWidgets.QDirModel(completer)
        model.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Drives | QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllDirs)
        completer.setModel(model)
        self.outputLineEdit.setCompleter(completer)

        self.outputToolButton = QtWidgets.QToolButton()
        self.outputToolButton.setText("...")
        self.outputToolButton.setStatusTip("Select output directory")
        self.outputToolButton.clicked.connect(self.selectOutput)

        self.waitingTimeContinuousSpinBox = QtWidgets.QDoubleSpinBox()
        self.waitingTimeContinuousSpinBox.setSuffix(" s")
        self.waitingTimeContinuousSpinBox.setDecimals(2)
        self.waitingTimeContinuousSpinBox.setStatusTip("Waiting time for continuous measurement")
        self.waitingTimeContinuousSpinBox.editingFinished.connect(
            lambda: self.waitingTimeContinuousChanged.emit(self.waitingTimeContinuous())
        )

        self.changeVoltageButton = QtWidgets.QToolButton()
        self.changeVoltageButton.setText("&Change Voltage...")
        self.changeVoltageButton.setStatusTip("Change voltage in continuous measurement")
        self.changeVoltageButton.setEnabled(False)

        self.measurementGroupBox = QtWidgets.QGroupBox()
        self.measurementGroupBox.setTitle("Measurement")

        self.outputGroupBox = QtWidgets.QGroupBox()
        self.outputGroupBox.setTitle("Output")
        self.outputGroupBox.setCheckable(True)
        self.outputGroupBox.setChecked(False)

        self.rampGroupBox = QtWidgets.QGroupBox()
        self.rampGroupBox.setTitle("Ramp")

        self.biasGroupBox = QtWidgets.QGroupBox()
        self.biasGroupBox.setTitle("Bias Voltage (SMU2)")

        self.complianceGroupBox = QtWidgets.QGroupBox()
        self.complianceGroupBox.setTitle("Compliance")

        self.continuousGroupBox = QtWidgets.QGroupBox()
        self.continuousGroupBox.setTitle("Continuous Meas.")

    def _createLayout(self):
        layout = QtWidgets.QVBoxLayout(self.measurementGroupBox)
        layout.addWidget(QtWidgets.QLabel("Type"))
        layout.addWidget(self.measurementComboBox)
        layout.addWidget(QtWidgets.QLabel("Instruments"))
        self.instrumentWidget = QtWidgets.QWidget()
        layout.addWidget(self.instrumentWidget)
        self.instrumentLayout = QtWidgets.QHBoxLayout(self.instrumentWidget)
        self.instrumentLayout.addWidget(self.smuCheckBox)
        self.instrumentLayout.addWidget(self.smu2CheckBox)
        self.instrumentLayout.addWidget(self.elmCheckBox)
        self.instrumentLayout.addWidget(self.elm2CheckBox)
        self.instrumentLayout.addWidget(self.lcrCheckBox)
        self.instrumentLayout.addWidget(self.dmmCheckBox)
        self.instrumentLayout.addWidget(self.switchCheckBox)
        self.instrumentLayout.addStretch()
        self.instrumentLayout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self.outputGroupBox)
        layout.addWidget(QtWidgets.QLabel("Sample Name"))
        layout.addWidget(self.sampleLineEdit)
        layout.addWidget(QtWidgets.QLabel("Output Path"))
        outputLayout = QtWidgets.QHBoxLayout()
        outputLayout.addWidget(self.outputLineEdit)
        outputLayout.addWidget(self.outputToolButton)
        layout.addLayout(outputLayout)
        layout.addStretch()

        layout = QtWidgets.QVBoxLayout(self.rampGroupBox)
        layout.addWidget(QtWidgets.QLabel("Begin"))
        layout.addWidget(self.beginVoltageSpinBox)
        layout.addWidget(QtWidgets.QLabel("End"))
        layout.addWidget(self.endVoltageSpinBox)
        layout.addWidget(QtWidgets.QLabel("Step"))
        layout.addWidget(self.stepVoltageSpinBox)
        layout.addWidget(QtWidgets.QLabel("Waiting Time"))
        layout.addWidget(self.waitingTimeSpinBox)

        layout = QtWidgets.QVBoxLayout(self.biasGroupBox)
        layout.addWidget(self.biasVoltageSpinBox)
        layout.addStretch()

        layout = QtWidgets.QVBoxLayout(self.complianceGroupBox)
        layout.addWidget(QtWidgets.QLabel("Current"))
        layout.addWidget(self.currentComplianceSpinBox)
        layout.addWidget(self.continueInComplianceCheckBox)

        layout.addStretch()

        waitingTimeLayout = QtWidgets.QHBoxLayout()
        waitingTimeLayout.addWidget(self.waitingTimeContinuousSpinBox)

        layout = QtWidgets.QVBoxLayout(self.continuousGroupBox)
        layout.addWidget(QtWidgets.QLabel("Waiting Time"))
        layout.addLayout(waitingTimeLayout)
        layout.addWidget(self.changeVoltageButton)
        layout.addStretch()

        layout = QtWidgets.QHBoxLayout(self)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.measurementGroupBox)
        vbox.addWidget(self.outputGroupBox)
        layout.addLayout(vbox)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.rampGroupBox)
        vbox.addWidget(self.biasGroupBox)
        layout.addLayout(vbox)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.complianceGroupBox)
        vbox.addWidget(self.continuousGroupBox)
        layout.addLayout(vbox)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)
        layout.setStretch(2, 1)

        self._currentComplianceLocked = False

    def setIdleState(self) -> None:
        self.measurementComboBox.setEnabled(True)
        self.instrumentWidget.setEnabled(True)
        self.outputGroupBox.setEnabled(True)
        self.beginVoltageSpinBox.setEnabled(True)
        self.endVoltageSpinBox.setEnabled(True)
        self.stepVoltageSpinBox.setEnabled(True)
        self.waitingTimeSpinBox.setEnabled(True)
        self.biasVoltageSpinBox.setEnabled(True)
        self.changeVoltageButton.setEnabled(False)
        self.currentComplianceSpinBox.setEnabled(not self._currentComplianceLocked)
        self.continueInComplianceCheckBox.setEnabled(True)

    def setRunningState(self) -> None:
        self.measurementComboBox.setEnabled(False)
        self.instrumentWidget.setEnabled(False)
        self.outputGroupBox.setEnabled(False)
        self.beginVoltageSpinBox.setEnabled(False)
        self.endVoltageSpinBox.setEnabled(False)
        self.stepVoltageSpinBox.setEnabled(False)
        self.waitingTimeSpinBox.setEnabled(False)
        self.biasVoltageSpinBox.setEnabled(False)

    def setStoppingState(self):
        self.changeVoltageButton.setEnabled(False)
        self.currentComplianceSpinBox.setEnabled(False)
        self.continueInComplianceCheckBox.setEnabled(False)

    def addMeasurement(self, spec):
        self.measurementComboBox.addItem(spec.get("title"), spec)

    def currentMeasurement(self):
        return self.measurementComboBox.currentData()

    def isSMUEnabled(self):
        return self.smuCheckBox.isChecked()

    def setSMUEnabled(self, enabled):
        return self.smuCheckBox.setChecked(enabled)

    def isSMU2Enabled(self):
        return self.smu2CheckBox.isChecked()

    def setSMU2Enabled(self, enabled):
        return self.smu2CheckBox.setChecked(enabled)

    def isELMEnabled(self):
        return self.elmCheckBox.isChecked()

    def setELMEnabled(self, enabled):
        return self.elmCheckBox.setChecked(enabled)

    def isELM2Enabled(self):
        return self.elm2CheckBox.isChecked()

    def setELM2Enabled(self, enabled):
        return self.elm2CheckBox.setChecked(enabled)

    def isLCREnabled(self):
        return self.lcrCheckBox.isChecked()

    def setLCREnabled(self, enabled):
        return self.lcrCheckBox.setChecked(enabled)

    def isDMMEnabled(self):
        return self.dmmCheckBox.isChecked()

    def setDMMEnabled(self, enabled):
        return self.dmmCheckBox.setChecked(enabled)

    def isSwitchEnabled(self):
        return self.switchCheckBox.isChecked()

    def setSwitchEnabled(self, enabled):
        return self.switchCheckBox.setChecked(enabled)

    def isOutputEnabled(self):
        return self.outputGroupBox.isChecked()

    def setOutputEnabled(self, enabled):
        self.outputGroupBox.setChecked(enabled)

    def sampleName(self):
        return self.sampleLineEdit.text().strip()

    def setSampleName(self, text):
        self.sampleLineEdit.setText(text)

    def outputDir(self):
        return self.outputLineEdit.text().strip()

    def setOutputDir(self, text):
        self.outputLineEdit.setText(text)

    def selectOutput(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select ouput path", self.outputDir())
        if path:
            self.setOutputDir(path)

    def setVoltageUnit(self, unit):
        self.beginVoltageSpinBox.setSuffix(f" {unit}")
        self.endVoltageSpinBox.setSuffix(f" {unit}")
        self.stepVoltageSpinBox.setSuffix(f" {unit}")

    def beginVoltage(self):
        unit = self.beginVoltageSpinBox.suffix().strip()
        return (self.beginVoltageSpinBox.value() * ureg(unit)).to("V").m

    def setBeginVoltage(self, value):
        unit = self.beginVoltageSpinBox.suffix().strip()
        self.beginVoltageSpinBox.setValue((value * ureg("V")).to(unit).m)

    def endVoltage(self):
        unit = self.endVoltageSpinBox.suffix().strip()
        return (self.endVoltageSpinBox.value() * ureg(unit)).to("V").m

    def setEndVoltage(self, value):
        unit = self.endVoltageSpinBox.suffix().strip()
        self.endVoltageSpinBox.setValue((value * ureg("V")).to(unit).m)

    def stepVoltage(self):
        unit = self.stepVoltageSpinBox.suffix().strip()
        return (self.stepVoltageSpinBox.value() * ureg(unit)).to("V").m

    def setStepVoltage(self, value):
        unit = self.stepVoltageSpinBox.suffix().strip()
        self.stepVoltageSpinBox.setValue((value * ureg("V")).to(unit).m)

    def waitingTime(self):
        return self.waitingTimeSpinBox.value()

    def setWaitingTime(self, value):
        self.waitingTimeSpinBox.setValue(value)

    def biasVoltage(self):
        unit = self.biasVoltageSpinBox.suffix().strip()
        return (self.biasVoltageSpinBox.value() * ureg(unit)).to("V").m

    def setBiasVoltage(self, value):
        unit = self.biasVoltageSpinBox.suffix().strip()
        self.biasVoltageSpinBox.setValue((value * ureg("V")).to(unit).m)

    def setCurrentComplianceUnit(self, unit):
        self.currentComplianceSpinBox.setSuffix(f" {unit}")

    def currentCompliance(self):
        unit = self.currentComplianceSpinBox.suffix().strip()
        return (self.currentComplianceSpinBox.value() * ureg(unit)).to("A").m

    def setCurrentCompliance(self, value):
        unit = self.currentComplianceSpinBox.suffix().strip()
        return self.currentComplianceSpinBox.setValue((value * ureg("A")).to(unit).m)

    def setCurrentComplianceLocked(self, state):
        self._currentComplianceLocked = state
        self.currentComplianceSpinBox.setEnabled(not state)

    def isContinueInCompliance(self):
        return self.continueInComplianceCheckBox.isChecked()

    def setContinueInCompliance(self, enabled):
        self.continueInComplianceCheckBox.setChecked(enabled)

    def waitingTimeContinuous(self):
        return self.waitingTimeContinuousSpinBox.value()

    def setWaitingTimeContinuous(self, value):
        self.waitingTimeContinuousSpinBox.setValue(value)
