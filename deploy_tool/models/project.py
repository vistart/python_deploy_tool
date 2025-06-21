# deploy_tool/models/project.py
"""Project information models"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ProjectInfo:
    """Project information"""
    name: str
    type: str = "general"
    description: str = ""
    root: str = "."
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'root': self.root,
            'version': self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectInfo':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            type=data.get('type', 'general'),
            description=data.get('description', ''),
            root=data.get('root', '.'),
            version=data.get('version', '1.0')
        )


@dataclass
class DeploymentInfo:
    """Deployment information"""
    target: str
    environment: str = "default"
    components: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'target': self.target,
            'environment': self.environment,
            'components': self.components
        }

        if self.timestamp:
            data['timestamp'] = self.timestamp
        if self.metadata:
            data['metadata'] = self.metadata

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentInfo':
        """Create from dictionary"""
        return cls(
            target=data['target'],
            environment=data.get('environment', 'default'),
            components=data.get('components', []),
            timestamp=data.get('timestamp'),
            metadata=data.get('metadata', {})
        )


@dataclass
class PathConfig:
    """Project path configuration"""
    deployment: str = "./deployment"
    manifests: str = "./deployment/manifests"
    releases: str = "./deployment/releases"
    configs: str = "./deployment/package-configs"
    dist: str = "./dist"
    cache: str = "./.deploy-tool-cache"

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            'deployment': self.deployment,
            'manifests': self.manifests,
            'releases': self.releases,
            'configs': self.configs,
            'dist': self.dist,
            'cache': self.cache
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'PathConfig':
        """Create from dictionary"""
        return cls(
            deployment=data.get('deployment', './deployment'),
            manifests=data.get('manifests', './deployment/manifests'),
            releases=data.get('releases', './deployment/releases'),
            configs=data.get('configs', './deployment/package-configs'),
            dist=data.get('dist', './dist'),
            cache=data.get('cache', './.deploy-tool-cache')
        )


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration"""
    name: str
    storage: Optional[Dict[str, Any]] = None
    paths: Optional[Dict[str, str]] = None
    defaults: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {'name': self.name}

        if self.storage:
            data['storage'] = self.storage
        if self.paths:
            data['paths'] = self.paths
        if self.defaults:
            data['defaults'] = self.defaults

        return data

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'EnvironmentConfig':
        """Create from dictionary"""
        return cls(
            name=name,
            storage=data.get('storage'),
            paths=data.get('paths'),
            defaults=data.get('defaults')
        )