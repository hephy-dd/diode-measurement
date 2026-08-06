import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import cast

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__
from ..controller import Controller
from ..core.plugin import PluginRegistry
from ..plugins import RPCServerPlugin, ScreenshotPlugin
from .mainwindow import MainWindow

__all__ = ["bootstrap"]

PACKAGE_PATH = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
ASSETS_PATH = os.path.join(PACKAGE_PATH, "assets")

logger = logging.getLogger()


def create_icon(filename: str) -> QtGui.QIcon:
    """Load icon into memory and create a QIcon, this prevents missing icons for
    pyinstaller single file builds.
    """
    with open(os.path.join(ASSETS_PATH, "icons", filename), "rb") as f:
        icon_bytes = f.read()
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(icon_bytes)
    return QtGui.QIcon(pixmap)


@dataclass
class LoggingConfig:
    log_level: int = logging.INFO
    write_logfile: bool = True
    logfile_max_bytes: int = 5 * 1024 * 1024
    logfile_backup_count: int = 3


def parse_log_level(log_level: str) -> int:
    match log_level.lower():
        case "info":
            return logging.INFO
        case "debug":
            return logging.DEBUG
        case _:
            return logging.INFO


def load_logging_config() -> LoggingConfig:
    settings = QtCore.QSettings()
    write_logfile = cast(bool, settings.value("logging/write_logfile", True, bool))
    log_level = parse_log_level(
        cast(str, settings.value("logging/log_level", "info", str))
    )
    return LoggingConfig(log_level, write_logfile)


def configure_logging(config: LoggingConfig):
    logger.setLevel(config.log_level)

    formatter = logging.Formatter(
        "%(asctime)s::%(name)s::%(levelname)s::%(message)s", "%Y-%m-%dT%H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(config.log_level)
    logger.addHandler(console_handler)

    if config.write_logfile:
        file_handler = RotatingFileHandler(
            Path.home() / "diode-measurement.log",
            maxBytes=config.logfile_max_bytes,
            backupCount=config.logfile_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(config.log_level)
        logger.addHandler(file_handler)


def bootstrap(app: QtWidgets.QApplication, debug: bool) -> None:
    app.setApplicationName("diode-measurement")
    app.setApplicationVersion(__version__)
    app.setApplicationDisplayName(f"Diode Measurement {__version__}")
    app.setOrganizationName("HEPHY")
    app.setOrganizationDomain("hephy.at")
    app.setWindowIcon(create_icon("diode-measurement.svg"))

    logging_config = load_logging_config()
    # Debug mode overrides settings
    if debug:
        logging_config.log_level = logging.DEBUG
    configure_logging(logging_config)

    window = MainWindow()
    window.add_logger(logger)
    window.set_log_level(logging_config.log_level)
    window.show()

    logger.info("Diode Measurement, version %s", __version__)

    controller = Controller(window)

    plugins = PluginRegistry(controller)

    startup = QtCore.QTimer(app)
    startup.setSingleShot(True)
    startup.timeout.connect(controller.start)
    startup.timeout.connect(controller.read_settings)
    startup.timeout.connect(lambda: plugins.install(RPCServerPlugin()))
    startup.timeout.connect(lambda: plugins.install(ScreenshotPlugin()))
    startup.start(10)

    app.aboutToQuit.connect(controller.write_settings)
    app.aboutToQuit.connect(controller.shutdown)
    app.aboutToQuit.connect(plugins.uninstall)

    app.exec()
