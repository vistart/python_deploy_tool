<<<<<<< Updated upstream
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
=======
"""Operation result models"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path


class OperationStatus(Enum):
    """Operation status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"


@dataclass
class ErrorDetail:
    """Detailed error information"""

    code: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "code": self.code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Result:
    """Base result class"""

    status: OperationStatus
    message: str = ""
    errors: List[ErrorDetail] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
>>>>>>> Stashed changes
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

    @property
    def is_success(self) -> bool:
        """Check if operation was successful"""
        return self.status == OperationStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if operation failed"""
        return self.status == OperationStatus.FAILED

    @property
    def duration(self) -> Optional[float]:
        """Get operation duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def add_error(self, code: str, message: str, **context) -> None:
        """Add an error"""
        self.errors.append(ErrorDetail(code=code, message=message, context=context))

    def add_warning(self, message: str) -> None:
        """Add a warning"""
        self.warnings.append(message)

    def complete(self, status: Optional[OperationStatus] = None) -> None:
        """Mark operation as complete"""
        self.end_time = datetime.utcnow()
        if status:
            self.status = status


@dataclass
class PackResult(Result):
    """Result of pack operation"""

    component_type: Optional[str] = None
    component_version: Optional[str] = None
    package_path: Optional[Path] = None
    package_size: Optional[int] = None
    manifest_path: Optional[Path] = None
    compression_algorithm: Optional[str] = None
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "message": self.message,
            "component_type": self.component_type,
            "component_version": self.component_version,
            "package_path": str(self.package_path) if self.package_path else None,
            "package_size": self.package_size,
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "compression_algorithm": self.compression_algorithm,
            "checksum": self.checksum,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "duration": self.duration
        }


@dataclass
class PublishLocationResult:
    """Result for a single publish location"""

    target_name: str
    status: OperationStatus
    message: str = ""
    location_info: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None
    transfer_size: Optional[int] = None
    transfer_duration: Optional[float] = None

    @property
    def archive_size(self) -> Optional[int]:
        """Get archive size if available"""
        if self.archive_path and Path(self.archive_path).exists():
            return Path(self.archive_path).stat().st_size
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
<<<<<<< Updated upstream
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
=======
            "target_name": self.target_name,
            "status": self.status.value,
            "message": self.message
        }

        if self.location_info:
            data["location_info"] = self.location_info
        if self.error:
            data["error"] = self.error.to_dict()
        if self.transfer_size:
            data["transfer_size"] = self.transfer_size
        if self.transfer_duration:
            data["transfer_duration"] = self.transfer_duration
>>>>>>> Stashed changes

        return data


@dataclass
<<<<<<< Updated upstream
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
=======
class PublishResult(Result):
    """Result of publish operation"""

    component_type: Optional[str] = None
    component_version: Optional[str] = None
    target_results: List[PublishLocationResult] = field(default_factory=list)
    manifest_updated: bool = False

    @property
    def successful_targets(self) -> List[str]:
        """Get list of successful target names"""
        return [r.target_name for r in self.target_results if r.status == OperationStatus.SUCCESS]

    @property
    def failed_targets(self) -> List[str]:
        """Get list of failed target names"""
        return [r.target_name for r in self.target_results if r.status == OperationStatus.FAILED]

    def add_target_result(self, result: PublishLocationResult) -> None:
        """Add a target result"""
        self.target_results.append(result)

        # Update overall status
        if all(r.status == OperationStatus.SUCCESS for r in self.target_results):
            self.status = OperationStatus.SUCCESS
        elif any(r.status == OperationStatus.SUCCESS for r in self.target_results):
            self.status = OperationStatus.PARTIAL
        else:
            self.status = OperationStatus.FAILED

    def get_filesystem_targets(self) -> List[PublishLocationResult]:
        """Get results for filesystem targets that need manual transfer"""
        fs_results = []
        for result in self.target_results:
            if result.location_info and result.location_info.get("type") == "filesystem":
                fs_results.append(result)
        return fs_results

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "message": self.message,
            "component_type": self.component_type,
            "component_version": self.component_version,
            "target_results": [r.to_dict() for r in self.target_results],
            "manifest_updated": self.manifest_updated,
            "successful_targets": self.successful_targets,
            "failed_targets": self.failed_targets,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "duration": self.duration
        }


@dataclass
class DeployResult(Result):
    """Result of deploy operation"""

    component_type: Optional[str] = None
    component_version: Optional[str] = None
    deploy_path: Optional[Path] = None
    source_used: Optional[str] = None
    sources_tried: List[str] = field(default_factory=list)
    version_switched: bool = False
    previous_version: Optional[str] = None
    links_updated: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "message": self.message,
            "component_type": self.component_type,
            "component_version": self.component_version,
            "deploy_path": str(self.deploy_path) if self.deploy_path else None,
            "source_used": self.source_used,
            "sources_tried": self.sources_tried,
            "version_switched": self.version_switched,
            "previous_version": self.previous_version,
            "links_updated": self.links_updated,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "duration": self.duration
        }


@dataclass
class BatchResult(Result):
    """Result of batch operations"""

    operation_type: str = ""  # pack, publish, deploy
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    results: List[Union[PackResult, PublishResult, DeployResult]] = field(default_factory=list)

    def add_result(self, result: Union[PackResult, PublishResult, DeployResult]) -> None:
        """Add an operation result"""
        self.results.append(result)
        self.total_operations += 1

        if result.is_success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1

        # Update overall status
        if self.failed_operations == 0:
            self.status = OperationStatus.SUCCESS
        elif self.successful_operations > 0:
            self.status = OperationStatus.PARTIAL
        else:
            self.status = OperationStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "message": self.message,
            "operation_type": self.operation_type,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "results": [r.to_dict() for r in self.results],
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "duration": self.duration
        }
>>>>>>> Stashed changes
