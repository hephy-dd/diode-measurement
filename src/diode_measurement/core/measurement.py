import contextlib
import logging
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event
from typing import Any, Self

from comet.estimate import Estimate
from comet.functions import LinearRange

from ..actors import TCUActor
from ..state import FSMState
from ..writer import Writer
from .driver import VoltageMeasurable
from .events import (
    ChangeVoltageDoneEvent,
    ExceptionEvent,
    Reading,
    UpdateContinueInCompliance,
    UpdateCurrentCompliance,
    UpdateMetricsEvent,
    UpdateWaitingTimeContinuous,
)
from .role import Role, RoleConfig
from .station import Station

__all__ = [
    "MeasurementParameters",
    "Measurement",
    "RangeMeasurement",
]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IVReading(Reading):
    voltage: float
    v_smu: float
    i_smu: float
    v_smu2: float
    i_smu2: float
    i_elm: float
    i_elm2: float


@dataclass(slots=True)
class MeasurementParameters:
    id: str
    type: str
    title: str
    measurement_cls: type["Measurement"]
    supported_roles: list[str]
    default_roles: list[str]
    default_begin_voltage: float
    default_end_voltage: float
    default_step_voltage: float
    default_waiting_time: float
    default_current_compliance: float
    voltage_unit: str
    current_compliance_unit: str
    default_bias_voltage: float = 0.0
    default_waiting_time_continuous: float = 1.0
    provides_continuous: bool = False


@dataclass(frozen=True, slots=True)
class ChangeVoltageParameters:
    end_voltage: float
    step_voltage: float
    waiting_time: float


@dataclass(frozen=True, slots=True)
class State:
    measurement_type: str = ""
    timestamp: float = 0.0
    sample: str = ""
    auto_reconnect: bool = False
    is_continuous: bool = False
    continue_in_compliance: bool = False
    waiting_time: float = 1.0
    waiting_time_continuous: float = 1.0
    source_voltage: float | None = None
    bias_voltage: float = 0.0
    voltage_begin: float = 0.0
    voltage_end: float = 0.0
    voltage_step: float = 1.0
    current_compliance: float = 0.0
    source_role: Role | None = None
    bias_source_role: Role | None = None
    discharge_timeout: float = 60.0
    discharge_threshold: float = 0.5
    roles: dict[Role, RoleConfig] = field(default_factory=dict)
    output_filename: str | None = None
    settle_waiting_time: float = 1.0
    tcu_poll_interval: float = 5.0

    def find_role(self, role: Role) -> RoleConfig | None:
        return self.roles.get(role)


@dataclass(slots=True)
class Context:
    state: State
    station: Station
    outbox_queue: Queue[Any]
    inbox_queue: Queue[Any]
    abort_event: Event

    def submit_event(self, event: Any) -> None:
        self.outbox_queue.put(event)

    @property
    def stop_requested(self) -> bool:
        return self.abort_event.is_set()


@dataclass(slots=True)
class RuntimeState:
    current_compliance: float
    continue_in_compliance: bool
    waiting_time_continuous: float
    change_voltage_request: ChangeVoltageParameters | None = None

    def pop_change_voltage_request(self) -> ChangeVoltageParameters | None:
        parameters = self.change_voltage_request
        self.change_voltage_request = None
        return parameters


