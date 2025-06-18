"""Plugin loader and discovery"""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import List, Dict, Type, Optional

from .base import Plugin, PluginManager
import logging


class PluginLoader:
    """Load plugins from various sources"""

    def __init__(self, plugin_manager: PluginManager):
        """
        Initialize plugin loader

        Args:
            plugin_manager: Plugin manager instance
        """
        self.plugin_manager = plugin_manager
        self.logger = logging.getLogger("PluginLoader")
        self._loaded_modules = set()

    def load_builtin_plugins(self) -> int:
        """
        Load all built-in plugins

        Returns:
            Number of plugins loaded
        """
        from . import builtin

        count = 0
        # Import all builtin modules
        builtin_modules = [
            'deploy_tool.plugins.builtin.git_integration',
            'deploy_tool.plugins.builtin.cache',
            'deploy_tool.plugins.builtin.hooks',
        ]

        for module_name in builtin_modules:
            try:
                if module_name not in self._loaded_modules:
                    module = importlib.import_module(module_name)
                    count += self._load_plugins_from_module(module)
                    self._loaded_modules.add(module_name)
            except ImportError as e:
                self.logger.warning(f"Failed to import builtin module {module_name}: {e}")

        return count

    def load_from_directory(self, plugin_dir: Path) -> int:
        """
        Load plugins from a directory

        Args:
            plugin_dir: Directory containing plugin modules

        Returns:
            Number of plugins loaded
        """
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            self.logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return 0

        count = 0

        # Add directory to Python path
        if str(plugin_dir) not in sys.path:
            sys.path.insert(0, str(plugin_dir))

        # Find all Python files
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    count += self._load_plugins_from_module(module)

            except Exception as e:
                self.logger.error(f"Failed to load plugin from {py_file}: {e}")

        return count

    def load_from_module(self, module_name: str) -> int:
        """
        Load plugins from a Python module

        Args:
            module_name: Fully qualified module name

        Returns:
            Number of plugins loaded
        """
        try:
            if module_name not in self._loaded_modules:
                module = importlib.import_module(module_name)
                count = self._load_plugins_from_module(module)
                self._loaded_modules.add(module_name)
                return count
            else:
                self.logger.info(f"Module {module_name} already loaded")
                return 0

        except ImportError as e:
            self.logger.error(f"Failed to import module {module_name}: {e}")
            return 0

    def _load_plugins_from_module(self, module) -> int:
        """
        Load all plugin classes from a module

        Args:
            module: Python module

        Returns:
            Number of plugins loaded
        """
        count = 0

        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                    issubclass(obj, Plugin) and
                    obj is not Plugin and
                    not inspect.isabstract(obj)):

                try:
                    # Create plugin instance
                    plugin = obj()

                    # Register with manager
                    self.plugin_manager.register(plugin)
                    count += 1

                except Exception as e:
                    self.logger.error(f"Failed to instantiate plugin {name}: {e}")

        return count

    def discover_plugins(self, search_paths: List[Path] = None) -> Dict[str, List[str]]:
        """
        Discover available plugins without loading them

        Args:
            search_paths: Additional paths to search

        Returns:
            Dictionary mapping plugin sources to plugin names
        """
        discovered = {
            'builtin': [],
            'user': [],
            'system': []
        }

        # Discover builtin plugins
        from . import builtin
        builtin_path = Path(builtin.__file__).parent

        for py_file in builtin_path.glob("*.py"):
            if not py_file.name.startswith("_"):
                discovered['builtin'].append(py_file.stem)

        # Discover user plugins
        user_plugin_dir = Path.home() / ".deploy-tool" / "plugins"
        if user_plugin_dir.exists():
            for py_file in user_plugin_dir.glob("*.py"):
                if not py_file.name.startswith("_"):
                    discovered['user'].append(py_file.stem)

        # Discover from additional paths
        if search_paths:
            for path in search_paths:
                if path.exists() and path.is_dir():
                    for py_file in path.glob("*.py"):
                        if not py_file.name.startswith("_"):
                            discovered['system'].append(py_file.stem)

        return discovered

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a specific plugin

        Args:
            plugin_name: Plugin name to reload

        Returns:
            True if successful
        """
        # First unregister the plugin
        self.plugin_manager.unregister(plugin_name)

        # Find and reload the module
        for module_name in list(self._loaded_modules):
            module = sys.modules.get(module_name)
            if module:
                # Check if this module contains the plugin
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                            issubclass(obj, Plugin) and
                            obj is not Plugin):

                        try:
                            plugin = obj()
                            if plugin.get_info().name == plugin_name:
                                # Reload the module
                                importlib.reload(module)
                                # Re-load plugins from it
                                self._load_plugins_from_module(module)
                                return True
                        except:
                            pass

        return False


# Convenience function
def load_all_plugins(plugin_manager: PluginManager = None) -> int:
    """
    Load all available plugins

    Args:
        plugin_manager: Plugin manager instance (uses global if not provided)

    Returns:
        Total number of plugins loaded
    """
    from .base import plugin_manager as global_pm

    pm = plugin_manager or global_pm
    loader = PluginLoader(pm)

    count = 0

    # Load builtin plugins
    count += loader.load_builtin_plugins()

    # Load user plugins
    user_plugin_dir = Path.home() / ".deploy-tool" / "plugins"
    if user_plugin_dir.exists():
        count += loader.load_from_directory(user_plugin_dir)

    return count