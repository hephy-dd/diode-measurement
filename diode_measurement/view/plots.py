import os
import time
from typing import Optional

from PySide6 import QtCharts, QtCore, QtWidgets

from ..utils import auto_scale

__all__ = ["IVPlotWidget", "ItPlotWidget", "CVPlotWidget", "CV2PlotWidget"]


def limit_range(minimum: float, maximum: float, value: float) -> tuple[float, float]:
    """Limit range to a minimum value."""
    diff = abs(maximum - minimum)
    if diff < value:
        maximum += (value * 0.5) - (diff * 0.5)
        minimum -= (value * 0.5) - (diff * 0.5)
    return minimum, maximum


class DynamicValueAxis(QtCharts.QValueAxis):
    def __init__(self, axis: QtCharts.QValueAxis, unit: str) -> None:
        super().__init__(axis)
        self._axis = axis
        self._unit = unit
        self.setRange(axis.min(), axis.max())
        axis.rangeChanged.connect(self.setRange)
        axis.hide()

    def setRange(self, minimum: float, maximum: float) -> None:
        # Get best matching scale/prefix
        base = max(abs(minimum), abs(maximum))
        scale, prefix, _ = auto_scale(base)
        # Update labels prefix
        unit = self._unit
        self.setLabelFormat(f"%G {prefix}{unit}")
        # Scale limits
        minimum *= 1 / scale
        maximum *= 1 / scale
        # Update axis range
        super().setRange(minimum, maximum)


class LimitsAggregator(QtCore.QObject):
    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._minimum: float = 0.0
        self._maximum: float = 0.0
        self._valid: bool = False

    def is_valid(self) -> bool:
        return self._valid

    def clear(self) -> None:
        self._minimum = 0.0
        self._maximum = 0.0
        self._valid = False

    def append(self, value: float) -> None:
        if self._valid:
            self._minimum = min(self.minimum(), value)
            self._maximum = max(self.maximum(), value)
        else:
            self._minimum = value
            self._maximum = value
        self._valid = True

    def minimum(self) -> float:
        return self._minimum

    def maximum(self) -> float:
        return self._maximum


class PlotToolButton(QtWidgets.QPushButton):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)


class PlotWidget(QtCharts.QChartView):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        chart = QtCharts.QChart()
        chart.setMargins(QtCore.QMargins(4, 4, 4, 4))
        chart.layout().setContentsMargins(0, 0, 0, 0)
        chart.legend().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setChart(chart)

        self.setRubberBand(QtCharts.QChartView.RubberBand.RectangleRubberBand)

        self.toolbar = QtWidgets.QWidget()
        self.toolbar.setObjectName("toolbar")
        self.toolbar.setStyleSheet("QWidget#toolbar{ background: transparent; }")
        proxy = self.scene().addWidget(self.toolbar)
        proxy.setPos(2, 2)
        proxy.setZValue(10000)
        # Set parent after adding widget to scene to trigger
        # widgets destruction on close of chart view.
        self.toolbar.setParent(self)
        self.toolbar.hide()

        self.reset_button = PlotToolButton()
        self.reset_button.setText("R")
        self.reset_button.setToolTip("Reset plot")
        self.reset_button.setStatusTip("Reset plot")
        self.reset_button.clicked.connect(self.reset)

        self.save_as_button = PlotToolButton()
        self.save_as_button.setText("S")
        self.save_as_button.setToolTip("Save plot as PNG")
        self.save_as_button.setStatusTip("Save plot as PNG")
        self.save_as_button.clicked.connect(self.save_as)

        layout = QtWidgets.QVBoxLayout(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.reset_button)
        layout.addWidget(self.save_as_button)

        self._series: dict[str, QtCharts.QXYSeries] = {}

    def mouseMoveEvent(self, event) -> None:
        self.toolbar.setVisible(self.underMouse())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.toolbar.hide()
        super().leaveEvent(event)

    def reset(self) -> None:
        self.chart().zoomReset()

    @QtCore.Slot()
    def save_as(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save File", ".", "PNG Image (*.png);;"
        )
        if filename:
            if os.path.splitext(filename)[1] != ".png":
                filename = f"{filename}.png"
            try:
                self.grab().save(filename)
            except Exception:
                pass

    def clear(self) -> None:
        for series in self.chart().series():
            if isinstance(series, QtCharts.QXYSeries):
                series.clear()

    def is_reverse(self) -> bool:
        for series in self.chart().series():
            if isinstance(series, QtCharts.QXYSeries):
                if series.count():
                    if series.at(series.count() - 1).x() < series.at(0).x():
                        return True
        return False

    def replace_series(self, name: str, points: list[QtCore.QPointF]) -> None:
        series = self._series.get(name)
        if isinstance(series, QtCharts.QXYSeries):
            series.replace(points)


