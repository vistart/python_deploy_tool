# deploy_tool/models/release.py
"""Release models for the deployment tool"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ReleaseManifest:
    """Release manifest containing multiple components"""
    release_version: str
    release_name: Optional[str] = None
    created_at: Optional[str] = None
    components: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'release_version': self.release_version,
            'release_name': self.release_name,
            'created_at': self.created_at,
            'components': self.components,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReleaseManifest':
        """Create from dictionary"""
        return cls(
            release_version=data['release_version'],
            release_name=data.get('release_name'),
            created_at=data.get('created_at'),
            components=data.get('components', []),
            metadata=data.get('metadata', {})
        )


@dataclass
class PublishResult:
    """Result of a publish operation"""
    success: bool
    release_version: Optional[str] = None
    method: Optional[str] = None
    location: Optional[str] = None
    instructions: Optional[str] = None
    published_files: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeployResult:
    """Result of a deployment operation"""
    success: bool
    release_version: Optional[str] = None
    target_dir: Optional[str] = None
    components: Dict[str, str] = field(default_factory=dict)  # type -> path
    symlinks: Dict[str, str] = field(default_factory=dict)  # link -> target
    state_file: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None


@dataclass
class DeploymentState:
    """Current deployment state"""
    release_version: str
    deployed_at: str
    target_dir: str
    components: Dict[str, str]
    symlinks: Dict[str, str]
    previous_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'release_version': self.release_version,
            'deployed_at': self.deployed_at,
            'target_dir': self.target_dir,
            'components': self.components,
            'symlinks': self.symlinks,
            'previous_version': self.previous_version,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentState':
        """Create from dictionary"""
        return cls(
            release_version=data['release_version'],
            deployed_at=data['deployed_at'],
            target_dir=data['target_dir'],
            components=data.get('components', {}),
            symlinks=data.get('symlinks', {}),
            previous_version=data.get('previous_version'),
            metadata=data.get('metadata', {})
        )


@dataclass
class ReleaseInfo:
    """Information about a release"""
    version: str
    name: Optional[str] = None
    created_at: Optional[str] = None
    component_count: int = 0
    total_size: Optional[int] = None
    components: List[Dict[str, str]] = field(default_factory=list)

    def format_size(self) -> str:
        """Format size in human-readable form"""
        if self.total_size is None:
            return "Unknown"

        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.total_size < 1024:
                return f"{self.total_size:.1f} {unit}"
            self.total_size /= 1024

        return f"{self.total_size:.1f} TB"