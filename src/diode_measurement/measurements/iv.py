import logging
import math
import time
from dataclasses import dataclass

from comet.estimate import Estimate

from ..core.measurement import IVReading, RangeMeasurement, State
from ..core.role import Role
from ..writer import Writer, safe_format

__all__ = ["IVMeasurement"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IVReadingEvent:
    reading: IVReading


@dataclass(frozen=True, slots=True)
class ItReadingEvent:
    reading: IVReading


class IVMeasurement(RangeMeasurement):
    def on_write_begin(self, writer: Writer) -> None:
        write_meta(writer, self.state)

    def on_iv_reading(self, reading: IVReading) -> None:
        self.context.submit_event(IVReadingEvent(reading))
        for writer in self.writers:
            write_iv_reading(writer, reading)

    def on_it_reading(self, reading: IVReading) -> None:
        self.context.submit_event(ItReadingEvent(reading))
        for writer in self.writers:
            write_it_reading(writer, reading)

    def acquire_reading_data(self, source_voltage: float) -> IVReading:
        smu = self.station.instruments.get(Role.SMU)
        elm = self.station.instruments.get(Role.ELM)
        elm2 = self.station.instruments.get(Role.ELM2)
        dmm = self.station.instruments.get(Role.DMM)
        i_smu, v_smu = smu.measure_iv() if smu else (math.nan, math.nan)
        i_elm = elm.measure_i() if elm else math.nan
        i_elm2 = elm2.measure_i() if elm2 else math.nan
        t_dmm = dmm.measure_temperature() if dmm else math.nan
        tcu_temperature = self.tcu_temperature()
        tcu_humidity = self.tcu_humidity()

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
            tcu_temperature=tcu_temperature,
            tcu_humidity=tcu_humidity,
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

        while not self.context.stop_requested:
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

            if self.context.stop_requested:
                break

            self.apply_waiting_time_continuous(estimate)
            self.update_estimate_message_continuous("Reading...", estimate)

            estimate.advance()


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
    writer.flush()


def write_iv_reading(writer: Writer, reading: IVReading) -> None:
    timestamp_utc = reading.timestamp
    if writer.current_table != "iv":
        writer.current_table = "iv"
        header = (
            [
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "i_elm[A]",
                "i_elm2[A]",
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
            safe_format(reading.i_elm, writer.value_format),
            safe_format(reading.i_elm2, writer.value_format),
        ]
        + writer.dmm_data(reading)
        + writer.tcu_data(reading)
    )
    writer.write_table_row(row)
    writer.flush()


def write_it_reading(writer: Writer, reading: IVReading) -> None:
    timestamp_utc = reading.timestamp
    if writer.current_table != "it":
        writer.current_table = "it"
        header = (
            [
                "timestamp[s]",
                "voltage[V]",
                "v_smu[V]",
                "i_smu[A]",
                "i_elm[A]",
                "i_elm2[A]",
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
            safe_format(reading.i_elm, writer.value_format),
            safe_format(reading.i_elm2, writer.value_format),
        ]
        + writer.dmm_data(reading)
        + writer.tcu_data(reading)
    )
    writer.write_table_row(row)
    writer.flush()