class Measurement:
    def __init__(self, context: Context) -> None:
        self.context: Context = context
        self.state: State = context.state
        self.station: Station = context.station

        self.tcu_actor: TCUActor | None = None

        self.writers: list[Writer] = []

        self.runtime_state = RuntimeState(
            current_compliance=self.state.current_compliance,
            continue_in_compliance=self.state.continue_in_compliance,
            waiting_time_continuous=self.state.waiting_time_continuous,
        )

    @classmethod
    def create(
        cls,
        state: State,
        station: Station,
        outbox_queue: Queue[Any],
        inbox_queue: Queue[Any],
        abort_event: Event,
    ) -> Self:
        return cls(Context(state, station, outbox_queue, inbox_queue, abort_event))

    def process_inbox(self) -> None:
        for _ in range(1024):
            try:
                event = self.context.inbox_queue.get_nowait()
            except Empty:
                break
            match event:
                case UpdateCurrentCompliance(compliance):
                    self.runtime_state.current_compliance = compliance
                case UpdateContinueInCompliance(is_continue):
                    self.runtime_state.continue_in_compliance = is_continue
                case UpdateWaitingTimeContinuous(waiting_time):
                    self.runtime_state.waiting_time_continuous = waiting_time
                case ChangeVoltageParameters() as parameters:
                    self.runtime_state.change_voltage_request = parameters
                case _:
                    logger.warning("unhandled inbox event: %r", event)

    def add_writer(self, writer: Writer) -> None:
        self.writers.append(writer)

    def on_write_begin(self, writer: Writer) -> None: ...

    def on_write_end(self, writer: Writer) -> None: ...

    def on_started(self) -> None:
        for writer in self.writers:
            self.on_write_begin(writer)

    def on_finished(self) -> None:
        for writer in self.writers:
            self.on_write_end(writer)
            writer.flush()

    def check_error_state(self, context) -> None:
        error = context.next_error()
        if error is not None:
            raise RuntimeError(f"Instrument Error: {error.code}: {error.message}")

    def tcu_temperature(self) -> float:
        if self.tcu_actor is not None:
            metrics = self.tcu_actor.cached_metrics()
            return metrics.temperature
        return math.nan

    def tcu_humidity(self) -> float:
        if self.tcu_actor is not None:
            metrics = self.tcu_actor.cached_metrics()
            return metrics.humidity
        return math.nan

    def submit_update(self, data: Mapping[str, Any]) -> None:
        self.context.submit_event(UpdateMetricsEvent(dict(data)))

    def set_fsm_state(self, state: FSMState) -> None:
        self.submit_update({"fsm_state": state})

    def initialize(self) -> None: ...

    def measure(self) -> None: ...

    def finalize(self) -> None: ...

    def run(self) -> None:
        try:
            logger.debug("run measurement...")
            self.set_fsm_state(FSMState.CONFIGURE)
            logger.debug("handle started callbacks...")
            self.on_started()
            logger.debug("handle started callbacks... done.")
            with contextlib.ExitStack() as stack:
                logger.debug("creating instrument contexts...")
                self.station.create_instruments(stack)
                logger.debug("creating instrument contexts... done.")
                try:
                    logger.debug("initialize...")
                    self.initialize()
                    logger.debug("initialize... done.")
                    logger.debug("measure...")
                    self.measure()
                    logger.debug("measure... done.")
                except Exception as exc:
                    logger.exception("failed to initialize measurement")
                    self.context.submit_event(ExceptionEvent(exc))
                finally:
                    logger.debug("finalize...")
                    self.set_fsm_state(FSMState.STOPPING)
                    self.finalize()
                    logger.debug("finalize... done.")
        except Exception as exc:
            logger.exception("failed to run measurement")
            self.context.submit_event(ExceptionEvent(exc))
        finally:
            logger.debug("handle finished callbacks...")
            self.on_finished()
            logger.debug("handle finished callbacks... done.")
            self.set_fsm_state(FSMState.IDLE)
            logger.debug("run measurement... done.")


