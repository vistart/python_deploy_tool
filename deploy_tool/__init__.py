"""Deploy Tool - A powerful deployment tool for ML models and algorithms.

This tool provides a unified solution for packaging, publishing, and deploying
various components of machine learning projects.
"""

__version__ = "1.0.0"
__author__ = "vistart"
__email__ = "i@vistart.me"
__license__ = "MIT"

# 核心API导出
from .api.packer import Packer, pack
from .api.publisher import Publisher, publish
from .api.deployer import Deployer, deploy
from .api.query import query

# 数据模型导出
from .models.component import Component, PublishComponent
from .models.result import PackResult, PublishResult, DeployResult
from .models.manifest import Manifest, ReleaseManifest

# 异常导出
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

# 工具函数导出
from .utils import (
    find_manifest,
    list_components,
    list_releases,
    verify_component,
    suggest_version,
)

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    "__license__",

    # 主要类
    "Packer",
    "Publisher",
    "Deployer",

    # 便捷函数
    "pack",
    "publish",
    "deploy",
    "query",

    # 数据模型
    "Component",
    "PublishComponent",
    "PackResult",
    "PublishResult",
    "DeployResult",
    "Manifest",
    "ReleaseManifest",

    # 异常类
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

    # 工具函数
    "find_manifest",
    "list_components",
    "list_releases",
    "verify_component",
    "suggest_version",
]