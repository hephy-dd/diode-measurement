import logging
from typing import Any, Mapping, Optional

from PySide6 import QtCore, QtWidgets

from .panel import InstrumentPanel
from .resource import ResourceWidget

__all__ = ["RoleWidget"]


class RoleWidget(QtWidgets.QWidget):
    def __init__(self, name: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._name: str = name
        self._resources: dict[str, Any] = {}  # TODO

        self.resource_widget = ResourceWidget(self)
        self.resource_widget.model_changed.connect(self.model_changed)

        self.stacked_widget = QtWidgets.QStackedWidget(self)

        self.restore_defaults_button = QtWidgets.QPushButton(self)
        self.restore_defaults_button.setText("Restore &Defaults")
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.resource_widget, 0, 0, 1, 1)
        layout.addWidget(self.stacked_widget, 0, 1, 1, 2)
        layout.addWidget(self.restore_defaults_button, 1, 2, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)

    def name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        self._name = name

    def model(self) -> str:
        return self.resource_widget.model()

    def set_model(self, model: str) -> None:
        self.resource_widget.set_model(model)

    def resource_name(self) -> str:
        return self.resource_widget.resource_name()

    def set_resource_name(self, resource_name: str) -> None:
        self.resource_widget.set_resource_name(resource_name)

    def termination(self) -> str:
        return self.resource_widget.termination()

    def set_termination(self, termination: str) -> None:
        self.resource_widget.set_termination(termination)

    def timeout(self) -> float:
        return self.resource_widget.timeout()

    def set_timeout(self, timeout: float) -> None:
        self.resource_widget.set_timeout(timeout)

    def resources(self) -> dict[str, Any]:
        return self._resources.copy()

    def set_resources(self, resources: Mapping[str, Any]) -> None:
        self._resources.update(resources)

    def sync_current_resource(self) -> None:
        widget = self.stacked_widget.currentWidget()
        if isinstance(widget, InstrumentPanel):
            model = widget.model()
            resource = {
                "resource_name": self.resource_name(),
                "termination": self.termination(),
                "timeout": self.timeout(),
            }
            self._resources.setdefault(model, {}).update(resource)

    def current_config(self) -> dict[str, Any]:
        widget = self.stacked_widget.currentWidget()
        if isinstance(widget, InstrumentPanel):
            return widget.config()
        return {}

    def configs(self) -> dict[str, Any]:
        configs = {}
        for widget in self.instrument_panels():
            configs[widget.model()] = widget.config()
        return configs

    def set_configs(self, configs: Mapping[str, Mapping[str, Any]]) -> None:
        for widget in self.instrument_panels():
            widget.apply_config(configs.get(widget.model(), {}))

    def set_locked(self, state: bool) -> None:
        self.resource_widget.set_locked(state)
        for widget in self.instrument_panels():
            widget.set_locked(state)
        self.restore_defaults_button.setEnabled(not state)

    def add_instrument_panel(self, widget: InstrumentPanel) -> None:
        self.resource_widget.add_model(widget.model())
        self.stacked_widget.addWidget(widget)

    def instrument_panels(self) -> list[InstrumentPanel]:
        """Return list of registered instrument panels."""
        widgets = []
        for index in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(index)
            if isinstance(widget, InstrumentPanel):
                widgets.append(widget)
        return widgets

    def find_instrument_panel(self, model: str) -> Optional[InstrumentPanel]:
        for widget in self.instrument_panels():
            if model == widget.model():
                return widget
        return None

    @QtCore.Slot(str)
    def model_changed(self, model: str) -> None:
        self.sync_current_resource()
        widget = self.find_instrument_panel(model)
        if isinstance(widget, InstrumentPanel):
            try:
                resource = self._resources.get(model, {})
                self.set_resource_name(resource.get("resource_name", ""))
                self.set_termination(resource.get("termination", "\r\n"))
                self.set_timeout(resource.get("timeout", 8.0))
            except Exception as exc:
                logging.exception(exc)
            self.stacked_widget.setCurrentWidget(widget)
            self.stacked_widget.show()
        else:
            self.stacked_widget.hide()

    @QtCore.Slot()
    def restore_defaults(self) -> None:
        widget = self.stacked_widget.currentWidget()
        if isinstance(widget, InstrumentPanel):
            widget.restore_defaults()
