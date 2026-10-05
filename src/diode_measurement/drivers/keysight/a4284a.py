import time
from collections.abc import Mapping
from enum import IntEnum, StrEnum
from typing import Annotated

import msgspec

from diode_measurement.core.driver import InstrumentError, handle_exception
from diode_measurement.core.resource import Resource
from diode_measurement.core.scpi import parse_scpi_error

__all__ = ["A4284AAdapter"]


class ImpedanceType(StrEnum):
    CPRP = "CPRP"


class IntegrationTime(StrEnum):
    SHORT = "SHOR"
    MEDIUM = "MED"
    LONG = "LONG"


class CorrectionLength(IntEnum):
    METER_0 = 0
    METER_1 = 1
    METER_2 = 2


AveragingRate = Annotated[int, msgspec.Meta(ge=1, le=128)]


class A4284AConfig(msgspec.Struct, frozen=True):
    function_type: ImpedanceType = msgspec.field(
        default=ImpedanceType.CPRP,
        name="function.type",
    )
    integration_time: IntegrationTime = msgspec.field(
        default=IntegrationTime.MEDIUM,
        name="aperture.integration_time",
    )
    averaging_rate: AveragingRate = msgspec.field(
        default=1,
        name="aperture.averaging_rate",
    )
    correction_length: CorrectionLength = msgspec.field(
        default=CorrectionLength.METER_0,
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
    voltage: float = 1.0
    frequency: float = 1000.0
    amplitude_alc: bool = msgspec.field(
        default=False,
        name="amplitude.alc",
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

    def configure(self, options: Mapping[str, object]) -> None:
        config = msgspec.convert(options, type=A4284AConfig)

        self._write(":INIT:CONT OFF")
        self._write(":TRIG:SOUR BUS")

        self.set_function_impedance_type(config.function_type)

        self.set_aperture(
            config.integration_time,
            config.averaging_rate,
        )

        self.set_correction_length(config.correction_length)
        self.set_correction_open_state(config.correction_open_enabled)
        self.set_correction_short_state(config.correction_short_enabled)

        self.set_amplitude_voltage(config.voltage)
        self.set_amplitude_frequency(config.frequency)
        self.set_amplitude_alc(config.amplitude_alc)

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

    def set_function_impedance_type(self, impedance_type: ImpedanceType) -> None:
        self._write(f":FUNC:IMP:TYPE {impedance_type}")

    def set_aperture(
        self, integration_time: IntegrationTime, averaging_rate: int
    ) -> None:
        self._write(f":APER {integration_time},{averaging_rate:d}")

    def set_correction_length(self, correction_length: CorrectionLength) -> None:
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
