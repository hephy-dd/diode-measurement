import logging
from typing import Any, Optional

from PyQt5 import QtWidgets

from .panels import InstrumentPanel
from .resource import ResourceWidget

__all__ = ["RoleWidget"]


class RoleWidget(QtWidgets.QWidget):

    def __init__(self, name, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName(name)

        self._resources: dict[str, Any] = {}  # TODO

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

    def resources(self) -> dict[str, Any]:
        return self._resources.copy()

    def setResources(self, resources: dict[str, Any]) -> None:
        self._resources.update(resources)

    def syncCurrentResource(self) -> None:
        widget = self.stackedWidget.currentWidget()
        if isinstance(widget, InstrumentPanel):
            model = widget.model()
            resource = {
                "resource_name": self.resourceName(),
                "termination": self.termination(),
                "timeout": self.timeout(),
            }
            self._resources.setdefault(model, {}).update(resource)

    def currentConfig(self) -> dict[str, Any]:
        widget = self.stackedWidget.currentWidget()
        if isinstance(widget, InstrumentPanel):
            return widget.config()
        return {}

    def configs(self) -> dict[str, Any]:
        configs = {}
        for widget in self.instrumentPanels():
            configs[widget.model()] = widget.config()
        return configs

    def setConfigs(self, configs: dict[str, dict[str, Any]]) -> None:
        for widget in self.instrumentPanels():
            widget.setConfig(configs.get(widget.model(), {}))

    def setLocked(self, state: bool) -> None:
        self.resourceWidget.setLocked(state)
        for widget in self.instrumentPanels():
            widget.setLocked(state)
        self.restoreDefaultsButton.setEnabled(not state)

    def addInstrumentPanel(self, widget: InstrumentPanel) -> None:
        self.resourceWidget.addModel(widget.model())
        self.stackedWidget.addWidget(widget)

    def instrumentPanels(self) -> list[InstrumentPanel]:
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
        self.syncCurrentResource()
        widget = self.findInstrumentPanel(model)
        if isinstance(widget, InstrumentPanel):
            try:
                resource = self._resources.get(model, {})
                self.setResourceName(resource.get("resource_name", ""))
                self.setTermination(resource.get("termination", "\r\n"))
                self.setTimeout(resource.get("timeout", 8.0))
            except Exception as exc:
                logging.exception(exc)
            self.stackedWidget.setCurrentWidget(widget)
            self.stackedWidget.show()
        else:
            self.stackedWidget.hide()

    def restoreDefaults(self) -> None:
        widget = self.stackedWidget.currentWidget()
        if isinstance(widget, InstrumentPanel):
            widget.restoreDefaults()
