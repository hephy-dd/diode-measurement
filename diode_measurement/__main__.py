import argparse
import logging
import signal
import sys
import traceback

from PySide6 import QtWidgets

from . import __version__
from .application import bootstrap
from .view.widgets import show_exception

__all__ = ["main"]

QT_STYLES = QtWidgets.QStyleFactory().keys()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="show debug messages")
    parser.add_argument(
        "--style", metavar="<name>", choices=QT_STYLES, help="select Qt style"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser.parse_args()


def configure_logger(debug=False):
    logger = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s::%(name)s::%(levelname)s::%(message)s", "%Y-%m-%dT%H:%M:%S"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Function to catch unhandled Python exceptions
    """
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.exception(tb)

    show_exception(exc_value)


def main():
    args = parse_args()

    configure_logger(args.debug)

    app = QtWidgets.QApplication(sys.argv)

    # install custom exception hook
    sys.excepthook = exception_hook

    # Register interupt signal handler
    def signal_handler(signum, frame):
        if signum == signal.SIGINT:
            app.quit()

    signal.signal(signal.SIGINT, signal_handler)

    if args.style:
        app.setStyle(args.style)

    bootstrap(app)


if __name__ == "__main__":
    main()
