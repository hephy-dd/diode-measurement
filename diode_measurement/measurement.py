import time
import contextlib
import logging

from PyQt5 import QtCore

from .resource import Resource

from .driver.k237 import K237
from .driver.k595 import K595
from .driver.k2410 import K2410
from .driver.k2470 import K2470
from .driver.k2657a import K2657A
from .driver.k6514 import K6514
from .driver.k6517b import K6517B
from .driver.e4980a import E4980A

from .functions import LinearRange
from .estimate import Estimate

logger = logging.getLogger(__name__)

DRIVERS = {
    'K237': K237,
    'K595': K595,
    'K2410': K2410,
    'K2470': K2470,
    'K2657A': K2657A,
    'K6514': K6514,
    'K6517B': K6517B,
    'E4980A': E4980A
}


class Measurement(QtCore.QObject):

    started = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    update = QtCore.pyqtSignal(dict)

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.contexts = {}
        self._registered = {}

    def registerInstrument(self, name, cls, resource):
        self._registered[name] = cls, resource

    def prepareDriver(self, name):
        role = self.state.get(name, {})
        if not role.get("enabled"):
            return None
        model = role.get('model')
        resource_name = role.get('resource_name')
        if not resource_name.strip():
            raise ValueError(f"Empty resource name not allowed for {name.upper()} ({model}).")
        visa_library = role.get('visa_library')
        termination = role.get('termination')
        timeout = role.get('timeout') * 1000  # in millisecs
        cls = DRIVERS.get(model)
        if not cls:
            logger.warning("No such driver: %s", model)
            return None
        resource = Resource(
            resource_name=resource_name,
            visa_library=visa_library,
            read_termination=termination,
            write_termination=termination,
            timeout=timeout
        )
        self.registerInstrument(name, cls, resource)

    def checkErrorState(self, context):
        code, message = context.error_state()
        if code:
            raise RuntimeError(f"Instrument Error: {code}: {message}")

    def initialize(self):
        pass

    def measure(self):
        pass

    def finalize(self):
        pass

    def run(self):
        try:
            self.started.emit()
            self.contexts.clear()
            with contextlib.ExitStack() as stack:
                for key, value in self._registered.items():
                    cls, resource = value
                    context = cls(stack.enter_context(resource))
                    self.contexts[key] = context
                try:
                    self.initialize()
                    self.measure()
                finally:
                    self.finalize()
        finally:
            self.contexts.clear()
            self.finished.emit()


