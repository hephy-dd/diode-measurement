import logging
import webbrowser
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__ as APP_VERSION
from ..utils import format_metric, format_switch

from .general import GeneralWidget
from .logwindow import LogWidget
from .preferences import PreferencesDialog
from .role import RoleWidget

__all__ = ["MainWindow"]

CONTENTS_URL: str = "https://github.com/hephy-dd/diode-measurement"

ABOUT_TEXT: str = f"""
    <h3>Diode Measurement</h3>
    <p>IV/CV measurements for silicon sensors.</p>
    <p>Version {APP_VERSION}</p>
    <p>This software is licensed under the GNU General Public License Version 3.</p>
    <p>Copyright &copy; 2021-2026 <a href=\"https://oeaw.ac.at/mbi\">MBI</a></p>
"""


def stylesheet_switch(state):
    if state is None:
        return ""
    return (
        "QLineEdit:enabled{ background-color: #339933; color: white; }" if state else ""
    )


class MainWindow(QtWidgets.QMainWindow):
    prepare_change_voltage = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._locked: bool = False

        self._create_actions()
        self._create_menus()
        self._create_widgets()
        self._create_layout()

    def _create_actions(self) -> None:
        self.import_action = QtGui.QAction("&Import File...")
        self.import_action.setStatusTip("Import measurement data")

        self.quitAction = QtGui.QAction("&Quit")
        self.quitAction.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        self.quitAction.setStatusTip("Quit the application")
        self.quitAction.triggered.connect(self.close)

        self.preferencesAction = QtGui.QAction("&Preferences...")
        self.preferencesAction.setStatusTip("Show preferences dialog")
        self.preferencesAction.triggered.connect(self.on_show_preferences)

        self.start_action = QtGui.QAction("&Start")
        self.start_action.setStatusTip("Start a new measurement")

        self.stop_action = QtGui.QAction("Sto&p")
        self.stop_action.setStatusTip("Stop an active measurement")

        self.continuous_action = QtGui.QAction("&Continuous Meas.")
        self.continuous_action.setCheckable(True)
        self.continuous_action.setStatusTip("Enable continuous measurement")

        self.changeVoltageAction = QtGui.QAction("&Change Voltage...")
        self.changeVoltageAction.setStatusTip(
            "Change voltage in continuous measurement"
        )
        self.changeVoltageAction.triggered.connect(self.prepare_change_voltage.emit)

        self.contentsAction = QtGui.QAction("&Contents")
        self.contentsAction.setStatusTip("Open the user manual")
        self.contentsAction.setShortcut(QtGui.QKeySequence("F1"))
        self.contentsAction.triggered.connect(self.on_show_contents)

        self.aboutQtAction = QtGui.QAction("About &Qt")
        self.aboutQtAction.setStatusTip("About the used Qt framework")
        self.aboutQtAction.triggered.connect(self.on_show_about_qt)

        self.aboutAction = QtGui.QAction("&About")
        self.aboutAction.setStatusTip("About the application")
        self.aboutAction.triggered.connect(self.on_show_about)

    def _create_menus(self) -> None:
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.import_action)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAction)

        self.editMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addAction(self.preferencesAction)

        self.viewMenu = self.menuBar().addMenu("&View")

        self.measureMenu = self.menuBar().addMenu("&Measure")
        self.measureMenu.addAction(self.start_action)
        self.measureMenu.addAction(self.stop_action)
        self.measureMenu.addSeparator()
        self.measureMenu.addAction(self.continuous_action)
        self.measureMenu.addAction(self.changeVoltageAction)

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.contentsAction)
        self.helpMenu.addAction(self.aboutQtAction)
        self.helpMenu.addAction(self.aboutAction)

    def _create_widgets(self) -> None:
        self.dataStackedWidget = QtWidgets.QStackedWidget()
        self.dataStackedWidget.setMinimumHeight(240)

        self.start_button = QtWidgets.QPushButton("&Start")
        self.start_button.setStatusTip("Start a new measurement")
        self.start_button.setCheckable(True)
        self.start_button.setStyleSheet("QPushButton:enabled{ color: green; }")

        self.stop_button = QtWidgets.QPushButton("Sto&p")
        self.stop_button.setStatusTip("Stop an active measurement")
        self.stop_button.setStyleSheet(
            "QPushButton:enabled{ background-color: #ff0000; color: white; } QPushButton:hover{ background-color: #ff3333; }"
        )
        self.stop_button.setCheckable(True)
        self.stop_button.setMinimumHeight(72)

        self.continuous_check_box = QtWidgets.QCheckBox("&Continuous Meas.")
        self.continuous_check_box.setStatusTip("Enable continuous measurement")

        self.reset_check_box = QtWidgets.QCheckBox("&Reset Instruments")
        self.reset_check_box.setStatusTip("Reset instruments on start")

        self.auto_reconnect_check_box = QtWidgets.QCheckBox("&Auto Reconnect")
        self.auto_reconnect_check_box.setStatusTip(
            "Auto reconnect and retry on connection erros"
        )

        self.general_widget = GeneralWidget()
        self.general_widget.change_voltage_clicked.connect(
            self.changeVoltageAction.trigger
        )

        self.roleWidgets: dict[str, RoleWidget] = {}

        self.control_tab_widget = QtWidgets.QTabWidget()
        self.control_tab_widget.addTab(
            self.general_widget, self.general_widget.windowTitle()
        )

        self.smu_group_box = QtWidgets.QGroupBox()
        self.smu_group_box.setTitle("SMU Status")

        self.smu2_group_box = QtWidgets.QGroupBox()
        self.smu2_group_box.setTitle("SMU2 Status")

        self.elm_group_box = QtWidgets.QGroupBox()
        self.elm_group_box.setTitle("ELM Status")

        self.elm2_group_box = QtWidgets.QGroupBox()
        self.elm2_group_box.setTitle("ELM2 Status")

        self.lcr_group_box = QtWidgets.QGroupBox()
        self.lcr_group_box.setTitle("LCR Status")

        self.dmm_group_box = QtWidgets.QGroupBox()
        self.dmm_group_box.setTitle("DMM Status")

        self.tcu_group_box = QtWidgets.QGroupBox()
        self.tcu_group_box.setTitle("TCU Status")

        self.smuVoltageLineEdit = QtWidgets.QLineEdit("---")
        self.smuVoltageLineEdit.setReadOnly(True)
        self.smuVoltageLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.smuCurrentLineEdit = QtWidgets.QLineEdit("---")
        self.smuCurrentLineEdit.setReadOnly(True)
        self.smuCurrentLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.smuOutputStateLineEdit = QtWidgets.QLineEdit()
        self.smuOutputStateLineEdit.setReadOnly(True)
        self.smuOutputStateLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.smu2VoltageLineEdit = QtWidgets.QLineEdit("---")
        self.smu2VoltageLineEdit.setReadOnly(True)
        self.smu2VoltageLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.smu2CurrentLineEdit = QtWidgets.QLineEdit("---")
        self.smu2CurrentLineEdit.setReadOnly(True)
        self.smu2CurrentLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.smu2OutputStateLineEdit = QtWidgets.QLineEdit()
        self.smu2OutputStateLineEdit.setReadOnly(True)
        self.smu2OutputStateLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.elmVoltageLineEdit = QtWidgets.QLineEdit("---")
        self.elmVoltageLineEdit.setReadOnly(True)
        self.elmVoltageLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.elmCurrentLineEdit = QtWidgets.QLineEdit("---")
        self.elmCurrentLineEdit.setReadOnly(True)
        self.elmCurrentLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.elmOutputStateLineEdit = QtWidgets.QLineEdit("---")
        self.elmOutputStateLineEdit.setReadOnly(True)
        self.elmOutputStateLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.elm2VoltageLineEdit = QtWidgets.QLineEdit("---")
        self.elm2VoltageLineEdit.setReadOnly(True)
        self.elm2VoltageLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.elm2CurrentLineEdit = QtWidgets.QLineEdit("---")
        self.elm2CurrentLineEdit.setReadOnly(True)
        self.elm2CurrentLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.elm2OutputStateLineEdit = QtWidgets.QLineEdit("---")
        self.elm2OutputStateLineEdit.setReadOnly(True)
        self.elm2OutputStateLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.lcrVoltageLineEdit = QtWidgets.QLineEdit("---")
        self.lcrVoltageLineEdit.setReadOnly(True)
        self.lcrVoltageLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.lcrCurrentLineEdit = QtWidgets.QLineEdit("---")
        self.lcrCurrentLineEdit.setReadOnly(True)
        self.lcrCurrentLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.lcrOutputStateLineEdit = QtWidgets.QLineEdit("---")
        self.lcrOutputStateLineEdit.setReadOnly(True)
        self.lcrOutputStateLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.dmmTemperatureLineEdit = QtWidgets.QLineEdit("---")
        self.dmmTemperatureLineEdit.setReadOnly(True)
        self.dmmTemperatureLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.tcuTemperatureLineEdit = QtWidgets.QLineEdit("---")
        self.tcuTemperatureLineEdit.setReadOnly(True)
        self.tcuTemperatureLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.tcuStateLineEdit = QtWidgets.QLineEdit("---")
        self.tcuStateLineEdit.setReadOnly(True)
        self.tcuStateLineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(centralWidget)

        # Dock widgets

        self.loggingWidget = LogWidget(self)
        self.loggingWidget.addLogger(logging.getLogger())
        self.loggingWidget.setLevel(logging.DEBUG)

        self.loggingDockWidget = QtWidgets.QDockWidget("Logging")
        self.loggingDockWidget.setObjectName("loggingDockWidget")
        self.loggingDockWidget.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.loggingDockWidget.setWidget(self.loggingWidget)
        self.loggingDockWidget.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.loggingDockWidget.hide()
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.loggingDockWidget
        )

        self.loggingAction = self.loggingDockWidget.toggleViewAction()
        self.loggingAction.setStatusTip("Toggle logging dock window")
        self.viewMenu.addAction(self.loggingAction)

        # Status bar

        self.message_label = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.message_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedWidth(240)
        self.statusBar().addPermanentWidget(self.progress_bar)

    def _create_layout(self) -> None:
        control_layout = QtWidgets.QVBoxLayout()
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.continuous_check_box)
        control_layout.addWidget(self.reset_check_box)
        control_layout.addWidget(self.auto_reconnect_check_box)
        control_layout.addStretch()

        smu_group_box = QtWidgets.QHBoxLayout(self.smu_group_box)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Voltage"))
        vboxLayout.addWidget(self.smuVoltageLineEdit)
        smu_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Current"))
        vboxLayout.addWidget(self.smuCurrentLineEdit)
        smu_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Output"))
        vboxLayout.addWidget(self.smuOutputStateLineEdit)
        smu_group_box.addLayout(vboxLayout)
        smu_group_box.setStretch(0, 3)
        smu_group_box.setStretch(1, 3)
        smu_group_box.setStretch(2, 1)

        smu2_group_box = QtWidgets.QHBoxLayout(self.smu2_group_box)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Voltage"))
        vboxLayout.addWidget(self.smu2VoltageLineEdit)
        smu2_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Current"))
        vboxLayout.addWidget(self.smu2CurrentLineEdit)
        smu2_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Output"))
        vboxLayout.addWidget(self.smu2OutputStateLineEdit)
        smu2_group_box.addLayout(vboxLayout)
        smu2_group_box.setStretch(0, 3)
        smu2_group_box.setStretch(1, 3)
        smu2_group_box.setStretch(2, 1)

        elm_group_box = QtWidgets.QHBoxLayout(self.elm_group_box)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Voltage"))
        vboxLayout.addWidget(self.elmVoltageLineEdit)
        elm_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Current"))
        vboxLayout.addWidget(self.elmCurrentLineEdit)
        elm_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Output"))
        vboxLayout.addWidget(self.elmOutputStateLineEdit)
        elm_group_box.addLayout(vboxLayout)
        elm_group_box.setStretch(0, 3)
        elm_group_box.setStretch(1, 3)
        elm_group_box.setStretch(2, 1)

        elm2_group_box = QtWidgets.QHBoxLayout(self.elm2_group_box)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Voltage"))
        vboxLayout.addWidget(self.elm2VoltageLineEdit)
        elm2_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Current"))
        vboxLayout.addWidget(self.elm2CurrentLineEdit)
        elm2_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Output"))
        vboxLayout.addWidget(self.elm2OutputStateLineEdit)
        elm2_group_box.addLayout(vboxLayout)
        elm2_group_box.setStretch(0, 3)
        elm2_group_box.setStretch(1, 3)
        elm2_group_box.setStretch(2, 1)

        lcr_group_box = QtWidgets.QHBoxLayout(self.lcr_group_box)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Voltage"))
        vboxLayout.addWidget(self.lcrVoltageLineEdit)
        lcr_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Capacity"))
        vboxLayout.addWidget(self.lcrCurrentLineEdit)
        lcr_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Output"))
        vboxLayout.addWidget(self.lcrOutputStateLineEdit)
        lcr_group_box.addLayout(vboxLayout)
        lcr_group_box.setStretch(0, 3)
        lcr_group_box.setStretch(1, 3)
        lcr_group_box.setStretch(2, 1)

        dmm_group_box = QtWidgets.QHBoxLayout(self.dmm_group_box)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Temperature"))
        vboxLayout.addWidget(self.dmmTemperatureLineEdit)
        dmm_group_box.addLayout(vboxLayout)
        dmm_group_box.addStretch()
        dmm_group_box.setStretch(0, 2)
        dmm_group_box.setStretch(1, 3)

        tcu_group_box = QtWidgets.QHBoxLayout(self.tcu_group_box)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("Temperature"))
        vboxLayout.addWidget(self.tcuTemperatureLineEdit)
        tcu_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel("State"))
        vboxLayout.addWidget(self.tcuStateLineEdit)
        tcu_group_box.addLayout(vboxLayout)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(QtWidgets.QLabel())
        tcu_group_box.addLayout(vboxLayout)
        tcu_group_box.setStretch(0, 3)
        tcu_group_box.setStretch(1, 3)
        tcu_group_box.setStretch(2, 1)

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.addLayout(control_layout)
        bottomLayout.addWidget(self.control_tab_widget)
        vboxLayout = QtWidgets.QVBoxLayout()
        vboxLayout.addWidget(self.smu_group_box)
        vboxLayout.addWidget(self.smu2_group_box)
        vboxLayout.addWidget(self.elm_group_box)
        vboxLayout.addWidget(self.elm2_group_box)
        vboxLayout.addWidget(self.lcr_group_box)
        vboxLayout.addWidget(self.dmm_group_box)
        vboxLayout.addWidget(self.tcu_group_box)
        vboxLayout.addStretch()
        bottomLayout.addLayout(vboxLayout)
        bottomLayout.setStretch(0, 0)
        bottomLayout.setStretch(1, 7)
        bottomLayout.setStretch(2, 3)

        layout = QtWidgets.QVBoxLayout(self.centralWidget())
        layout.addWidget(self.dataStackedWidget)
        layout.addLayout(bottomLayout)

    def set_data_widget(self, widget: QtWidgets.QWidget) -> None:
        while self.dataStackedWidget.count():
            self.dataStackedWidget.removeWidget(self.dataStackedWidget.currentWidget())
        self.dataStackedWidget.addWidget(widget)

    def add_role(self, name: str) -> RoleWidget:
        if name in self.roleWidgets:
            raise KeyError(f"No suc role: {name}")
        widget = RoleWidget(name)
        self.roleWidgets[name] = widget
        self.control_tab_widget.addTab(widget, widget.name())
        return widget

    def find_role(self, name: str) -> Optional[RoleWidget]:
        return self.roleWidgets.get(name)

    def roles(self) -> list[RoleWidget]:
        return list(self.roleWidgets.values())

    def clear(self) -> None:
        """Clear displayed data in plots and inputs."""
        self.smuVoltageLineEdit.setText("---")
        self.smuCurrentLineEdit.setText("---")
        self.setSMUOutputState(None)
        self.smu2VoltageLineEdit.setText("---")
        self.smu2CurrentLineEdit.setText("---")
        self.setSMU2OutputState(None)
        self.elmVoltageLineEdit.setText("---")
        self.elmCurrentLineEdit.setText("---")
        self.setELMOutputState(None)
        self.elm2VoltageLineEdit.setText("---")
        self.elm2CurrentLineEdit.setText("---")
        self.setELM2OutputState(None)
        self.lcrVoltageLineEdit.setText("---")
        self.lcrCurrentLineEdit.setText("---")
        self.setLCROutputState(None)
        self.dmmTemperatureLineEdit.setText("---")
        self.tcuTemperatureLineEdit.setText("---")
        self.tcuStateLineEdit.setText("---")

    def set_idle_state(self) -> None:
        self.import_action.setEnabled(True)
        self.preferencesAction.setEnabled(True)
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.continuous_action.setEnabled(True)
        self.start_button.setEnabled(True)
        self.start_button.setChecked(False)
        self.stop_button.setEnabled(False)
        self.stop_button.setChecked(False)
        self.continuous_check_box.setEnabled(True)
        self.reset_check_box.setEnabled(True)
        self.auto_reconnect_check_box.setEnabled(True)
        self.general_widget.set_idle_state()
        self.set_change_voltage_enabled(False)
        for role in self.roles():
            role.set_locked(False)
        self.setSMUOutputState(None)
        self.setSMU2OutputState(None)
        self.setELMOutputState(None)
        self.setLCROutputState(None)
        self._locked = False

    def set_running_state(self) -> None:
        self._locked = True
        self.import_action.setEnabled(False)
        self.preferencesAction.setEnabled(False)
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.continuous_action.setEnabled(False)
        self.start_button.setEnabled(False)
        self.start_button.setChecked(True)
        self.stop_button.setEnabled(True)
        self.stop_button.setChecked(False)
        self.continuous_check_box.setEnabled(False)
        self.reset_check_box.setEnabled(False)
        self.auto_reconnect_check_box.setEnabled(False)
        self.general_widget.set_running_state()
        for role in self.roles():
            role.set_locked(True)
        self.loggingWidget.ensureRecentRecordsVisible()

    def set_stopping_state(self) -> None:
        self.stop_action.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.general_widget.set_stopping_state()
        self.set_change_voltage_enabled(False)

    def set_message(self, message: str) -> None:
        self.message_label.show()
        self.message_label.setText(message)

    def clear_message(self) -> None:
        self.message_label.hide()
        self.message_label.clear()

    def set_progress(self, minimum: int, maximum: int, value: int) -> None:
        self.progress_bar.show()
        self.progress_bar.setRange(minimum, maximum)
        self.progress_bar.setValue(value)

    def clear_progress(self) -> None:
        self.progress_bar.hide()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

    def is_continuous(self) -> bool:
        return self.continuous_action.isChecked()

    def set_continuous(self, enabled: bool) -> None:
        self.continuous_action.setChecked(enabled)
        self.continuous_check_box.setChecked(enabled)

    def is_change_voltage_enabled(self) -> bool:
        return self.changeVoltageAction.isEnabled()

    def set_change_voltage_enabled(self, state: bool) -> None:
        self.changeVoltageAction.setEnabled(state)
        self.general_widget.set_change_voltage_enabled(state)

    def is_reset_instruments(self) -> bool:
        return self.reset_check_box.isChecked()

    def set_reset_instruments(self, enabled: bool) -> None:
        return self.reset_check_box.setChecked(enabled)

    def is_auto_reconnect(self) -> bool:
        return self.auto_reconnect_check_box.isChecked()

    def set_auto_reconnect(self, enabled: bool) -> None:
        self.auto_reconnect_check_box.setChecked(enabled)

    def setSMUOutputState(self, state) -> None:
        self.smuOutputStateLineEdit.setText(format_switch(state))
        self.smuOutputStateLineEdit.setStyleSheet(stylesheet_switch(state))

    def setSMU2OutputState(self, state) -> None:
        self.smu2OutputStateLineEdit.setText(format_switch(state))
        self.smu2OutputStateLineEdit.setStyleSheet(stylesheet_switch(state))

    def setELMOutputState(self, state) -> None:
        self.elmOutputStateLineEdit.setText(format_switch(state))
        self.elmOutputStateLineEdit.setStyleSheet(stylesheet_switch(state))

    def setELM2OutputState(self, state) -> None:
        self.elm2OutputStateLineEdit.setText(format_switch(state))
        self.elm2OutputStateLineEdit.setStyleSheet(stylesheet_switch(state))

    def setLCROutputState(self, state) -> None:
        self.lcrOutputStateLineEdit.setText(format_switch(state))
        self.lcrOutputStateLineEdit.setStyleSheet(stylesheet_switch(state))

    def updateSourceVoltage(self, voltage: float) -> None:
        if self.smu_group_box.isEnabled():
            self.updateSMUVoltage(voltage)
        elif self.elm_group_box.isEnabled():
            self.updateELMVoltage(voltage)
        elif self.elm2_group_box.isEnabled():
            self.updateELM2Voltage(voltage)
        elif self.lcr_group_box.isEnabled():
            self.updateLCRVoltage(voltage)

    def updateBiasSourceVoltage(self, voltage: float) -> None:
        self.updateSMU2Voltage(voltage)

    def updateSourceOutputState(self, state: bool) -> None:
        if self.smu_group_box.isEnabled():
            self.setSMUOutputState(state)
        elif self.elm_group_box.isEnabled():
            self.setELMOutputState(state)
        elif self.lcr_group_box.isEnabled():
            self.setLCROutputState(state)

    def updateBiasSourceOutputState(self, state: bool) -> None:
        if self.smu2_group_box.isEnabled():
            self.setSMU2OutputState(state)

    def updateSMUVoltage(self, voltage: float) -> None:
        self.smuVoltageLineEdit.setText(format_metric(voltage, "V"))

    def updateSMUCurrent(self, current: float) -> None:
        self.smuCurrentLineEdit.setText(format_metric(current, "A"))

    def updateSMU2Voltage(self, voltage: float) -> None:
        self.smu2VoltageLineEdit.setText(format_metric(voltage, "V"))

    def updateSMU2Current(self, current: float) -> None:
        self.smu2CurrentLineEdit.setText(format_metric(current, "A"))

    def updateELMVoltage(self, voltage: float) -> None:
        self.elmVoltageLineEdit.setText(format_metric(voltage, "V"))

    def updateELMCurrent(self, current: float) -> None:
        self.elmCurrentLineEdit.setText(format_metric(current, "A"))

    def updateELM2Voltage(self, voltage: float) -> None:
        self.elm2VoltageLineEdit.setText(format_metric(voltage, "V"))

    def updateELM2Current(self, current: float) -> None:
        self.elm2CurrentLineEdit.setText(format_metric(current, "A"))

    def updateLCRVoltage(self, voltage: float) -> None:
        self.lcrVoltageLineEdit.setText(format_metric(voltage, "V"))

    def updateLCRCapacity(self, capacity: float) -> None:
        self.lcrCurrentLineEdit.setText(format_metric(capacity, "F"))

    def updateDMMTemperature(self, temperature: float) -> None:
        self.dmmTemperatureLineEdit.setText(format_metric(temperature, "°C", 1))

    def updateTCUTemperature(self, temperature: float) -> None:
        self.tcuTemperatureLineEdit.setText(format_metric(temperature, "°C", 1))

    def updateTCUState(self, state: str) -> None:
        self.tcuStateLineEdit.setText(str(state or "---"))

    @QtCore.Slot()
    def on_show_preferences(self) -> None:
        dialog = PreferencesDialog(self)
        dialog.read_settings()
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            dialog.write_settings()

    @QtCore.Slot()
    def on_show_contents(self) -> None:
        webbrowser.open(CONTENTS_URL)

    @QtCore.Slot()
    def on_show_about_qt(self) -> None:
        QtWidgets.QMessageBox.aboutQt(self)

    @QtCore.Slot()
    def on_show_about(self) -> None:
        QtWidgets.QMessageBox.about(self, "About", ABOUT_TEXT)

    def show_active_info(self) -> None:
        title = "Measurement active"
        text = "Stop the current measurement to exiting the application."
        QtWidgets.QMessageBox.information(self, title, text)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._locked:
            self.show_active_info()
            event.ignore()
        else:
            event.accept()
