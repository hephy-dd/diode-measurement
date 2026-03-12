import logging
import time
from collections.abc import Callable
from typing import Any, Optional

import pyvisa

__all__ = ["ResourceError", "Resource", "AutoReconnectResource"]

logger = logging.getLogger(__name__)


class ResourceError(Exception): ...


class Resource:
    def __init__(self, resource_name: str, visa_library: str, **options):
        self.resource_name = resource_name
        self.visa_library = visa_library
        self.options = {
            "read_termination": "\r\n",
            "write_termination": "\r\n",
            "timeout": 8000,
        }
        self.options.update(options)
        self._rm: Optional[pyvisa.ResourceManager] = None
        self._resource: Optional[pyvisa.resources.MessageBasedResource] = None

    def __enter__(self):
        try:
            self._rm = pyvisa.ResourceManager(self.visa_library)
            self._resource = self._rm.open_resource(
                resource_name=self.resource_name, **self.options
            )
        except pyvisa.Error as exc:
            raise ResourceError(f"{self.resource_name}: {exc}") from exc
        return self

    def __exit__(self, *exc):
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
    retry_attempts = 3
    retry_delay = 1.0

    def _reconnect_retry(self, target: Callable, *args) -> Any:
        for attempt in range(self.retry_attempts + 1):
            try:
                if attempt:
                    logger.info(
                        "auto reconnect to resource (%d/%d): %s",
                        attempt,
                        self.retry_attempts,
                        repr(self.resource_name),
                    )
                    try:
                        self.__exit__()
                    except Exception:
                        ...
                    time.sleep(self.retry_delay)
                    self.__enter__()
                return target(*args)
            except (pyvisa.Error, ConnectionError, ResourceError) as exc:
                if attempt < self.retry_attempts:
                    logger.exception(exc)
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
