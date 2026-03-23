import logging
import math
import time

from comet.estimate import Estimate

from ..core.measurement import ReadingType, Context, EventHandler, RangeMeasurement

__all__ = ["IVBiasMeasurement"]

logger = logging.getLogger(__name__)


class IVBiasMeasurement(RangeMeasurement):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.iv_reading_event: EventHandler = EventHandler()

    def acquire_reading_data(self, voltage=None) -> ReadingType:
        instruments = self.context.instruments
        smu = instruments.get("smu")
        smu2 = instruments.get("smu2")
        elm = instruments.get("elm")
        elm2 = instruments.get("elm2")
        dmm = instruments.get("dmm")
        if voltage is None:
            voltage = self.get_source_voltage()
        i_smu, v_smu = smu.measure_iv() if smu else (math.nan, math.nan)
        i_smu2, v_smu2 = smu2.measure_iv() if smu2 else (math.nan, math.nan)
        i_elm = elm.measure_i() if elm else math.nan
        i_elm2 = elm2.measure_i() if elm2 else math.nan
        t_dmm = dmm.measure_temperature() if dmm else math.nan
        return {
            "timestamp": time.time(),
            "voltage": voltage,
            "v_smu": v_smu,
            "i_smu": i_smu,
            "v_smu2": v_smu2,
            "i_smu2": i_smu2,
            "i_elm": i_elm,
            "i_elm2": i_elm2,
            "t_dmm": t_dmm,
        }

    def acquire_reading(self) -> None:
        reading: ReadingType = self.acquire_reading_data()
        reading.setdefault("type", "iv")
        logger.info(reading)

        self.state.reading_queue.put_nowait(reading)
        self.iv_reading_event(reading)

        self.update_event(
            {
                "smu_voltage": reading.get("v_smu"),
                "smu_current": reading.get("i_smu"),
                "smu2_voltage": reading.get("v_smu2"),
                "smu2_current": reading.get("i_smu2"),
                "elm_current": reading.get("i_elm"),
                "elm2_current": reading.get("i_elm2"),
                "dmm_temperature": reading.get("t_dmm"),
            }
        )

    def acquire_continuous_reading(self) -> None:
        t: float = time.time()
        interval: float = 1.0

        estimate: Estimate = Estimate(1)

        self.update_progress(0, 0, 0)

        def handle_reading(reading: ReadingType) -> None:
            """Handle a single reading, update UI and write to files."""
            logger.info(reading)
            self.state.reading_queue.put_nowait(reading)
            self.it_reading_event(reading)

        voltage = self.get_source_voltage()

        while not self.context.stop_requested:
            dt: float = time.time() - t

            reading: ReadingType = self.acquire_reading_data(voltage=voltage)
            reading.setdefault("type", "it")
            handle_reading(reading)

            # Limit some actions for fast measurements
            if dt > interval:
                self.check_current_compliance()
                self.update_current_compliance()

                if self.bias_source_instrument:
                    self.check_bias_current_compliance()
                    self.update_bias_current_compliance()

                self.apply_change_voltage()

                voltage = self.get_source_voltage()

                self.update_event(
                    {
                        "smu_voltge": reading.get("v_smu"),
                        "smu_current": reading.get("i_smu"),
                        "smu2_voltage": reading.get("v_smu2"),
                        "smu2_current": reading.get("i_smu2"),
                        "elm_current": reading.get("i_elm"),
                        "elm2_current": reading.get("i_elm2"),
                        "dmm_temperature": reading.get("t_dmm"),
                    }
                )

                t = time.time()

            if self.context.stop_requested:
                break

            self.apply_waiting_time_continuous(estimate)
            self.update_estimate_message_continuous("Reading...", estimate)

            estimate.advance()