class RangeMeasurement(Measurement):
    def on_it_reading(self, reading) -> None: ...

    # Interlock check

    def check_interlock(self, instrument) -> None:
        if hasattr(instrument, "is_interlock") and not instrument.is_interlock():
            name = type(instrument).__name__
            raise RuntimeError(f"{name}: instrument not interlocked!")

    # Source

    def get_source_output_state(self) -> bool:
        return self.source_instrument.get_output_enabled()  # type: ignore

    def set_source_output_state(self, state: bool) -> None:
        logger.info("Source output state: %s", state)
        self.source_instrument.set_output_enabled(state)  # type: ignore
        self.submit_update({"source_output_state": state})

    def get_source_voltage(self) -> float:
        return self.source_instrument.get_voltage_level()  # type: ignore

    def set_source_voltage(self, voltage: float) -> None:
        logger.info("Source voltage level: %gV", voltage)
        self.source_instrument.set_voltage_level(voltage)  # type: ignore
        self.submit_update({"source_voltage": voltage})

    def set_source_voltage_range(self, voltage: float) -> None:
        logger.info("Source voltage range: %gV", voltage)
        self.source_instrument.set_voltage_range(voltage)  # type: ignore

    # Bias source

    def get_bias_source_output_state(self) -> bool:
        return self.bias_source_instrument.get_output_enabled()  # type: ignore

    def set_bias_source_output_state(self, state: bool) -> None:
        logger.info("Bias source output state: %s", state)
        self.bias_source_instrument.set_output_enabled(state)  # type: ignore
        self.submit_update({"bias_source_output_state": state})

    def get_bias_source_voltage(self) -> float:
        return self.bias_source_instrument.get_voltage_level()  # type: ignore

    def set_bias_source_voltage(self, voltage: float) -> None:
        logger.info("Bias source voltage level: %gV", voltage)
        self.bias_source_instrument.set_voltage_level(voltage)  # type: ignore
        self.submit_update({"bias_source_voltage": voltage})

    def set_bias_source_voltage_range(self, voltage: float) -> None:
        logger.info("Bias source voltage range: %gV", voltage)
        self.bias_source_instrument.set_voltage_range(voltage)  # type: ignore

    def check_current_compliance(self) -> None:
        """Raise exception if current compliance tripped and continue in
        compliance option is not active.
        """
        self.process_inbox()
        if (
            not self.runtime_state.continue_in_compliance
            and self.source_instrument is not None
            and self.source_instrument.compliance_tripped()
        ):
            raise RuntimeError("Source compliance tripped!")

    def update_current_compliance(self) -> None:
        """Update current compliance if value changed."""
        self.process_inbox()
        current_compliance = self.runtime_state.current_compliance
        if self.current_compliance != current_compliance:  # type: ignore
            self.current_compliance = current_compliance
            self.set_source_compliance(self.current_compliance)
            self.check_error_state(self.source_instrument)

    def set_source_compliance(self, compliance: float) -> None:
        logger.info("Source current compliance level: %gA", compliance)
        self.source_instrument.set_current_compliance_level(compliance)  # type: ignore

    def set_bias_source_compliance(self, compliance: float) -> None:
        logger.info("Bias source current compliance level: %gA", compliance)
        self.bias_source_instrument.set_current_compliance_level(compliance)  # type: ignore

    def check_bias_current_compliance(self) -> None:
        """Raise exception if biascurrent compliance tripped and continue in
        compliance option is not active.
        """
        self.process_inbox()
        if (
            not self.runtime_state.continue_in_compliance
            and self.bias_source_instrument is not None
            and self.bias_source_instrument.compliance_tripped()
        ):
            raise RuntimeError("Source compliance tripped!")

    def update_bias_current_compliance(self) -> None:
        """Update current compliance if value changed."""
        self.process_inbox()
        current_compliance = self.runtime_state.current_compliance
        if self.bias_current_compliance != current_compliance:  # type: ignore
            self.bias_current_compliance = current_compliance
            self.set_bias_source_compliance(self.bias_current_compliance)
            self.check_error_state(self.bias_source_instrument)

    def apply_waiting_time(self) -> None:
        waiting_time: float = self.state.waiting_time
        logger.info("Waiting for %.2f sec", waiting_time)
        time.sleep(waiting_time)

    def apply_waiting_time_continuous(self, estimate: Estimate) -> None:
        self.process_inbox()
        waiting_time: float = self.runtime_state.waiting_time_continuous
        interval: float = 1.0
        logger.info("Waiting for %.2f sec", waiting_time)
        if waiting_time < interval:
            time.sleep(waiting_time)
        else:
            now: float = time.monotonic()
            threshold: float = now + waiting_time
            while now < threshold:
                if self.context.stop_requested:
                    self.update_message("Stopping...")
                    break
                # Abort waiting in case change voltsage request arrives
                self.process_inbox()
                if self.runtime_state.change_voltage_request is not None:
                    break
                remaining: float = round(threshold - now)
                self.update_estimate_message_continuous(
                    f"Next reading in {remaining:d} sec...", estimate
                )
                time.sleep(interval)
                now = time.monotonic()

    def apply_change_voltage(self):
        self.process_inbox()
        parameters = self.runtime_state.pop_change_voltage_request()
        if parameters is not None:
            self.set_fsm_state(FSMState.RAMPING)
            self.ramp_to_continuous(
                end_voltage=parameters.end_voltage,
                step_voltage=parameters.step_voltage,
                waiting_time=parameters.waiting_time,
            )
            if not self.context.stop_requested:  # hack
                self.set_fsm_state(FSMState.CONTINUOUS)
            self.context.submit_event(ChangeVoltageDoneEvent())

    def update_message(self, message: str) -> None:
        """Emit update message event."""
        self.submit_update({"message": message})

    def update_progress(self, begin: int, end: int, step: int) -> None:
        """Emit update progress event."""
        self.submit_update({"progress": (begin, end, step)})

    def update_estimate_message(self, message: str, estimate: Estimate) -> None:
        """Emit update message event for ramp iterations."""
        elapsed_time = format(estimate.elapsed).split(".")[0]
        remaining_time = format(estimate.remaining).split(".")[0]
        average_time = format(estimate.average.total_seconds(), ".2f")
        self.update_message(
            f"{message} | Elapsed {elapsed_time} | Remaining {remaining_time} | Average {average_time} s"
        )

    def update_estimate_message_continuous(
        self, message: str, estimate: Estimate
    ) -> None:
        """Emit update message event for continuous iterations."""
        elapsed_time = format(estimate.elapsed).split(".")[0]
        average_time = format(estimate.average.total_seconds(), ".3f")
        self.update_message(
            f"{message} | Elapsed {elapsed_time} | Average {average_time} s"
        )

    def update_estimate_progress(self, estimate: Estimate) -> None:
        """Emit update progress event for ramp iterations."""
        self.update_progress(0, estimate.total, estimate.passed)

    def initialize(self) -> None:
        source_role = self.state.source_role
        if source_role is None:
            raise RuntimeError("No source instrument set")
        self.source_instrument = self.station.instruments.get(source_role)
        if self.source_instrument is None:
            raise RuntimeError("No source instrument set")

        # Bias

        self.bias_source_instrument = None
        if self.state.measurement_type in ["iv_bias"]:  # TODO
            bias_source_role = self.state.bias_source_role
            if bias_source_role is None:
                raise RuntimeError("No bias source instrument set")
            self.bias_source_instrument = self.station.instruments.get(bias_source_role)
            if self.bias_source_instrument is None:
                raise RuntimeError("No bias source instrument set")

        logger.debug("querying context identities...")
        for role, instrument in self.station.instruments.items():
            logger.debug("reading %s identity...", role.upper())
            identity: str = instrument.identify()
            logger.debug("reading %s identity... done.", role.upper())
            logger.info("%s IDN: %s", role.upper(), identity)
        logger.debug("querying context identities... done.")

        logger.debug("get source output state...")
        source_output_state: bool = self.get_source_output_state()
        logger.debug("get source output state... done.")

        if source_output_state:
            self.ramp_to_zero()
        else:
            self.set_source_voltage(0.0)

        # Bias

        if self.bias_source_instrument:
            logger.debug("get bias source output state...")
            bias_source_output_state = self.get_bias_source_output_state()
            logger.debug("get bias source output state... done.")

            if bias_source_output_state:
                self.ramp_bias_to_zero()
            else:
                self.set_bias_source_voltage(0.0)

        # Switch
        self.initialize_switch()

        # Reset (optional)
        for role, instrument in self.station.instruments.items():
            role_config = self.state.find_role(role)
            if role_config and role_config.reset_instrument:
                logger.info("Reset %s...", role.upper())
                instrument.reset()
                logger.info("Reset %s... done.", role.upper())

        # Clear state
        for role, instrument in self.station.instruments.items():
            logger.info("Clear %s...", role.upper())
            instrument.clear()
            logger.info("Clear %s... done.", role.upper())

        # Configure
        for role, instrument in self.station.instruments.items():
            logger.info("Configure %s...", role.upper())
            role_config = self.state.find_role(role)
            if role_config is not None:
                for name, value in role_config.options.items():
                    logger.info("%s: %r", name, value)
                instrument.configure(role_config.options)
                self.check_error_state(instrument)
            logger.info("Configure %s... done.", role.upper())

        # Compliance
        self.current_compliance = self.runtime_state.current_compliance
        self.set_source_compliance(self.current_compliance)
        self.check_error_state(self.source_instrument)

        # check interlock (optional)
        for instrument in self.station.instruments.values():
            self.check_interlock(instrument)

        # TCU (optional)
        tcu = self.station.instruments.get(Role.TCU)
        if tcu is not None:
            self.tcu_actor = TCUActor(
                tcu=tcu,
                event_queue=self.context.outbox_queue,
                abort_event=self.context.abort_event,
            )

        if self.tcu_actor is not None:
            self.tcu_actor.start()
            if not self.tcu_actor.is_within_setpoint():
                self.update_message("Waiting for TCU to reach setpoint...")
                self.update_progress(0, 0, 0)
            self.tcu_actor.ensure_setpoint()

        self.bias_current_compliance = self.runtime_state.current_compliance
        if self.bias_source_instrument:
            self.set_bias_source_compliance(self.bias_current_compliance)
            self.check_error_state(self.bias_source_instrument)

        if self.bias_source_instrument:
            self.set_bias_source_output_state(True)
            self.ramp_bias_to_bias()
            self.check_error_state(self.bias_source_instrument)

        # Enable output
        self.set_source_output_state(True)

        self.initialize_elms()

        self.ramp_to_begin()

        self.apply_settle_waiting_time()

    def initialize_elms(self) -> None:
        elm = self.station.instruments.get(Role.ELM)
        if elm is not None:
            elm.set_zero_check_enabled(False)
            logger.info("ELM zero check: off")

        elm2 = self.station.instruments.get(Role.ELM2)
        if elm2 is not None:
            elm2.set_zero_check_enabled(False)
            logger.info("ELM2 zero check: off")

    def initialize_switch(self) -> None:
        switch = self.station.instruments.get(Role.SWITCH)
        if switch is not None:
            switch.open_all_channels()
            logger.info("Switch: opened ALL channels")

    def apply_settle_waiting_time(self) -> None:
        """Wait after output enable/ramp"""
        waiting_time_settle: float = self.state.settle_waiting_time
        logger.debug("apply settle time...")
        time.sleep(waiting_time_settle)
        logger.debug("apply settle time... done.")

    def measure(self) -> None:
        ramp: LinearRange = LinearRange(
            self.state.voltage_begin,
            self.state.voltage_end,
            self.state.voltage_step,
        )

        self.update_message(f"Ramp to {ramp.end} V")
        estimate: Estimate = Estimate(len(ramp))

        self.set_fsm_state(FSMState.RAMPING)

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.context.stop_requested:
                self.update_message("Stopping...")
                return
            self.set_source_voltage(voltage)

            self.apply_waiting_time()

            self.acquire_reading(voltage)

            self.check_current_compliance()
            self.update_current_compliance()

            if self.bias_source_instrument:
                self.check_bias_current_compliance()
                self.update_bias_current_compliance()

            estimate.advance()

        self.update_message("")

        if self.context.stop_requested:
            self.update_message("Stopping...")
            return

        if self.state.is_continuous:
            self.update_message("Continuous measurement...")
            self.set_fsm_state(FSMState.CONTINUOUS)
            self.acquire_continuous_reading()

    def finalize(self) -> None:
        try:
            if self.tcu_actor is not None:
                self.tcu_actor.stop()

            self.finalize_elms()

            self.ramp_to_zero()

            if self.bias_source_instrument:
                self.ramp_bias_to_zero()

            self.finalize_lcr()

            self.assure_discharge()

            self.set_source_output_state(False)

            if self.bias_source_instrument:
                self.set_bias_source_output_state(False)

            self.finalize_switch()
        finally:
            if self.tcu_actor is not None:
                self.tcu_actor.stop()

            self.submit_update(
                {
                    "source_voltage": None,
                    "bias_source_voltage": None,
                    "smu_voltage": None,
                    "smu_current": None,
                    "smu2_voltage": None,
                    "smu2_current": None,
                    "elm_current": None,
                    "elm2_current": None,
                    "lcr_capacity": None,
                    "dmm_temperature": None,
                }
            )

    def finalize_elms(self) -> None:
        elm = self.station.instruments.get(Role.ELM)
        if elm is not None:
            elm.set_zero_check_enabled(True)
            logger.info("ELM zero check: on")

        elm2 = self.station.instruments.get(Role.ELM2)
        if elm2 is not None:
            elm2.set_zero_check_enabled(True)
            logger.info("ELM2 zero check: on")

    def finalize_lcr(self) -> None:
        lcr = self.station.instruments.get(Role.LCR)
        if lcr is not None and hasattr(lcr, "finalize"):
            lcr.finalize()

    def finalize_switch(self) -> None:
        switch = self.station.instruments.get(Role.SWITCH)
        if switch:
            switch.open_all_channels()
            logger.info("Switch: opened ALL channels")

    def assure_discharge(self) -> None:
        """Wait until capacitors discared before output disable."""

        discharge_timeout: float = self.state.discharge_timeout
        discharge_threshold: float = abs(self.state.discharge_threshold)

        def read_source_voltage():
            if isinstance(self.source_instrument, VoltageMeasurable):
                return self.source_instrument.measure_v()
            logger.warning("Source instrument does not provide voltage readings.")
            return 0.0

        self.update_message("Waiting for voltage settled...")
        self.update_progress(0, 0, 0)

        start = time.monotonic()

        while abs(read_source_voltage()) > discharge_threshold:
            time.sleep(1.0)

            delta = time.monotonic() - start
            if delta > discharge_timeout:
                raise TimeoutError(
                    f"Timeout while waiting for voltage to settle < {discharge_threshold} V, source output still enabled."
                )

        self.update_message("")

    def acquire_reading(self, source_voltage: float) -> None:
        raise NotImplementedError

    def acquire_reading_data(self, source_voltage: float) -> IVReading:
        raise NotImplementedError

    def acquire_continuous_reading(self) -> None: ...

    def ramp_to_begin(self) -> None:
        source_voltage = self.get_source_voltage()
        voltage_begin: float = self.state.voltage_begin
        voltage_end: float = self.state.voltage_end
        voltage_step: float = 5.0
        waiting_time: float = 0.250

        # Set voltage range according to highest voltage in ramp.
        # Including reverse ramps, eg. -100V...+10V -> range is 100V
        self.set_source_voltage_range(max(abs(voltage_begin), abs(voltage_end)))

        ramp: LinearRange = LinearRange(source_voltage, voltage_begin, voltage_step)
        estimate: Estimate = Estimate(len(ramp))

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.context.stop_requested:
                break
            self.set_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()

    def ramp_to_zero(self) -> None:
        source_voltage = self.get_source_voltage()
        self.submit_update(
            {
                "smu_voltage": None,
                "smu_current": None,
                "smu2_voltage": None,
                "smu2_current": None,
                "elm_current": None,
                "elm2_current": None,
                "lcr_capacity": None,
                "dmm_temperature": None,
                "tcu_temperature": None,
                "tcu_humidity": None,
                "tcu_state": None,
            }
        )

        source_voltage_end: float = 0.0
        source_voltage_step: float = 5.0
        waiting_time: float = 0.250

        ramp: LinearRange = LinearRange(
            source_voltage, source_voltage_end, source_voltage_step
        )
        estimate: Estimate = Estimate(len(ramp))
        logger.info("Ramp source to zero...")
        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            self.set_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()
        logger.info("Ramp source to zero... done.")

    def ramp_bias_to_bias(self) -> None:
        bias_voltage_end: float = self.state.bias_voltage
        self.set_bias_source_voltage_range(bias_voltage_end)

        bias_voltage_begin: float = 0.0
        bias_voltage_step: float = 5.0
        waiting_time: float = 0.250

        ramp: LinearRange = LinearRange(
            bias_voltage_begin, bias_voltage_end, bias_voltage_step
        )
        estimate: Estimate = Estimate(len(ramp))

        logger.info("Ramp bias source to %g V...", ramp.end)
        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp bias to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.context.stop_requested:
                break
            self.set_bias_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()
        logger.info("Ramp bias source to %g V... done.", ramp.end)

    def ramp_bias_to_zero(self) -> None:
        bias_source_voltage: float = self.get_bias_source_voltage()
        end_voltage: float = 0.0
        step_voltage: float = 5.0
        waiting_time: float = 0.250
        self.submit_update(
            {
                "smu_voltage": None,
                "smu_current": None,
                "smu2_voltage": None,
                "smu2_current": None,
                "elm_current": None,
                "elm2_current": None,
                "lcr_capacity": None,
                "dmm_temperature": None,
                "tcu_temperature": None,
                "tcu_humidity": None,
                "tcu_state": None,
            }
        )
        ramp: LinearRange = LinearRange(bias_source_voltage, end_voltage, step_voltage)
        estimate: Estimate = Estimate(len(ramp))
        logger.info("Ramp bias source to zero...")
        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp bias to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            self.set_bias_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()
        logger.info("Ramp bias source to zero... done.")

    def ramp_to_continuous(
        self, end_voltage: float, step_voltage: float, waiting_time: float
    ) -> None:
        source_voltage: float = self.get_source_voltage()

        ramp: LinearRange = LinearRange(source_voltage, end_voltage, step_voltage)
        estimate: Estimate = Estimate(len(ramp))

        # If end voltage higher, set new range before ramp.
        if abs(ramp.end) > abs(ramp.begin):
            self.set_source_voltage_range(ramp.end)

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.context.stop_requested:
                self.update_message("Stopping...")
                return

            self.set_source_voltage(voltage)

            time.sleep(waiting_time)

            reading: IVReading = self.acquire_reading_data(voltage)
            logger.info(reading)

            self.on_it_reading(reading)

            self.submit_update(
                {
                    "smu_voltage": reading.v_smu,
                    "smu_current": reading.i_smu,
                    "smu2_voltage": reading.v_smu2,
                    "smu2_current": reading.i_smu2,
                    "elm_current": reading.i_elm,
                    "elm2_current": reading.i_elm2,
                }
            )

            self.check_current_compliance()
            self.update_current_compliance()

            if self.bias_source_instrument:
                self.check_bias_current_compliance()
                self.update_bias_current_compliance()

            estimate.advance()

        # If end voltage lower, set new range after ramp.
        if abs(ramp.end) < abs(ramp.begin):
            self.set_source_voltage_range(ramp.end)
