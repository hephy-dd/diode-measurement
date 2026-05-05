from dataclasses import dataclass, field
from typing import Any


@dataclass
class Role:
    enabled: bool
    model: str
    resource_name: str
    visa_library: str
    termination: str
    timeout: float
    reset_instrument: bool
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Role":
        return cls(
            enabled=data.get("enabled", False),
            model=data.get("model", ""),
            resource_name=data.get("resource_name", ""),
            visa_library=data.get("visa_library", "@py"),
            termination=data.get("termination", "\n"),
            timeout=float(data.get("timeout", 4.0)),
            reset_instrument=data.get("reset_instrument", False),
            options=dict(data.get("options", {})),
        )
