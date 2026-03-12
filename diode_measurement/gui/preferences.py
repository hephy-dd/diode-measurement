from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..utils import get_str

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

        self.output_widget = QtWidgets.QWidget(self)

        self.timestamp_format_combo_box = QtWidgets.QComboBox(self.output_widget)

        for timestamp_format in TIMESTAMP_FORMATS:
            self.timestamp_format_combo_box.addItem(
                format(1.0, timestamp_format), timestamp_format
            )

        self.value_format_combo_box = QtWidgets.QComboBox(self.output_widget)

        for value_format in VALUE_FORMATS:
            self.value_format_combo_box.addItem(format(1.0, value_format), value_format)

        output_widget_layout = QtWidgets.QFormLayout(self.output_widget)
        output_widget_layout.addRow("Timestamp Format", self.timestamp_format_combo_box)
        output_widget_layout.addRow("Value Format", self.value_format_combo_box)

        self.tab_widget = QtWidgets.QTabWidget(self)
        self.tab_widget.addTab(self.output_widget, "Output")

        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        self.dialog_button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.dialog_button_box.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.dialog_button_box.accepted.connect(self.accept)
        self.dialog_button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.dialog_button_box)

    def timestamp_format(self) -> str:
        value = self.timestamp_format_combo_box.currentData()
        return value if isinstance(value, str) else TIMESTAMP_FORMATS[1]

    def set_timestamp_format(self, timestamp_format: str) -> None:
        """Select the timestamp format, falling back to the default if unknown."""
        index = self.timestamp_format_combo_box.findData(timestamp_format)
        if index < 0:
            index = 1  # default: TIMESTAMP_FORMATS[1]
        self.timestamp_format_combo_box.setCurrentIndex(index)

    def valueFormat(self) -> str:
        value = self.value_format_combo_box.currentData()
        return value if isinstance(value, str) else VALUE_FORMATS[0]

    def set_value_format(self, value_format: str) -> None:
        """Select the value format, falling back to the default if unknown."""
        index = self.value_format_combo_box.findData(value_format)
        if index < 0:
            index = 0  # default: VALUE_FORMATS[0]
        self.value_format_combo_box.setCurrentIndex(index)

    def read_settings(self) -> None:
        settings = QtCore.QSettings()
        timestamp_format = get_str(
            settings.value("writer/timestampFormat"), TIMESTAMP_FORMATS[1]
        )
        self.set_timestamp_format(timestamp_format)
        value_format = get_str(settings.value("writer/valueFormat"), VALUE_FORMATS[0])
        self.set_value_format(value_format)

    def write_settings(self) -> None:
        settings = QtCore.QSettings()
        settings.setValue("writer/timestampFormat", self.timestamp_format())
        settings.setValue("writer/valueFormat", self.valueFormat())
