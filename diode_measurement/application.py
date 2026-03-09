import logging
import os

from PySide6 import QtCore, QtGui, QtWidgets

from . import __version__
from .controller import Controller
from .view.mainwindow import MainWindow
from .plugins import PluginRegistry
from .plugins.rpcserver import RPCServerPlugin
from .plugins.screenshot import ScreenshotPlugin

__all__ = ["bootstrap"]

logger = logging.getLogger(__name__)

PACKAGE_PATH = os.path.realpath(os.path.dirname(__file__))
ASSETS_PATH = os.path.join(PACKAGE_PATH, "assets")


def create_icon(filename: str) -> QtGui.QIcon:
    """Load icon into memory and create a QIcon, this prevents missing icons for
    pyinstaller single file builds.
    """
    with open(os.path.join(ASSETS_PATH, "icons", filename), "rb") as f:
        icon_bytes = f.read()
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(icon_bytes)
    return QtGui.QIcon(pixmap)


def bootstrap(app: QtWidgets.QApplication) -> None:
    app.setApplicationName("diode-measurement")
    app.setApplicationVersion(__version__)
    app.setApplicationDisplayName(f"Diode Measurement {__version__}")
    app.setOrganizationName("HEPHY")
    app.setOrganizationDomain("hephy.at")
    app.setWindowIcon(create_icon("diode-measurement.svg"))

    window = MainWindow()
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
