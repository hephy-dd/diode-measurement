import contextlib
import logging
import os
import time
from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional, Protocol

from .core.measurement import Context, Measurement
from .measurements.iv import IVMeasurement
from .measurements.iv_bias import IVBiasMeasurement
from .measurements.cv import CVMeasurement

from .drivers import driver_factory, K4215
from .resource import Resource, AutoReconnectResource
from .state import Role, State
from .utils import open_resource
from .writer import Writer

logger = logging.getLogger(__name__)

measurement_registry: dict[str, type[Measurement]] = {
    "iv": IVMeasurement,
    "iv_bias": IVBiasMeasurement,
    "cv": CVMeasurement,
}


class Job(Protocol):
    def __call__(self) -> None: ...


@dataclass
class MeasurementJob:
    state: State
    roles: list[str]
    timestamp_format: str
    value_format: str
    on_finished: Callable[[], None]
    on_failed: Callable[[Exception], None]
    on_update: Callable[[dict], None]
    on_voltage_changed: Callable[[], None]

    def create_resource(self, role: Role, auto_reconnect: bool) -> Resource:
        # If auto reconnect use experimental class AutoReconnectResource
        resource_cls = AutoReconnectResource if auto_reconnect else Resource
        resource = resource_cls(
            resource_name=role.resource_name,
            visa_library=role.visa_library,
            read_termination=role.termination,
            write_termination=role.termination,
            timeout=role.timeout * 1000,  # in millisecs
        )
        return resource

    def create_measurement(self, stack) -> Measurement:
        context = Context(self.state)
        auto_reconnect = self.state.auto_reconnect
        for name in self.roles:
            role = self.state.find_role(name)
            if role is None:
                raise KeyError(f"No such role: {name!r}")
            if not role.enabled:
                continue
            if not role.resource_name.strip():
                raise ValueError(
                    f"Empty resource name not allowed for {name.upper()} ({role.model})."
                )
            cls = driver_factory(role.model)
            if not cls:
                raise RuntimeError("No such driver: %s", role.model)
            resource = self.create_resource(role, auto_reconnect)
            context.instruments[name] = cls(stack.enter_context(resource))

        measurement_type = self.state.measurement_type
        measurement_cls = measurement_registry.get(measurement_type)
        if measurement_cls is None:
            raise ValueError(f"No such measurement type: {measurement_type}")

        return measurement_cls(context)

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
            self.on_finished()

    def run_measurement(self) -> None:
        with contextlib.ExitStack() as stack:
            measurement = self.create_measurement(stack)
            measurement.failed_event.subscribe(self.on_failed)
            measurement.update_event.subscribe(self.on_update)
            measurement.change_voltage_ready_event.subscribe(self.on_voltage_changed)

            filename = self.state.filename
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
                    lambda state=self.state: writer.write_meta(state)
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
