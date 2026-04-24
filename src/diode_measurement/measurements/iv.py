import logging
import math
import time
from dataclasses import asdict

from comet.estimate import Estimate

from ..core.measurement import RangeMeasurement, IVReading

__all__ = ["IVMeasurement"]

logger = logging.getLogger(__name__)


class IVMeasurement(RangeMeasurement):
    def on_iv_reading(self, reading: IVReading) -> None:
        self.state.append_iv_reading(reading)
        for writer in self.writers:
            writer.write_iv_row(asdict(reading))

    def on_it_reading(self, reading: IVReading) -> None:
        self.state.append_it_reading(reading)
        for writer in self.writers:
            writer.write_it_row(asdict(reading))

    def acquire_reading_data(self, source_voltage: float) -> IVReading:
        smu = self.instruments.get("smu")
        elm = self.instruments.get("elm")
        elm2 = self.instruments.get("elm2")
        dmm = self.instruments.get("dmm")
        i_smu, v_smu = smu.measure_iv() if smu else (math.nan, math.nan)
        i_elm = elm.measure_i() if elm else math.nan
        i_elm2 = elm2.measure_i() if elm2 else math.nan
        t_dmm = dmm.measure_temperature() if dmm else math.nan
        return IVReading(
            timestamp=time.time(),
            voltage=source_voltage,
            v_smu=v_smu,
            v_smu2=math.nan,
            i_smu2=math.nan,
            i_smu=i_smu,
            i_elm=i_elm,
            i_elm2=i_elm2,
            t_dmm=t_dmm,
        )

    def acquire_reading(self, source_voltage: float) -> None:
        reading: IVReading = self.acquire_reading_data(source_voltage)
        logger.info(reading)
        self.submit_update(
            {
                "smu_voltage": reading.v_smu,
                "smu_current": reading.i_smu,
                "elm_current": reading.i_elm,
                "elm2_current": reading.i_elm2,
                "dmm_temperature": reading.t_dmm,
            }
        )
        self.on_iv_reading(reading)

    def acquire_continuous_reading(self) -> None:
        t = time.monotonic()
        interval = 1.0

        estimate = Estimate(1)

        self.update_progress(0, 0, 0)

        voltage = self.get_source_voltage()

        while not self.state.stop_requested:
            dt = time.monotonic() - t

            reading: IVReading = self.acquire_reading_data(voltage)
            logger.info(reading)
            self.on_it_reading(reading)

            # Limit some actions for fast measurements
            if dt > interval:
                self.check_current_compliance()
                self.update_current_compliance()

                self.apply_change_voltage()

                voltage = self.get_source_voltage()

                self.submit_update(
                    {
                        "smu_voltage": reading.v_smu,
                        "smu_current": reading.i_smu,
                        "elm_current": reading.i_elm,
                        "elm2_current": reading.i_elm2,
                        "dmm_temperature": reading.t_dmm,
                    }
                )

                t = time.monotonic()

            if self.state.stop_requested:
                break

            self.apply_waiting_time_continuous(estimate)
            self.update_estimate_message_continuous("Reading...", estimate)

            estimate.advance()
