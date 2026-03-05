"""Plugin implementing a simple TCP server providing a JSON-RCP protocol
to control measurements remotely by third party software.
"""

import asyncio
import datetime
import jsonrpc
import logging
import math
import threading
import time
from dataclasses import dataclass
from concurrent.futures import Future
from queue import Queue, Empty
from typing import Any, Callable, Optional

from PySide6 import QtCore, QtWidgets

from diode_measurement.utils import safe_bool, safe_int, safe_str
from diode_measurement.controller import Controller

from . import Plugin

__all__ = ["RPCServerPlugin"]

logger = logging.getLogger(__name__)


def is_finite(value: Any) -> bool:
    """Return `True` if value is finite float or `True` for any other value type."""
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def json_dict(d: dict) -> dict:
    """Replace non-finite floats (nan, +inf, -inf) with `None` to be converted to `null` in JSON."""
    return {k: (v if is_finite(v) else None) for k, v in d.items()}


@dataclass
class StartEvent:
    parameters: dict

    def __call__(self, controller: Controller) -> None:
        controller.configure(self.parameters)
        controller.started.emit()


@dataclass
class StopEvent:
    def __call__(self, controller: Controller) -> None:
        controller.aborted.emit()


@dataclass
class ChangeVoltageEvent:
    end_voltage: float
    step_voltage: float
    waiting_time: float

    def __call__(self, controller: Controller) -> None:
        controller.requestChangeVoltage(
            self.end_voltage,
            self.step_voltage,
            self.waiting_time,
        )


@dataclass
class StateEvent:
    def __call__(self, controller: Controller) -> dict[str, Any]:
        return controller.snapshot()


@dataclass
class Envelope:
    event: Any
    future: Future


class EventHandler:
    def __init__(self, controller: Controller) -> None:
        self.controller = controller
        self.inbox: Queue[Envelope] = Queue()
        self.poll_max_events: int = 64
        self.event_timer = QtCore.QTimer()
        self.event_timer.timeout.connect(self.on_poll_events)
        self.event_timer.start(50)

    def shutdown(self) -> None:
        self.event_timer.stop()

    def notify(self, event: Callable[[Controller], Any]) -> Future:
        future: Future = Future()
        self.inbox.put_nowait(Envelope(event, future))
        return future

    def poll_event(self) -> Optional[Envelope]:
        try:
            return self.inbox.get_nowait()
        except Empty:
            return None

    def on_poll_events(self) -> None:
        for _ in range(self.poll_max_events):
            try:
                envelope = self.poll_event()
                if envelope is None:
                    break
                try:
                    result = envelope.event(self.controller)
                except Exception as exc:
                    envelope.future.set_exception(exc)
                else:
                    envelope.future.set_result(result)
            except Exception as exc:
                logger.exception(exc)


class RPCHandler:
    def __init__(self, event_handler: EventHandler) -> None:
        self.timeout: float = 5.0
        self.event_handler = event_handler
        self.dispatcher = jsonrpc.Dispatcher()
        self.dispatcher["start"] = self.on_start
        self.dispatcher["stop"] = self.on_stop
        self.dispatcher["change_voltage"] = self.on_change_voltage
        self.dispatcher["state"] = self.on_state
        self.manager = jsonrpc.JSONRPCResponseManager()

    def handle(self, request) -> dict[str, Any]:
        return self.manager.handle(request, self.dispatcher)

    def on_start(
        self,
        reset: Optional[bool] = None,
        continuous: Optional[bool] = None,
        auto_reconnect: Optional[bool] = None,
        measurement_type: Optional[str] = None,
        measurement_instruments: Optional[list[str]] = None,
        begin_voltage: Optional[float] = None,
        end_voltage: Optional[float] = None,
        step_voltage: Optional[float] = None,
        waiting_time: Optional[float] = None,
        compliance: Optional[float] = None,
        waiting_time_continuous: Optional[float] = None,
    ) -> None:
        parameters: dict[str, Any] = {}
        if reset is not None:
            parameters["reset"] = reset
        if continuous is not None:
            parameters["continuous"] = continuous
        if auto_reconnect is not None:
            parameters["auto_reconnect"] = auto_reconnect
        if measurement_type is not None:
            parameters["measurement_type"] = measurement_type
        if measurement_instruments is not None:
            parameters["measurement_roles"] = measurement_instruments
        if begin_voltage is not None:
            parameters["begin_voltage"] = begin_voltage
        if end_voltage is not None:
            parameters["end_voltage"] = end_voltage
        if step_voltage is not None:
            parameters["step_voltage"] = step_voltage
        if waiting_time is not None:
            parameters["waiting_time"] = waiting_time
        if compliance is not None:
            parameters["compliance"] = compliance
        if waiting_time_continuous is not None:
            parameters["waiting_time_continuous"] = waiting_time_continuous
        self.event_handler.notify(StartEvent(parameters)).result(self.timeout)

    def on_stop(self) -> None:
        self.event_handler.notify(StopEvent()).result(self.timeout)

    def on_change_voltage(
        self,
        end_voltage: float,
        step_voltage: float = 1.0,
        waiting_time: float = 1.0,
    ) -> None:
        self.event_handler.notify(
            ChangeVoltageEvent(
                end_voltage=end_voltage,
                step_voltage=step_voltage,
                waiting_time=waiting_time,
            )
        ).result(self.timeout)

    def on_state(self) -> dict[str, Any]:
        result = self.event_handler.notify(StateEvent()).result(self.timeout)
        return json_dict(result)


