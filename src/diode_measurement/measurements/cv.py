import logging
import math
import time
from dataclasses import asdict

from comet.utils import inverse_square

from ..core.measurement import RangeMeasurement
from ..state import CVReading

__all__ = ["CVMeasurement"]

logger = logging.getLogger(__name__)


class CVMeasurement(RangeMeasurement):
    def on_cv_reading(self, reading: CVReading) -> None:
        self.state.append_cv_reading(reading)
        for writer in self.writers:
            writer.write_cv_row(asdict(reading))

    def acquire_cv_reading_data(self, source_voltage: float) -> CVReading:
        smu = self.station.instruments.get("smu")
        lcr = self.station.instruments.get("lcr")
        dmm = self.station.instruments.get("dmm")
        c_lcr, r_lcr = lcr.measure_impedance() if lcr else (math.nan, math.nan)
        # Calcualte 1c^2 as c2_lcr
        c2_lcr = inverse_square(c_lcr) if math.isfinite(c_lcr) else math.nan
        i_smu, v_smu = smu.measure_iv() if smu else (math.nan, math.nan)
        t_dmm = dmm.measure_temperature() if dmm else math.nan
        return CVReading(
            timestamp=time.time(),
            voltage=source_voltage,
            v_smu=v_smu,
            i_smu=i_smu,
            c_lcr=c_lcr,
            c2_lcr=c2_lcr,
            r_lcr=r_lcr,
            t_dmm=t_dmm,
        )

    def acquire_reading(self, source_voltage: float) -> None:
        reading: CVReading = self.acquire_cv_reading_data(source_voltage)
        self.submit_update(
            {
                "smu_voltage": reading.v_smu,
                "smu_current": reading.i_smu,
                "lcr_capacity": reading.c_lcr,
                "dmm_temperature": reading.t_dmm,
            }
        )
        self.on_cv_reading(reading)
