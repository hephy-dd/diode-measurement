import os
import time
from typing import Optional

from PyQt5 import QtChart, QtCore, QtWidgets

from ..utils import auto_scale

__all__ = [
    "IVPlotWidget",
    "ItPlotWidget",
    "CVPlotWidget",
    "CV2PlotWidget"
]


def limitRange(minimum: float, maximum: float, value: float) -> tuple[float, float]:
    """Limit range to a minimum value."""
    diff = abs(maximum - minimum)
    if diff < value:
        maximum += (value * 0.5) - (diff * 0.5)
        minimum -= (value * 0.5) - (diff * 0.5)
    return minimum, maximum


class DynamicValueAxis(QtChart.QValueAxis):
    def __init__(self, axis: QtChart.QValueAxis, unit: str) -> None:
        super().__init__(axis)
        self.setProperty("axis", axis)
        self.setUnit(unit)
        self.setRange(axis.min(), axis.max())
        axis.rangeChanged.connect(self.setRange)
        axis.hide()

    def axis(self) -> QtChart.QValueAxis:
        return self.property("axis")

    def unit(self) -> str:
        return self.property("unit")

    def setUnit(self, unit: str) -> None:
        self.setProperty("unit", unit)

    def setRange(self, minimum: float, maximum: float) -> None:
        # Get best matching scale/prefix
        base = max(abs(minimum), abs(maximum))
        scale, prefix, _ = auto_scale(base)
        # Update labels prefix
        unit = self.unit()
        self.setLabelFormat(f"%G {prefix}{unit}")
        # Scale limits
        minimum *= 1 / scale
        maximum *= 1 / scale
        # Update axis range
        super().setRange(minimum, maximum)


class LimitsAggregator(QtCore.QObject):
    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._minimum: float = 0.
        self._maximum: float = 0.
        self._valid: bool = False

    def isValid(self) -> bool:
        return self._valid

    def clear(self) -> None:
        self._minimum = 0.
        self._maximum = 0.
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


