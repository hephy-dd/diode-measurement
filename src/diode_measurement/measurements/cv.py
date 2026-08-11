import logging
import math
import time
from dataclasses import dataclass

from comet.utils import inverse_square

from ..core.events import Reading
from ..core.measurement import RangeMeasurement, State
from ..core.role import Role
from ..writer import Writer, safe_format

__all__ = ["CVMeasurement"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CVReading(Reading):
    voltage: float
    v_smu: float
    i_smu: float
    c_lcr: float
    c2_lcr: float
    r_lcr: float


@dataclass(frozen=True, slots=True)
class CVReadingEvent:
    reading: CVReading


class CVMeasurement(RangeMeasurement):
    @classmethod
    def filter_source_roles(cls, checked_roles: list[Role]) -> list[Role]:
        checked = set(checked_roles)
        has_smu = bool(checked & {Role.SMU, Role.SMU2})

        allowed = {Role.SMU, Role.SMU2}

        if not has_smu:
            allowed.add(Role.LCR)

        return [role for role in checked_roles if role in allowed]

    def on_write_begin(self, writer: Writer) -> None:
        write_meta(writer, self.state)

    def on_cv_reading(self, reading: CVReading) -> None:
        self.context.submit_event(CVReadingEvent(reading))
        for writer in self.writers:
            write_cv_reading(writer, reading)

    def acquire_cv_reading_data(self, source_voltage: float) -> CVReading:
        smu = self.station.instruments.get(Role.SMU)
        lcr = self.station.instruments.get(Role.LCR)
        dmm = self.station.instruments.get(Role.DMM)
        c_lcr, r_lcr = lcr.measure_impedance() if lcr else (math.nan, math.nan)
        # Calcualte 1c^2 as c2_lcr
        c2_lcr = inverse_square(c_lcr) if math.isfinite(c_lcr) else math.nan
        i_smu, v_smu = smu.measure_iv() if smu else (math.nan, math.nan)
        t_dmm = dmm.measure_temperature() if dmm else math.nan
        tcu_temperature = self.tcu_temperature()
        tcu_humidity = self.tcu_humidity()

        return CVReading(
            timestamp=time.time(),
            voltage=source_voltage,
            v_smu=v_smu,
            i_smu=i_smu,
            c_lcr=c_lcr,
            c2_lcr=c2_lcr,
            r_lcr=r_lcr,
            t_dmm=t_dmm,
            tcu_temperature=tcu_temperature,
            tcu_humidity=tcu_humidity,
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


def write_meta(writer: Writer, state: State) -> None:
    writer.current_table = None
    writer.write_tag("sample", state.sample)
    writer.write_tag("measurement_type", state.measurement_type)
    writer.write_tag(
        "voltage_begin[V]", safe_format(state.voltage_begin, writer.value_format)
    )
    writer.write_tag(
        "voltage_end[V]", safe_format(state.voltage_end, writer.value_format)
    )
    writer.write_tag(
        "voltage_step[V]", safe_format(state.voltage_step, writer.value_format)
    )
    writer.write_tag(
        "waiting_time[s]", safe_format(state.waiting_time, writer.value_format)
    )
    writer.write_tag(
        "current_compliance[A]",
        safe_format(state.current_compliance, writer.value_format),
    )
    write_meta_lcr(writer, state)
    writer.flush()


def write_meta_lcr(writer: Writer, state: State) -> None:
    lcr = state.roles.get(Role.LCR)
    if lcr and lcr.enabled:
        lcr_options = lcr.options
        # lcr.options.voltage
        voltage = lcr_options.get("voltage")
        if voltage is not None:
            writer.write_tag(
                "lcr_ac_amplitude[V]", safe_format(voltage, writer.value_format)
            )
        # lcr.options.frequency
        frequency = lcr_options.get("frequency")
        if frequency is not None:
            writer.write_tag(
                "lcr_ac_frequency[Hz]", safe_format(frequency, writer.value_format)
            )


def write_cv_reading(writer: Writer, reading: CVReading) -> None:
    timestamp_utc = reading.timestamp
    if writer.current_table != "cv":
        writer.current_table = "cv"
        header = (
            [
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "c_lcr[F]",
                "c2_lcr[1/F^2]",
                "r_lcr[Ohm]",
            ]
            + writer.dmm_header()
            + writer.tcu_header()
        )
        writer.write_table_header(header)
        writer.reset_timestamp_offset(timestamp_utc)
    row = (
        [
            safe_format(writer.get_timestamp(timestamp_utc), writer.timestamp_format),
            safe_format(reading.voltage, writer.value_format),
            safe_format(reading.v_smu, writer.value_format),
            safe_format(reading.i_smu, writer.value_format),
            safe_format(reading.c_lcr, writer.value_format),
            safe_format(reading.c2_lcr, writer.value_format),
            safe_format(reading.r_lcr, writer.value_format),
        ]
        + writer.dmm_data(reading)
        + writer.tcu_data(reading)
    )
    writer.write_table_row(row)
    writer.flush()
