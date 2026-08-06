from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = ["RoleConfig", "Role"]


class Role(StrEnum):
    SMU = "smu"
    SMU2 = "smu2"
    ELM = "elm"
    ELM2 = "elm2"
    LCR = "lcr"
    DMM = "dmm"
    SWITCH = "switch"
    TCU = "tcu"


@dataclass(frozen=True, slots=True)
class RoleConfig:
    enabled: bool
    model: str
    resource_name: str
    visa_library: str
    termination: str
    timeout: float
    reset_instrument: bool
    options: dict[str, Any] = field(default_factory=dict)
