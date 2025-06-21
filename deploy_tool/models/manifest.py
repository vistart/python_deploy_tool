# deploy_tool/models/manifest.py
"""Manifest models"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class FileEntry:
    """File entry in manifest"""
    path: str  # File path (relative)
    size: int  # File size in bytes
    checksum: Optional[str] = None  # File checksum
    is_dir: bool = False  # Is directory

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'path': self.path,
            'size': self.size,
            'is_dir': self.is_dir
        }
        if self.checksum:
            data['checksum'] = self.checksum
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileEntry':
        """Create from dictionary"""
        return cls(
            path=data['path'],
            size=data['size'],
            checksum=data.get('checksum'),
            is_dir=data.get('is_dir', False)
        )


@dataclass
class Manifest:
    """Component manifest"""
    manifest_version: str
    project: Dict[str, str]
    package: Dict[str, Any]
    archive: Dict[str, Any]
    build: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'manifest_version': self.manifest_version,
            'project': self.project,
            'package': self.package,
            'archive': self.archive,
            'build': self.build
        }

        if self.metadata:
            data['metadata'] = self.metadata

        if self.signature:
            data['signature'] = self.signature

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Manifest':
        """Create from dictionary"""
        return cls(
            manifest_version=data['manifest_version'],
            project=data['project'],
            package=data['package'],
            archive=data['archive'],
            build=data['build'],
            metadata=data.get('metadata', {}),
            signature=data.get('signature')
        )

    def get_component_key(self) -> str:
        """Get component key (type:version)"""
        return f"{self.package['type']}:{self.package['version']}"


@dataclass
class ComponentRef:
    """Component reference in release manifest"""
    type: str
    version: str
    manifest: str  # Manifest file path

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            'type': self.type,
            'version': self.version,
            'manifest': self.manifest
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ComponentRef':
        """Create from dictionary"""
        return cls(
            type=data['type'],
            version=data['version'],
            manifest=data['manifest']
        )


@dataclass
class ReleaseManifest:
    """Release manifest containing multiple components"""
    manifest_version: str
    release: Dict[str, Any]
    components: List[ComponentRef]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'manifest_version': self.manifest_version,
            'release': self.release,
            'components': [c.to_dict() for c in self.components]
        }

        if self.metadata:
            data['metadata'] = self.metadata

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReleaseManifest':
        """Create from dictionary"""
        return cls(
            manifest_version=data['manifest_version'],
            release=data['release'],
            components=[ComponentRef.from_dict(c) for c in data['components']],
            metadata=data.get('metadata', {})
        )

    def get_component_count(self) -> int:
        """Get number of components"""
        return len(self.components)

    def get_component_types(self) -> List[str]:
        """Get unique component types"""
        return sorted(set(c.type for c in self.components))

    def find_component(self, component_type: str) -> Optional[ComponentRef]:
        """Find component by type"""
        for component in self.components:
            if component.type == component_type:
                return component
        return None


@dataclass
class ComponentManifest:
    """Detailed component manifest with file listing"""
    manifest_version: str
    component: Dict[str, Any]
    files: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'manifest_version': self.manifest_version,
            'component': self.component,
            'files': self.files
        }

        if self.metadata:
            data['metadata'] = self.metadata

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentManifest':
        """Create from dictionary"""
        return cls(
            manifest_version=data['manifest_version'],
            component=data['component'],
            files=data['files'],
            metadata=data.get('metadata', {})
        )