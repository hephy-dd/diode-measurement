import logging
import time
from collections.abc import Mapping
from enum import StrEnum

import msgspec
import pyvisa.errors

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["K4215Adapter"]

logger = logging.getLogger(__name__)


class ImpedanceType(StrEnum):
    ZTHETA = "ZTHETA"
    RPLUSJX = "RPLUSJX"
    CPRP = "CPRP"
    CPGP = "CPGP"
    CSRS = "CSRS"
    CPD = "CPD"
    CSD = "CSD"
    YTHETA = "YTHETA"


class K4215Config(msgspec.Struct, frozen=True):
    external_bias_tee_enabled: bool = msgspec.field(
        default=False,
        name="external_bias_tee.enabled",
    )
    function_type: ImpedanceType = msgspec.field(
        default=ImpedanceType.CPRP,
        name="function.type",
    )
    aperture: float = msgspec.field(
        default=1.0,
        name="aperture.aperture",
    )
    aperture_filter_factor: int = msgspec.field(
        default=5,
        name="aperture.filter_factor",
    )
    aperture_delay_factor: int = msgspec.field(
        default=10,
        name="aperture.delay_factor",
    )
    correction_length: float = msgspec.field(
        default=0.0,
        name="correction.length",
    )
    correction_open_enabled: bool = msgspec.field(
        default=False,
        name="correction.open.enabled",
    )
    correction_short_enabled: bool = msgspec.field(
        default=False,
        name="correction.short.enabled",
    )
    correction_load_enabled: bool = msgspec.field(
        default=False,
        name="correction.load.enabled",
    )
    voltage: float = 0.1
    frequency: float = 1.0e5
    bias_voltage: float | None = None
    ac_range: float | None = None


