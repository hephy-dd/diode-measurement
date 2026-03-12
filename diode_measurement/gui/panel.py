from typing import Any, Callable, Mapping, Optional, Protocol

from PySide6 import QtWidgets

from .metric import MetricWidget


class Parameter(Protocol):
    def value(self) -> Any: ...
    def setValue(self, value: Any) -> None: ...


class WidgetParameter:
    def __init__(self, widget: QtWidgets.QWidget) -> None:
        self._widget = widget

    def value(self) -> Any:
        widget = self._widget
        if isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        elif isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QComboBox):
            return widget.currentData()
        elif isinstance(widget, MetricWidget):
            return widget.value()
        raise TypeError(f"Invalid widget type: {widget!r}")

    def setValue(self, value: Any) -> None:
        widget = self._widget
        if isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(value)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(value)
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(value)
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(value)
        elif isinstance(widget, QtWidgets.QComboBox):
            index = widget.findData(value)
            widget.setCurrentIndex(index)
        elif isinstance(widget, MetricWidget):
            widget.setValue(value)
        else:
            raise TypeError(f"Invalid widget type: {widget!r}")


class MethodParameter:
    def __init__(
        self, getter: Callable[[], Any], setter: Callable[[Any], None]
    ) -> None:
        self._getter = getter
        self._setter = setter

    def value(self) -> Any:
        return self._getter()

    def setValue(self, value: Any) -> None:
        self._setter(value)


class InstrumentPanel(QtWidgets.QWidget):
    def __init__(self, model: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._parameters: dict[str, Parameter] = {}
        self._model = model

    def model(self) -> str:
        return self._model

    def restore_defaults(self) -> None: ...

    def set_locked(self, state: bool) -> None: ...

    def bind_parameter(self, key: str, parameter: Parameter) -> None:
        if key in self._parameters:
            raise KeyError(f"Parameter already exists: {key!r}")
        self._parameters[key] = parameter

    def config(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        for key, parameter in self._parameters.items():
            config[key] = parameter.value()
        return config

    def apply_config(self, config: Mapping[str, Any]) -> None:
        for key, value in config.items():
            parameter = self._parameters.get(key)
            if parameter is None:
                raise KeyError(f"No such parameter: {key!r}")
            parameter.setValue(value)
