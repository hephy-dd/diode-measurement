from dataclasses import dataclass
from typing import Any

__all__ = [
    "ExceptionEvent",
    "ChangeVoltageDoneEvent",
    "UpdateMetricsEvent",
]


@dataclass(frozen=True, slots=True)
class ExceptionEvent:
    exception: Exception


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