class AsyncioTCPServer:
    buffer_size: int = 4096

    def __init__(self, hostname: str, port: int, rpc_handler, message_ready) -> None:
        self.hostname = hostname
        self.port = port
        self.rpc_handler = rpc_handler
        self.message_ready = message_ready
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[asyncio.base_events.Server] = None

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        peer_host = peer[0] if isinstance(peer, tuple) and peer else "?"
        try:
            data = await reader.read(self.buffer_size)
            if not data:
                return
            text = data.strip().decode("utf-8")
            logger.info("TCP %s wrote: %s", peer_host, text)
            if self.message_ready:
                self.message_ready.emit(format(text))

            if self.rpc_handler:
                response = self.rpc_handler.handle(text)
                if response:
                    payload = response.json.encode("utf-8")
                    logger.info("TCP %s returned: %s", peer_host, response.json)
                    if self.message_ready:
                        self.message_ready.emit(format(response.json))
                    writer.write(payload)
                    await writer.drain()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.hostname,
            port=self.port,
            reuse_address=True,
        )

    def shutdown(self) -> None:
        """Thread-safe shutdown."""
        if not self._loop:
            return

        def _do_shutdown() -> None:
            if self._server is not None:
                self._server.close()
            if self._loop is not None:
                self._loop.stop()

        self._loop.call_soon_threadsafe(_do_shutdown)


class RPCWidget(QtWidgets.QWidget):
    MaximumEntries: int = 1024
    """Maximum number of visible protocol entries."""

    restart_signal = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("RPC")

        # Widgets

        self.rpc_group_box = QtWidgets.QGroupBox("JSON-RPC Server")

        self.state_label = QtWidgets.QLabel()
        self.state_label.setText("Stop")

        self.hostname_line_edit = QtWidgets.QLineEdit()
        self.hostname_line_edit.setToolTip("Hostname")
        self.hostname_line_edit.setStatusTip("Hostname")

        self.port_spin_box = QtWidgets.QSpinBox()
        self.port_spin_box.setToolTip("Port")
        self.port_spin_box.setStatusTip("Port")
        self.port_spin_box.setRange(0, 999999)

        self.enabled_check_box = QtWidgets.QCheckBox("Enabled")
        self.enabled_check_box.setToolTip("Run server")
        self.enabled_check_box.setStatusTip("Run server")

        self.protocol_text_edit = QtWidgets.QTextEdit()
        self.protocol_text_edit.setReadOnly(True)
        self.protocol_text_edit.document().setMaximumBlockCount(
            type(self).MaximumEntries
        )

        self.protocol_group_box = QtWidgets.QGroupBox("Protocol")

        # Layouts

        form_layout = QtWidgets.QFormLayout(self.rpc_group_box)
        form_layout.addRow("State", self.state_label)
        form_layout.addRow("Hostname", self.hostname_line_edit)
        form_layout.addRow("Port", self.port_spin_box)
        form_layout.addRow("", self.enabled_check_box)

        protocol_layout = QtWidgets.QVBoxLayout(self.protocol_group_box)
        protocol_layout.addWidget(self.protocol_text_edit)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.rpc_group_box)
        layout.addWidget(self.protocol_group_box)
        layout.setStretch(0, 1)
        layout.setStretch(1, 2)

        # Connections
        self.enabled_check_box.toggled.connect(self.restart_signal)

    def is_server_enabled(self) -> bool:
        return self.enabled_check_box.isChecked()

    def set_server_enabled(self, enabled: bool) -> None:
        self.enabled_check_box.setChecked(enabled)

    def set_connected(self, connected: bool) -> None:
        self.port_spin_box.setEnabled(not connected)
        self.hostname_line_edit.setEnabled(not connected)
        self.set_state("Running" if connected else "Stopped")

    def hostname(self) -> str:
        return self.hostname_line_edit.text().strip()

    def set_hostname(self, hostname: str) -> None:
        self.hostname_line_edit.setText(hostname)

    def port(self) -> int:
        return self.port_spin_box.value()

    def set_port(self, port: int) -> None:
        self.port_spin_box.setValue(port)

    def set_state(self, text: str) -> None:
        self.state_label.setText(text)


