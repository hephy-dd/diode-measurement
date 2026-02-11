"""Plugin implementing a simple TCP server providing a JSON-RCP protocol
to control measurements remotely by third party software.
"""

import datetime
import jsonrpc
import logging
import math
import socketserver
import threading
import time

from typing import Any, Optional, Union

from PyQt5 import QtCore, QtWidgets

from . import Plugin

__all__ = ["TCPServerPlugin"]

logger = logging.getLogger(__name__)


def is_finite(value: Any) -> bool:
    """Return `True` if value is finite float or `True` for any other value type."""
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def json_dict(d: dict) -> dict:
    """Replace non-finite floats (nan, +inf, -inf) with `None` to be converted to `null` in JSON."""
    return {k: (v if is_finite(v) else None) for k, v in d.items()}


class RPCHandler:
    def __init__(self, controller) -> None:
        self.controller = controller
        self.dispatcher = jsonrpc.Dispatcher()
        self.dispatcher["start"] = self.on_start
        self.dispatcher["stop"] = self.on_stop
        self.dispatcher["change_voltage"] = self.on_change_voltage
        self.dispatcher["state"] = self.on_state
        self.manager = jsonrpc.JSONRPCResponseManager()

    def handle(self, request) -> dict[str, Any]:
        return self.manager.handle(request, self.dispatcher)

    def on_start(self, reset: Optional[bool] = None, continuous: Optional[bool] = None,
                 auto_reconnect: Optional[bool] = None, measurement_type: Optional[str] = None,
                 begin_voltage: Optional[float] = None, end_voltage: Optional[float] = None,
                 step_voltage: Optional[float] = None, waiting_time: Optional[float] = None,
                 compliance: Optional[float] = None,
                 waiting_time_continuous: Optional[float] = None) -> None:
        with self.controller.rpc_params:
            rpc_params: dict[str, Union[None, int, float, str]] = {}
            if reset is not None:
                rpc_params["reset"] = reset
            if continuous is not None:
                rpc_params["continuous"] = continuous
            if auto_reconnect is not None:
                rpc_params["auto_reconnect"] = auto_reconnect
            if begin_voltage is not None:
                rpc_params["begin_voltage"] = begin_voltage
            if end_voltage is not None:
                rpc_params["end_voltage"] = end_voltage
            if step_voltage is not None:
                rpc_params["step_voltage"] = step_voltage
            if waiting_time is not None:
                rpc_params["waiting_time"] = waiting_time
            if compliance is not None:
                rpc_params["compliance"] = compliance
            if waiting_time_continuous is not None:
                rpc_params["waiting_time_continuous"] = waiting_time_continuous
            self.controller.rpc_params.update(rpc_params)
            self.controller.started.emit()

    def on_stop(self) -> None:
        self.controller.aborted.emit()

    def on_change_voltage(self, end_voltage: float, step_voltage: float = 1.0,
                          waiting_time: float = 1.0) -> None:
        self.controller.requestChangeVoltage.emit(end_voltage, step_voltage, waiting_time)

    def on_state(self) -> dict[str, Union[None, int, float, str]]:
        return json_dict(self.controller.snapshot())


class TCPHandler(socketserver.BaseRequestHandler):
    buffer_size: int = 1024

    def handle(self) -> None:
        self.data = self.request.recv(self.buffer_size).strip().decode("utf-8")
        logger.info("TCP %s wrote: %s", self.client_address[0], self.data)
        rpc_handler = getattr(self.server, "rpc_handler", None)
        message_ready = getattr(self.server, "message_ready", None)
        if message_ready:
            message_ready.emit(format(self.data))
        if rpc_handler:
            response = rpc_handler.handle(self.data)
            if response:
                data = response.json.encode("utf-8")
                logger.info("TCP %s returned: %s", self.client_address[0], response.json)
                if message_ready:
                    message_ready.emit(format(response.json))
                self.request.sendall(data)


class TCPServer(socketserver.TCPServer):
    allow_reuse_address: bool = True


class RPCWidget(QtWidgets.QWidget):
    MaximumEntries: int = 1024 * 64
    """Maximum number of visible protocol entries."""

    restartSignal = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("RPC")

        # Widgets

        self.rpcGroupBox = QtWidgets.QGroupBox("JSON-RPC Server")

        self.stateLabel = QtWidgets.QLabel()
        self.stateLabel.setText("Stop")

        self.hostnameLineEdit = QtWidgets.QLineEdit()
        self.hostnameLineEdit.setToolTip(self.tr("Hostname"))
        self.hostnameLineEdit.setStatusTip(self.tr("Hostname"))

        self.portSpinBox = QtWidgets.QSpinBox()
        self.portSpinBox.setToolTip(self.tr("Port"))
        self.portSpinBox.setStatusTip(self.tr("Port"))
        self.portSpinBox.setRange(0, 999999)

        self.enabledCheckBox = QtWidgets.QCheckBox(self.tr("Enabled"))
        self.enabledCheckBox.setToolTip(self.tr("Run server"))
        self.enabledCheckBox.setStatusTip(self.tr("Run server"))

        self.protocolTextEdit = QtWidgets.QTextEdit()
        self.protocolTextEdit.setReadOnly(True)
        self.protocolTextEdit.document().setMaximumBlockCount(type(self).MaximumEntries)

        self.protocolGroupBox = QtWidgets.QGroupBox(self.tr("Protocol"))

        # Layouts

        formLayout = QtWidgets.QFormLayout(self.rpcGroupBox)
        formLayout.addRow(self.tr("State"), self.stateLabel)
        formLayout.addRow(self.tr("Hostname"), self.hostnameLineEdit)
        formLayout.addRow(self.tr("Port"), self.portSpinBox)
        formLayout.addRow("", self.enabledCheckBox)

        protocolLayout = QtWidgets.QVBoxLayout(self.protocolGroupBox)
        protocolLayout.addWidget(self.protocolTextEdit)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.rpcGroupBox)
        layout.addWidget(self.protocolGroupBox)
        layout.setStretch(0, 1)
        layout.setStretch(1, 2)

        # Connections
        self.enabledCheckBox.toggled.connect(self.restartSignal)

    def isServerEnabled(self) -> bool:
        return self.enabledCheckBox.isChecked()

    def setServerEnabled(self, enabled: bool) -> None:
        self.enabledCheckBox.setChecked(enabled)

    def setConnected(self, connected: bool) -> None:
        self.portSpinBox.setEnabled(not connected)
        self.hostnameLineEdit.setEnabled(not connected)
        self.setState("Running" if connected else "Stopped")

    def hostname(self) -> str:
        return self.hostnameLineEdit.text().strip()

    def setHostname(self, hostname: str) -> None:
        self.hostnameLineEdit.setText(hostname)

    def port(self) -> int:
        return self.portSpinBox.value()

    def setPort(self, port: int) -> None:
        self.portSpinBox.setValue(port)

    def setState(self, text: str) -> None:
        self.stateLabel.setText(text)


