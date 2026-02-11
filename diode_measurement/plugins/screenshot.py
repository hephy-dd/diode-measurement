import logging
import pathlib

from PyQt5 import QtCore, QtGui, QtWidgets

from . import Plugin

__all__ = ["ScreenshotPlugin"]

logger = logging.getLogger(__name__)


class ScreenshotPlugin(Plugin):
    def install(self, context) -> None:
        self.context = context
        self.createWidgets(context)
        self.loadSettings()

    def uninstall(self, context) -> None:
        self.storeSettings()
        self.removeWidgets(context)
        self.context = None

    def createWidgets(self, context) -> None:
        self.saveScreenshotCheckBox = QtWidgets.QCheckBox()
        self.saveScreenshotCheckBox.setText("Save Screenshot")
        self.saveScreenshotCheckBox.setStatusTip("Save screenshot of plots at end of measurement")

        layout = context.view.generalWidget.outputGroupBox.layout()
        layout.insertWidget(layout.count() - 1, self.saveScreenshotCheckBox)

        self.context.finished.connect(self.saveScreenshot)

    def removeWidgets(self, context) -> None:
        context.finished.disconnect(self.saveScreenshot)

        layout = context.view.generalWidget.outputGroupBox.layout()
        layout.removeWidget(self.saveScreenshotCheckBox)

        self.saveScreenshotCheckBox.setParent(None)  # type: ignore
        self.saveScreenshotCheckBox.deleteLater()

    def loadSettings(self) -> None:
        settings = QtCore.QSettings()
        enabled = settings.value("saveScreenshot", False, bool)
        self.saveScreenshotCheckBox.setChecked(enabled)

    def storeSettings(self) -> None:
        enabled = self.saveScreenshotCheckBox.isChecked()
        settings = QtCore.QSettings()
        settings.setValue("saveScreenshot", enabled)

    def outputFilename(self) -> str:
        filename = self.context.state.get("filename")
        if isinstance(filename, str):
            return filename
        return ""

    def isOptionEnabled(self) -> bool:
        if self.context.view.generalWidget.outputGroupBox.isChecked():
            if self.saveScreenshotCheckBox.isChecked():
                return True
        return False

    def grabScreenshot(self) -> QtGui.QPixmap:
        return self.context.view.dataStackedWidget.grab()

    def saveScreenshot(self) -> None:
        """Save screenshot of active IV/CV plots."""
        try:
            if self.isOptionEnabled():
                p = pathlib.Path(self.outputFilename())
                # Only if output file was produced.
                if p.exists():
                    filename = str(p.with_suffix(".png"))
                    pixmap = self.grabScreenshot()
                    pixmap.save(filename, "PNG")
                    logger.info("Saved screenshot to %s", filename)
        except Exception as exc:
            logger.exception(exc)
            self.context.handleException(exc)
