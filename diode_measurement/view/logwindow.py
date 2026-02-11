import logging
import threading
from typing import Callable

from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ["LogWindow", "LogWidget"]


class Handler(logging.Handler):

    def __init__(self, callback: Callable) -> None:
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        self.callback(record)


class RecordsQueue:

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.records: list[logging.LogRecord] = []

    def append(self, record: logging.LogRecord) -> None:
        with self.lock:
            self.records.append(record)

    def fetch(self) -> list[logging.LogRecord]:
        with self.lock:
            records = self.records[:]
            self.records.clear()
            return records


class LogWidget(QtWidgets.QTextEdit):

    MaximumEntries: int = 1024 * 1024
    """Maximum number of visible log entries."""

    received = QtCore.pyqtSignal(logging.LogRecord)
    """Received is emitted when a new log record is appended by a logger."""

    updateInterval = 200
    """Update interval in milliseconds."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.document().setMaximumBlockCount(type(self).MaximumEntries)
        self.recordsQueue = RecordsQueue()
        self.handler = Handler(self.received.emit)
        self.setLevel(logging.INFO)
        self.received.connect(self.appendRecord)

        self.updateTimer = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.applyRecords)
        self.updateTimer.start(self.updateInterval)

        self.recordFormats = {}

        errorFormat = QtGui.QTextCharFormat()
        errorFormat.setForeground(QtGui.QColor("red"))
        self.recordFormats[logging.ERROR] = errorFormat

        warningFormat = QtGui.QTextCharFormat()
        warningFormat.setForeground(QtGui.QColor("orange"))
        self.recordFormats[logging.WARNING] = warningFormat

        infoFormat = QtGui.QTextCharFormat()
        infoFormat.setForeground(QtGui.QColor())
        self.recordFormats[logging.INFO] = infoFormat

        debugFormat = QtGui.QTextCharFormat()
        debugFormat.setForeground(QtGui.QColor("grey"))
        self.recordFormats[logging.DEBUG] = debugFormat

    def setLevel(self, level: int) -> None:
        """Set log level of widget."""
        self.handler.setLevel(level)

    def addLogger(self, logger: logging.Logger) -> None:
        """Add logger to widget."""
        logger.addHandler(self.handler)

    def removeLogger(self, logger: logging.Logger) -> None:
        """Remove logger from widget."""
        logger.removeHandler(self.handler)

    def appendRecord(self, record: logging.LogRecord) -> None:
        """Append log record to queue."""
        self.recordsQueue.append(record)

    def applyRecords(self) -> None:
        """Append records from queue to log widget."""
        records = self.recordsQueue.fetch()
        if records:
            # Get current scrollbar position
            scrollbar = self.verticalScrollBar()
            position = scrollbar.value()
            # Lock to current position or to bottom
            lock = False
            if position + 1 >= scrollbar.maximum():
                lock = True
            # Append formatted log messages
            for record in records:
                for level, recordFormat in self.recordFormats.items():
                    if record.levelno >= level:
                        self.setCurrentCharFormat(recordFormat)
                        break
                self.append(self.formatRecord(record))
            # Scroll to bottom
            if lock:
                scrollbar.setValue(scrollbar.maximum())
            else:
                scrollbar.setValue(position)

    def ensureRecentRecordsVisible(self) -> None:
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @classmethod
    def formatTime(cls, seconds: float) -> str:
        """Format timestamp for log record."""
        dt = QtCore.QDateTime.fromMSecsSinceEpoch(int(seconds * 1e3))
        return dt.toString("yyyy-MM-dd hh:mm:ss")

    @classmethod
    def formatRecord(cls, record: logging.LogRecord) -> str:
        """Format log record."""
        timestamp = cls.formatTime(record.created)
        return "{}\t{}\t{}".format(timestamp, record.levelname, record.message)


class LogWindow(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Logging"))

        self.logHeader = QtWidgets.QLabel()
        self.logHeader.setTextFormat(QtCore.Qt.RichText)
        self.logHeader.setText("<span style=\"white-space:pre\">Time\t\tLevel\tMessage</span>")

        self.logWidget = LogWidget()

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setStandardButtons(self.buttonBox.Close)
        self.buttonBox.rejected.connect(lambda: self.hide())

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.logHeader)
        layout.addWidget(self.logWidget)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def setLevel(self, level: int) -> None:
        """Set log level of widget."""
        self.logWidget.setLevel(level)

    def addLogger(self, logger: logging.Logger) -> None:
        """Add logger to widget."""
        self.logWidget.addLogger(logger)

    def removeLogger(self, logger: logging.Logger) -> None:
        """Remove logger from widget."""
        self.logWidget.removeLogger(logger)

    def clear(self) -> None:
        """Clear log history."""
        self.logWidget.clear()