class TCPServerPlugin(Plugin, QtCore.QObject):

    running = QtCore.pyqtSignal(bool)
    failed = QtCore.pyqtSignal(object)
    message_ready = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = threading.Thread(target=self.run)
        self._enabled = threading.Event()
        self._shutdownHandlers = []
        self._messageCache = []
        self._messageCacheLock = threading.RLock()
        self._messageTimer = QtCore.QTimer()
        self._messageTimer.timeout.connect(self.appendCachedMessages)
        self.failed.connect(lambda _: self.rpcWidget.setServerEnabled(False))  # disable on error

    def install(self, context):
        self.failed.connect(context.handleException)
        self._installTab(context)
        self.rpc_handler = RPCHandler(context)
        self.loadSettings()
        self._startThread()
        self._messageTimer.start(250)

    def uninstall(self, context):
        self._messageTimer.stop()
        self.failed.disconnect(context.handleException)
        self._enabled.clear()
        for handler in self._shutdownHandlers:
            handler()
        self.storeSettings()

    def loadSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("tcpServer")
        enabled = settings.value("enabled", False, bool)
        hostname = settings.value("hostname", "", str)
        port = settings.value("port", 8000, int)
        settings.endGroup()
        self.rpcWidget.setServerEnabled(enabled)
        self.rpcWidget.setHostname(hostname)
        self.rpcWidget.setPort(port)

    def storeSettings(self):
        settings = QtCore.QSettings()
        enabled = self.rpcWidget.isServerEnabled()
        hostname = self.rpcWidget.hostname()
        port = self.rpcWidget.port()
        settings.beginGroup("tcpServer")
        settings.setValue("enabled", enabled)
        settings.setValue("hostname", hostname)
        settings.setValue("port", port)
        settings.endGroup()

    def requestRestart(self):
        for handler in self._shutdownHandlers:
            handler()

    def join(self):
        self._thread.join()

    def _installTab(self, context):
        self.rpcWidget = RPCWidget()
        self.running.connect(lambda state: self.rpcWidget.setConnected(state))
        self.rpcWidget.restartSignal.connect(lambda: self.requestRestart())
        context.view.controlTabWidget.insertTab(1000, self.rpcWidget, self.rpcWidget.windowTitle())
        self.message_ready.connect(self.appendProtocol)

    def appendProtocol(self, message: str) -> None:
        with self._messageCacheLock:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self._messageCache.append(f"{timestamp} {message}")

    def fetchCachedMessages(self) -> list:
        with self._messageCacheLock:
            messages = self._messageCache[:]
            self._messageCache.clear()
            return messages

    def appendCachedMessages(self) -> None:
        messages = self.fetchCachedMessages()
        if messages:
            textEdit = self.rpcWidget.protocolTextEdit
            # Get current scrollbar position
            scrollbar = textEdit.verticalScrollBar()
            pos = scrollbar.value()
            # Lock to current position or to bottom
            lock = False
            if pos + 1 >= scrollbar.maximum():
                lock = True
            # Append messages
            for message in messages:
                textEdit.append(message)
            # Scroll to bottom
            if lock:
                scrollbar.setValue(scrollbar.maximum())
            else:
                scrollbar.setValue(pos)

    def _startThread(self):
        self._enabled.set()
        self._thread.start()

    def _setupServer(self, server):
        self._shutdownHandlers.append(server.shutdown)
        server.rpc_handler = self.rpc_handler
        server.message_ready = self.message_ready

    def run(self):
        while self._enabled.is_set():
            if self.rpcWidget.isServerEnabled():
                hostname = self.rpcWidget.hostname()
                port = self.rpcWidget.port()
                self._runServer(hostname, port)
            else:
                time.sleep(.50)

    def _runServer(self, hostname: str, port: int) -> None:
        logger.info("TCP started %s:%s", hostname, port)
        try:
            with TCPServer((hostname, port), TCPHandler) as server:
                self.running.emit(True)
                self._setupServer(server)
                server.serve_forever()
        except Exception as exc:
            logger.exception(exc)
            self.failed.emit(exc)
        finally:
            logger.info("TCP stopped %s:%s", hostname, port)
            self.running.emit(False)
            self._shutdownHandlers.clear()
            time.sleep(.50)