class K4215Adapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource
        self._external_bias_tee_enabled: bool = False

    def identify(self) -> str:
        return self._query("*IDN?").strip()

    def reset(self) -> None:
        self._write("*RST")

    def clear(self) -> None:
        self._write("BC")
        # clear last errors
        self._write(":ERROR:LAST:CLEAR")

    def next_error(self) -> InstrumentError | None:
        """Get the next error from the instrument's error queue."""
        # KXCI uses :ERROR:LAST:GET to retrieve the last error
        response = self._query(":ERROR:LAST:GET")
        self._write(":ERROR:LAST:CLEAR")

        # if response is empty, return no error
        if not response.strip():
            return None

        # Try to parse response in standard SCPI format: code,"message"
        if "," in response and '"' in response:
            try:
                return parse_scpi_error(response)
            except Exception:
                logger.exception("failed to parse error message: %r", response)

        # Try to parse response in format: message. (code)
        if "(" in response and ")" in response:
            try:
                code_str = response.split("(")[-1].split(")")[0]
                code = int(code_str)
                message = response.split("(")[0].strip().rstrip(".")
                if code == 0:
                    return None
                return InstrumentError(code, message)
            except Exception:
                logger.exception("failed to parse error message: %r", response)

        # Fallback: return the raw response with error code -1
        return InstrumentError(-1, response.strip())

    def configure(self, options: Mapping[str, object]) -> None:
        """Configure the CVU for measurements options."""
        config = msgspec.convert(options, type=K4215Config)

        # Set CVU mode (0 = user mode)
        self._write(":CVU:MODE 0")

        # Configure external bias tee option
        self._external_bias_tee_enabled = config.external_bias_tee_enabled

        # Enable -10V DC bias for P3 bias tee if selected
        if self._external_bias_tee_enabled:
            self.enable_bias_tee_dc_voltage()

        # Configure impedance/function type
        self.set_function_impedance_type(config.function_type)

        # Configure aperture/speed settings
        self.set_aperture(
            config.aperture,
            config.aperture_filter_factor,
            config.aperture_delay_factor,
        )

        # Configure correction settings
        self.set_correction_length(config.correction_length)
        self.set_correction(
            config.correction_open_enabled,
            config.correction_short_enabled,
            config.correction_load_enabled,
        )

        # Set measurement parameters
        self.set_amplitude_voltage(config.voltage)
        self.set_amplitude_frequency(config.frequency)

        # Set bias voltage only if external bias tee is NOT enabled
        if not config.external_bias_tee_enabled and config.bias_voltage is not None:
            self.set_voltage_level(config.bias_voltage)

        # Set AC impedance range if specified
        if config.ac_range is not None:
            self.set_aci_range(config.ac_range)
        else:
            self.set_aci_range(0)  # Auto range

    def set_aci_range(self, level: float) -> None:
        """Set the AC current measurement range

        Args:
            level (float): AC current range in Amperes. 1E-6, 30E-6, 1E-3
                           For auto range, use 0.
        """

        if level not in [0, 1e-6, 30e-6, 1e-3]:
            raise ValueError("AC current range must be one of: 0, 1uA, 30uA, 1mA")

        self._write(f":CVU:ACZ:RANGE {level:.6E}")

    def set_output_enabled(self, enabled: bool) -> None:
        """Enable or disable the CVU output."""
        value = "1" if enabled else "0"
        self._write(f":CVU:OUTPUT {value}")

    def get_output_enabled(self) -> bool:
        """Check if the CVU output is enabled."""
        # not implemented in K4215
        return False

    def _validate_correction_length(self, length: float) -> None:
        if length not in [0, 1.5, 3.0, 4.0, 5.0, 6.0, 7.0]:
            raise ValueError(
                "Correction length must be one of: 0, 1.5, 3.0, 4.0, 5.0, 6.0 or 7.0"
            )

    def _is_custom_correction_length(self, length: float) -> bool:
        return length == 4.0

    def set_correction_length(self, length: float) -> None:
        """Set cable length correction for the K4215."""
        self._validate_correction_length(length)
        self._write(f":CVU:LENGTH {length:.1f}")

    def set_correction(self, open_state=False, short_state=False, load_state=False):
        """Enable or disable open, short, and load compensation."""
        open_val = 1 if open_state else 0
        short_val = 1 if short_state else 0
        load_val = 1 if load_state else 0
        self._write(f":CVU:CORRECT {open_val},{short_val},{load_val}")

    def has_correction_finished(self) -> bool:
        """4215 CVU does not provide an operation complete meachanism. Starting
        a correction does render the SCPI interface not working, not even
        accepting writes. Only workaround is polling *IDN? until a response is
        returned.
        """
        try:
            self._resource.query("*IDN?")
        except pyvisa.errors.VisaIOError:
            return False
        return True

    def start_open_correction(self, length: float) -> None:
        self._validate_correction_length(length)
        if self._is_custom_correction_length(length):
            self._write(":CVU:CABLE:COMP:MEASCUSTOM")
        self._write(f":CVU:CABLE:COMP:OPEN {length:.1f}")

    def start_short_correction(self, length: float) -> None:
        self._validate_correction_length(length)
        if self._is_custom_correction_length(length):
            self._write(":CVU:CABLE:COMP:MEASCUSTOM")
        self._write(f":CVU:CABLE:COMP:SHORT {length:.1f}")

    def start_load_correction(self, length: float, load: int) -> None:
        self._validate_correction_length(length)
        if load < 0:
            raise ValueError("Correction load must be a positive value")
        if self._is_custom_correction_length(length):
            self._write(":CVU:CABLE:COMP:MEASCUSTOM")
        self._write(f":CVU:CABLE:COMP:LOAD {length:.1f}, {load}")

    def _fetch(self, timeout: float = 15.0) -> str:
        """Fetch measurement data with proper synchronization.

        For KXCI CVU measurements, this method implements proper timing
        and synchronization to ensure reliable measurements.
        """
        threshold = time.monotonic() + timeout
        while time.monotonic() < threshold:
            try:
                return self._query(":CVU:MEASZ?")
            except Exception as exc:
                raise RuntimeError(f"Failed to fetch LCR reading: {exc}") from exc
        raise RuntimeError(f"LCR reading timeout, exceeded {timeout:G} s")

    def measure_impedance(self) -> tuple[float, float]:
        result = self._fetch().split(",")
        try:
            return float(result[0]), float(result[1])
        except Exception as exc:
            raise RuntimeError(
                f"Failed to parse impedance reading: {result!r}"
            ) from exc

    def set_function_impedance_type(self, impedance_type: ImpedanceType) -> None:
        """Set the impedance equivalent circuit representation."""
        type_map = {
            ImpedanceType.ZTHETA: 0,
            ImpedanceType.RPLUSJX: 1,
            ImpedanceType.CPRP: 2,
            ImpedanceType.CPGP: 2,
            ImpedanceType.CSRS: 3,
            ImpedanceType.CPD: 4,
            ImpedanceType.CSD: 5,
            ImpedanceType.YTHETA: 7,
        }
        self._write(f":CVU:MODEL {type_map[impedance_type]}")

    def set_aperture(
        self, aperture: float = 10.0, filter_factor: int = 1, delay_factor: int = 1
    ) -> None:
        """Set measurement speed and aperture settings.

        Args:
            aperture: Aperture setting in PLC (Power Line Cycles) (0.006-10.002)
            filter_factor: Filter count for noise reduction
            delay_factor: Delay factor for settling
        """
        if aperture < 0.006 or aperture > 10.002:
            raise ValueError("Aperture must be between 0.006 and 10.002 PLC")
        if filter_factor < 0 or filter_factor > 707:
            raise ValueError("Filter factor must be between 0 and 707")
        if delay_factor < 0 or delay_factor > 100:
            raise ValueError("Delay factor must be between 0 and 100")

        # Set speed with delay factor, filter factor and aperture
        self._write(
            f":CVU:SPEED 3,{delay_factor:.3E},{filter_factor:.3E},{aperture:.3E}"
        )

    def set_amplitude_voltage(self, voltage: float) -> None:
        if not (0.01 <= voltage <= 1.0):
            raise ValueError("AC voltage must be between 10mV and 1V")
        self._write(f":CVU:ACV {voltage:E}")

    def set_amplitude_frequency(self, frequency: float) -> None:
        if not (1e3 <= frequency <= 1e7):
            raise ValueError("Frequency must be between 1kHz and 10MHz")
        self._write(f":CVU:FREQ {int(frequency)}")

    def _write(self, message: str) -> None:
        _ = self._resource.write(message)

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()

    def set_voltage_level(self, level: float) -> None:
        """Set the DC bias voltage level."""
        if not (-30.0 <= level <= 30.0):
            raise ValueError("Bias voltage level must be between -30V and 30V")

        if self._external_bias_tee_enabled:
            raise RuntimeError(
                "Cannot change bias voltage level when external P3 bias tee is enabled"
            )
        self._write(f":CVU:DCV {level:.3E}")

    def get_voltage_level(self) -> float:
        """Get the current DC bias voltage level."""
        # not implemented by the instrument, return 0
        return 0.0

    def set_voltage_offset(self, offset: float) -> None:
        """Set the DC voltage offset level."""
        if not (-30.0 <= offset <= 30.0):
            raise ValueError("Bias voltage offset must be between -30V and 30V")
        if self._external_bias_tee_enabled:
            raise RuntimeError(
                "Cannot change bias voltage offset when external P3 bias tee is enabled"
            )
        self._write(f":CVU:DCV:OFFSET {offset:.3E}")

    def get_voltage_offset(self) -> float:
        """Get the current DC voltage offset level."""
        # not implemented by the instrument, return 0
        return 0.0

    def enable_bias_tee_dc_voltage(self) -> None:
        """Enable -10V DC at HI and LO terminals for P3 bias tee."""
        self._write(":CVU:CONFIG:ACVHI 1")
        self._write(":CVU:CONFIG:DCVHI 1")
        # don't use set_voltage_offset and set_voltage_level because
        # these methods dont allow for the bias voltage to be changed
        # if the external bias tee is in use
        self._write(":CVU:DCV:OFFSET -10")
        self._write(":CVU:DCV -10")

    def reset_bias_tee_dc_voltage(self) -> None:
        self._write(":CVU:CONFIG:ACVHI 1")
        self._write(":CVU:CONFIG:DCVHI 1")
        self._write(":CVU:DCV:OFFSET 0")
        self._write(":CVU:DCV 0")

    def compliance_tripped(self) -> bool:
        """Check if current compliance is tripped."""
        # K4215 doesn't have current compliance, always return False
        return False

    def measure_i(self) -> float:
        """Measure current - not supported on K4215."""
        return 0.0

    def measure_iv(self) -> tuple[float, float]:
        """Measure current and voltage - not supported on K4215."""
        return 0.0, 0.0

    def set_current_compliance_level(self, level: float) -> None:
        """Set current compliance - not supported on K4215."""

    def set_voltage_range(self, level: float) -> None:
        """Set voltage range - not supported on K4215."""

    def finalize(self) -> None:
        """Clean up and reset the instrument."""
        if self._external_bias_tee_enabled:
            self.reset_bias_tee_dc_voltage()
