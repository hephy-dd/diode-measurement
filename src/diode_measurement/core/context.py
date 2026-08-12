import logging
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event
from typing import Any

from .events import (
    ChangeDewpointControl,
    ChangeSetpointEnabled,
    ChangeSetpointTolerance,
    ChangeTargetTemperature,
    ChangeVoltageParameters,
    ChangeWaitForSetpoint,
    UpdateContinueInCompliance,
    UpdateCurrentCompliance,
    UpdateWaitingTimeContinuous,
)
from .role import Role, RoleConfig
from .station import Station

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class State:
    measurement_type: str = ""
    timestamp: float = 0.0
    sample: str = ""
    auto_reconnect: bool = False
    is_continuous: bool = False
    continue_in_compliance: bool = False
    waiting_time: float = 1.0
    waiting_time_continuous: float = 1.0
    source_voltage: float | None = None
    bias_voltage: float = 0.0
    voltage_begin: float = 0.0
    voltage_end: float = 0.0
    voltage_step: float = 1.0
    current_compliance: float = 0.0
    source_role: Role | None = None
    bias_source_role: Role | None = None
    discharge_timeout: float = 60.0
    discharge_threshold: float = 0.5
    roles: dict[Role, RoleConfig] = field(default_factory=dict)
    output_filename: str | None = None
    settle_waiting_time: float = 1.0
    tcu_poll_interval: float = 5.0
    setpoint_enabled: bool = False
    wait_for_setpoint: bool = False

    def find_role(self, role: Role) -> RoleConfig | None:
        return self.roles.get(role)


@dataclass(slots=True)
class PendingChanges:
    voltage_change: ChangeVoltageParameters | None = None
    target_temperature: ChangeTargetTemperature | None = None
    setpoint_tolerance: ChangeSetpointTolerance | None = None
    dewpoint_control: ChangeDewpointControl | None = None

    def pop_voltage_change(self) -> ChangeVoltageParameters | None:
        event = self.voltage_change
        self.voltage_change = None
        return event

    def pop_target_temperature(self) -> ChangeTargetTemperature | None:
        event = self.target_temperature
        self.target_temperature = None
        return event

    def pop_setpoint_tolerance(self) -> ChangeSetpointTolerance | None:
        event = self.setpoint_tolerance
        self.setpoint_tolerance = None
        return event

    def pop_dewpoint_control(self) -> ChangeDewpointControl | None:
        event = self.dewpoint_control
        self.dewpoint_control = None
        return event


class RuntimeEventError(RuntimeError): ...


@dataclass(slots=True)
class RuntimeState:
    pending: PendingChanges
    current_compliance: float
    continue_in_compliance: bool
    waiting_time_continuous: float
    setpoint_enabled: bool
    wait_for_setpoint: bool

    def handle_event(self, event: Any) -> None:
        match event:
            case UpdateCurrentCompliance(compliance):
                self.current_compliance = compliance
            case UpdateContinueInCompliance(is_continue):
                self.continue_in_compliance = is_continue
            case UpdateWaitingTimeContinuous(waiting_time):
                self.waiting_time_continuous = waiting_time
            case ChangeVoltageParameters() as evt:
                self.pending.voltage_change = evt
            case ChangeSetpointEnabled(enabled):
                self.setpoint_enabled = enabled
            case ChangeTargetTemperature() as evt:
                self.pending.target_temperature = evt
            case ChangeSetpointTolerance() as evt:
                self.pending.setpoint_tolerance = evt
            case ChangeDewpointControl() as evt:
                self.pending.dewpoint_control = evt
            case ChangeWaitForSetpoint(enabled):
                self.wait_for_setpoint = enabled
            case _:
                logger.warning("Unsupported runtime event: %r", event)


@dataclass(slots=True)
class Context:
    state: State
    station: Station
    outbox_queue: Queue[Any]
    inbox_queue: Queue[Any]
    abort_event: Event
    runtime_state: RuntimeState

    def submit_event(self, event: Any) -> None:
        self.outbox_queue.put(event)

    @property
    def stop_requested(self) -> bool:
        return self.abort_event.is_set()

    def wait(self, seconds: float) -> bool:
        return self.abort_event.wait(seconds)

    def process_inbox(self, max_events: int = 1024) -> None:
        for _ in range(max_events):
            try:
                event = self.inbox_queue.get_nowait()
            except Empty:
                return
            self.runtime_state.handle_event(event)
