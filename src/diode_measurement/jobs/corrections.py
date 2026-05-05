import logging
import time
from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

from ..core.resource import ResourceConfig, Resource
from ..drivers import K4215

__all__ = ["K4215PerformCorrectionJob"]

logger = logging.getLogger(__name__)


@dataclass
class K4215PerformCorrectionJob:
    resource_config: ResourceConfig
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

        with Resource(self.resource_config) as res:
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
