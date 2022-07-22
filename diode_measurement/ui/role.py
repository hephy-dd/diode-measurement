from typing import Any, Dict, List, Optional

from PyQt5 import QtWidgets

from .panels import InstrumentPanel
from .resource import ResourceWidget

__all__ = ["RoleWidget"]


class RoleWidget(QtWidgets.QWidget):

    def __init__(self, name, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setName(name)

        self.resourceWidget = ResourceWidget(self)
        self.resourceWidget.modelChanged.connect(self.modelChanged)

        self.stackedWidget = QtWidgets.QStackedWidget(self)

        self.restoreDefaultsButton = QtWidgets.QPushButton(self)
        self.restoreDefaultsButton.setText("Restore &Defaults")
        self.restoreDefaultsButton.clicked.connect(self.restoreDefaults)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.resourceWidget, 0, 0, 1, 1)
        layout.addWidget(self.stackedWidget, 0, 1, 1, 2)
        layout.addWidget(self.restoreDefaultsButton, 1, 2, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)

    def name(self) -> str:
        return self.property("name")

    def setName(self, name: str) -> None:
        self.setProperty("name", name)

    def model(self) -> str:
        return self.resourceWidget.model()

    def setModel(self, model: str) -> None:
        self.resourceWidget.setModel(model)

    def resourceName(self) -> str:
        return self.resourceWidget.resourceName()

    def setResourceName(self, resource: str) -> None:
        self.resourceWidget.setResourceName(resource)

    def termination(self) -> str:
        return self.resourceWidget.termination()

    def setTermination(self, termination: str) -> None:
        self.resourceWidget.setTermination(termination)

    def timeout(self) -> float:
        return self.resourceWidget.timeout()

    def setTimeout(self, timeout: float) -> None:
        self.resourceWidget.setTimeout(timeout)

    def config(self) -> Dict[str, Any]:
        config = {}
        for widget in self.instrumentPanels():
            config[widget.model()] = widget.config()
        return config

    def setConfig(self, config: Dict[str, Dict[str, Any]]) -> None:
        for widget in self.instrumentPanels():
            widget.setConfig(config.get(widget.model(), {}))

    def setLocked(self, state: bool) -> None:
        self.resourceWidget.setLocked(state)
        for widget in self.instrumentPanels():
            widget.setLocked(state)
        self.restoreDefaultsButton.setEnabled(not state)

    def addInstrumentPanel(self, widget: InstrumentPanel) -> None:
        self.resourceWidget.addModel(widget.model())
        self.stackedWidget.addWidget(widget)

    def instrumentPanels(self) -> List[InstrumentPanel]:
        """Return list of registered instrument panels."""
        widgets = []
        for index in range(self.stackedWidget.count()):
            widget = self.stackedWidget.widget(index)
            if isinstance(widget, InstrumentPanel):
                widgets.append(widget)
        return widgets

    def findInstrumentPanel(self, model: str) -> Optional[InstrumentPanel]:
        for widget in self.instrumentPanels():
            if model == widget.model():
                return widget
        return None

    def modelChanged(self, model: str) -> None:
        widget = self.findInstrumentPanel(model)
        if widget is None:
            self.stackedWidget.hide()
        else:
            self.stackedWidget.setCurrentWidget(widget)
            self.stackedWidget.show()

    def restoreDefaults(self) -> None:
        widget = self.stackedWidget.currentWidget()
        if isinstance(widget, InstrumentPanel):
            widget.restoreDefaults()
