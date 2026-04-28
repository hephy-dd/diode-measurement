from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..utils import get_str, get_float

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

        self.output_widget = OutputWidget(self)
        self.misc_widget = MiscWidget(self)

        self.tab_widget = QtWidgets.QTabWidget(self)
        self.tab_widget.addTab(self.output_widget, "Output")
        self.tab_widget.addTab(self.misc_widget, "Misc")

        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        self.dialog_button_box.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        self.dialog_button_box.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )

        self.dialog_button_box.accepted.connect(self.accept)
        self.dialog_button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.dialog_button_box)

    def read_settings(self) -> None:
        self.output_widget.read_settings()
        self.misc_widget.read_settings()

    def write_settings(self) -> None:
        self.output_widget.write_settings()
        self.misc_widget.write_settings()


class OutputWidget(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.timestamp_format_combo_box = QtWidgets.QComboBox(self)

        for timestamp_format in TIMESTAMP_FORMATS:
            self.timestamp_format_combo_box.addItem(
                format(1.0, timestamp_format),
                timestamp_format,
            )

        self.value_format_combo_box = QtWidgets.QComboBox(self)

        for value_format in VALUE_FORMATS:
            self.value_format_combo_box.addItem(
                format(1.0, value_format),
                value_format,
            )

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("Timestamp Format", self.timestamp_format_combo_box)
        layout.addRow("Value Format", self.value_format_combo_box)

    def timestamp_format(self) -> str:
        value = self.timestamp_format_combo_box.currentData()
        return value if isinstance(value, str) else TIMESTAMP_FORMATS[1]

    def set_timestamp_format(self, timestamp_format: str) -> None:
        index = self.timestamp_format_combo_box.findData(timestamp_format)
        if index < 0:
            index = 1
        self.timestamp_format_combo_box.setCurrentIndex(index)

    def value_format(self) -> str:
        value = self.value_format_combo_box.currentData()
        return value if isinstance(value, str) else VALUE_FORMATS[0]

    def set_value_format(self, value_format: str) -> None:
        index = self.value_format_combo_box.findData(value_format)
        if index < 0:
            index = 0
        self.value_format_combo_box.setCurrentIndex(index)

    def read_settings(self) -> None:
        settings = QtCore.QSettings()

        timestamp_format = get_str(
            settings.value("writer/timestampFormat"),
            TIMESTAMP_FORMATS[1],
        )
        self.set_timestamp_format(timestamp_format)

        value_format = get_str(
            settings.value("writer/valueFormat"),
            VALUE_FORMATS[0],
        )
        self.set_value_format(value_format)

    def write_settings(self) -> None:
        settings = QtCore.QSettings()

        settings.setValue("writer/timestampFormat", self.timestamp_format())
        settings.setValue("writer/valueFormat", self.value_format())


class MiscWidget(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.discharge_timeout_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.discharge_timeout_spin_box.setRange(0.0, 360.0)
        self.discharge_timeout_spin_box.setSuffix(" s")
        self.discharge_timeout_spin_box.setDecimals(1)
        self.discharge_timeout_spin_box.setSingleStep(1.0)
        self.discharge_timeout_spin_box.setToolTip(
            "Sets the timeout for voltage discharge. "
            "The discharge waits until the source voltage is below the discharge threshold."
        )

        self.discharge_threshold_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.discharge_threshold_spin_box.setRange(0.0, 1_000_000.0)
        self.discharge_threshold_spin_box.setSuffix(" V")
        self.discharge_threshold_spin_box.setDecimals(3)
        self.discharge_threshold_spin_box.setSingleStep(0.1)
        self.discharge_threshold_spin_box.setToolTip(
            "Voltage threshold below which the source is considered discharged."
        )

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("Discharge timeout", self.discharge_timeout_spin_box)
        layout.addRow("Discharge threshold", self.discharge_threshold_spin_box)

        self.read_settings()

    def read_settings(self) -> None:
        settings = QtCore.QSettings()

        discharge_timeout = get_float(settings.value("misc/discharge_timeout"), 60.0)
        discharge_threshold = get_float(settings.value("misc/discharge_threshold"), 0.5)

        self.discharge_timeout_spin_box.setValue(discharge_timeout)
        self.discharge_threshold_spin_box.setValue(discharge_threshold)

    def write_settings(self) -> None:
        settings = QtCore.QSettings()

        settings.setValue(
            "misc/discharge_timeout",
            self.discharge_timeout_spin_box.value(),
        )
        settings.setValue(
            "misc/discharge_threshold",
            self.discharge_threshold_spin_box.value(),
        )
