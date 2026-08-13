import logging
from contextlib import ExitStack
from typing import Any

from .driver import InstrumentAdapter, adapter_factory
from .resource import AutoReconnectResource, Resource, ResourceConfig
from .role import Role, RoleConfig

__all__ = ["Station"]

logger = logging.getLogger(__name__)


class Station:
    def __init__(self) -> None:
        self.auto_reconnect: bool = False
        self.instruments: dict[Role, Any] = {}
        self._instrument_registry: dict[
            Role, tuple[type[InstrumentAdapter], Resource]
        ] = {}
        self._adapter_factory = adapter_factory

    def register_instrument(self, role: Role, role_config: RoleConfig) -> None:
        model = role_config.model
        if not role_config.resource_name.strip():
            raise ValueError(
                f"Empty resource name not allowed for {role.upper()} ({model})."
            )

        adapter_cls = self._adapter_factory(model)

        resource_config = ResourceConfig(
            resource_name=role_config.resource_name,
            visa_library=role_config.visa_library,
            termination=role_config.termination,
            timeout=role_config.timeout,
        )
        resource = self._create_resource(resource_config)
        self._instrument_registry[role] = adapter_cls, resource

    def _create_resource(self, config: ResourceConfig) -> Resource:
        # If auto reconnect use experimental class AutoReconnectResource
        resource_cls = AutoReconnectResource if self.auto_reconnect else Resource
        return resource_cls(config)

    def create_instruments(self, stack: ExitStack) -> None:
        for role, (cls, resource) in self._instrument_registry.items():
            logger.debug("creating instrument context %s: %s...", role, cls.__name__)
            context = cls(stack.enter_context(resource))
            self.instruments[role] = context
