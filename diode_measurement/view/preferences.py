from typing import Optional

from PyQt5 import QtCore, QtWidgets

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

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        super().__init__(parent)

        self.setWindowTitle("Preferences")
        self.setMinimumSize(320, 240)

        # Output Tab

        self.outputWidget = QtWidgets.QWidget(self)

        self.timestampFormatComboBox = QtWidgets.QComboBox(self)

        for timestampFormat in TIMESTAMP_FORMATS:
            self.timestampFormatComboBox.addItem(format(1.0, timestampFormat), timestampFormat)

        self.valueFormatComboBox = QtWidgets.QComboBox(self)

        for valueFormat in VALUE_FORMATS:
            self.valueFormatComboBox.addItem(format(1.0, valueFormat), valueFormat)

        outputWidgetLayout = QtWidgets.QFormLayout(self.outputWidget)
        outputWidgetLayout.addRow("Timestamp Format", self.timestampFormatComboBox)
        outputWidgetLayout.addRow("Value Format", self.valueFormatComboBox)

        self.tabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.outputWidget, "Output")

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        timestampFormat = settings.value("writer/timestampFormat", TIMESTAMP_FORMATS[1], str)
        index = self.timestampFormatComboBox.findData(timestampFormat)
        self.timestampFormatComboBox.setCurrentIndex(index)

        valueFormat = settings.value("writer/valueFormat", VALUE_FORMATS[0], str)
        index = self.valueFormatComboBox.findData(valueFormat)
        self.valueFormatComboBox.setCurrentIndex(index)

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()

        timestampFormat = self.timestampFormatComboBox.currentData() or TIMESTAMP_FORMATS[1]
        settings.setValue("writer/timestampFormat", timestampFormat)

        valueFormat = self.valueFormatComboBox.currentData() or VALUE_FORMATS[0]
        settings.setValue("writer/valueFormat", valueFormat)
