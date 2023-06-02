import contextlib
import logging
import time

from typing import Any, Callable, Dict, List

from ..resource import Resource, AutoReconnectResource
from ..driver import driver_factory

from ..functions import LinearRange
from ..estimate import Estimate

__all__ = ["Measurement", "RangeMeasurement"]

logger = logging.getLogger(__name__)

ReadingType = Dict[str, Any]
StateType = Dict[str, Any]


class EventHandler:

    def __init__(self) -> None:
        self.handlers: List[Callable] = []

    def subscribe(self, handler: Callable) -> None:
        self.handlers.append(handler)

    def __call__(self, *args, **kwargs) -> None:
        for handler in self.handlers:
            handler(*args, **kwargs)


class Measurement:

    def __init__(self, state: StateType) -> None:
        super().__init__()
        self.state: StateType = state
        self.instruments: Dict = {}
        self._instruments: Dict = {}
        self.started_event: EventHandler = EventHandler()
        self.finished_event: EventHandler = EventHandler()
        self.failed_event: EventHandler = EventHandler()
        self.update_event: EventHandler = EventHandler()

    def register_instrument(self, name: str) -> None:
        role = self.state.get("roles", {}).get(name, {})
        if not role.get("enabled"):
            return None
        model = role.get("model")
        resource_name = role.get("resource_name")
        if not resource_name.strip():
            raise ValueError(f"Empty resource name not allowed for {name.upper()} ({model}).")
        visa_library = role.get("visa_library")
        termination = role.get("termination")
        timeout = role.get("timeout") * 1000  # in millisecs
        cls = driver_factory(model)
        if not cls:
            logger.warning("No such driver: %s", model)
            return None
        # If auto reconnect use experimental class AutoReconnectResource
        auto_reconnect = self.state.get("auto_reconnect", False)
        resource_cls = AutoReconnectResource if auto_reconnect else Resource
        resource = resource_cls(
            resource_name=resource_name,
            visa_library=visa_library,
            read_termination=termination,
            write_termination=termination,
            timeout=timeout
        )
        self._instruments[name] = cls, resource

    def check_error_state(self, context) -> None:
        code, message = context.error_state()
        if code:
            raise RuntimeError(f"Instrument Error: {code}: {message}")

    def update_rpc_state(self, state) -> None:
        self.update_event({"rpc_state": state})

    @property
    def stop_requested(self) -> bool:
        return self.state.get("stop_requested") is True

    def initialize(self) -> None:
        ...

    def measure(self) -> None:
        ...

    def finalize(self) -> None:
        ...

    def run(self) -> None:
        try:
            logger.debug("run measurement...")
            self.update_rpc_state("configure")
            logger.debug("handle started callbacks...")
            self.started_event()
            logger.debug("handle started callbacks... done.")
            self.instruments.clear()
            with contextlib.ExitStack() as stack:
                logger.debug("creating instrument contexts...")
                for key, value in self._instruments.items():
                    cls, resource = value
                    logger.debug("creating instrument context %s: %s...", key, cls.__name__)
                    context = cls(stack.enter_context(resource))
                    self.instruments[key] = context
                logger.debug("creating instrument contexts... done.")
                try:
                    logger.debug("initialize...")
                    self.initialize()
                    logger.debug("initialize... done.")
                    logger.debug("measure...")
                    self.measure()
                    logger.debug("measure... done.")
                except Exception as exc:
                    logger.exception(exc)
                    self.failed_event(exc)
                finally:
                    logger.debug("finalize...")
                    self.update_rpc_state("stopping")
                    self.finalize()
                    logger.debug("finalize... done.")
        except Exception as exc:
            logger.exception(exc)
            self.failed_event(exc)
        finally:
            logger.debug("handle finished callbacks...")
            self.finished_event()
            logger.debug("handle finished callbacks... done.")
            self.instruments.clear()
            self.update_rpc_state("idle")
            logger.debug("run measurement... done.")


