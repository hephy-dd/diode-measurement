from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..utils import safe_str

TIMESTAMP_FORMATS: list[str] = [
    ".3f",
    ".6f",
    ".9f",
]

VALUE_FORMATS: list[str] = [
    "+.3E",
    "+.6E",
    "+.9E",
    "+.12E",
]


class PreferencesDialog(QtWidgets.QDialog):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Preferences")
        self.setMinimumSize(320, 240)

        # Output Tab

        self.outputWidget = QtWidgets.QWidget(self)

        self.timestampFormatComboBox = QtWidgets.QComboBox(self.outputWidget)

        for timestampFormat in TIMESTAMP_FORMATS:
            self.timestampFormatComboBox.addItem(format(1.0, timestampFormat), timestampFormat)

        self.valueFormatComboBox = QtWidgets.QComboBox(self.outputWidget)

        for valueFormat in VALUE_FORMATS:
            self.valueFormatComboBox.addItem(format(1.0, valueFormat), valueFormat)

        outputWidgetLayout = QtWidgets.QFormLayout(self.outputWidget)
        outputWidgetLayout.addRow("Timestamp Format", self.timestampFormatComboBox)
        outputWidgetLayout.addRow("Value Format", self.valueFormatComboBox)

        self.tabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.outputWidget, "Output")

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)

    def timestampFormat(self) -> str:
        value = self.timestampFormatComboBox.currentData()
        return value if isinstance(value, str) else TIMESTAMP_FORMATS[1]

    def setTimestampFormat(self, value: str) -> None:
        """Select the timestamp format, falling back to the default if unknown."""
        index = self.timestampFormatComboBox.findData(value)
        if index < 0:
            index = 1  # default: TIMESTAMP_FORMATS[1]
        self.timestampFormatComboBox.setCurrentIndex(index)

    def valueFormat(self) -> str:
        value = self.valueFormatComboBox.currentData()
        return value if isinstance(value, str) else VALUE_FORMATS[0]

    def setValueFormat(self, value: str) -> None:
        """Select the value format, falling back to the default if unknown."""
        index = self.valueFormatComboBox.findData(value)
        if index < 0:
            index = 0  # default: VALUE_FORMATS[0]
        self.valueFormatComboBox.setCurrentIndex(index)

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        timestamp_format = safe_str(settings.value("writer/timestampFormat"), TIMESTAMP_FORMATS[1])
        self.setTimestampFormat(timestamp_format)
        value_format = safe_str(settings.value("writer/valueFormat"), VALUE_FORMATS[0])
        self.setValueFormat(value_format)

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.setValue("writer/timestampFormat", self.timestampFormat())
        settings.setValue("writer/valueFormat", self.valueFormat())
