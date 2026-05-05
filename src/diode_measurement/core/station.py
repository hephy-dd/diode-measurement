import logging
from typing import Any

from .driver import driver_factory, Driver
from .role import Role
from .resource import ResourceConfig, Resource, AutoReconnectResource

__all__ = ["Station"]


class Station:
    def __init__(self) -> None:
        self.auto_reconnect: bool = False
        self._instruments: dict[str, tuple[type[Driver], Resource]] = {}
        self.instruments: dict[str, Any] = {}

    def register_instrument(self, name: str, role: Role) -> None:
        model = role.model
        if not role.resource_name.strip():
            raise ValueError(
                f"Empty resource name not allowed for {name.upper()} ({model})."
            )

        driver_cls = driver_factory(model)
        if not driver_cls:
            logging.warning("No such driver: %s", model)
            return None

        resource_config = ResourceConfig(
            resource_name=role.resource_name,
            visa_library=role.visa_library,
            termination=role.termination,
            timeout=role.timeout,
        )
        resource = self._create_resource(resource_config)
        self._instruments[name] = driver_cls, resource

    def _create_resource(self, config: ResourceConfig) -> Resource:
        # If auto reconnect use experimental class AutoReconnectResource
        resource_cls = AutoReconnectResource if self.auto_reconnect else Resource
        return resource_cls(config)
