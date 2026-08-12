from dataclasses import dataclass
from typing import Any

__all__ = []


@dataclass(frozen=True, slots=True)
class Reading:
    timestamp: float
    t_dmm: float
    tcu_temperature: float
    tcu_humidity: float


@dataclass(frozen=True, slots=True)
class ExceptionEvent:
    exception: Exception


@dataclass(frozen=True, slots=True)
class ChangeVoltageParameters:
    end_voltage: float
    step_voltage: float
    waiting_time: float


@dataclass(frozen=True, slots=True)
class ChangeVoltageDoneEvent: ...


@dataclass(frozen=True, slots=True)
class UpdateMetricsEvent:
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class UpdateContinueInCompliance:
    is_continue: bool


@dataclass(frozen=True, slots=True)
class UpdateCurrentCompliance:
    current_compliance: float


@dataclass(frozen=True, slots=True)
class UpdateWaitingTimeContinuous:
    waiting_time: float


@dataclass(frozen=True, slots=True)
class ChangeSetpointEnabled:
    enabled: bool


@dataclass(frozen=True, slots=True)
class ChangeTargetTemperature:
    target_temperature: float


@dataclass(frozen=True, slots=True)
class ChangeSetpointTolerance:
    tolerance: float


@dataclass(frozen=True, slots=True)
class ChangeDewpointControl:
    enabled: bool


@dataclass(frozen=True, slots=True)
class ChangeWaitForSetpoint:
    enabled: bool
