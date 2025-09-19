import time
from typing import Tuple

from .driver import LCRMeter, handle_exception

__all__ = ["K4215"]


class K4215(LCRMeter):

    def __init__(self, resource):
        super().__init__(resource)
        self._external_bias_tee_enabled = False

    def identity(self) -> str:
        return self._query("*IDN?").strip()

    def reset(self) -> None:
        self._write("*RST")
        # clear last errors
        self._write(":ERROR:LAST:CLEAR")

    def clear(self) -> None:
        self._write("BC")

    def next_error(self) -> Tuple[int, str]:
        """Get the next error from the instrument's error queue."""
        # KXCI uses :ERROR:LAST:GET to retrieve the last error
        response = self._query(":ERROR:LAST:GET")
        self._write(":ERROR:LAST:CLEAR")

        # if response is empty, return no error
        if len(response.strip()) == 0:
            return 0, "No error"

        # Try to parse response in standard SCPI format: code,"message"
        if "," in response and '"' in response:
            try:
                parts = response.split(",", 1)
                code = int(parts[0])
                message = parts[1].strip().strip('"')
                return code, message
            except Exception:
                pass

        # Try to parse response in format: message. (code)
        if "(" in response and ")" in response:
            try:
                code_str = response.split("(")[-1].split(")")[0]
                code = int(code_str)
                message = response.split("(")[0].strip().rstrip(".")
                return code, message
            except Exception:
                pass

        # Fallback: return the raw response with error code -1
        return -1, response.strip()

    def configure(self, options: dict) -> None:
        """Configure the CVU for measurements options."""
        # Set CVU mode (0 = user mode)
        self._write(":CVU:MODE 0")

        # Configure external bias tee option
        external_bias_tee = options.get("external_bias_tee.enabled", False)
        self._external_bias_tee_enabled = external_bias_tee

        # Enable -10V DC bias for P3 bias tee if selected
        if self._external_bias_tee_enabled:
            self._enable_bias_tee_dc_voltage()

        # Configure impedance/function type, default CPRP
        function_type = options.get("function.type", "CPRP")
        self.set_function_impedance_type(function_type)

        # Configure aperture/speed settings
        aperture = options.get("aperture.aperture", 1)
        filter_factor = options.get("aperture.filter_factor", 5)
        delay_factor = options.get("aperture.delay_factor", 10)
        self.set_aperture(aperture, filter_factor, delay_factor)

        # Configure correction settings
        correction_length = options.get("correction.length", 0)
        self.set_correction_length(correction_length)

        correction_open = options.get("correction.open.enabled", False)
        correction_short = options.get("correction.short.enabled", False)
        correction_load = options.get("correction.load.enabled", False)
        self.set_correction(correction_open, correction_short, correction_load)

        # Set measurement parameters
        voltage = options.get("voltage", 0.1)
        self.set_amplitude_voltage(voltage)

        frequency = options.get("frequency", 1.0e5)
        self.set_amplitude_frequency(frequency)

        # Set bias voltage only if external bias tee is NOT enabled
        if not external_bias_tee:
            bias_voltage = options.get("bias_voltage", None)
            if bias_voltage is not None:
                self.set_voltage_level(bias_voltage)

        # Set AC impedance range if specified
        ac_range = options.get("ac_range", None)
        if ac_range is not None:
            self.set_aci_range(ac_range)
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


    def set_correction(self, open_state=False, short_state=False, load_state=False):
        """Enable or disable open, short, and load compensation."""
        open_val = 1 if open_state else 0
        short_val = 1 if short_state else 0
        load_val = 1 if load_state else 0
        self._write(f":CVU:CORRECT {open_val},{short_val},{load_val}")

    def _fetch(self, timeout=15.0, interval=0.250) -> str:
        """Fetch measurement data with proper synchronization.

        For KXCI CVU measurements, this method implements proper timing
        and synchronization to ensure reliable measurements.
        """
        threshold = time.time() + timeout
        interval = min(timeout, interval)
        while time.time() < threshold:
            try:
                return self._query(":CVU:MEASZ?")
            except Exception as exc:
                raise RuntimeError(f"Failed to fetch LCR reading: {exc}") from exc
            time.sleep(interval)
        raise RuntimeError(f"LCR reading timeout, exceeded {timeout:G} s")

    def measure_impedance(self) -> Tuple[float, float]:
        result = self._fetch().split(",")
        try:
            return float(result[0]), float(result[1])
        except Exception as exc:
            raise RuntimeError(
                f"Failed to parse impedance reading: {result!r}"
            ) from exc

    def set_function_impedance_type(self, impedance_type) -> None:
        """Set the impedance equivalent circuit representation.

        Args:
            impedance_type: Can be integer (0-7) or string ("CPRP", "CSRS", etc.)

        CVU model types:
        0: Z, theta
        1: R + jX
        2: Cp, Gp
        3: Cs, Rs
        4: Cp, D
        5: Cs, D
        7: Y, theta
        """
        if isinstance(impedance_type, str):
            # Map string types to integer values
            type_map = {
                "ZTHETA": 0,
                "RPLUSJX": 1,
                "CPRP": 2,
                "CPGP": 2,
                "CSRS": 3,
                "CPD": 4,
                "CSD": 5,
                "YTHETA": 7,
            }
            impedance_type = type_map.get(impedance_type.upper(), 2)  # Default to Cp,Rp
        if not isinstance(impedance_type, int) or impedance_type not in [
            0,
            1,
            2,
            3,
            4,
            5,
            7,
        ]:
            impedance_type = 2  # Default to Cp,Rp if invalid

        self._write(f":CVU:MODEL {impedance_type}")

    def set_aperture(self, aperture=10, filter_factor=1, delay_factor=1) -> None:
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
        self._write(f":CVU:SPEED 3,{delay_factor:.3E},{filter_factor:.3E},{aperture:.3E}")

    def set_amplitude_voltage(self, voltage: float) -> None:
        if not (0.01 <= voltage <= 1.0):
            raise ValueError("AC voltage must be between 10mV and 1V")
        self._write(f":CVU:ACV {voltage:E}")

    def set_amplitude_frequency(self, frequency: float) -> None:
        if not (1e3 <= frequency <= 1e7):
            raise ValueError("Frequency must be between 1kHz and 10MHz")
        self._write(f":CVU:FREQ {int(frequency)}")

    def _write(self, message):
        """Write command and wait for operation complete."""
        self.resource.write(message)

    def _write_nowait(self, message):
        self.resource.write(message)

    @handle_exception
    def _query(self, message):
        return self.resource.query(message).strip()

    def set_correction_length(self, correction_length: int) -> None:
        """Set cable length correction for the K4215.

        Args:
            correction_length: Cable length in meters (0, 1.5, or 3.0)
        """
        if correction_length not in [0, 1.5, 3.0]:
            raise ValueError("Correction length must be 0, 1.5, or 3.0 meters")
        self._write(f":CVU:LENGTH {correction_length:.1f}")

    def get_voltage_level(self) -> float:
        """Get the current DC bias voltage level."""
        try:
            response = self._query(":CVU:DCV?")
            return float(response.strip())
        except Exception:
            # Return 0 if query fails
            return 0.0

    def set_voltage_level(self, level: float) -> None:
        """Set the DC bias voltage level."""
        if not (-30.0 <= level <= 30.0):
            raise ValueError("Bias voltage level must be between -30V and 30V")


        if self._external_bias_tee_enabled:
            raise RuntimeError(
                "Cannot change bias voltage level when external P3 bias tee is enabled"
            )
        self._write(f":CVU:DCV {level:.3E}")

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
        response = self._query(":CVU:DCV:OFFSET?")
        return float(response.strip())

    def _enable_bias_tee_dc_voltage(self):
        """Enable -10V DC at HI and LO terminals for P3 bias tee."""
        self._write(":CVU:CONFIG:ACVHI 1")
        self._write(":CVU:CONFIG:DCVHI 1")
        # don't use set_voltage_offset and set_voltage_level because
        # these methods dont allow for the bias voltage to be changed
        # if the external bias tee is in use
        self._write(":CVU:DCV:OFFSET -10")
        self._write(":CVU:DCV -10")

    def compliance_tripped(self) -> bool:
        """Check if current compliance is tripped."""
        # K4215 doesn't have current compliance, always return False
        return False

    def measure_i(self) -> float:
        """Measure current - not supported on K4215."""
        return 0.0

    def measure_iv(self) -> Tuple[float, float]:
        """Measure current and voltage - not supported on K4215."""
        return 0.0, 0.0

    def set_current_compliance_level(self, level: float) -> None:
        """Set current compliance - not supported on K4215."""
        pass  # Not supported by K4215

    def set_voltage_range(self, level: float) -> None:
        pass  # Not supported by K4215

    def finalize(self):
        """Clean up and reset the instrument."""
        self.reset()
