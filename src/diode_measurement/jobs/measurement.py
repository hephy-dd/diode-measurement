import contextlib
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass

from ..core.measurement import Measurement
from ..writer import Writer

__all__ = ["MeasurementJob"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MeasurementJob:
    measurement: Measurement
    timestamp_format: str
    value_format: str
    has_finished: Callable[[], None]

    def create_writer(self, fp) -> Writer:
        writer: Writer = Writer(fp)
        # Configure writer
        writer.timestamp_format = self.timestamp_format
        writer.value_format = self.value_format
        return writer

    def __call__(self) -> None:
        try:
            self.run_measurement()
        finally:
            self.has_finished()

    def run_measurement(self) -> None:
        measurement = self.measurement
        filename = measurement.state.get("filename")
        with contextlib.ExitStack() as stack:
            if filename:
                logger.info("preparing output file: %s", filename)

                path = os.path.dirname(filename)
                if not os.path.exists(path):
                    logger.debug("create output dir: %s", path)
                    os.makedirs(path)

                fp = stack.enter_context(open(filename, "w", newline=""))
                writer = self.create_writer(fp)
                measurement.add_writer(writer)
            measurement.run()