class RangeMeasurement(Measurement):

    def __init__(self, state: StateType) -> None:
        super().__init__(state)
        self.it_reading_event: EventHandler = EventHandler()
        self.it_change_voltage_ready_event: EventHandler = EventHandler()

    @property
    def is_continuous(self) -> bool:
        return self.state.get("continuous") is True

    # Source

    def get_source_output_state(self) -> bool:
        return self.source_instrument.get_output_enabled()

    def set_source_output_state(self, state: bool) -> None:
        logger.info("Source output state: %s", state)
        self.source_instrument.set_output_enabled(state)
        self.update_event({"source_output_state": state})
        self.state.update({"source_output_state": state})

    def get_source_voltage(self) -> float:
        return self.source_instrument.get_voltage_level()

    def set_source_voltage(self, voltage: float) -> None:
        logger.info("Source voltage level: %gV", voltage)
        self.source_instrument.set_voltage_level(voltage)
        self.update_event({"source_voltage": voltage})
        self.state.update({"source_voltage": voltage})

    def set_source_voltage_range(self, voltage: float) -> None:
        logger.info("Source voltage range: %gV", voltage)
        self.source_instrument.set_voltage_range(voltage)

    # Bias source

    def get_bias_source_output_state(self) -> bool:
        return self.bias_source_instrument.get_output_enabled()

    def set_bias_source_output_state(self, state: bool) -> None:
        logger.info("Bias source output state: %s", state)
        self.bias_source_instrument.set_output_enabled(state)
        self.update_event({"bias_source_output_state": state})
        self.state.update({"bias_source_output_state": state})

    def get_bias_source_voltage(self) -> float:
        return self.bias_source_instrument.get_voltage_level()

    def set_bias_source_voltage(self, voltage: float) -> None:
        logger.info("Bias source voltage level: %gV", voltage)
        self.bias_source_instrument.set_voltage_level(voltage)
        self.update_event({"bias_source_voltage": voltage})
        self.state.update({"bias_source_voltage": voltage})

    def set_bias_source_voltage_range(self, voltage: float) -> None:
        logger.info("Bias source voltage range: %gV", voltage)
        self.bias_source_instrument.set_voltage_range(voltage)

    def check_current_compliance(self) -> None:
        """Raise exception if current compliance tripped and continue in
        compliance option is not active.
        """
        if not self.state.get("continue_in_compliance", False):
            if self.source_instrument.compliance_tripped():
                raise RuntimeError("Source compliance tripped!")

    def update_current_compliance(self) -> None:
        """Update current compliance if value changed."""
        current_compliance = self.state.get("current_compliance", 0.0)
        if self.current_compliance != current_compliance:
            self.current_compliance = current_compliance
            self.set_source_compliance(self.current_compliance)
            self.check_error_state(self.source_instrument)

    def set_source_compliance(self, compliance: float) -> None:
        logger.info("Source current compliance level: %gA", compliance)
        self.source_instrument.set_current_compliance_level(compliance)

    def set_bias_source_compliance(self, compliance: float) -> None:
        logger.info("Bias source current compliance level: %gA", compliance)
        self.bias_source_instrument.set_current_compliance_level(compliance)

    def check_bias_current_compliance(self) -> None:
        """Raise exception if biascurrent compliance tripped and continue in
        compliance option is not active.
        """
        if not self.state.get("continue_in_compliance", False):
            if self.bias_source_instrument.compliance_tripped():
                raise RuntimeError("Source compliance tripped!")

    def update_bias_current_compliance(self) -> None:
        """Update current compliance if value changed."""
        current_compliance = self.state.get("current_compliance", 0.0)
        if self.bias_current_compliance != current_compliance:
            self.bias_current_compliance = current_compliance
            self.set_bias_source_compliance(self.bias_current_compliance)
            self.check_error_state(self.bias_source_instrument)

    def apply_waiting_time(self) -> None:
        waiting_time: float = self.state.get("waiting_time", 1.0)
        logger.info("Waiting for %.2f sec", waiting_time)
        time.sleep(waiting_time)

    def apply_waiting_time_continuous(self, estimate: Estimate) -> None:
        waiting_time: float = self.state.get("waiting_time_continuous", 1.0)
        interval: float = 1.0
        logger.info("Waiting for %.2f sec", waiting_time)
        if waiting_time < interval:
            time.sleep(waiting_time)
        else:
            now: float = time.time()
            threshold: float = now + waiting_time
            while now < threshold:
                if self.stop_requested:
                    self.update_message("Stopping...")
                    break
                if self.state.get("change_voltage_continuous"):
                    break
                remaining: float = round(threshold - now)
                self.update_estimate_message_continuous(f"Next reading in {remaining:d} sec...", estimate)
                time.sleep(interval)
                now = time.time()

    def apply_change_voltage(self):
        params = self.state.get("change_voltage_continuous")
        if params is not None:
            del self.state.state["change_voltage_continuous"]  # TODO
            self.update_rpc_state("ramping")
            self.ramp_to_continuous(params.get("end_voltage"), params.get("step_voltage"), params.get("waiting_time"))
            if not self.stop_requested:  # hack
                self.update_rpc_state("continuous")
        self.it_change_voltage_ready_event()

    def update_message(self, message: str) -> None:
        """Emit update message event."""
        self.update_event({"message": message})

    def update_progress(self, begin: int, end: int, step: int) -> None:
        """Emit update progress event."""
        self.update_event({"progress": (begin, end, step)})

    def update_estimate_message(self, message: str, estimate: Estimate) -> None:
        """Emit update message event for ramp iterations."""
        elapsed_time = format(estimate.elapsed).split(".")[0]
        remaining_time = format(estimate.remaining).split(".")[0]
        average_time = format(estimate.average.total_seconds(), ".2f")
        self.update_message(f"{message} | Elapsed {elapsed_time} | Remaining {remaining_time} | Average {average_time} s")

    def update_estimate_message_continuous(self, message: str, estimate: Estimate) -> None:
        """Emit update message event for continuous iterations."""
        elapsed_time = format(estimate.elapsed).split(".")[0]
        average_time = format(estimate.average.total_seconds(), ".3f")
        self.update_message(f"{message} | Elapsed {elapsed_time} | Average {average_time} s")

    def update_estimate_progress(self, estimate: Estimate) -> None:
        """Emit update progress event for ramp iterations."""
        self.update_progress(0, estimate.count, estimate.passed)

    def initialize(self) -> None:
        source: str = self.state.get("source_role")
        if source in self.instruments:
            self.source_instrument = self.instruments.get(source)
        else:
            raise RuntimeError("No source instrument set")

        # Bias

        self.bias_source_instrument = None
        if self.state.get("measurement_type") in ["iv_bias"]:  # TODO
            bias_source: str = self.state.get("bias_source_role")
            if bias_source in self.instruments:
                self.bias_source_instrument = self.instruments.get(bias_source)
            else:
                raise RuntimeError("No bias source instrument set")

        logger.debug("querying context identities...")
        for key, context in self.instruments.items():
            logger.debug("reading %s identity...", key.upper())
            identity: str = context.identity()
            logger.debug("reading %s identity... done.", key.upper())
            logger.info("%s IDN: %s", key.upper(), identity)
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

        # Reset (optional)
        if self.state.get("reset"):
            for key, context in self.instruments.items():
                logger.info("Reset %s...", key.upper())
                context.reset()
                logger.info("Reset %s... done.", key.upper())

        # Clear state
        for key, context in self.instruments.items():
            logger.info("Clear %s...", key.upper())
            context.clear()
            logger.info("Clear %s... done.", key.upper())

        # Configure
        for key, context in self.instruments.items():
            logger.info("Configure %s...", key.upper())
            options = self.state.get("roles", {}).get(key, {}).get("options", {})
            for name, value in options.items():
                logger.info("%s: %r" , name, value)
            context.configure(options)
            self.check_error_state(context)
            logger.info("Configure %s... done.", key.upper())

        # Compliance
        self.current_compliance = self.state.get("current_compliance", 0.0)
        self.set_source_compliance(self.current_compliance)
        self.check_error_state(self.source_instrument)

        self.bias_current_compliance = self.state.get("current_compliance", 0.0)
        if self.bias_source_instrument:
            self.set_bias_source_compliance(self.bias_current_compliance)
            self.check_error_state(self.bias_source_instrument)

        if self.bias_source_instrument:
            self.set_bias_source_output_state(True)
            self.ramp_bias_to_bias()
            self.check_error_state(self.bias_source_instrument)

        # Enable output
        self.set_source_output_state(True)

        elm = self.instruments.get("elm")
        if elm is not None:
            elm.set_zero_check_enabled(False)
            logger.info("ELM zero check: off")

        elm2 = self.instruments.get("elm2")
        if elm2 is not None:
            elm2.set_zero_check_enabled(False)
            logger.info("ELM2 zero check: off")

        self.ramp_to_begin()

        # Wait after output enable/ramp
        waiting_time_settle: float = 1.0
        logger.debug("apply settle time...")
        time.sleep(waiting_time_settle)
        logger.debug("apply settle time... done.")

    def measure(self) -> None:
        ramp: LinearRange = LinearRange(
            self.state.get("voltage_begin"),
            self.state.get("voltage_end"),
            self.state.get("voltage_step")
        )

        self.update_message(f"Ramp to {ramp.end} V")
        estimate: Estimate = Estimate(len(ramp))

        self.update_rpc_state("ramping")

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.stop_requested:
                self.update_message("Stopping...")
                return
            self.set_source_voltage(voltage)

            self.apply_waiting_time()

            self.acquire_reading()

            self.check_current_compliance()
            self.update_current_compliance()

            if self.bias_source_instrument:
                self.check_bias_current_compliance()
                self.update_bias_current_compliance()

            estimate.advance()

        self.update_rpc_state("measure")

        self.update_message("")

        if self.stop_requested:
            self.update_message("Stopping...")
            return

        if self.is_continuous:
            self.update_message("Continuous measurement...")
            self.update_rpc_state("continuous")
            self.acquire_continuous_reading()

    def finalize(self) -> None:
        try:
            elm = self.instruments.get("elm")
            if elm is not None:
                elm.set_zero_check_enabled(True)
                logger.info("ELM zero check: on")

            elm2 = self.instruments.get("elm2")
            if elm2 is not None:
                elm2.set_zero_check_enabled(True)
                logger.info("ELM2 zero check: on")

            self.ramp_to_zero()

            if self.bias_source_instrument:
                self.ramp_bias_to_zero()

            # HACK: wait until capacitors discared before output disable
            def read_source_voltage():
                if hasattr(self.source_instrument, "read_voltage"):
                    return self.source_instrument.read_voltage()
                logger.warning("Source instrument does not provide voltage readings.")
                return 0.

            threshold: float = 0.5  # Volt

            self.update_message("Waiting for voltage settled...")
            self.update_progress(0, 0, 0)

            t = time.time()

            while abs(read_source_voltage()) > threshold:
                time.sleep(1.0)

                dt = time.time() - t
                if dt > 60.0:
                    raise RuntimeError(f"Timeout while waiting for voltage to settle < {threshold} V, source output still enabled.")

            self.update_message("")

            # HACK: end

            self.set_source_output_state(False)

            if self.bias_source_instrument:
                self.set_bias_source_output_state(False)

        finally:
            self.update_event({
                "source_voltage": None,
                "bias_source_voltage": None,
                "smu_current": None,
                "smu2_current": None,
                "elm_current": None,
                "elm2_current": None,
                "lcr_capacity": None,
                "dmm_temperature": None
            })

    def acquire_reading(self) -> None:
        ...

    def acquire_reading_data(self) -> ReadingType:
        return {}

    def acquire_continuous_reading(self) -> None:
        ...

    def ramp_to_begin(self) -> None:
        # Set voltage range to end voltage
        voltage_end = self.state.get("voltage_end")
        self.set_source_voltage_range(voltage_end)

        source_voltage: float = self.state.get("source_voltage", 0.0)
        voltage_begin = self.state.get("voltage_begin", 0.0)
        voltage_step: float = 5.0
        waiting_time: float = 0.250

        ramp: LinearRange = LinearRange(source_voltage, voltage_begin, voltage_step)
        estimate: Estimate = Estimate(len(ramp))

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.stop_requested:
                break
            self.set_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()

    def ramp_to_zero(self) -> None:
        source_voltage = self.get_source_voltage()
        self.update_event({
            "smu_current": None,
            "smu2_current": None,
            "elm_current": None,
            "elm2_current": None,
            "lcr_capacity": None,
            "dmm_temperature": None
        })

        source_voltage_end: float = 0.0
        source_voltage_step: float = 5.0
        waiting_time: float = 0.250

        ramp: LinearRange = LinearRange(source_voltage, source_voltage_end, source_voltage_step)
        estimate: Estimate = Estimate(len(ramp))
        logging.info("Ramp source to zero...")
        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            self.set_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()
        logging.info("Ramp source to zero... done.")

    def ramp_bias_to_bias(self) -> None:
        bias_voltage_end: float = self.state.get("bias_voltage", 0.0)
        self.set_bias_source_voltage_range(bias_voltage_end)

        bias_voltage_begin: float = 0.0
        bias_voltage_step: float = 5.0
        waiting_time: float = 0.250

        ramp: LinearRange = LinearRange(bias_voltage_begin, bias_voltage_end, bias_voltage_step)
        estimate: Estimate = Estimate(len(ramp))

        logging.info("Ramp bias source to %g V...", ramp.end)
        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp bias to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.stop_requested:
                break
            self.set_bias_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()
        logging.info("Ramp bias source to %g V... done.", ramp.end)

    def ramp_bias_to_zero(self) -> None:
        bias_source_voltage: float = self.state.get("bias_source_voltage", 0.0)
        end_voltage: float = 0.0
        step_voltage: float = 5.0
        waiting_time: float = 0.250
        self.update_event({
            "smu_current": None,
            "smu2_current": None,
            "elm_current": None,
            "elm2_current": None,
            "lcr_capacity": None,
            "dmm_temperature": None
        })
        ramp: LinearRange = LinearRange(bias_source_voltage, end_voltage, step_voltage)
        estimate: Estimate = Estimate(len(ramp))
        logging.info("Ramp bias source to zero...")
        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp bias to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            self.set_bias_source_voltage(voltage)
            time.sleep(waiting_time)
            estimate.advance()
        logging.info("Ramp bias source to zero... done.")

    def ramp_to_continuous(self, end_voltage: float, step_voltage: float, waiting_time: float) -> None:
        source_voltage: float = self.state.get("source_voltage", 0.0)

        ramp: LinearRange = LinearRange(source_voltage, end_voltage, step_voltage)
        estimate: Estimate = Estimate(len(ramp))

        # If end voltage higher, set new range before ramp.
        if abs(ramp.end) > abs(ramp.begin):
            self.set_source_voltage_range(ramp.end)

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(f"Ramp to {ramp.end} V", estimate)
            self.update_estimate_progress(estimate)

            if self.stop_requested:
                self.update_message("Stopping...")
                return

            self.set_source_voltage(voltage)

            time.sleep(waiting_time)

            reading = self.acquire_reading_data()
            logger.info(reading)

            # TODO
            if hasattr(self, "itReadingLock") and hasattr(self, "itReadingQueue"):
                with self.itReadingLock:
                    self.itReadingQueue.append(reading)

            self.it_reading_event(reading)

            self.update_event({
                "smu_current": reading.get("i_smu"),
                "smu2_current": reading.get("i_smu2"),
                "elm_current": reading.get("i_elm"),
                "elm2_current": reading.get("i_elm2"),
            })

            self.check_current_compliance()
            self.update_current_compliance()

            if self.bias_source_instrument:
                self.check_bias_current_compliance()
                self.update_bias_current_compliance()

            estimate.advance()

        # If end voltage lower, set new range after ramp.
        if abs(ramp.end) < abs(ramp.begin):
            self.set_source_voltage_range(ramp.end)
