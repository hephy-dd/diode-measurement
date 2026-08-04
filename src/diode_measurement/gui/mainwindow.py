import logging
import webbrowser

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__ as APP_VERSION
from ..state import Roles
from .general import GeneralWidget
from .logwindow import LogWidget
from .preferences import PreferencesDialog
from .role import RoleWidget
from .status import (
    DMMStatusGroupBox,
    ELMStatusGroupBox,
    LCRStatusGroupBox,
    SMUStatusGroupBox,
    TCUStatusGroupBox,
)

__all__ = ["MainWindow"]

CONTENTS_URL: str = "https://github.com/hephy-dd/diode-measurement"

ABOUT_TEXT: str = f"""
    <h3>Diode Measurement</h3>
    <p>IV/CV measurements for silicon sensors.</p>
    <p>Version {APP_VERSION}</p>
    <p>This software is licensed under the GNU General Public License Version 3.</p>
    <p>Copyright &copy; 2021-2026 <a href=\"https://oeaw.ac.at/mbi\">MBI</a></p>
"""


class MainWindow(QtWidgets.QMainWindow):
    prepare_change_voltage = QtCore.Signal()
    role_browse_resources = QtCore.Signal(str)
    role_test_connection = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._locked: bool = False

        self._create_actions()
        self._create_menus()
        self._create_widgets()
        self._create_layout()

    def _create_actions(self) -> None:
        self.import_action = QtGui.QAction("&Import File...")
        self.import_action.setStatusTip("Import measurement data")

        self.quit_action = QtGui.QAction("&Quit")
        self.quit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        self.quit_action.setStatusTip("Quit the application")
        self.quit_action.triggered.connect(self.close)

        self.preferences_action = QtGui.QAction("&Preferences...")
        self.preferences_action.setStatusTip("Show preferences dialog")
        self.preferences_action.triggered.connect(self.on_show_preferences)

        self.start_action = QtGui.QAction("&Start")
        self.start_action.setStatusTip("Start a new measurement")

        self.stop_action = QtGui.QAction("Sto&p")
        self.stop_action.setStatusTip("Stop an active measurement")

        self.continuous_action = QtGui.QAction("&Continuous Meas.")
        self.continuous_action.setCheckable(True)
        self.continuous_action.setStatusTip("Enable continuous measurement")

        self.change_voltage_action = QtGui.QAction("&Change Voltage...")
        self.change_voltage_action.setStatusTip(
            "Change voltage in continuous measurement"
        )
        self.change_voltage_action.triggered.connect(self.prepare_change_voltage.emit)

        self.contents_action = QtGui.QAction("&Contents")
        self.contents_action.setStatusTip("Open the user manual")
        self.contents_action.setShortcut(QtGui.QKeySequence("F1"))
        self.contents_action.triggered.connect(self.on_show_contents)

        self.about_qt_action = QtGui.QAction("About &Qt")
        self.about_qt_action.setStatusTip("About the used Qt framework")
        self.about_qt_action.triggered.connect(self.on_show_about_qt)

        self.about_action = QtGui.QAction("&About")
        self.about_action.setStatusTip("About the application")
        self.about_action.triggered.connect(self.on_show_about)

    def _create_menus(self) -> None:
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.import_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.quit_action)

        self.edit_menu = self.menuBar().addMenu("&Edit")
        self.edit_menu.addAction(self.preferences_action)

        self.view_menu = self.menuBar().addMenu("&View")

        self.measure_menu = self.menuBar().addMenu("&Measure")
        self.measure_menu.addAction(self.start_action)
        self.measure_menu.addAction(self.stop_action)
        self.measure_menu.addSeparator()
        self.measure_menu.addAction(self.continuous_action)
        self.measure_menu.addAction(self.change_voltage_action)

        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.addAction(self.contents_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_qt_action)
        self.help_menu.addAction(self.about_action)

    def _create_widgets(self) -> None:
        self.data_stacked_widget = QtWidgets.QStackedWidget()
        self.data_stacked_widget.setMinimumHeight(240)

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

        self.auto_reconnect_check_box = QtWidgets.QCheckBox("&Auto Reconnect")
        self.auto_reconnect_check_box.setStatusTip(
            "Auto reconnect and retry on connection erros"
        )

        self.general_widget = GeneralWidget()
        self.general_widget.change_voltage_clicked.connect(
            self.change_voltage_action.trigger
        )

        self.role_widgets: dict[str, RoleWidget] = {}

        self.control_tab_widget = QtWidgets.QTabWidget()
        self.control_tab_widget.addTab(
            self.general_widget, self.general_widget.windowTitle()
        )

        self.smu_group_box = SMUStatusGroupBox(self)
        self.smu_group_box.setTitle("SMU Status")

        self.smu2_group_box = SMUStatusGroupBox(self)
        self.smu2_group_box.setTitle("SMU2 Status")

        self.elm_group_box = ELMStatusGroupBox(self)
        self.elm_group_box.setTitle("ELM Status")

        self.elm2_group_box = ELMStatusGroupBox(self)
        self.elm2_group_box.setTitle("ELM2 Status")

        self.lcr_group_box = LCRStatusGroupBox(self)
        self.lcr_group_box.setTitle("LCR Status")

        self.dmm_group_box = DMMStatusGroupBox(self)
        self.dmm_group_box.setTitle("DMM Status")

        self.tcu_group_box = TCUStatusGroupBox(self)
        self.tcu_group_box.setTitle("TCU Status")

        self.status_group_boxes: dict[str, QtWidgets.QGroupBox] = {}
        self.status_group_boxes[Roles.SMU] = self.smu_group_box
        self.status_group_boxes[Roles.SMU2] = self.smu2_group_box
        self.status_group_boxes[Roles.ELM] = self.elm_group_box
        self.status_group_boxes[Roles.ELM2] = self.elm2_group_box
        self.status_group_boxes[Roles.LCR] = self.lcr_group_box
        self.status_group_boxes[Roles.DMM] = self.dmm_group_box
        self.status_group_boxes[Roles.TCU] = self.tcu_group_box

        self.tcu_temperature_line_edit = QtWidgets.QLineEdit("---")
        self.tcu_temperature_line_edit.setReadOnly(True)
        self.tcu_temperature_line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.setCentralWidget(QtWidgets.QWidget())

        # Dock widgets

        self.logging_widget = LogWidget(self)
        self.logging_widget.addLogger(logging.getLogger())
        self.logging_widget.setLevel(logging.DEBUG)

        self.logging_dock_widget = QtWidgets.QDockWidget("Logging")
        self.logging_dock_widget.setObjectName("logging_dock_widget")
        self.logging_dock_widget.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.logging_dock_widget.setWidget(self.logging_widget)
        self.logging_dock_widget.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.logging_dock_widget.hide()
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.logging_dock_widget
        )

        self.logging_action = self.logging_dock_widget.toggleViewAction()
        self.logging_action.setStatusTip("Toggle logging dock window")
        self.view_menu.addAction(self.logging_action)

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
        control_layout.addWidget(self.auto_reconnect_check_box)
        control_layout.addStretch()

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.addLayout(control_layout)
        bottomLayout.addWidget(self.control_tab_widget)
        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(self.smu_group_box)
        vbox_layout.addWidget(self.smu2_group_box)
        vbox_layout.addWidget(self.elm_group_box)
        vbox_layout.addWidget(self.elm2_group_box)
        vbox_layout.addWidget(self.lcr_group_box)
        vbox_layout.addWidget(self.dmm_group_box)
        vbox_layout.addWidget(self.tcu_group_box)
        vbox_layout.addStretch()
        bottomLayout.addLayout(vbox_layout)
        bottomLayout.setStretch(0, 0)
        bottomLayout.setStretch(1, 7)
        bottomLayout.setStretch(2, 3)

        layout = QtWidgets.QVBoxLayout(self.centralWidget())
        layout.addWidget(self.data_stacked_widget)
        layout.addLayout(bottomLayout)

    def set_data_widget(self, widget: QtWidgets.QWidget) -> None:
        while self.data_stacked_widget.count():
            self.data_stacked_widget.removeWidget(
                self.data_stacked_widget.currentWidget()
            )
        self.data_stacked_widget.addWidget(widget)

    def add_role(self, role: str, title: str) -> RoleWidget:
        if role in self.role_widgets:
            raise KeyError(f"No such role: {role!r}")
        self.general_widget.add_role(role, title)
        widget = RoleWidget(role)
        widget.browse_resources.connect(
            lambda role=role: self.role_browse_resources.emit(role)
        )
        widget.test_connection.connect(
            lambda role=role: self.role_test_connection.emit(role)
        )
        self.role_widgets[role] = widget
        self.control_tab_widget.addTab(widget, title)
        return widget

    def find_role(self, role: str) -> RoleWidget | None:
        return self.role_widgets.get(role)

    def roles(self) -> list[RoleWidget]:
        return list(self.role_widgets.values())

    def set_role_enabled(self, role: str, enabled: bool) -> None:
        self.general_widget.set_role_enabled(role, enabled)
        status = self.status_group_boxes.get(role)
        if status is not None:
            status.setEnabled(enabled)

    def clear(self) -> None:
        """Clear displayed data in plots and inputs."""
        self.smu_group_box.clear()
        self.smu2_group_box.clear()
        self.elm_group_box.clear()
        self.elm2_group_box.clear()
        self.lcr_group_box.clear()
        self.dmm_group_box.clear()
        self.tcu_group_box.clear()

    def set_idle_state(self) -> None:
        self.import_action.setEnabled(True)
        self.preferences_action.setEnabled(True)
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.continuous_action.setEnabled(True)
        self.start_button.setEnabled(True)
        self.start_button.setChecked(False)
        self.stop_button.setEnabled(False)
        self.stop_button.setChecked(False)
        self.continuous_check_box.setEnabled(True)
        self.auto_reconnect_check_box.setEnabled(True)
        self.general_widget.set_idle_state()
        self.set_change_voltage_enabled(False)
        for role in self.roles():
            role.set_locked(False)
        self.smu_group_box.clear()
        self.smu2_group_box.clear()
        self.elm_group_box.clear()
        self.elm2_group_box.clear()
        self.lcr_group_box.clear()
        self.dmm_group_box.clear()
        self.tcu_group_box.clear()
        self._locked = False

    def set_running_state(self) -> None:
        self._locked = True
        self.import_action.setEnabled(False)
        self.preferences_action.setEnabled(False)
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.continuous_action.setEnabled(False)
        self.start_button.setEnabled(False)
        self.start_button.setChecked(True)
        self.stop_button.setEnabled(True)
        self.stop_button.setChecked(False)
        self.continuous_check_box.setEnabled(False)
        self.auto_reconnect_check_box.setEnabled(False)
        self.general_widget.set_running_state()
        for role in self.roles():
            role.set_locked(True)
        self.logging_widget.ensure_recent_records_visible()

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
        return self.change_voltage_action.isEnabled()

    def set_change_voltage_enabled(self, state: bool) -> None:
        self.change_voltage_action.setEnabled(state)
        self.general_widget.set_change_voltage_enabled(state)

    def is_auto_reconnect(self) -> bool:
        return self.auto_reconnect_check_box.isChecked()

    def set_auto_reconnect(self, enabled: bool) -> None:
        self.auto_reconnect_check_box.setChecked(enabled)

    def set_smu_output_state(self, state: bool) -> None:
        self.smu_group_box.set_output_state(state)

    def set_smu2_output_state(self, state: bool) -> None:
        self.smu2_group_box.set_output_state(state)

    def set_elm_output_state(self, state: bool) -> None:
        self.elm_group_box.set_output_state(state)

    def set_elm2_output_state(self, state: bool) -> None:
        self.elm2_group_box.set_output_state(state)

    def set_lcr_output_state(self, state: bool) -> None:
        self.lcr_group_box.set_output_state(state)

    def update_source_voltage(self, voltage: float) -> None:
        if self.smu_group_box.isEnabled():
            self.update_smu_voltage(voltage)
        elif self.elm_group_box.isEnabled():
            self.update_elm_voltage(voltage)
        elif self.elm2_group_box.isEnabled():
            self.update_elm2_voltage(voltage)
        elif self.lcr_group_box.isEnabled():
            self.update_lcr_voltage(voltage)

    def update_bias_source_voltage(self, voltage: float) -> None:
        self.update_smu2_voltage(voltage)

    def update_source_output_state(self, state: bool) -> None:
        if self.smu_group_box.isEnabled():
            self.set_smu_output_state(state)
        elif self.elm_group_box.isEnabled():
            self.set_elm_output_state(state)
        elif self.lcr_group_box.isEnabled():
            self.set_lcr_output_state(state)

    def update_bias_source_output_state(self, state: bool) -> None:
        if self.smu2_group_box.isEnabled():
            self.set_smu2_output_state(state)

    def update_smu_voltage(self, voltage: float) -> None:
        self.smu_group_box.set_voltage(voltage)

    def update_smu_current(self, current: float) -> None:
        self.smu_group_box.set_current(current)

    def update_smu2_voltage(self, voltage: float) -> None:
        self.smu2_group_box.set_voltage(voltage)

    def update_smu2_current(self, current: float) -> None:
        self.smu2_group_box.set_current(current)

    def update_elm_voltage(self, voltage: float) -> None:
        self.elm_group_box.set_voltage(voltage)

    def update_elm_current(self, current: float) -> None:
        self.elm_group_box.set_current(current)

    def update_elm2_voltage(self, voltage: float) -> None:
        self.elm2_group_box.set_voltage(voltage)

    def update_elm2_current(self, current: float) -> None:
        self.elm2_group_box.set_current(current)

    def update_lcr_voltage(self, voltage: float) -> None:
        self.lcr_group_box.set_voltage(voltage)

    def update_lcr_capacity(self, capacity: float) -> None:
        self.lcr_group_box.set_capacity(capacity)

    def update_dmm_temperature(self, temperature: float) -> None:
        self.dmm_group_box.set_temperature(temperature)

    def update_tcu_temperature(self, temperature: float) -> None:
        self.tcu_group_box.set_temperature(temperature)

    def update_tcu_humidity(self, humidity: float) -> None:
        self.tcu_group_box.set_humidity(humidity)

    def update_tcu_state(self, state: str) -> None:
        self.tcu_group_box.set_state(state)

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
