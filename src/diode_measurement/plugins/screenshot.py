import logging
import pathlib

from PySide6 import QtCore, QtGui, QtWidgets

from diode_measurement.controller import Controller
from diode_measurement.core.plugin import Plugin
from diode_measurement.utils import get_bool

__all__ = ["ScreenshotPlugin"]

logger = logging.getLogger(__name__)


class ScreenshotPlugin(Plugin):
    def install(self, context: Controller) -> None:
        self.context = context
        self.create_widgets(context)
        self.read_settings()

    def uninstall(self, context: Controller) -> None:
        self.write_settings()
        self.remove_widgets(context)

    def create_widgets(self, context: Controller) -> None:
        self.save_screenshot_check_box = QtWidgets.QCheckBox()
        self.save_screenshot_check_box.setText("Save Screenshot")
        self.save_screenshot_check_box.setStatusTip(
            "Save screenshot of plots at end of measurement"
        )

        layout = context.main_window.general_widget.output_group_box.layout()
        if isinstance(layout, QtWidgets.QVBoxLayout):
            layout.insertWidget(layout.count() - 1, self.save_screenshot_check_box)

        self.context.measurement_finished.connect(self.save_screenshot)

    def remove_widgets(self, context) -> None:
        context.measurement_finished.disconnect(self.save_screenshot)

        layout = context.main_window.general_widget.output_group_box.layout()
        if isinstance(layout, QtWidgets.QVBoxLayout):
            layout.removeWidget(self.save_screenshot_check_box)

        self.save_screenshot_check_box.setParent(None)  # type: ignore
        self.save_screenshot_check_box.deleteLater()

    def read_settings(self) -> None:
        settings = QtCore.QSettings()
        enabled = get_bool(settings.value("saveScreenshot"), False)
        self.save_screenshot_check_box.setChecked(enabled)

    def write_settings(self) -> None:
        settings = QtCore.QSettings()
        enabled = self.save_screenshot_check_box.isChecked()
        settings.setValue("saveScreenshot", enabled)

    def is_option_enabled(self) -> bool:
        return (
            self.context.main_window.general_widget.output_group_box.isChecked()
            and self.save_screenshot_check_box.isChecked()
        )

    def grab_screenshot(self) -> QtGui.QPixmap:
        return self.context.main_window.data_stacked_widget.grab()

    def save_screenshot(self) -> None:
        """Save screenshot of active IV/CV plots."""
        try:
            if self.is_option_enabled():
                filename = self.context.last_output_filename()
                if filename is not None:
                    p = pathlib.Path(filename)
                    # Only if output file was produced.
                    if p.exists():
                        filename = str(p.with_suffix(".png"))
                        pixmap = self.grab_screenshot()
                        pixmap.save(filename, "PNG")
                        logger.info("Saved screenshot to %s", filename)
        except Exception as exc:
            logger.exception("failed to save screenshot")
            self.context.handle_exception(exc)
