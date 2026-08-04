import logging
from collections.abc import Iterable, Mapping
from typing import Any, Protocol, runtime_checkable

from comet.driver.generic import InstrumentError

from .resource import Resource

__all__ = [
    "BaseDriver",
    "Driver",
    "driver_registry",
    "driver_factory",
]

logger = logging.getLogger(__name__)


def handle_exception(method):
    def handle_exception(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:
            raise DriverError(f"{type(self).__name__}: {exc}") from exc

    return handle_exception


class DriverError(Exception): ...


class BaseDriver:
    def __init__(self, resource: Resource) -> None:
        self.resource = resource


class Driver(Protocol):
    def __init__(self, resource: Resource) -> None: ...
    def identify(self) -> str: ...
    def reset(self) -> None: ...
    def clear(self) -> None: ...
    def next_error(self) -> InstrumentError | None: ...
    def configure(self, options: Mapping[str, Any]) -> None: ...


class SourceMeter(Driver, Protocol):
    def get_output_enabled(self) -> bool: ...
    def set_output_enabled(self, enabled: bool) -> None: ...
    def get_voltage_level(self) -> float: ...
    def set_voltage_level(self, level: float) -> None: ...
    def set_voltage_range(self, level: float) -> None: ...
    def set_current_compliance_level(self, level: float) -> None: ...
    def compliance_tripped(self) -> bool: ...
    def measure_i(self) -> float: ...
    def measure_iv(self) -> tuple[float, float]: ...


class Electrometer(SourceMeter, Protocol):
    def set_zero_check_enabled(self, enabled: bool) -> None: ...


class LCRMeter(SourceMeter, Protocol):
    def measure_impedance(self) -> tuple[float, float]: ...


class DMM(Driver, Protocol):
    def measure_temperature(self) -> float: ...


class TCU(Driver, Protocol):
    def get_temperature(self) -> float: ...
    def get_humidity(self) -> float: ...
    def set_target_temperature(self, temperature: float) -> None: ...
    def is_within_setpoint(self) -> bool: ...
    def get_state(self) -> str: ...


class SwitchingMatrix(Driver, Protocol):
    def close_channels(self, channels: Iterable[str]) -> None: ...
    def open_channels(self, channels: Iterable[str]) -> None: ...
    def open_all_channels(self) -> None: ...
    def closed_channels(self) -> list[str]: ...


@runtime_checkable
class VoltageMeasurable(Protocol):
    def measure_v(self) -> float: ...


driver_registry: dict[str, type[Driver]] = {}


def driver_factory(model: str) -> type[Driver]:
    """Return the driver class for the given model."""
    try:
        return driver_registry[model]
    except KeyError as exc:
        raise ValueError(f"Unknown driver model: {model}") from exc