class RPCServerPlugin(Plugin, QtCore.QObject):
    running = QtCore.Signal(bool)
    failed = QtCore.Signal(object)
    message_ready = QtCore.Signal(str)

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._thread = threading.Thread(target=self.run)
        self._enabled = threading.Event()
        self._shutdown_handlers: list = []
        self._message_cache: list = []
        self._message_cache_lock = threading.RLock()
        self._message_timer = QtCore.QTimer()
        self._message_timer.timeout.connect(self.append_cached_messages)
        self.failed.connect(
            lambda _: self.rpc_widget.set_server_enabled(False)
        )  # disable on error

    def install(self, context) -> None:
        self.failed.connect(context.handleException)
        self._install_tab(context)
        self.event_handler = EventHandler(context)
        self.rpc_handler = RPCHandler(self.event_handler)
        self.read_settings()
        self._start_thread()
        self._message_timer.start(250)

    def uninstall(self, context) -> None:
        self._message_timer.stop()
        self.failed.disconnect(context.handleException)
        self._enabled.clear()
        for handler in self._shutdown_handlers:
            handler()
        self.write_settings()

    def read_settings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("tcpServer")
        enabled = safe_bool(settings.value("enabled"), False)
        hostname = safe_str(settings.value("hostname"), "")
        port = safe_int(settings.value("port"), 8000)
        settings.endGroup()
        self.rpc_widget.set_server_enabled(enabled)
        self.rpc_widget.set_hostname(hostname)
        self.rpc_widget.set_port(port)

    def write_settings(self) -> None:
        settings = QtCore.QSettings()
        enabled = self.rpc_widget.is_server_enabled()
        hostname = self.rpc_widget.hostname()
        port = self.rpc_widget.port()
        settings.beginGroup("tcpServer")
        settings.setValue("enabled", enabled)
        settings.setValue("hostname", hostname)
        settings.setValue("port", port)
        settings.endGroup()

    def _request_restart(self) -> None:
        for handler in self._shutdown_handlers:
            handler()

    def join(self) -> None:
        self._thread.join()

    def _install_tab(self, context) -> None:
        self.rpc_widget = RPCWidget()
        self.running.connect(lambda state: self.rpc_widget.set_connected(state))
        self.rpc_widget.restart_signal.connect(lambda: self._request_restart())
        context.view.controlTabWidget.insertTab(
            1000, self.rpc_widget, self.rpc_widget.windowTitle()
        )
        self.message_ready.connect(self._append_protocol)

    def _append_protocol(self, message: str) -> None:
        with self._message_cache_lock:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self._message_cache.append(f"{timestamp} {message}")

    def fetch_cached_messages(self) -> list[str]:
        with self._message_cache_lock:
            messages = self._message_cache[:]
            self._message_cache.clear()
            return messages

    def append_cached_messages(self) -> None:
        messages = self.fetch_cached_messages()
        if messages:
            textEdit = self.rpc_widget.protocol_text_edit
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

    def _start_thread(self) -> None:
        self._enabled.set()
        self._thread.start()

    def _setup_server(self, server) -> None:
        self._shutdown_handlers.append(server.shutdown)

    def run(self) -> None:
        while self._enabled.is_set():
            if self.rpc_widget.is_server_enabled():
                hostname = self.rpc_widget.hostname()
                port = self.rpc_widget.port()
                self._run_server(hostname, port)
            else:
                time.sleep(0.50)

    def _run_server(self, hostname: str, port: int) -> None:
        logger.info("TCP started %s:%s", hostname, port)
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server = AsyncioTCPServer(
                hostname=hostname,
                port=port,
                rpc_handler=self.rpc_handler,
                message_ready=self.message_ready,
            )
            loop.run_until_complete(server.start(loop))
            self.running.emit(True)
            self._setup_server(server)
            loop.run_forever()
            # Ensure server is closed once the loop was stopped.
            if server._server is not None:
                server._server.close()
                loop.run_until_complete(server._server.wait_closed())
        except Exception as exc:
            logger.exception(exc)
            self.failed.emit(exc)
        finally:
            try:
                if loop is not None:
                    loop.stop()
                    loop.close()
            except Exception:
                pass
            logger.info("TCP stopped %s:%s", hostname, port)
            self.running.emit(False)
            self._shutdown_handlers.clear()
            time.sleep(0.50)
