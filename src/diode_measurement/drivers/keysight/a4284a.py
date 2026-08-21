import time
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

import msgspec

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["A4284AAdapter"]


class FunctionType(StrEnum):
    CPRP = "CPRP"


class IntegrationTime(StrEnum):
    SHORT = "SHOR"
    MEDIUM = "MED"
    LONG = "LONG"


class A4284AOptions(msgspec.Struct):
    function_type: FunctionType = msgspec.field(
        name="function.type",
        default=FunctionType.CPRP,
    )
    integration_time: IntegrationTime = msgspec.field(
        name="aperture.integration_time",
        default=IntegrationTime.MEDIUM,
    )
    averaging_rate: int = msgspec.field(
        name="aperture.averaging_rate",
        default=1,
    )
    correction_length: int = msgspec.field(
        name="correction.length",
        default=0,
    )
    correction_open_enabled: bool = msgspec.field(
        name="correction.open.enabled",
        default=False,
    )
    correction_short_enabled: bool = msgspec.field(
        name="correction.short.enabled",
        default=False,
    )
    amplitude_voltage: float = msgspec.field(
        name="voltage",
        default=1.0,
    )
    amplitude_frequency: float = msgspec.field(
        name="frequency",
        default=1000.0,
    )
    amplitude_alc: bool = msgspec.field(
        name="amplitude.alc",
        default=False,
    )


class A4284AAdapter:
    def __init__(self, resource: Resource) -> None:
        self._resource: Resource = resource

    def identify(self) -> str:
        return self._query("*IDN?").strip()

    def reset(self) -> None:
        self._write("*RST")

    def clear(self) -> None:
        self._write("*CLS")

    def next_error(self) -> InstrumentError | None:
        return parse_scpi_error(self._query(":SYST:ERR?"))

    def configure(self, options: Mapping[str, Any]) -> None:
        self._configure(msgspec.convert(options, type=A4284AOptions))

    def _configure(self, options: A4284AOptions) -> None:
        self._write(":INIT:CONT OFF")
        self._write(":TRIG:SOUR BUS")

        self.set_function_impedance_type(options.function_type)

        # Apterture
        self.set_aperture(options.integration_time, options.averaging_rate)

        # Correction cable length
        self.set_correction_length(options.correction_length)

        # Enable open correction
        self.set_correction_open_state(options.correction_open_enabled)

        # Enable short correction
        self.set_correction_short_state(options.correction_short_enabled)

        self.set_amplitude_voltage(options.amplitude_voltage)
        self.set_amplitude_frequency(options.amplitude_frequency)
        self.set_amplitude_alc(options.amplitude_alc)

    def get_output_enabled(self) -> bool:
        return self._query(":BIAS:STAT?") == "1"

    def set_output_enabled(self, enabled: bool) -> None:
        value = {False: "0", True: "1"}[enabled]
        self._write(f":BIAS:STAT {value}")

    def get_voltage_level(self) -> float:
        return float(self._query(":BIAS:VOLT:LEV?"))

    def set_voltage_level(self, level: float) -> None:
        self._write(f":BIAS:VOLT:LEV {level:.3E}")

    def set_voltage_range(self, level: float) -> None:
        pass  # TODO

    def set_current_compliance_level(self, level: float) -> None: ...  # not supported

    def compliance_tripped(self) -> bool:
        return False

    def measure_i(self) -> float:
        return 0.0

    def measure_iv(self) -> tuple[float, float]:
        return 0.0, 0.0

    def measure_impedance(self) -> tuple[float, float]:
        result = self._fetch().split(",")
        try:
            return float(result[0]), float(result[1])
        except Exception as exc:
            raise RuntimeError(
                f"Failed to parse impedance reading: {result!r}"
            ) from exc

    def set_function_impedance_type(self, impedance_type: FunctionType) -> None:
        self._write(f":FUNC:IMP:TYPE {impedance_type}")

    def set_aperture(
        self, integration_time: IntegrationTime, averaging_rate: int
    ) -> None:
        assert 1 <= averaging_rate <= 128
        self._write(f":APER {integration_time},{averaging_rate:d}")

    def set_correction_length(self, correction_length: int) -> None:
        assert correction_length in [0, 1, 2]
        self._write(f":CORR:LENG {correction_length:d}")

    def set_correction_open_state(self, state: bool) -> None:
        self._write(f":CORR:OPEN:STAT {state:d}")

    def set_correction_short_state(self, state: bool) -> None:
        self._write(f":CORR:SHOR:STAT {state:d}")

    def set_amplitude_voltage(self, voltage: float) -> None:
        self._write(f":VOLT {voltage:E}")

    def set_amplitude_frequency(self, frequency: float) -> None:
        self._write(f":FREQ {frequency:E}")

    def set_amplitude_alc(self, enabled: bool) -> None:
        self._write(f":AMPL:ALC {enabled:d}")

    @handle_exception
    def _write(self, message: str) -> None:
        _ = self._resource.write(message)
        _ = self._resource.query("*OPC?")

    @handle_exception
    def _write_nowait(self, message: str):
        _ = self._resource.write(message)

    @handle_exception
    def _query(self, message: str) -> str:
        return self._resource.query(message).strip()

    def _fetch(self, timeout: float = 10.0, interval: float = 0.250) -> str:
        # Request operation complete
        self._write("*CLS")
        self._write_nowait("*OPC")
        # Initiate measurement
        self._write_nowait(":TRIG:IMM")
        threshold = time.monotonic() + timeout
        interval = min(timeout, interval)
        while time.monotonic() < threshold:
            # Read event status
            if int(self._query("*ESR?")) & 0x1:
                try:
                    return self._query(":FETC?")
                except Exception as exc:
                    raise RuntimeError(f"Failed to fetch LCR reading: {exc}") from exc
            time.sleep(interval)
        raise RuntimeError(f"LCR reading timeout, exceeded {timeout:G} s")
