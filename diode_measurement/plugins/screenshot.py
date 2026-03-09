import logging
import pathlib

from PySide6 import QtCore, QtGui, QtWidgets

from diode_measurement.utils import safe_bool

from . import Plugin

__all__ = ["ScreenshotPlugin"]

logger = logging.getLogger(__name__)


class ScreenshotPlugin(Plugin):
    def install(self, context) -> None:
        self.context = context
        self.create_widgets(context)
        self.read_settings()

    def uninstall(self, context) -> None:
        self.write_settings()
        self.remove_widgets(context)
        self.context = None

    def create_widgets(self, context) -> None:
        self.save_screenshot_check_box = QtWidgets.QCheckBox()
        self.save_screenshot_check_box.setText("Save Screenshot")
        self.save_screenshot_check_box.setStatusTip("Save screenshot of plots at end of measurement")

        layout = context.view.general_widget.output_group_box.layout()
        layout.insertWidget(layout.count() - 1, self.save_screenshot_check_box)

        self.context.measurement_finished.connect(self.save_screenshot)

    def remove_widgets(self, context) -> None:
        context.measurement_finished.disconnect(self.save_screenshot)

        layout = context.view.general_widget.output_group_box.layout()
        layout.removeWidget(self.save_screenshot_check_box)

        self.save_screenshot_check_box.setParent(None)  # type: ignore
        self.save_screenshot_check_box.deleteLater()

    def read_settings(self) -> None:
        settings = QtCore.QSettings()
        enabled = safe_bool(settings.value("saveScreenshot"), False)
        self.save_screenshot_check_box.setChecked(enabled)

    def write_settings(self) -> None:
        settings = QtCore.QSettings()
        enabled = self.save_screenshot_check_box.isChecked()
        settings.setValue("saveScreenshot", enabled)

    def output_filename(self) -> str:
        filename = self.context.state.get("filename")
        if isinstance(filename, str):
            return filename
        return ""

    def is_option_enabled(self) -> bool:
        if self.context.view.general_widget.output_group_box.isChecked():
            if self.save_screenshot_check_box.isChecked():
                return True
        return False

    def grab_screenshot(self) -> QtGui.QPixmap:
        return self.context.view.dataStackedWidget.grab()

    def save_screenshot(self) -> None:
        """Save screenshot of active IV/CV plots."""
        try:
            if self.is_option_enabled():
                p = pathlib.Path(self.output_filename())
                # Only if output file was produced.
                if p.exists():
                    filename = str(p.with_suffix(".png"))
                    pixmap = self.grab_screenshot()
                    pixmap.save(filename, "PNG")
                    logger.info("Saved screenshot to %s", filename)
        except Exception as exc:
            logger.exception(exc)
            self.context.handle_exception(exc)
