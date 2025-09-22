import logging
from typing import Any

__all__ = ["Plugin", "PluginRegistry"]

logger = logging.getLogger(__name__)


class Plugin:
    """Base class for plugins."""

    def install(self, context: Any) -> None:
        ...

    def uninstall(self, context: Any) -> None:
        ...


class PluginRegistry:
    """Manager class for handling plugins."""

    def __init__(self, context: Any) -> None:
        self._context: Any = context
        self._plugins: list[Plugin] = []

    def install(self, plugin: Plugin) -> None:
        """Install a plugin."""
        logger.debug("Installing plugin %s...", repr(type(plugin).__name__))
        self._plugins.append(plugin)
        plugin.install(self._context)
        logger.debug("Installing plugin %s... done.", repr(type(plugin).__name__))

    @property
    def plugins(self) -> list[Plugin]:
        """Return list of installed plugins."""
        return [plugin for plugin in self._plugins]

    def uninstall(self) -> None:
        """Uninstall all plugins."""
        for plugin in self._plugins[:]:
            logger.debug("Uninstalling plugin %s...", repr(type(plugin).__name__))
            plugin.uninstall(self._context)
            self._plugins.remove(plugin)
            logger.debug("Uninstalling plugin %s... done.", repr(type(plugin).__name__))
