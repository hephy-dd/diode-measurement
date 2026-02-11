import logging
import math
import time

from ..utils import inverse_square

from . import ReadingType, State, EventHandler, RangeMeasurement

__all__ = ["CVMeasurement"]

logger = logging.getLogger(__name__)


class CVMeasurement(RangeMeasurement):

    def __init__(self, state: State) -> None:
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
        smu = self.instruments.get("smu")
        lcr = self.instruments.get("lcr")
        dmm = self.instruments.get("dmm")
        voltage = self.get_source_voltage()
        c_lcr, r_lcr = lcr.measure_impedance() if lcr else (math.nan, math.nan)
        i_smu, v_smu = smu.measure_iv() if smu else (math.nan, math.nan)
        t_dmm = dmm.measure_temperature() if dmm else math.nan
        return {
            "timestamp": time.time(),
            "voltage": voltage,
            "v_smu": v_smu,
            "i_smu": i_smu,
            "c_lcr": c_lcr,
            "r_lcr": r_lcr,
            "t_dmm": t_dmm
        }

    def acquire_reading(self) -> None:
        reading: ReadingType = self.acquire_reading_data()
        self.extend_cv_reading(reading)
        # TODO
        if hasattr(self, "cvReadingLock") and hasattr(self, "cvReadingQueue"):
            with self.cvReadingLock:
                self.cvReadingQueue.append(reading)
        self.update_event({
            "smu_voltage": reading.get("v_smu"),
            "smu_current": reading.get("i_smu"),
            "elm_current": reading.get("i_elm"),
            "lcr_capacity": reading.get("c_lcr"),
            "dmm_temperature": reading.get("t_dmm")
        })
        self.cv_reading_event(reading)
