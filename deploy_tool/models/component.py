"""Component models"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Component:
    """Component definition"""
    type: str  # Component type (user-defined)
    version: str  # Version string
    manifest_path: Optional[str] = None  # Path to manifest file

    def __str__(self) -> str:
        return f"{self.type}:{self.version}"

    def __repr__(self) -> str:
        return f"Component(type='{self.type}', version='{self.version}')"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'type': self.type,
            'version': self.version
        }
        if self.manifest_path:
            data['manifest_path'] = self.manifest_path
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Component':
        """Create from dictionary"""
        return cls(
            type=data['type'],
            version=data['version'],
            manifest_path=data.get('manifest_path')
        )

    @classmethod
    def from_string(cls, component_str: str) -> 'Component':
        """
        Create from string format 'type:version'

        Args:
            component_str: Component string

        Returns:
            Component instance

        Raises:
            ValueError: If format is invalid
        """
        parts = component_str.strip().split(':', 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid component format: '{component_str}'. "
                "Expected format: 'type:version'"
            )

        return cls(type=parts[0], version=parts[1])


@dataclass
class PublishComponent(Component):
    """Component prepared for publishing"""
    archive_path: Optional[str] = None  # Path to archive file
    archive_size: int = 0  # Archive file size
    checksum: Optional[str] = None  # Archive checksum
    storage_path: Optional[str] = None  # Remote storage path
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()

        if self.archive_path:
            data['archive_path'] = self.archive_path
        if self.archive_size:
            data['archive_size'] = self.archive_size
        if self.checksum:
            data['checksum'] = self.checksum
        if self.storage_path:
            data['storage_path'] = self.storage_path
        if self.metadata:
            data['metadata'] = self.metadata

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PublishComponent':
        """Create from dictionary"""
        return cls(
            type=data['type'],
            version=data['version'],
            manifest_path=data.get('manifest_path'),
            archive_path=data.get('archive_path'),
            archive_size=data.get('archive_size', 0),
            checksum=data.get('checksum'),
            storage_path=data.get('storage_path'),
            metadata=data.get('metadata', {})
        )

    @classmethod
    def from_component(cls, component: Component, **kwargs) -> 'PublishComponent':
        """
        Create from base Component

        Args:
            component: Base component
            **kwargs: Additional fields

        Returns:
            PublishComponent instance
        """
        return cls(
            type=component.type,
            version=component.version,
            manifest_path=component.manifest_path,
            **kwargs
        )