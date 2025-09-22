import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

__all__ = ["Driver"]


def handle_exception(method):
    def handle_exception(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:
            raise DriverError(f"{type(self).__name__}: {exc}") from exc
    return handle_exception


class DriverError(Exception):

    ...


class Driver(ABC):

    def __init__(self, resource):
        self.resource = resource

    @abstractmethod
    def identity(self) -> str:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def next_error(self) -> tuple[int, str]:
        ...

    @abstractmethod
    def configure(self, options: dict) -> None:
        ...


class SourceMeter(Driver):

    @abstractmethod
    def get_output_enabled(self) -> bool:
        ...

    @abstractmethod
    def set_output_enabled(self, enabled: bool) -> None:
        ...

    @abstractmethod
    def get_voltage_level(self) -> float:
        ...

    @abstractmethod
    def set_voltage_level(self, level: float) -> None:
        ...

    @abstractmethod
    def set_voltage_range(self, level: float) -> None:
        ...

    @abstractmethod
    def set_current_compliance_level(self, level: float) -> None:
        ...

    @abstractmethod
    def compliance_tripped(self) -> bool:
        ...

    @abstractmethod
    def measure_i(self) -> float:
        ...

    @abstractmethod
    def measure_iv(self) -> tuple[float, float]:
        ...


class Electrometer(SourceMeter):

    @abstractmethod
    def set_zero_check_enabled(self, enabled: bool) -> None:
        ...

    @abstractmethod
    def measure_i(self) -> float:
        ...


class LCRMeter(SourceMeter):

    @abstractmethod
    def measure_impedance(self) -> tuple[float, float]:
        ...


class DMM(Driver):

    @abstractmethod
    def measure_temperature(self) -> float:
        ...


class SwitchingMatrix(Driver):

    @abstractmethod
    def close_channels(self, channels: list) -> None:
        ...

    @abstractmethod
    def open_channels(self, channels: list) -> None:
        ...

    @abstractmethod
    def open_all_channels(self) -> None:
        ...

    @abstractmethod
    def closed_channels(self) -> list:
        ...
