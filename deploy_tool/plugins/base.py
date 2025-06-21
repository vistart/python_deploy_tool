# deploy_tool/plugins/base.py
"""Plugin system base classes and manager"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class PluginPriority(Enum):
    """Plugin execution priority"""
    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


class HookPoint(Enum):
    """Available hook points in the deployment lifecycle"""
    # Project lifecycle
    PROJECT_INIT_PRE = "project.init.pre"
    PROJECT_INIT_POST = "project.init.post"

    # Pack lifecycle
    PACK_PRE = "pack.pre"
    PACK_VALIDATE = "pack.validate"
    PACK_PROCESS = "pack.process"
    PACK_POST = "pack.post"

    # Publish lifecycle
    PUBLISH_PRE = "publish.pre"
    PUBLISH_VALIDATE = "publish.validate"
    PUBLISH_UPLOAD = "publish.upload"
    PUBLISH_POST = "publish.post"

    # Deploy lifecycle
    DEPLOY_PRE = "deploy.pre"
    DEPLOY_VALIDATE = "deploy.validate"
    DEPLOY_EXECUTE = "deploy.execute"
    DEPLOY_VERIFY = "deploy.verify"
    DEPLOY_POST = "deploy.post"

    # Component lifecycle
    COMPONENT_REGISTER = "component.register"
    COMPONENT_VALIDATE = "component.validate"
    COMPONENT_DELETE = "component.delete"

    # Storage operations
    STORAGE_UPLOAD_PRE = "storage.upload.pre"
    STORAGE_UPLOAD_POST = "storage.upload.post"
    STORAGE_DOWNLOAD_PRE = "storage.download.pre"
    STORAGE_DOWNLOAD_POST = "storage.download.post"


@dataclass
class PluginContext:
    """Context passed to plugin hooks"""
    hook_point: HookPoint
    operation: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add error message"""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add warning message"""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if context has errors"""
        return len(self.errors) > 0


@dataclass
class PluginInfo:
    """Plugin metadata"""
    name: str
    version: str
    description: str
    author: Optional[str] = None
    enabled: bool = True
    priority: PluginPriority = PluginPriority.NORMAL
    hook_points: List[HookPoint] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """Base class for all plugins"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize plugin

        Args:
            config: Plugin-specific configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_info(self) -> PluginInfo:
        """Get plugin information"""
        pass

    async def initialize(self) -> None:
        """Initialize plugin (optional)"""
        pass

    async def cleanup(self) -> None:
        """Cleanup plugin resources (optional)"""
        pass

    async def handle_hook(self, context: PluginContext) -> PluginContext:
        """
        Handle hook point

        Args:
            context: Plugin context

        Returns:
            Modified context
        """
        hook_point = context.hook_point
        handler_name = f"on_{hook_point.value.replace('.', '_')}"

        # Look for specific handler method
        handler = getattr(self, handler_name, None)
        if handler and callable(handler):
            return await handler(context)

        return context


class PluginManager:
    """Central plugin manager"""

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[HookPoint, List[Plugin]] = {hp: [] for hp in HookPoint}
        self.logger = logging.getLogger("PluginManager")

    def register(self, plugin: Plugin) -> None:
        """
        Register a plugin

        Args:
            plugin: Plugin instance
        """
        info = plugin.get_info()

        if info.name in self._plugins:
            self.logger.warning(f"Plugin {info.name} already registered, replacing")

        self._plugins[info.name] = plugin

        # Register hooks
        for hook_point in info.hook_points:
            if hook_point in self._hooks:
                self._hooks[hook_point].append(plugin)
                # Sort by priority
                self._hooks[hook_point].sort(
                    key=lambda p: p.get_info().priority.value
                )

        self.logger.info(f"Registered plugin: {info.name} v{info.version}")

    def unregister(self, plugin_name: str) -> None:
        """
        Unregister a plugin

        Args:
            plugin_name: Plugin name
        """
        if plugin_name not in self._plugins:
            return

        plugin = self._plugins[plugin_name]
        del self._plugins[plugin_name]

        # Remove from hooks
        for hook_list in self._hooks.values():
            if plugin in hook_list:
                hook_list.remove(plugin)

        self.logger.info(f"Unregistered plugin: {plugin_name}")

    async def initialize_all(self) -> None:
        """Initialize all registered plugins"""
        for plugin in self._plugins.values():
            try:
                await plugin.initialize()
            except Exception as e:
                self.logger.error(f"Failed to initialize plugin {plugin.get_info().name}: {e}")

    async def cleanup_all(self) -> None:
        """Cleanup all registered plugins"""
        for plugin in self._plugins.values():
            try:
                await plugin.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to cleanup plugin {plugin.get_info().name}: {e}")

    async def execute_hook(self,
                           hook_point: HookPoint,
                           context: PluginContext) -> PluginContext:
        """
        Execute plugins for a hook point

        Args:
            hook_point: Hook point to execute
            context: Plugin context

        Returns:
            Modified context after all plugins
        """
        if hook_point not in self._hooks:
            return context

        plugins = self._hooks[hook_point]

        for plugin in plugins:
            info = plugin.get_info()

            if not info.enabled:
                continue

            try:
                self.logger.debug(f"Executing plugin {info.name} for {hook_point.value}")
                context = await plugin.handle_hook(context)

                # Stop if errors occurred and plugin has high priority
                if context.has_errors() and info.priority.value <= PluginPriority.HIGH.value:
                    self.logger.warning(f"Plugin {info.name} reported errors, stopping hook execution")
                    break

            except Exception as e:
                self.logger.error(f"Plugin {info.name} failed: {e}")
                context.add_error(f"Plugin {info.name} error: {str(e)}")

        return context

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name"""
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginInfo]:
        """List all registered plugins"""
        return [p.get_info() for p in self._plugins.values()]

    def enable_plugin(self, name: str) -> None:
        """Enable a plugin"""
        if name in self._plugins:
            self._plugins[name].get_info().enabled = True

    def disable_plugin(self, name: str) -> None:
        """Disable a plugin"""
        if name in self._plugins:
            self._plugins[name].get_info().enabled = False


# Global plugin manager instance
plugin_manager = PluginManager()