import argparse
import logging
import signal
import sys
import traceback

from PySide6 import QtWidgets

from . import __version__
from .gui.application import bootstrap
from .gui.widgets import show_exception

__all__ = ["main"]

QT_STYLES = QtWidgets.QStyleFactory().keys()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show debug messages",
    )
    parser.add_argument(
        "--style",
        metavar="<name>",
        choices=QT_STYLES,
        help="select Qt style",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Function to catch unhandled Python exceptions
    """
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.exception(tb)  # noqa: LOG015

    show_exception(exc_value)


def main():
    args = parse_args()

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

    bootstrap(app, debug=args.debug)


if __name__ == "__main__":
    main()
