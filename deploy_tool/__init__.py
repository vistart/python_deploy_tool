"""Deploy Tool - A powerful deployment tool for ML models and algorithms.

This tool provides a unified solution for packaging, publishing, and deploying
various components of machine learning projects.
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
__author__ = "vistart"
__email__ = "i@vistart.me"
__license__ = "MIT"
__copyright__ = "Copyright 2025 vistart"

# Core API
from .api.packer import Packer, pack
from .api.publisher import Publisher, publish
from .api.deployer import Deployer, deploy
from .api.query import query

# Data models
from .models.component import Component, PublishComponent
from .models.result import PackResult, PublishResult, DeployResult
from .models.manifest import Manifest, ReleaseManifest

# Exceptions
from .api.exceptions import (
    DeployToolError,
    PackError,
    MissingTypeError,
    PublishError,
    ComponentNotFoundError,
    DeployError,
    ReleaseNotFoundError,
    ValidationError,
    ConfigError,
    PathError,
    ProjectNotFoundError,
)

# Utility functions
from .utils import (
    find_manifest,
    list_components,
    list_releases,
    verify_component,
    suggest_version,
)

__all__ = [
    # Version information
    "__version__",
    "__version_info__",
    "__author__",
    "__email__",
    "__license__",

    # Main classes
    "Packer",
    "Publisher",
    "Deployer",

    # Core API functions
    "pack",
    "publish",
    "deploy",
    "query",

    # Data models
    "Component",
    "PublishComponent",
    "PackResult",
    "PublishResult",
    "DeployResult",
    "Manifest",
    "ReleaseManifest",

    # Exceptions
    "DeployToolError",
    "PackError",
    "MissingTypeError",
    "PublishError",
    "ComponentNotFoundError",
    "DeployError",
    "ReleaseNotFoundError",
    "ValidationError",
    "ConfigError",
    "PathError",
    "ProjectNotFoundError",

    # Utility functions
    "find_manifest",
    "list_components",
    "list_releases",
    "verify_component",
    "suggest_version",
]