import logging
from typing import Any

from .driver import Driver, driver_factory
from .resource import AutoReconnectResource, Resource, ResourceConfig
from .role import Role

__all__ = ["Station"]

logger = logging.getLogger(__name__)


class Station:
    def __init__(self) -> None:
        self.auto_reconnect: bool = False
        self.instrument_registry: dict[str, tuple[type[Driver], Resource]] = {}
        self.instruments: dict[str, Any] = {}
        self._driver_factory = driver_factory

    def register_instrument(self, name: str, role: Role) -> None:
        model = role.model
        if not role.resource_name.strip():
            raise ValueError(
                f"Empty resource name not allowed for {name.upper()} ({model})."
            )

        driver_cls = self._driver_factory(model)

        resource_config = ResourceConfig(
            resource_name=role.resource_name,
            visa_library=role.visa_library,
            termination=role.termination,
            timeout=role.timeout,
        )
        resource = self._create_resource(resource_config)
        self.instrument_registry[name] = driver_cls, resource

    def _create_resource(self, config: ResourceConfig) -> Resource:
        # If auto reconnect use experimental class AutoReconnectResource
        resource_cls = AutoReconnectResource if self.auto_reconnect else Resource
        return resource_cls(config)
