"""Result models for operations"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from .component import Component, PublishComponent


@dataclass
class PackResult:
    """Packing operation result"""
    success: bool
    package_type: str
    version: str
    manifest_path: Optional[str] = None
    archive_path: Optional[str] = None
    config_path: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    git_suggestions: List[str] = field(default_factory=list)

    @property
    def archive_size(self) -> Optional[int]:
        """Get archive size if available"""
        if self.archive_path and Path(self.archive_path).exists():
            return Path(self.archive_path).stat().st_size
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'package_type': self.package_type,
            'version': self.version,
            'duration': self.duration
        }

        if self.manifest_path:
            data['manifest_path'] = self.manifest_path
        if self.archive_path:
            data['archive_path'] = self.archive_path
        if self.config_path:
            data['config_path'] = self.config_path
        if self.error:
            data['error'] = self.error
        if self.metadata:
            data['metadata'] = self.metadata
        if self.git_suggestions:
            data['git_suggestions'] = self.git_suggestions

        return data


@dataclass
class ComponentPublishResult:
    """Single component publish result"""
    component: PublishComponent
    success: bool
    storage_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'component': self.component.to_dict(),
            'success': self.success
        }

        if self.storage_path:
            data['storage_path'] = self.storage_path
        if self.error:
            data['error'] = self.error

        return data


@dataclass
class PublishResult:
    """Publishing operation result"""
    success: bool
    release_version: Optional[str] = None
    release_manifest: Optional[str] = None
    components: List[ComponentPublishResult] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0

    @property
    def total_size(self) -> int:
        """Get total size of published components"""
        return sum(c.component.archive_size for c in self.components)

    @property
    def successful_count(self) -> int:
        """Get count of successfully published components"""
        return sum(1 for c in self.components if c.success)

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
    target_host: str
    deployed_components: List[Component] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0
    rollback_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'target_host': self.target_host,
            'duration': self.duration,
            'rollback_available': self.rollback_available,
            'deployed_components': [c.to_dict() for c in self.deployed_components]
        }

        if self.error:
            data['error'] = self.error

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