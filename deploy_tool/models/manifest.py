"""Manifest data models"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..constants import MANIFEST_VERSION, StorageType


@dataclass
class ChecksumInfo:
    """Checksum information"""
    algorithm: str
    value: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            "algorithm": self.algorithm,
            "value": self.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ChecksumInfo':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class LocationInfo:
    """Information about a publish location"""

    name: str
    type: str  # filesystem, bos, s3
    status: str  # success, failed
    uploaded_at: datetime

    # Storage-specific fields
    # For filesystem
    path: Optional[str] = None

    # For BOS/S3
    endpoint: Optional[str] = None
    bucket: Optional[str] = None
    object_key: Optional[str] = None

    # Error information if failed
    error: Optional[str] = None

    def __post_init__(self):
        """Validate location info"""
        if self.type == StorageType.FILESYSTEM.value:
            if not self.path:
                raise ValueError("Filesystem location requires 'path'")
        elif self.type in [StorageType.BOS.value, StorageType.S3.value]:
            if not all([self.endpoint, self.bucket, self.object_key]):
                raise ValueError(f"{self.type} location requires endpoint, bucket, and object_key")

    @property
    def storage_type(self) -> StorageType:
        """Get StorageType enum"""
        return StorageType(self.type)

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote storage location"""
        return self.type in [StorageType.BOS.value, StorageType.S3.value]

    @property
    def display_path(self) -> str:
        """Get display path for the location"""
        if self.type == StorageType.FILESYSTEM.value:
            return self.path or ""
        else:
            return f"{self.type}://{self.bucket}/{self.object_key}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "uploaded_at": self.uploaded_at.isoformat()
        }

        if self.path:
            data["path"] = self.path
        if self.endpoint:
            data["endpoint"] = self.endpoint
        if self.bucket:
            data["bucket"] = self.bucket
        if self.object_key:
            data["object_key"] = self.object_key
        if self.error:
            data["error"] = self.error

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocationInfo':
        """Create from dictionary"""
        uploaded_at = datetime.fromisoformat(data["uploaded_at"])

        return cls(
            name=data["name"],
            type=data["type"],
            status=data["status"],
            uploaded_at=uploaded_at,
            path=data.get("path"),
            endpoint=data.get("endpoint"),
            bucket=data.get("bucket"),
            object_key=data.get("object_key"),
            error=data.get("error")
        )


@dataclass
class PackageInfo:
    """Package information in manifest"""

    file: str
    size: int
    checksum: ChecksumInfo
    compression_algorithm: Optional[str] = "gzip"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "file": self.file,
            "size": self.size,
            "checksum": self.checksum.to_dict(),
            "compression_algorithm": self.compression_algorithm
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PackageInfo':
        """Create from dictionary"""
        return cls(
            file=data["file"],
            size=data["size"],
            checksum=ChecksumInfo.from_dict(data["checksum"]),
            compression_algorithm=data.get("compression_algorithm", "gzip")
        )


@dataclass
class Manifest:
    """Complete manifest for a component"""

    version: str = MANIFEST_VERSION
    component_type: str = ""
    component_version: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    package: Optional[PackageInfo] = None
    locations: List[LocationInfo] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def component_name(self) -> str:
        """Get component name"""
        return f"{self.component_type}-{self.component_version}"

    def add_location(self, location: LocationInfo) -> None:
        """Add or update a location"""
        # Remove existing location with same name
        self.locations = [loc for loc in self.locations if loc.name != location.name]
        self.locations.append(location)

    def get_location(self, name: str) -> Optional[LocationInfo]:
        """Get location by name"""
        for location in self.locations:
            if location.name == name:
                return location
        return None

    def get_successful_locations(self) -> List[LocationInfo]:
        """Get all successful locations"""
        return [loc for loc in self.locations if loc.status == "success"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "component": {
                "type": self.component_type,
                "version": self.component_version,
                "created_at": self.created_at.isoformat()
            },
            "package": self.package.to_dict() if self.package else None,
            "locations": [loc.to_dict() for loc in self.locations],
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Manifest':
        """Create from dictionary"""
        component = data["component"]

        manifest = cls(
            version=data.get("version", MANIFEST_VERSION),
            component_type=component["type"],
            component_version=component["version"],
            created_at=datetime.fromisoformat(component["created_at"]),
            metadata=data.get("metadata", {})
        )

        if data.get("package"):
            manifest.package = PackageInfo.from_dict(data["package"])

        for loc_data in data.get("locations", []):
            manifest.locations.append(LocationInfo.from_dict(loc_data))

        return manifest


@dataclass
class VersionEntry:
    """Entry for a deployed version"""

    version: str
    deployed_at: datetime
    deployed_from: str  # Source location name
    is_current: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "deployed_at": self.deployed_at.isoformat(),
            "deployed_from": self.deployed_from,
            "is_current": self.is_current,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionEntry':
        """Create from dictionary"""
        return cls(
            version=data["version"],
            deployed_at=datetime.fromisoformat(data["deployed_at"]),
            deployed_from=data["deployed_from"],
            is_current=data.get("is_current", False),
            metadata=data.get("metadata", {})
        )


@dataclass
class DeploymentState:
    """Deployment state for a component"""

    component_type: str
    current_version: Optional[str] = None
    versions: List[VersionEntry] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def add_version(self, version: str, source: str) -> VersionEntry:
        """Add a new deployed version"""
        # Check if version already exists
        for entry in self.versions:
            if entry.version == version:
                return entry

        # Create new entry
        entry = VersionEntry(
            version=version,
            deployed_at=datetime.utcnow(),
            deployed_from=source
        )
        self.versions.append(entry)
        self.last_updated = datetime.utcnow()

        return entry

    def set_current(self, version: str) -> None:
        """Set current version"""
        for entry in self.versions:
            entry.is_current = (entry.version == version)

        self.current_version = version
        self.last_updated = datetime.utcnow()

    def get_version(self, version: str) -> Optional[VersionEntry]:
        """Get version entry"""
        for entry in self.versions:
            if entry.version == version:
                return entry
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "component_type": self.component_type,
            "current_version": self.current_version,
            "versions": [v.to_dict() for v in self.versions],
            "last_updated": self.last_updated.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentState':
        """Create from dictionary"""
        state = cls(
            component_type=data["component_type"],
            current_version=data.get("current_version"),
            last_updated=datetime.fromisoformat(data["last_updated"])
        )

        for v_data in data.get("versions", []):
            state.versions.append(VersionEntry.from_dict(v_data))

        return state