class PlotWidget(QtChart.QChartView):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        chart = QtChart.QChart()
        chart.setMargins(QtCore.QMargins(4, 4, 4, 4))
        chart.layout().setContentsMargins(0, 0, 0, 0)
        chart.legend().setAlignment(QtCore.Qt.AlignRight)
        self.setChart(chart)

        self.setRubberBand(QtChart.QChartView.RectangleRubberBand)

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

        self.resetButton = PlotToolButton()
        self.resetButton.setText("R")
        self.resetButton.setToolTip("Reset plot")
        self.resetButton.setStatusTip("Reset plot")
        self.resetButton.clicked.connect(self.reset)

        self.saveAsButton = PlotToolButton()
        self.saveAsButton.setText("S")
        self.saveAsButton.setToolTip("Save plot as PNG")
        self.saveAsButton.setStatusTip("Save plot as PNG")
        self.saveAsButton.clicked.connect(self.saveAs)

        layout = QtWidgets.QVBoxLayout(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.resetButton)
        layout.addWidget(self.saveAsButton)

        self._series: dict[str, QtChart.QXYSeries] = {}

    def mouseMoveEvent(self, event) -> None:
        self.toolbar.setVisible(self.underMouse())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.toolbar.hide()
        super().leaveEvent(event)

    def reset(self) -> None:
        self.chart().zoomReset()

    def saveAs(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save File",
            ".",
            "PNG Image (*.png);;"
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
            if isinstance(series, QtChart.QXYSeries):
                series.clear()

    def isReverse(self) -> bool:
        for series in self.chart().series():
            if isinstance(series, QtChart.QXYSeries):
                if series.count():
                    if series.at(series.count() - 1).x() < series.at(0).x():
                        return True
        return False

    def replace_series(self, name: str, points: list[QtCore.QPointF]) -> None:
        series = self._series.get(name)
        if isinstance(series, QtChart.QXYSeries):
            series.replace(points)


class IVPlotWidget(PlotWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("I vs. V")

        self.smuSeries = QtChart.QLineSeries()
        self.smuSeries.setName("SMU")
        self.smuSeries.setColor(QtCore.Qt.red)
        self.smuSeries.setPointsVisible(True)
        self.chart().addSeries(self.smuSeries)

        self.smu2Series = QtChart.QLineSeries()
        self.smu2Series.setName("SMU2")
        self.smu2Series.setColor(QtCore.Qt.darkRed)
        self.smu2Series.setPointsVisible(True)
        self.chart().addSeries(self.smu2Series)

        self.elmSeries = QtChart.QLineSeries()
        self.elmSeries.setName("ELM")
        self.elmSeries.setColor(QtCore.Qt.blue)
        self.elmSeries.setPointsVisible(True)
        self.chart().addSeries(self.elmSeries)

        self.elm2Series = QtChart.QLineSeries()
        self.elm2Series.setName("ELM2")
        self.elm2Series.setColor(QtCore.Qt.darkBlue)
        self.elm2Series.setPointsVisible(True)
        self.chart().addSeries(self.elm2Series)

        self.iAxis = QtChart.QValueAxis()
        self.chart().addAxis(self.iAxis, QtCore.Qt.AlignLeft)
        self.smuSeries.attachAxis(self.iAxis)
        self.smu2Series.attachAxis(self.iAxis)
        self.elmSeries.attachAxis(self.iAxis)
        self.elm2Series.attachAxis(self.iAxis)

        self.iDynamicAxis = DynamicValueAxis(self.iAxis, "A")
        self.iDynamicAxis.setTitleText("Current")
        self.iDynamicAxis.setTickCount(9)
        self.chart().addAxis(self.iDynamicAxis, QtCore.Qt.AlignLeft)
        self.iAxis.setRange(0, 200e-9)

        self.vAxis = QtChart.QValueAxis()
        self.vAxis.setTitleText("Voltage")
        self.vAxis.setLabelFormat("%g V")
        self.vAxis.setRange(-100, +100)
        self.chart().addAxis(self.vAxis, QtCore.Qt.AlignBottom)
        self.smuSeries.attachAxis(self.vAxis)
        self.smu2Series.attachAxis(self.vAxis)
        self.elmSeries.attachAxis(self.vAxis)
        self.elm2Series.attachAxis(self.vAxis)

        self.iLimits = LimitsAggregator(self)
        self.vLimits = LimitsAggregator(self)

        self._series["smu"] = self.smuSeries
        self._series["smu2"] = self.smu2Series
        self._series["elm"] = self.elmSeries
        self._series["elm2"] = self.elm2Series

    def fitVAxis(self) -> None:
        self.vAxis.setReverse(self.isReverse())
        if self.vLimits.isValid():
            minimum = self.vLimits.minimum()
            maximum = self.vLimits.maximum()
        else:
            minimum = 0
            maximum = 100
        self.vAxis.setRange(minimum, maximum)

    def fitIAxis(self) -> None:
        if self.iLimits.isValid():
            minimum = self.iLimits.minimum()
            maximum = self.iLimits.maximum()
        else:
            minimum = 0
            maximum = 200e-9
        # HACK limit axis range to 1 pA minimum
        minimum, maximum = limitRange(minimum, maximum, 2e-12)
        self.iAxis.setRange(minimum, maximum)
        self.iAxis.applyNiceNumbers()

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        self.fitVAxis()
        self.fitIAxis()

    def clear(self) -> None:
        super().clear()
        self.iLimits.clear()
        self.vLimits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(x, y)
            self.iLimits.append(y)
            self.vLimits.append(x)
            self.fit()


class ItPlotWidget(PlotWidget):
    MAX_POINTS: int = 60 * 60 * 24

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("I vs. t")

        self.smuSeries = QtChart.QLineSeries()
        self.smuSeries.setName("SMU")
        self.smuSeries.setColor(QtCore.Qt.red)
        self.smuSeries.setPointsVisible(True)
        self.chart().addSeries(self.smuSeries)

        self.smu2Series = QtChart.QLineSeries()
        self.smu2Series.setName("SMU2")
        self.smu2Series.setColor(QtCore.Qt.darkRed)
        self.smu2Series.setPointsVisible(True)
        self.chart().addSeries(self.smu2Series)

        self.elmSeries = QtChart.QLineSeries()
        self.elmSeries.setName("ELM")
        self.elmSeries.setColor(QtCore.Qt.blue)
        self.elmSeries.setPointsVisible(True)
        self.chart().addSeries(self.elmSeries)

        self.elm2Series = QtChart.QLineSeries()
        self.elm2Series.setName("ELM2")
        self.elm2Series.setColor(QtCore.Qt.darkBlue)
        self.elm2Series.setPointsVisible(True)
        self.chart().addSeries(self.elm2Series)

        self.iAxis = QtChart.QValueAxis()
        self.iAxis.hide()
        self.chart().addAxis(self.iAxis, QtCore.Qt.AlignLeft)
        self.smuSeries.attachAxis(self.iAxis)
        self.smu2Series.attachAxis(self.iAxis)
        self.elmSeries.attachAxis(self.iAxis)
        self.elm2Series.attachAxis(self.iAxis)

        self.iDynamicAxis = DynamicValueAxis(self.iAxis, "A")
        self.iDynamicAxis.setTitleText("Current")
        self.iDynamicAxis.setTickCount(9)
        self.chart().addAxis(self.iDynamicAxis, QtCore.Qt.AlignLeft)
        self.iAxis.setRange(0, 200e-9)

        self.tAxis = QtChart.QDateTimeAxis()
        self.tAxis.setTitleText("Time")
        self.tAxis.setTickCount(3)
        self.chart().addAxis(self.tAxis, QtCore.Qt.AlignBottom)
        self.smuSeries.attachAxis(self.tAxis)
        self.smu2Series.attachAxis(self.tAxis)
        self.elmSeries.attachAxis(self.tAxis)
        self.elm2Series.attachAxis(self.tAxis)

        self.iLimits = LimitsAggregator(self)
        self.tLimits = LimitsAggregator(self)

        self._series["smu"] = self.smuSeries
        self._series["smu2"] = self.smu2Series
        self._series["elm"] = self.elmSeries
        self._series["elm2"] = self.elm2Series

    def fitTAxis(self) -> None:
        if self.tLimits.isValid():
            minimum = self.tLimits.minimum()
            maximum = self.tLimits.maximum()
        else:
            t = time.time()
            minimum = t - 60
            maximum = t
        t0 = QtCore.QDateTime.fromMSecsSinceEpoch(int(minimum * 1e3))
        t1 = QtCore.QDateTime.fromMSecsSinceEpoch(int(maximum * 1e3))
        self.tAxis.setRange(t0, t1)

    def fitIAxis(self) -> None:
        if self.iLimits.isValid():
            minimum = self.iLimits.minimum()
            maximum = self.iLimits.maximum()
        else:
            minimum = 0
            maximum = 200e-9
        # HACK limit axis range to 1 pA minimum
        minimum, maximum = limitRange(minimum, maximum, 2e-12)
        self.iAxis.setRange(minimum, maximum)
        self.iAxis.applyNiceNumbers()

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        self.fitTAxis()
        self.fitIAxis()

    def clear(self) -> None:
        super().clear()
        self.iLimits.clear()
        self.tLimits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(QtCore.QPointF(x * 1e3, y))
            if series.count() > self.MAX_POINTS:
                series.remove(0)
            self.iLimits.append(y)
            self.tLimits.append(x)
            self.fit()


class CVPlotWidget(PlotWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("C vs. V")

        self.lcrSeries = QtChart.QLineSeries()
        self.lcrSeries.setName("LCR")
        self.lcrSeries.setColor(QtCore.Qt.magenta)
        self.chart().addSeries(self.lcrSeries)

        self.cAxis = QtChart.QValueAxis()
        self.chart().addAxis(self.cAxis, QtCore.Qt.AlignLeft)
        self.lcrSeries.attachAxis(self.cAxis)

        self.cDynamicAxis = DynamicValueAxis(self.cAxis, "F")
        self.cDynamicAxis.setTitleText("Capacitance")
        self.cDynamicAxis.setTickCount(9)
        self.chart().addAxis(self.cDynamicAxis, QtCore.Qt.AlignLeft)
        self.cAxis.setRange(0, 200e-9)

        self.vAxis = QtChart.QValueAxis()
        self.vAxis.setTitleText("Voltage")
        self.vAxis.setLabelFormat("%g V")
        self.vAxis.setRange(0, 200)
        self.vAxis.setTickCount(9)
        self.chart().addAxis(self.vAxis, QtCore.Qt.AlignBottom)
        self.lcrSeries.attachAxis(self.vAxis)

        self.cLimits = LimitsAggregator(self)
        self.vLimits = LimitsAggregator(self)

        self._series["lcr"] = self.lcrSeries

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        minimum: float = self.vLimits.minimum()
        maximum: float = self.vLimits.maximum()
        self.vAxis.setReverse(minimum > maximum)
        minimum, maximum = sorted((minimum, maximum))
        self.vAxis.setRange(minimum, maximum)
        # HACK limit axis range to 1 pF minimum
        minimum, maximum = limitRange(self.cLimits.minimum(), self.cLimits.maximum(), 2e-12)
        self.cAxis.setRange(minimum, maximum)
        self.cAxis.applyNiceNumbers()

    def clear(self) -> None:
        super().clear()
        self.cLimits.clear()
        self.vLimits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(x, y)
            self.cLimits.append(y)
            self.vLimits.append(x)
            self.fit()


class CV2PlotWidget(PlotWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.chart().setTitle("1/C^2 vs. V")

        self.lcrSeries = QtChart.QLineSeries()
        self.lcrSeries.setName("LCR")
        self.lcrSeries.setColor(QtCore.Qt.magenta)
        self.chart().addSeries(self.lcrSeries)

        self.cAxis = QtChart.QValueAxis()
        self.cAxis.setTitleText("Capacitance [1/F^2]")
        self.cAxis.setLabelFormat("%g")
        self.cAxis.setRange(0, 1 / 200**2)
        self.cAxis.setTickCount(9)
        self.chart().addAxis(self.cAxis, QtCore.Qt.AlignLeft)
        self.lcrSeries.attachAxis(self.cAxis)

        self.vAxis = QtChart.QValueAxis()
        self.vAxis.setTitleText("Voltage")
        self.vAxis.setLabelFormat("%g V")
        self.vAxis.setRange(0, 200)
        self.vAxis.setTickCount(9)
        self.chart().addAxis(self.vAxis, QtCore.Qt.AlignBottom)
        self.lcrSeries.attachAxis(self.vAxis)

        self.cLimits = LimitsAggregator(self)
        self.vLimits = LimitsAggregator(self)

        self._series["lcr"] = self.lcrSeries

    def fit(self) -> None:
        if self.chart().isZoomed():
            return
        minimum = self.vLimits.minimum()
        maximum = self.vLimits.maximum()
        self.vAxis.setReverse(minimum > maximum)
        minimum, maximum = sorted((minimum, maximum))
        self.vAxis.setRange(minimum, maximum)
        self.cAxis.setRange(self.cLimits.minimum(), self.cLimits.maximum())
        self.cAxis.applyNiceNumbers()
        self.cAxis.setTickCount(9)

    def clear(self) -> None:
        super().clear()
        self.cLimits.clear()
        self.vLimits.clear()

    def append(self, name: str, x: float, y: float) -> None:
        series = self._series.get(name)
        if series is not None:
            series.append(x, y)
            self.cLimits.append(y)
            self.vLimits.append(x)
            self.fit()
