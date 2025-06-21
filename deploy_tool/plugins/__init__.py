# deploy_tool/plugins/__init__.py
"""Plugin system for deploy-tool"""

from .base import (
    Plugin,
    PluginInfo,
    PluginContext,
    PluginManager,
    PluginPriority,
    HookPoint,
    plugin_manager,
)
from .loader import PluginLoader, load_all_plugins

__all__ = [
    # Base classes
    'Plugin',
    'PluginInfo',
    'PluginContext',
    'PluginManager',
    'PluginPriority',
    'HookPoint',

    # Global instance
    'plugin_manager',

    # Loader
    'PluginLoader',
    'load_all_plugins',
]