import contextlib
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from .measurement import Measurement
from .measurement.iv import IVMeasurement
from .measurement.iv_bias import IVBiasMeasurement
from .measurement.cv import CVMeasurement

from .driver import driver_factory
from .utils import open_resource
from .writer import Writer

logger = logging.getLogger(__name__)


@dataclass
class MeasurementJob:
    measurement: Measurement
    options: Optional[dict] = None

    def create_writer(self, fp) -> Writer:
        writer: Writer = Writer(fp)
        # Configure writer
        timestamp_format = self.options.get("timestamp_format")
        if timestamp_format:
            writer.timestamp_format = timestamp_format
        value_format = self.options.get("value_format")
        if value_format:
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
    config: dict
    progress: object
    message: object

    def __call__(self) -> None:
        logger.info("Performing cable correction...")
        self.message("Performing cable correction...")
        with open_resource(self.resource_name, self.termination, self.timeout) as res:
            instr = driver_factory(self.model)(res)
            logger.info(instr.identity())
        # TODO mockup
        for _ in range(3):
            self.progress(0, 3, _+1)
            time.sleep(1)
        logger.info("Done")
