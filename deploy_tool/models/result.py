"""Result models for deploy-tool operations"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .component import Component


@dataclass
class PackResult:
    """Pack operation result"""
    success: bool
    package_type: str
    version: str
    manifest_path: Optional[str] = None
    archive_path: Optional[str] = None
    archive_size: Optional[int] = None
    config_path: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    git_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'package_type': self.package_type,
            'version': self.version,
            'duration': self.duration,
            'metadata': self.metadata,
            'git_suggestions': self.git_suggestions
        }

        if self.manifest_path:
            data['manifest_path'] = self.manifest_path
        if self.archive_path:
            data['archive_path'] = self.archive_path
        if self.archive_size is not None:
            data['archive_size'] = self.archive_size
        if self.config_path:
            data['config_path'] = self.config_path
        if self.error:
            data['error'] = self.error

        return data


@dataclass
class ComponentPublishResult:
    """Single component publish result"""
    component: Component
    success: bool
    storage_path: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'component': self.component.to_dict(),
            'success': self.success,
            'storage_path': self.storage_path
        }

        if self.error:
            data['error'] = self.error

        return data


@dataclass
class PublishResult:
    """Publish operation result"""
    success: bool
    release_version: Optional[str] = None
    release_manifest: Optional[str] = None
    components: List[ComponentPublishResult] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'duration': self.duration,
            'components': [c.to_dict() for c in self.components]
        }

        if self.release_version:
            data['release_version'] = self.release_version
        if self.release_manifest:
            data['release_manifest'] = self.release_manifest
        if self.error:
            data['error'] = self.error

        return data


@dataclass
class DeployResult:
    """Deployment operation result"""
    success: bool
    deploy_type: str  # "release" or "component"
    deploy_target: str
    deployed_components: List[Component] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0
    verification: Optional['VerifyResult'] = None
    rollback_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'deploy_type': self.deploy_type,
            'deploy_target': self.deploy_target,
            'duration': self.duration,
            'rollback_available': self.rollback_available,
            'deployed_components': [c.to_dict() for c in self.deployed_components]
        }

        if self.error:
            data['error'] = self.error

        if self.verification:
            data['verification'] = self.verification.to_dict()

        return data


@dataclass
class VerifyResult:
    """Verification operation result"""
    success: bool
    component_type: str
    version: str
    checksum_valid: bool = False
    files_complete: bool = False
    manifest_valid: bool = False
    issues: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'component_type': self.component_type,
            'version': self.version,
            'checksum_valid': self.checksum_valid,
            'files_complete': self.files_complete,
            'manifest_valid': self.manifest_valid,
            'issues': self.issues
        }

        if self.error:
            data['error'] = self.error

        return data