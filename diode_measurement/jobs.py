import contextlib
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Protocol

from .measurement import Measurement
from .measurement.iv import IVMeasurement
from .measurement.iv_bias import IVBiasMeasurement
from .measurement.cv import CVMeasurement

from .driver import driver_factory
from .utils import open_resource
from .writer import Writer

logger = logging.getLogger(__name__)


class Job(Protocol):
    def __call__(self) -> None: ...


@dataclass
class MeasurementJob:
    measurement: Measurement
    options: Mapping[str, Any]

    def create_writer(self, fp) -> Writer:
        writer: Writer = Writer(fp)
        # Configure writer
        timestamp_format = self.options.get("timestamp_format")
        if timestamp_format is not None:
            writer.timestamp_format = timestamp_format
        value_format = self.options.get("value_format")
        if value_format is not None:
            writer.value_format = value_format
        return writer

    def __call__(self) -> None:
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
                # TODO
                # Note: using signals executes slots in main thread, should be worker thread
                measurement.started_event.subscribe(lambda state=dict(measurement.state): writer.write_meta(state))
                if isinstance(measurement, IVMeasurement):
                    measurement.iv_reading_event.subscribe(lambda reading: writer.write_iv_row(reading))
                    measurement.it_reading_event.subscribe(lambda reading: writer.write_it_row(reading))
                if isinstance(measurement, IVBiasMeasurement):
                    measurement.iv_reading_event.subscribe(lambda reading: writer.write_iv_bias_row(reading))
                    measurement.it_reading_event.subscribe(lambda reading: writer.write_it_bias_row(reading))
                if isinstance(measurement, CVMeasurement):
                    measurement.cv_reading_event.subscribe(lambda reading: writer.write_cv_row(reading))
                measurement.finished_event.subscribe(lambda: writer.flush())
            measurement.run()


@dataclass
class K4215PerformCorrectionJob:
    model: str
    resource_name: str
    termination: str
    timeout: float
    cable_length: float
    open_correction: bool
    short_correction: bool
    load_correction: Optional[int]
    # TODO
    progress: Callable[[int, int, int], None]
    message: Callable[[str], None]

    def __call__(self) -> None:
        logger.info("Performing cable correction...")
        self.progress(0, 0, 0)
        with open_resource(self.resource_name, self.termination, self.timeout) as res:
            instr = driver_factory(self.model)(res)
            if self.open_correction:
                self.message("Performing OPEN correction...")
                instr.perform_open_correction(self.cable_length)
            if self.short_correction:
                self.message("Performing SHORT correction...")
                instr.perform_short_correction(self.cable_length)
            if self.load_correction is not None:
                self.message("Performing LOAD correction...")
                instr.perform_load_correction(self.cable_length, self.load_correction)
            logger.info(instr.identity())
        self.message("")
        logger.info("Cable correction done.")
