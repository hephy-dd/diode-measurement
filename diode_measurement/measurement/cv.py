import logging
import math
import time

from typing import Any, Callable, Dict, List

from PyQt5 import QtCore

from ..utils import inverse_square

from . import ReadingType, StateType, EventHandler, RangeMeasurement

__all__ = ["CVMeasurement"]

logger = logging.getLogger(__name__)


class CVMeasurement(RangeMeasurement):

    def __init__(self, state: StateType) -> None:
        super().__init__(state)
        self.cv_reading_event: EventHandler = EventHandler()

    def extend_cv_reading(self, reading: ReadingType) -> ReadingType:
        # Calcualte 1c^2 as c2_lcr
        c_lcr = reading.get("c_lcr", math.nan)
        if math.isfinite(c_lcr) and c_lcr:
            reading["c2_lcr"] = inverse_square(c_lcr)
        else:
            reading["c2_lcr"] = math.nan
        return reading

    def acquire_reading_data(self) -> ReadingType:
        smu = self.contexts.get("smu")
        lcr = self.contexts.get("lcr")
        dmm = self.contexts.get("dmm")
        voltage = self.get_source_voltage()
        if lcr:
            c_lcr = lcr.read_capacity()
        else:
            c_lcr = float("NaN")
        if smu:
            i_smu = smu.read_current()
        else:
            i_smu = float("NaN")
        if dmm:
            t_dmm = dmm.read_temperature()
        else:
            t_dmm = float("NaN")
        return {
            "timestamp": time.time(),
            "voltage": voltage,
            "i_smu": i_smu,
            "c_lcr": c_lcr,
            "t_dmm": t_dmm
        }

    def acquire_reading(self) -> None:
        reading: ReadingType = self.acquire_reading_data()
        self.extend_cv_reading(reading)
        with self.cvReadingLock:
            self.cvReadingQueue.append(reading)
        self.update_event({
            "smu_current": reading.get("i_smu"),
            "elm_current": reading.get("i_elm"),
            "lcr_capacity": reading.get("c_lcr"),
            "dmm_temperature": reading.get("t_dmm")
        })
        self.cv_reading_event(reading)
