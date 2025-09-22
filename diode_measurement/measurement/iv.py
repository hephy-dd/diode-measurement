import logging
import math
import time
import threading

from typing import Any, Callable

from ..estimate import Estimate

from . import ReadingType, State, EventHandler, RangeMeasurement

__all__ = ["IVMeasurement"]

logger = logging.getLogger(__name__)


class IVMeasurement(RangeMeasurement):

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.iv_reading_event: EventHandler = EventHandler()

    def acquire_reading_data(self, voltage=None) -> ReadingType:
        smu = self.instruments.get("smu")
        elm = self.instruments.get("elm")
        elm2 = self.instruments.get("elm2")
        dmm = self.instruments.get("dmm")
        if voltage is None:
            voltage = self.get_source_voltage()
        i_smu, v_smu = smu.measure_iv() if smu else (math.nan, math.nan)
        i_elm = elm.measure_i() if elm else math.nan
        i_elm2 = elm2.measure_i() if elm2 else math.nan
        t_dmm = dmm.measure_temperature() if dmm else math.nan
        return {
            "timestamp": time.time(),
            "voltage": voltage,
            "v_smu": v_smu,
            "i_smu": i_smu,
            "i_elm": i_elm,
            "i_elm2": i_elm2,
            "t_dmm": t_dmm,
        }

    def acquire_reading(self) -> None:
        reading: ReadingType = self.acquire_reading_data()
        logger.info(reading)

        # TODO
        if hasattr(self, "ivReadingLock") and hasattr(self, "ivReadingQueue"):
            with self.ivReadingLock:
                self.ivReadingQueue.append(reading)

        self.update_event({
            "smu_voltage": reading.get("v_smu"),
            "smu_current": reading.get("i_smu"),
            "elm_current": reading.get("i_elm"),
            "elm2_current": reading.get("i_elm2"),
            "dmm_temperature": reading.get("t_dmm"),
        })
        self.iv_reading_event(reading)

    def acquire_continuous_reading(self) -> None:
        t = time.time()
        interval = 1.0

        estimate = Estimate(1)

        self.update_progress(0, 0, 0)

        def handle_reading(reading: ReadingType) -> None:
            """Handle a single reading, update UI and write to files."""
            logger.info(reading)
            self.it_reading_event(reading)

        voltage = self.get_source_voltage()

        while not self.state.stop_requested:
            dt = time.time() - t

            reading: ReadingType = self.acquire_reading_data(voltage=voltage)
            handle_reading(reading)

            # TODO
            if hasattr(self, "itReadingLock") and hasattr(self, "itReadingQueue"):
                with self.itReadingLock:
                    self.itReadingQueue.append(reading)

            # Limit some actions for fast measurements
            if dt > interval:
                self.check_current_compliance()
                self.update_current_compliance()

                self.apply_change_voltage()

                voltage = self.get_source_voltage()

                self.update_event({
                    "smu_voltage": reading.get("v_smu"),
                    "smu_current": reading.get("i_smu"),
                    "elm_current": reading.get("i_elm"),
                    "elm2_current": reading.get("i_elm2"),
                    "dmm_temperature": reading.get("t_dmm")
                })

                t = time.time()

            if self.state.stop_requested:
                break

            self.apply_waiting_time_continuous(estimate)
            self.update_estimate_message_continuous("Reading...", estimate)

            estimate.advance()
