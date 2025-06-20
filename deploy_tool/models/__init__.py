"""Data models for deploy-tool"""

from .project import Project, ProjectConfig
from .component import Component, ComponentManifest, ComponentType
from .manifest import (
    Manifest,
    PackageInfo,
    LocationInfo,
    ChecksumInfo,
    DeploymentState,
    VersionEntry
)
from .config import (
    Config,
    PublishTarget,
    DeployConfig,
    FailoverConfig,
    RetentionPolicy,
    CacheConfig
)
from .result import (
    Result,
    PackResult,
    PublishResult,
    DeployResult,
    OperationStatus,
    ErrorDetail, PublishLocationResult
)

__all__ = [
    # Project models
    "Project",
    "ProjectConfig",

    # Component models
    "Component",
    "ComponentManifest",
    "ComponentType",

    # Manifest models
    "Manifest",
    "PackageInfo",
    "LocationInfo",
    "ChecksumInfo",
    "DeploymentState",
    "VersionEntry",

    # Config models
    "Config",
    "PublishTarget",
    "DeployConfig",
    "FailoverConfig",
    "RetentionPolicy",
    "CacheConfig",

    # Result models
    "Result",
    "PackResult",
    "PublishResult",
    "DeployResult",
    "OperationStatus",
    "ErrorDetail",
    "PublishLocationResult",
]