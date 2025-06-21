# deploy_tool/plugins/builtin/__init__.py
"""Built-in plugins for deploy-tool"""

from .git_integration import GitIntegrationPlugin
from .cache import CachePlugin
from .hooks import LifecycleHooksPlugin

__all__ = [
    'GitIntegrationPlugin',
    'CachePlugin',
    'LifecycleHooksPlugin',
]