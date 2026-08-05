import logging
from dataclasses import dataclass, field
from enum import StrEnum

from .core.role import Role, RoleConfig

__all__ = ["State"]

logger = logging.getLogger(__name__)


class FSMState(StrEnum):
    IDLE = "idle"
    CONFIGURE = "configure"
    RAMPING = "ramping"
    CONTINUOUS = "continuous"
    STOPPING = "stopping"


@dataclass(frozen=True, slots=True)
class ChangeVoltageParameters:
    end_voltage: float
    step_voltage: float
    waiting_time: float


@dataclass(frozen=True, slots=True)
class Reading:
    timestamp: float
    t_dmm: float
    tcu_temperature: float
    tcu_humidity: float


@dataclass(frozen=True, slots=True)
class IVReading(Reading):
    voltage: float
    v_smu: float
    i_smu: float
    v_smu2: float
    i_smu2: float
    i_elm: float
    i_elm2: float


@dataclass(frozen=True, slots=True)
class CVReading(Reading):
    voltage: float
    v_smu: float
    i_smu: float
    c_lcr: float
    c2_lcr: float
    r_lcr: float


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

    def find_role(self, role: Role) -> RoleConfig | None:
        return self.roles.get(role)
