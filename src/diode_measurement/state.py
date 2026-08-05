import logging
from enum import StrEnum

__all__ = ["FSMState"]

logger = logging.getLogger(__name__)


class FSMState(StrEnum):
    IDLE = "idle"
    CONFIGURE = "configure"
    RAMPING = "ramping"
    CONTINUOUS = "continuous"
    STOPPING = "stopping"
