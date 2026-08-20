import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from ..core.resource import Resource, ResourceConfig, list_resources
from ..drivers import K4215Adapter, driver_factory

__all__ = [
    "TestConnectionJob",
    "ListResourcesJob",
    "K4215PerformCorrectionJob",
]

logger = logging.getLogger(__name__)


@dataclass
class TestConnectionJob:
    model: str
    resource_config: ResourceConfig
    on_result_ready: Callable[[str], None]

    def __call__(self) -> None:
        with Resource(self.resource_config) as res:
            instr = driver_factory(self.model)(res)
            identity = instr.identify()
            self.on_result_ready(identity)


@dataclass
class ListResourcesJob:
    on_result_ready: Callable[[list], None]

    def __call__(self) -> None:
        resource_names = list_resources()
        self.on_result_ready(resource_names)


@dataclass
class K4215PerformCorrectionJob:
    resource_config: ResourceConfig
    cable_length: float
    open_correction: bool
    short_correction: bool
    load_correction: int | None
    external_bias_tee: bool
    on_message_changed: Callable[[str], None]
    correction_timeout: float = 120.0  # TODO

    def __call__(self) -> None:
        logger.info("Performing cable correction...")

        def wait_until_done(
            instr: K4215Adapter,
            timeout: float = 120.0,
            interval: float = 1.0,
        ) -> None:
            timeout_at = time.monotonic() + timeout
            while time.monotonic() < timeout_at:
                if instr.has_correction_finished():
                    return
                else:
                    time.sleep(interval)
            raise TimeoutError("Timeout expired before cable correction completed.")

        with Resource(self.resource_config) as res:
            instr = K4215Adapter(res)

            if self.open_correction:
                if self.external_bias_tee:
                    self.set_message("Performing OPEN correction with Bias Tee...")
                    logger.info("Enable external Bias Tee (-10V DC)")
                    try:
                        instr.enable_bias_tee_dc_voltage()
                        time.sleep(1)
                        instr.start_open_correction(self.cable_length)
                        wait_until_done(instr, self.correction_timeout)
                    finally:
                        logger.info("Reset external Bias Tee")
                        instr.reset_bias_tee_dc_voltage()
                else:
                    self.set_message("Performing OPEN correction...")
                    instr.start_open_correction(self.cable_length)
                    wait_until_done(instr, self.correction_timeout)

            if self.short_correction:
                self.set_message("Performing SHORT correction...")
                instr.start_short_correction(self.cable_length)
                wait_until_done(instr, self.correction_timeout)

            if self.load_correction is not None:
                self.set_message("Performing LOAD correction...")
                instr.start_load_correction(self.cable_length, self.load_correction)
                wait_until_done(instr, self.correction_timeout)

        logger.info("Cable correction done.")

    def set_message(self, message: str) -> None:
        self.on_message_changed(message)