class RangeMeasurement(Measurement):

    def __init__(self, state):
        super().__init__(state)

    def get_source_output_state(self):
        return self.source_instrument.get_output_enabled()

    def set_source_output_state(self, state):
        logger.info("Source output state: %s", state)
        self.source_instrument.set_output_enabled(state)
        self.update.emit({'source_output_state': state})
        self.state['source_output_state'] = state

    def get_source_voltage(self):
        return self.source_instrument.get_voltage_level()

    def set_source_voltage(self, voltage):
        logger.info("Source voltage level: %gV", voltage)
        self.source_instrument.set_voltage_level(voltage)
        self.update.emit({'source_voltage': voltage})
        self.state['source_voltage'] = voltage

    def set_source_voltage_range(self, voltage):
        logger.info("Source voltage range: %gV", voltage)
        self.source_instrument.set_voltage_range(voltage)

    def check_current_compliance(self):
        """Raise exception if current compliance tripped and continue in
        compliance option is not active.
        """
        if not self.state.get('continue_in_compliance', False):
            if self.source_instrument.compliance_tripped():
                raise RuntimeError("Source compliance tripped!")

    def update_current_compliance(self):
        """Update current compliance if value changed."""
        current_compliance = self.state.get('current_compliance', 0.0)
        if self.current_compliance != current_compliance:
            self.current_compliance = current_compliance
            self.set_source_compliance(self.current_compliance)
            self.checkErrorState(self.source_instrument)

    def set_source_compliance(self, compiance):
        logger.info("Source current compliance level: %gA", compiance)
        self.source_instrument.set_current_compliance_level(compiance)

    def apply_waiting_time(self):
        waiting_time = self.state.get('waiting_time', 1.0)
        logger.info("Waiting for %.2f sec", waiting_time)
        time.sleep(waiting_time)

    def apply_waiting_time_continuous(self):
        waiting_time = self.state.get('waiting_time_continuous', 1.0)
        logger.info("Waiting for %.2f sec", waiting_time)
        interval = 1.0
        if waiting_time < interval:
            time.sleep(waiting_time)
        else:
            now = time.time()
            threshold = now + waiting_time
            while now < threshold:
                if self.state.get('stop_requested'):
                    self.update_message("Stopping...")
                    break
                if self.state.get('change_voltage_continuous'):
                    break
                remaining = round(threshold - now)
                self.update_message(f"Next reading in {remaining:d} sec...")
                time.sleep(interval)
                now = time.time()

    def apply_change_voltage(self):
        params = self.state.get('change_voltage_continuous')
        if params is not None:
            del self.state['change_voltage_continuous']
            self.rampToContinuous(params.get("end_voltage"), params.get("step_voltage"), params.get("waiting_time"))
        self.itChangeVoltageReady.emit()

    def update_message(self, message: str) -> None:
        """Emit update message event."""
        self.update.emit({"message": message})

    def update_progress(self, begin: int, end: int, step: int) -> None:
        """Emit update progress event."""
        self.update.emit({"progress": (begin, end, step)})

    def update_estimate_message(self, voltage: float, estimate: Estimate) -> None:
        """Emit update message event for ramp iterations."""
        elapsed_time = format(estimate.elapsed).split('.')[0]
        remaining_time = format(estimate.remaining).split('.')[0]
        self.update_message(f"Ramp to {voltage} V | Elapsed {elapsed_time} | Remaining {remaining_time}")

    def update_estimate_progress(self, estimate: Estimate) -> None:
        """Emit update progress event for ramp iterations."""
        self.update_progress(0, estimate.count, estimate.passed)

    def initialize(self):
        source = self.state.get('source')
        if source in self.contexts:
            self.source_instrument = self.contexts.get(source)
        else:
            raise RuntimeError("No source instrument set")

        for key, context in self.contexts.items():
            logging.info("%s IDN: %s", key.upper(), context.identity())

        source_output_state = self.get_source_output_state()

        if source_output_state:
            self.rampZero()
        else:
            self.set_source_voltage(0.0)

        # Reset (optional)
        if self.state.get('reset'):
            for key, context in self.contexts.items():
                logging.info("Reset %s...", key.upper())
                context.reset()

        # Clear state
        for key, context in self.contexts.items():
            logging.info("Clear %s...", key.upper())
            context.clear()

        # Configure
        for key, context in self.contexts.items():
            logging.info("%s IDN: %s", key.upper(), context.identity())
            context.configure()
            self.checkErrorState(context)

        # Compliance
        self.current_compliance = self.state.get('current_compliance', 0.0)
        self.set_source_compliance(self.current_compliance)
        self.checkErrorState(self.source_instrument)

        # Enable output
        self.set_source_output_state(True)

        self.rampBegin()

        # Wait after output enable/ramp
        time.sleep(1.0)

    def measure(self):
        ramp = LinearRange(
            self.state.get('voltage_begin'),
            self.state.get('voltage_end'),
            self.state.get('voltage_step')
        )

        self.update_message(f"Ramp to {ramp.end} V")
        estimate = Estimate(len(ramp))

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(ramp.end, estimate)
            self.update_estimate_progress(estimate)

            if self.state.get('stop_requested'):
                self.update_message("Stopping...")
                return
            self.set_source_voltage(voltage)

            self.apply_waiting_time()

            self.acquireReading()
            self.check_current_compliance()
            self.update_current_compliance()

            estimate.advance()

        self.update_message("")

        if self.state.get('stop_requested'):
            self.update_message("Stopping...")
            return

        if self.state.get('continuous'):
            self.update_message("Continuous measurement...")
            self.acquireContinuousReading()

    def finalize(self):
        try:
            self.rampZero()
        finally:
            self.set_source_output_state(False)
            self.update.emit({
                'source_voltage': None,
                'smu_current': None,
                'elm_current': None,
                'lcr_capacity': None
            })

    def acquireReading(self):
        pass

    def acquireContinuousReading(self):
        pass

    def rampBegin(self):
        # Set voltage range to end voltage
        voltage_end = self.state.get('voltage_end')
        self.set_source_voltage_range(voltage_end)

        voltage_begin = self.state.get('voltage_begin', 0.0)
        ramp = LinearRange(
            self.state.get('source_voltage', 0.0),
            voltage_begin,
            5.0
        )
        estimate = Estimate(len(ramp))

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(ramp.end, estimate)
            self.update_estimate_progress(estimate)

            if self.state.get('stop_requested'):
                break
            self.set_source_voltage(voltage)
            time.sleep(.250)
            estimate.advance()

    def rampZero(self):
        source_voltage = self.state.get('source_voltage', 0.0)
        self.update.emit({
            'smu_current': None,
            'elm_current': None,
            'lcr_capacity': None
        })
        ramp = LinearRange(source_voltage, 0.0, 5.0)
        estimate = Estimate(len(ramp))
        for step, voltage in enumerate(ramp):
            self.update_estimate_message(ramp.end, estimate)
            self.update_estimate_progress(estimate)

            self.set_source_voltage(voltage)
            time.sleep(.250)
            estimate.advance()

    def rampToContinuous(self, end_voltage, step_voltage, waiting_time):
        source_voltage = self.state.get('source_voltage', 0.0)

        ramp = LinearRange(source_voltage, end_voltage, step_voltage)
        estimate = Estimate(len(ramp))

        # If end voltage higher, set new range before ramp.
        if abs(ramp.end) > abs(ramp.begin):
            self.set_source_voltage_range(ramp.end)

        for step, voltage in enumerate(ramp):
            self.update_estimate_message(ramp.end, estimate)
            self.update_estimate_progress(estimate)

            if self.state.get('stop_requested'):
                self.update_message("Stopping...")
                return

            self.set_source_voltage(voltage)

            time.sleep(waiting_time)

            reading = self.acquireReadingData()
            logging.info(reading)
            self.itReading.emit(reading)
            self.update.emit({
                'smu_current': reading.get('i_smu'),
                'elm_current': reading.get('i_elm')
            })

            self.check_current_compliance()
            self.update_current_compliance()

            estimate.advance()

        # If end voltage lower, set new range after ramp.
        if abs(ramp.end) < abs(ramp.begin):
            self.set_source_voltage_range(ramp.end)


