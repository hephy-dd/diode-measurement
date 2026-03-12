import contextlib
import logging
import os
import time
from dataclasses import dataclass
from collections.abc import Callable, Mapping
from typing import Any, Optional, Protocol

from .measurements import Measurement
from .measurements.iv import IVMeasurement
from .measurements.iv_bias import IVBiasMeasurement
from .measurements.cv import CVMeasurement

from .drivers import K4215
from .utils import open_resource
from .writer import Writer

logger = logging.getLogger(__name__)


class Job(Protocol):
    def __call__(self) -> None: ...


@dataclass
class MeasurementJob:
    measurement: Measurement
    options: Mapping[str, Any]
    has_finished: Callable[[], None]

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
                # TODO
                # Note: using signals executes slots in main thread, should be worker thread
                measurement.started_event.subscribe(
                    lambda state=dict(measurement.state): writer.write_meta(state)
                )
                if isinstance(measurement, IVMeasurement):
                    measurement.iv_reading_event.subscribe(
                        lambda reading: writer.write_iv_row(reading)
                    )
                    measurement.it_reading_event.subscribe(
                        lambda reading: writer.write_it_row(reading)
                    )
                if isinstance(measurement, IVBiasMeasurement):
                    measurement.iv_reading_event.subscribe(
                        lambda reading: writer.write_iv_bias_row(reading)
                    )
                    measurement.it_reading_event.subscribe(
                        lambda reading: writer.write_it_bias_row(reading)
                    )
                if isinstance(measurement, CVMeasurement):
                    measurement.cv_reading_event.subscribe(
                        lambda reading: writer.write_cv_row(reading)
                    )
                measurement.finished_event.subscribe(lambda: writer.flush())
            measurement.run()


@dataclass
class K4215PerformCorrectionJob:
    resource_name: str
    termination: str
    timeout: float
    cable_length: float
    open_correction: bool
    short_correction: bool
    load_correction: Optional[int]
    external_bias_tee: bool
    # TODO
    progress: Callable[[int, int, int], None]
    message: Callable[[str], None]

    def __call__(self) -> None:
        correction_timeout: float = 120.0  # TODO

        logger.info("Performing cable correction...")
        self.progress(0, 0, 0)

        def wait_until_done(
            instr: K4215, timeout: float = 120.0, interval: float = 1.0
        ) -> None:
            timeout_at = time.monotonic() + timeout
            while time.monotonic() < timeout_at:
                if instr.has_correction_finished():
                    return
                else:
                    time.sleep(interval)
            raise TimeoutError("Timeout expired before cable correction completed.")

        with open_resource(self.resource_name, self.termination, self.timeout) as res:
            instr = K4215(res)

            if self.open_correction:
                if self.external_bias_tee:
                    self.message("Performing OPEN correction with Bias Tee...")
                    logger.info("Enable external Bias Tee (-10V DC)")
                    try:
                        instr.enable_bias_tee_dc_voltage()
                        time.sleep(1)
                        instr.start_open_correction(self.cable_length)
                        wait_until_done(instr, correction_timeout)
                    finally:
                        logger.info("Reset external Bias Tee")
                        instr.reset_bias_tee_dc_voltage()
                else:
                    self.message("Performing OPEN correction...")
                    instr.start_open_correction(self.cable_length)
                    wait_until_done(instr, correction_timeout)

            if self.short_correction:
                self.message("Performing SHORT correction...")
                instr.start_short_correction(self.cable_length)
                wait_until_done(instr, correction_timeout)

            if self.load_correction is not None:
                self.message("Performing LOAD correction...")
                instr.start_load_correction(self.cable_length, self.load_correction)
                wait_until_done(instr, correction_timeout)

        self.message("")
        logger.info("Cable correction done.")
