import logging
import sys
import os

from PyQt5 import QtCore, QtGui, QtWidgets

from . import __version__
from .controller import Controller
from .view.mainwindow import MainWindow
from .plugins import PluginRegistry
from .plugins.tcpserver import TCPServerPlugin
from .plugins.screenshot import ScreenshotPlugin

__all__ = ["Application"]

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


class Application(QtWidgets.QApplication):

    def __init__(self):
        super().__init__(sys.argv)
        self.setApplicationName("diode-measurement")
        self.setApplicationVersion(__version__)
        self.setApplicationDisplayName(f"Diode Measurement {__version__}")
        self.setOrganizationName("HEPHY")
        self.setOrganizationDomain("hephy.at")
        self.setWindowIcon(create_icon("diode-measurement.svg"))

    def bootstrap(self):
        # Initialize settings
        QtCore.QSettings()

        window = MainWindow()

        logger.info("Diode Measurement, version %s", __version__)

        controller = Controller(window)
        controller.loadSettings()

        plugins = PluginRegistry(controller)
        plugins.install(TCPServerPlugin())
        plugins.install(ScreenshotPlugin())

        self.aboutToQuit.connect(lambda: controller.storeSettings())
        window.show()

        # Interrupt timer
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(250)

        self.exec()

        controller.shutdown()
        plugins.uninstall()