class IVMeasurement(RangeMeasurement):

    ivReading = QtCore.pyqtSignal(dict)
    itReading = QtCore.pyqtSignal(dict)
    itChangeVoltageReady = QtCore.pyqtSignal()

    def __init__(self, state):
        super().__init__(state)

    def measure(self):
        super().measure()
        if self.state.get('continuous'):
            self.acquireContinuousReading()

    def acquireReadingData(self):
        smu = self.contexts.get('smu')
        elm = self.contexts.get('elm')
        voltage = self.get_source_voltage()
        if smu:
            i_smu = smu.read_current()
        else:
            i_smu = float('NaN')
        if elm:
            i_elm = elm.read_current()
        else:
            i_elm = float('NaN')
        return {
            'timestamp': time.time(),
            'voltage': voltage,
            'i_smu': i_smu,
            'i_elm': i_elm
        }

    def acquireReading(self):
        reading = self.acquireReadingData()
        logging.info(reading)
        self.ivReading.emit(reading)
        self.update.emit({
            'smu_current': reading.get('i_smu'),
            'elm_current': reading.get('i_elm')
        })

    def acquireContinuousReading(self):
        while not self.state.get('stop_requested'):
            self.update_message("Reading...")
            self.update_progress(0, 0, 0)
            reading = self.acquireReadingData()
            logging.info(reading)
            self.itReading.emit(reading)
            self.update.emit({
                'smu_current': reading.get('i_smu'),
                'elm_current': reading.get('i_elm')
            })

            self.check_current_compliance()
            self.update_current_compliance()

            self.apply_change_voltage()

            self.apply_waiting_time_continuous()


class CVMeasurement(RangeMeasurement):

    cvReading = QtCore.pyqtSignal(dict)

    def __init__(self, state):
        super().__init__(state)

    def acquireReadingData(self):
        smu = self.contexts.get('smu')
        lcr = self.contexts.get('lcr')
        voltage = self.get_source_voltage()
        if lcr:
            c_lcr = lcr.read_capacity()
        else:
            c_lcr = float('NaN')
        if smu:
            i_smu = smu.read_current()
        else:
            i_smu = float('NaN')
        return {
            'timestamp': time.time(),
            'voltage': voltage,
            'i_smu': i_smu,
            'c_lcr': c_lcr
        }

    def acquireReading(self):
        reading = self.acquireReadingData()
        self.cvReading.emit(reading)
        self.update.emit({
            'smu_current': reading.get('i_smu'),
            'elm_current': reading.get('i_elm'),
            'lcr_capacity': reading.get('c_lcr')
        })
