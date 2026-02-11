from typing import Optional

from PyQt5 import QtCore, QtWidgets

from ..driver import driver_factory
from ..utils import open_resource


__all__ = ["ResourceWidget"]


class ResourceWidget(QtWidgets.QGroupBox):

    modelChanged = QtCore.pyqtSignal(str)
    resourceChanged = QtCore.pyqtSignal(str)
    terminationChanged = QtCore.pyqtSignal(str)
    timeoutChanged = QtCore.pyqtSignal(float)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Instrument")

        self.modelLabel = QtWidgets.QLabel("Model")

        self.modelComboBox = QtWidgets.QComboBox()
        self.modelComboBox.setStatusTip("Instrument model.")
        self.modelComboBox.currentTextChanged.connect(
            lambda text: self.modelChanged.emit(text)
        )

        self.resourceLabel = QtWidgets.QLabel("Resource")

        self.resourceLineEdit = QtWidgets.QLineEdit()
        self.resourceLineEdit.setStatusTip("Instrument resource GPIB number, IP and port or any valid VISA resource name.")
        self.resourceLineEdit.editingFinished.connect(
            lambda: self.resourceChanged.emit(self.resourceName())
        )

        self.terminationLabel = QtWidgets.QLabel("Termination")

        self.terminationComboBox = QtWidgets.QComboBox()
        self.terminationComboBox.setStatusTip("Read and write termination characters.")
        self.terminationComboBox.addItem("CR+LF", "\r\n")
        self.terminationComboBox.addItem("CR", "\r")
        self.terminationComboBox.addItem("LF", "\n")
        self.terminationComboBox.currentIndexChanged.connect(
            lambda index: self.terminationChanged.emit(self.terminationComboBox.itemData(index))
        )

        self.timeoutLabel = QtWidgets.QLabel("Timeout")

        self.timeoutSpinBox = QtWidgets.QDoubleSpinBox()
        self.timeoutSpinBox.setStatusTip("Timeout for communication in seconds.")
        self.timeoutSpinBox.setSuffix(" s")
        self.timeoutSpinBox.setRange(1, 60)
        self.timeoutSpinBox.setValue(4)
        self.timeoutSpinBox.setDecimals(2)
        self.timeoutSpinBox.valueChanged.connect(
            lambda value: self.timeoutChanged.emit(value)
        )

        self.testConntectionButton = QtWidgets.QPushButton(self)
        self.testConntectionButton.setText("&Test")
        self.testConntectionButton.setStatusTip("Test instrument connection.")
        self.testConntectionButton.setMaximumWidth(48)
        self.testConntectionButton.clicked.connect(self.testConntection)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.modelLabel, 0, 0, 1, 3)
        layout.addWidget(self.modelComboBox, 1, 0, 1, 3)
        layout.addWidget(self.resourceLabel, 2, 0, 1, 3)
        layout.addWidget(self.resourceLineEdit, 3, 0, 1, 3)
        layout.addWidget(self.terminationLabel, 4, 0, 1, 1)
        layout.addWidget(self.timeoutLabel, 4, 1, 1, 1)
        layout.addWidget(self.terminationComboBox, 5, 0, 1, 1)
        layout.addWidget(self.timeoutSpinBox, 5, 1, 1, 1)
        layout.addWidget(self.testConntectionButton, 5, 2, 1, 1)
        layout.setRowStretch(6, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)

    def setLocked(self, state: bool) -> None:
        self.modelComboBox.setEnabled(not state)
        self.resourceLineEdit.setEnabled(not state)
        self.terminationComboBox.setEnabled(not state)
        self.timeoutSpinBox.setEnabled(not state)
        self.testConntectionButton.setEnabled(not state)

    def model(self) -> str:
        return self.modelComboBox.currentText()

    def setModel(self, model: str) -> None:
        index = self.modelComboBox.findText(model)
        self.modelComboBox.setCurrentIndex(max(0, index))
        self.modelChanged.emit(self.modelComboBox.itemText(max(0, index)))

    def addModel(self, model: str) -> None:
        self.modelComboBox.addItem(model)

    def resourceName(self) -> str:
        return self.resourceLineEdit.text().strip()

    def setResourceName(self, resource: str) -> None:
        self.resourceLineEdit.setText(resource)

    def termination(self) -> str:
        return self.terminationComboBox.currentData()

    def setTermination(self, termination: str) -> None:
        index = self.terminationComboBox.findData(termination)
        self.terminationComboBox.setCurrentIndex(max(0, index))
        self.terminationChanged.emit(self.terminationComboBox.itemData(max(0, index)))

    def timeout(self) -> float:
        return self.timeoutSpinBox.value()

    def setTimeout(self, timeout: float) -> None:
        self.timeoutSpinBox.setValue(timeout)

    def openResource(self):
        return open_resource(self.resourceName(), self.termination(), self.timeout())

    def readIdentity(self) -> str:
        with self.openResource() as res:
            instr = driver_factory(self.model())(res)
            return instr.identity()

    @QtCore.pyqtSlot()
    def testConntection(self) -> None:
        try:
            identity = self.readIdentity()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Connection Test", format(exc))
        else:
            QtWidgets.QMessageBox.information(self, "Connection Test", format(identity))
