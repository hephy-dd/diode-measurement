import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Self

import pyvisa
from pyvisa.resources import MessageBasedResource

__all__ = [
    "parse_resource",
    "ResourceConfig",
    "ResourceError",
    "Resource",
    "AutoReconnectResource",
]

logger = logging.getLogger(__name__)


def parse_resource(resource_name: str) -> tuple[str, str]:
    """Create valid VISA resource name for short descriptors."""
    resource_name = resource_name.strip()

    if m := re.match(r"^(\d+)$", resource_name):
        resource_name = f"GPIB0::{m.group(1)}::INSTR"

    if m := re.match(r"^COM(\d+)$", resource_name):
        resource_name = f"ASRL{m.group(1)}::INSTR"

    if m := re.match(r"^ASRL(\d+)$", resource_name):
        resource_name = f"ASRL{m.group(1)}::INSTR"

    if m := re.match(r"^(\d+\.\d+\.\d+\.\d+)\:(\d+)$", resource_name):
        resource_name = f"TCPIP0::{m.group(1)}::{m.group(2)}::SOCKET"

    if m := re.match(r"^(\w+)\:(\d+)$", resource_name):
        resource_name = f"TCPIP0::{m.group(1)}::{m.group(2)}::SOCKET"

    visa_library = ""
    if resource_name.startswith("ASRL"):
        visa_library = "@py"
    if resource_name.startswith("TCPIP"):
        visa_library = "@py"

    return resource_name, visa_library


def list_resources() -> list[str]:
    rm = pyvisa.ResourceManager()
    try:
        return list(rm.list_resources())
    finally:
        rm.close()


@dataclass(frozen=True, slots=True)
class ResourceConfig:
    resource_name: str
    visa_library: str = "@py"
    termination: str = "\n"
    timeout: float = 4.0
    baud_rate: int = 9_600


class ResourceError(Exception): ...


class Resource:
    def __init__(self, resource_config: ResourceConfig) -> None:
        self._resource_config = resource_config
        self._rm: pyvisa.ResourceManager | None = None
        self._resource: pyvisa.resources.MessageBasedResource | None = None

    def __enter__(self) -> Self:
        try:
            resource_config = self._resource_config
            self._rm = pyvisa.ResourceManager(resource_config.visa_library)

            resource = self._rm.open_resource(
                resource_name=resource_config.resource_name,
                read_termination=resource_config.termination,
                write_termination=resource_config.termination,
                timeout=resource_config.timeout * 1_000,  # millisecs
            )

            if hasattr(resource, "baud_rate"):
                resource.baud_rate = resource_config.baud_rate  # type: ignore

            if not isinstance(resource, MessageBasedResource):
                resource.close()
                raise TypeError(
                    f"Expected MessageBasedResource, got {type(resource).__name__}"
                )
            self._resource = resource
        except pyvisa.Error as exc:
            raise ResourceError(f"{self.resource_name}: {exc}") from exc
        return self

    def __exit__(self, *args) -> Literal[False]:
        try:
            if self._resource is not None:
                self._resource.close()
        except pyvisa.Error as exc:
            raise ResourceError(f"{self.resource_name}: {exc}") from exc
        finally:
            try:
                if self._rm is not None:
                    self._rm.close()
            finally:
                self._rm = None
                self._resource = None
        return False

    @property
    def resource(self) -> pyvisa.resources.MessageBasedResource:
        if self._resource is None:
            raise RuntimeError("no open resource")
        return self._resource

    @property
    def resource_name(self) -> str:
        return self._resource_config.resource_name

    def query(self, message: str) -> str:
        try:
            logger.debug("resource.write: `%s`", message)
            result = self.resource.query(message)
            logger.debug("resource.read: `%s`", result)
            return result
        except pyvisa.Error as exc:
            raise ResourceError(f"{self.resource_name}: {exc}") from exc

    def write(self, message: str) -> int:
        try:
            logger.debug("resource.write: `%s`", message)
            return self.resource.write(message)
        except pyvisa.Error as exc:
            raise ResourceError(f"{self.resource_name}: {exc}") from exc

    def read(self) -> str:
        try:
            result = self.resource.read()
            logger.debug("resource.read: `%s`", result)
            return result
        except pyvisa.Error as exc:
            raise ResourceError(f"{self.resource_name}: {exc}") from exc

    def clear(self) -> None:
        try:
            self.resource.clear()
        except pyvisa.Error as exc:
            raise ResourceError(f"{self.resource_name}: {exc}") from exc


class AutoReconnectResource(Resource):
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def _reconnect_retry(self, target: Callable, *args) -> Any:
        for attempt in range(self.retry_attempts + 1):
            try:
                if attempt:
                    logger.info(
                        "auto reconnect to resource (%d/%d): %r",
                        attempt,
                        self.retry_attempts,
                        self.resource_name,
                    )
                    try:
                        self.__exit__()
                    except Exception:
                        ...
                    time.sleep(self.retry_delay)
                    self.__enter__()
                return target(*args)
            except (pyvisa.Error, ConnectionError, ResourceError):
                if attempt < self.retry_attempts:
                    logger.exception("failed to connect, retry...")
                else:
                    raise

    def query(self, message: str) -> str:
        return self._reconnect_retry(super().query, message)

    def write(self, message: str) -> int:
        return self._reconnect_retry(super().write, message)

    def read(self) -> str:
        return self._reconnect_retry(super().read)

    def clear(self) -> None:
        return self._reconnect_retry(super().clear)
