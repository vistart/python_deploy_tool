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
<<<<<<< HEAD
    remote_path: Optional[str] = None
=======
    storage_path: Optional[str] = None
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
<<<<<<< HEAD
            'component': self.component.to_dict() if hasattr(self.component, 'to_dict') else str(self.component),
            'success': self.success
        }

        if self.remote_path:
            data['remote_path'] = self.remote_path
=======
            'component': self.component.to_dict(),
            'success': self.success
        }

        if self.storage_path:
            data['storage_path'] = self.storage_path
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
        if self.error:
            data['error'] = self.error

        return data


@dataclass
class PublishResult:
    """Publishing operation result"""
    success: bool
    published_components: List[ComponentPublishResult] = field(default_factory=list)
    release_version: Optional[str] = None
    release_path: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0
    post_publish_instructions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

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
            'published_components': [c.to_dict() for c in self.published_components],
            'post_publish_instructions': self.post_publish_instructions,
            'metadata': self.metadata
        }

        if self.release_version:
            data['release_version'] = self.release_version
        if self.release_path:
            data['release_path'] = self.release_path
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
<<<<<<< HEAD
    verification: Optional['VerifyResult'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
=======
    rollback_available: bool = False
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'target_host': self.target_host,
            'duration': self.duration,
            'deployed_components': [
                c.to_dict() if hasattr(c, 'to_dict') else str(c)
                for c in self.deployed_components
            ],
            'metadata': self.metadata
        }

        if self.error:
            data['error'] = self.error
<<<<<<< HEAD
        if self.verification:
            data['verification'] = self.verification.to_dict()
=======
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

        return data


@dataclass
class VerifyResult:
    """Verification result"""
    success: bool
    component_type: str
    version: str
    checksum_valid: bool = True
    files_complete: bool = True
    manifest_valid: bool = True
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


@dataclass
class ValidationResult:
    """Validation result with detailed findings"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add error message"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add warning message"""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add info message"""
        self.info.append(message)

    def add_success(self, message: str) -> None:
        """Add success message (alias for info)"""
        self.info.append(message)

    def __bool__(self) -> bool:
        """Boolean evaluation returns is_valid"""
        return self.is_valid

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info
        }


@dataclass
class QueryResult:
    """Query operation result"""
    success: bool
    query_type: str  # "components", "releases", "status", etc.
    results: List[Any] = field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'success': self.success,
            'query_type': self.query_type,
            'results': self.results,
            'total_count': self.total_count,
            'metadata': self.metadata
        }

        if self.error:
            data['error'] = self.error

        return data


@dataclass
class StatusResult:
    """Status check result"""
    healthy: bool
    service: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'healthy': self.healthy,
            'service': self.service,
            'details': self.details
        }

        if self.error:
            data['error'] = self.error

        return data