class IVPlotWidget(PlotWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("I vs. V")

        self.smu_series = QtCharts.QLineSeries()
        self.smu_series.setName("SMU")
        self.smu_series.setColor(QtCore.Qt.GlobalColor.red)
        self.smu_series.setPointsVisible(True)
        self.chart().addSeries(self.smu_series)

        self.smu2_series = QtCharts.QLineSeries()
        self.smu2_series.setName("SMU2")
        self.smu2_series.setColor(QtCore.Qt.GlobalColor.darkRed)
        self.smu2_series.setPointsVisible(True)
        self.chart().addSeries(self.smu2_series)

        self.elm_series = QtCharts.QLineSeries()
        self.elm_series.setName("ELM")
        self.elm_series.setColor(QtCore.Qt.GlobalColor.blue)
        self.elm_series.setPointsVisible(True)
        self.chart().addSeries(self.elm_series)

        self.elm2_series = QtCharts.QLineSeries()
        self.elm2_series.setName("ELM2")
        self.elm2_series.setColor(QtCore.Qt.GlobalColor.darkBlue)
        self.elm2_series.setPointsVisible(True)
        self.chart().addSeries(self.elm2_series)

        self.i_axis = QtCharts.QValueAxis()
        self.chart().addAxis(self.i_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.smu_series.attachAxis(self.i_axis)
        self.smu2_series.attachAxis(self.i_axis)
        self.elm_series.attachAxis(self.i_axis)
        self.elm2_series.attachAxis(self.i_axis)

        self.i_dynamic_axis = DynamicValueAxis(self.i_axis, "A")
        self.i_dynamic_axis.setTitleText("Current")
        self.i_dynamic_axis.setTickCount(9)
        self.chart().addAxis(self.i_dynamic_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.i_axis.setRange(0, 200e-9)

        self.v_axis = QtCharts.QValueAxis()
        self.v_axis.setTitleText("Voltage")
        self.v_axis.setLabelFormat("%g V")
        self.v_axis.setRange(-100, +100)
        self.chart().addAxis(self.v_axis, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.smu_series.attachAxis(self.v_axis)
        self.smu2_series.attachAxis(self.v_axis)
        self.elm_series.attachAxis(self.v_axis)
        self.elm2_series.attachAxis(self.v_axis)

        self.i_limits = LimitsAggregator(self)
        self.v_limits = LimitsAggregator(self)

        self._series["smu"] = self.smu_series
        self._series["smu2"] = self.smu2_series
        self._series["elm"] = self.elm_series
        self._series["elm2"] = self.elm2_series

    def fit_v_axis(self) -> None:
        self.v_axis.setReverse(self.is_reverse())
        if self.v_limits.is_valid():
            minimum = self.v_limits.minimum()
            maximum = self.v_limits.maximum()
        else:
            minimum = 0
            maximum = 100
        self.v_axis.setRange(minimum, maximum)

    def fit_i_axis(self) -> None:
        if self.i_limits.is_valid():
            minimum = self.i_limits.minimum()
            maximum = self.i_limits.maximum()
        else:
            minimum = 0
            maximum = 200e-9
        # HACK limit axis range to 1 pA minimum
        minimum, maximum = limit_range(minimum, maximum, 2e-12)
        self.i_axis.setRange(minimum, maximum)
        self.i_axis.applyNiceNumbers()

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        self.fit_v_axis()
        self.fit_i_axis()

    def clear(self) -> None:
        super().clear()
        self.i_limits.clear()
        self.v_limits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(x, y)
            self.i_limits.append(y)
            self.v_limits.append(x)
            self.fit()


class ItPlotWidget(PlotWidget):
    MAX_POINTS: int = 60 * 60 * 24

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("I vs. t")

        self.smu_series = QtCharts.QLineSeries()
        self.smu_series.setName("SMU")
        self.smu_series.setColor(QtCore.Qt.GlobalColor.red)
        self.smu_series.setPointsVisible(True)
        self.chart().addSeries(self.smu_series)

        self.smu2_series = QtCharts.QLineSeries()
        self.smu2_series.setName("SMU2")
        self.smu2_series.setColor(QtCore.Qt.GlobalColor.darkRed)
        self.smu2_series.setPointsVisible(True)
        self.chart().addSeries(self.smu2_series)

        self.elm_series = QtCharts.QLineSeries()
        self.elm_series.setName("ELM")
        self.elm_series.setColor(QtCore.Qt.GlobalColor.blue)
        self.elm_series.setPointsVisible(True)
        self.chart().addSeries(self.elm_series)

        self.elm2_series = QtCharts.QLineSeries()
        self.elm2_series.setName("ELM2")
        self.elm2_series.setColor(QtCore.Qt.GlobalColor.darkBlue)
        self.elm2_series.setPointsVisible(True)
        self.chart().addSeries(self.elm2_series)

        self.i_axis = QtCharts.QValueAxis()
        self.i_axis.hide()
        self.chart().addAxis(self.i_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.smu_series.attachAxis(self.i_axis)
        self.smu2_series.attachAxis(self.i_axis)
        self.elm_series.attachAxis(self.i_axis)
        self.elm2_series.attachAxis(self.i_axis)

        self.i_dynamic_axis = DynamicValueAxis(self.i_axis, "A")
        self.i_dynamic_axis.setTitleText("Current")
        self.i_dynamic_axis.setTickCount(9)
        self.chart().addAxis(self.i_dynamic_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.i_axis.setRange(0, 200e-9)

        self.tAxis = QtCharts.QDateTimeAxis()
        self.tAxis.setTitleText("Time")
        self.tAxis.setTickCount(3)
        self.chart().addAxis(self.tAxis, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.smu_series.attachAxis(self.tAxis)
        self.smu2_series.attachAxis(self.tAxis)
        self.elm_series.attachAxis(self.tAxis)
        self.elm2_series.attachAxis(self.tAxis)

        self.i_limits = LimitsAggregator(self)
        self.t_limits = LimitsAggregator(self)

        self._series["smu"] = self.smu_series
        self._series["smu2"] = self.smu2_series
        self._series["elm"] = self.elm_series
        self._series["elm2"] = self.elm2_series

    def fitTAxis(self) -> None:
        if self.t_limits.is_valid():
            minimum = self.t_limits.minimum()
            maximum = self.t_limits.maximum()
        else:
            t = time.time()
            minimum = t - 60
            maximum = t
        t0 = QtCore.QDateTime.fromMSecsSinceEpoch(int(minimum * 1e3))
        t1 = QtCore.QDateTime.fromMSecsSinceEpoch(int(maximum * 1e3))
        self.tAxis.setRange(t0, t1)

    def fit_i_axis(self) -> None:
        if self.i_limits.is_valid():
            minimum = self.i_limits.minimum()
            maximum = self.i_limits.maximum()
        else:
            minimum = 0
            maximum = 200e-9
        # HACK limit axis range to 1 pA minimum
        minimum, maximum = limit_range(minimum, maximum, 2e-12)
        self.i_axis.setRange(minimum, maximum)
        self.i_axis.applyNiceNumbers()

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        self.fitTAxis()
        self.fit_i_axis()

    def clear(self) -> None:
        super().clear()
        self.i_limits.clear()
        self.t_limits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(QtCore.QPointF(x * 1e3, y))
            if series.count() > self.MAX_POINTS:
                series.remove(0)
            self.i_limits.append(y)
            self.t_limits.append(x)
            self.fit()


class CVPlotWidget(PlotWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("C vs. V")

        self.lcr_series = QtCharts.QLineSeries()
        self.lcr_series.setName("LCR")
        self.lcr_series.setColor(QtCore.Qt.GlobalColor.magenta)
        self.chart().addSeries(self.lcr_series)

        self.c_axis = QtCharts.QValueAxis()
        self.chart().addAxis(self.c_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lcr_series.attachAxis(self.c_axis)

        self.c_dynamic_axis = DynamicValueAxis(self.c_axis, "F")
        self.c_dynamic_axis.setTitleText("Capacitance")
        self.c_dynamic_axis.setTickCount(9)
        self.chart().addAxis(self.c_dynamic_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.c_axis.setRange(0, 200e-9)

        self.v_axis = QtCharts.QValueAxis()
        self.v_axis.setTitleText("Voltage")
        self.v_axis.setLabelFormat("%g V")
        self.v_axis.setRange(0, 200)
        self.v_axis.setTickCount(9)
        self.chart().addAxis(self.v_axis, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.lcr_series.attachAxis(self.v_axis)

        self.c_limits = LimitsAggregator(self)
        self.v_limits = LimitsAggregator(self)

        self._series["lcr"] = self.lcr_series

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        minimum: float = self.v_limits.minimum()
        maximum: float = self.v_limits.maximum()
        self.v_axis.setReverse(minimum > maximum)
        minimum, maximum = sorted((minimum, maximum))
        self.v_axis.setRange(minimum, maximum)
        # HACK limit axis range to 1 pF minimum
        minimum, maximum = limit_range(
            self.c_limits.minimum(), self.c_limits.maximum(), 2e-12
        )
        self.c_axis.setRange(minimum, maximum)
        self.c_axis.applyNiceNumbers()

    def clear(self) -> None:
        super().clear()
        self.c_limits.clear()
        self.v_limits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(x, y)
            self.c_limits.append(y)
            self.v_limits.append(x)
            self.fit()


class CV2PlotWidget(PlotWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("1/C^2 vs. V")

        self.lcr_series = QtCharts.QLineSeries()
        self.lcr_series.setName("LCR")
        self.lcr_series.setColor(QtCore.Qt.GlobalColor.magenta)
        self.chart().addSeries(self.lcr_series)

        self.c_axis = QtCharts.QValueAxis()
        self.c_axis.setTitleText("Capacitance [1/F^2]")
        self.c_axis.setLabelFormat("%g")
        self.c_axis.setRange(0, 1 / 200**2)
        self.c_axis.setTickCount(9)
        self.chart().addAxis(self.c_axis, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lcr_series.attachAxis(self.c_axis)

        self.v_axis = QtCharts.QValueAxis()
        self.v_axis.setTitleText("Voltage")
        self.v_axis.setLabelFormat("%g V")
        self.v_axis.setRange(0, 200)
        self.v_axis.setTickCount(9)
        self.chart().addAxis(self.v_axis, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.lcr_series.attachAxis(self.v_axis)

        self.c_limits = LimitsAggregator(self)
        self.v_limits = LimitsAggregator(self)

        self._series["lcr"] = self.lcr_series

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        minimum = self.v_limits.minimum()
        maximum = self.v_limits.maximum()
        self.v_axis.setReverse(minimum > maximum)
        minimum, maximum = sorted((minimum, maximum))
        self.v_axis.setRange(minimum, maximum)
        self.c_axis.setRange(self.c_limits.minimum(), self.c_limits.maximum())
        self.c_axis.applyNiceNumbers()
        self.c_axis.setTickCount(9)

    def clear(self) -> None:
        super().clear()
        self.c_limits.clear()
        self.v_limits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(x, y)
            self.c_limits.append(y)
            self.v_limits.append(x)
            self.fit()
