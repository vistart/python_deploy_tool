"""Component data models"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from ..constants import ComponentStatus


class ComponentType(Enum):
    """Common component types"""
    MODEL = "model"
    CONFIG = "config"
    RUNTIME = "runtime"
    DATA = "data"
    SCRIPT = "script"
    CUSTOM = "custom"

    @classmethod
    def from_string(cls, value: str) -> 'ComponentType':
        """Create ComponentType from string, defaulting to CUSTOM if not found"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.CUSTOM


@dataclass
class Component:
    """Represents a deployable component"""

    type: str
    version: str
    path: Path
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Post-initialization processing"""
        if isinstance(self.path, str):
            self.path = Path(self.path)

        if self.created_at is None:
            self.created_at = datetime.utcnow()

    @property
    def name(self) -> str:
        """Get component name (type-version)"""
        return f"{self.type}-{self.version}"

    @property
    def component_type(self) -> ComponentType:
        """Get ComponentType enum"""
        return ComponentType.from_string(self.type)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "version": self.version,
            "path": str(self.path),
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Component':
        """Create from dictionary"""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        return cls(
            type=data["type"],
            version=data["version"],
            path=Path(data["path"]),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
            created_at=created_at
        )


@dataclass
class ComponentManifest:
    """Component manifest with package and location information"""

    component: Component
    package_file: str
    package_size: int
    checksum_algorithm: str
    checksum_value: str
    locations: List['LocationInfo'] = field(default_factory=list)

    @property
    def type(self) -> str:
        """Get component type"""
        return self.component.type

    @property
    def version(self) -> str:
        """Get component version"""
        return self.component.version

    @property
    def successful_locations(self) -> List['LocationInfo']:
        """Get list of successful publish locations"""
        return [loc for loc in self.locations if loc.status == "success"]

    @property
    def available_sources(self) -> List[str]:
        """Get list of available deployment sources"""
        return [loc.name for loc in self.successful_locations]

    def add_location(self, location: 'LocationInfo') -> None:
        """Add a publish location"""
        # Remove existing location with same name if exists
        self.locations = [loc for loc in self.locations if loc.name != location.name]
        self.locations.append(location)

    def get_location(self, name: str) -> Optional['LocationInfo']:
        """Get location by name"""
        for loc in self.locations:
            if loc.name == name:
                return loc
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "component": self.component.to_dict(),
            "package": {
                "file": self.package_file,
                "size": self.package_size,
                "checksum": {
                    "algorithm": self.checksum_algorithm,
                    "value": self.checksum_value
                }
            },
            "locations": [loc.to_dict() for loc in self.locations]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentManifest':
        """Create from dictionary"""
        from .manifest import LocationInfo

        component = Component.from_dict(data["component"])
        package = data["package"]

        manifest = cls(
            component=component,
            package_file=package["file"],
            package_size=package["size"],
            checksum_algorithm=package["checksum"]["algorithm"],
            checksum_value=package["checksum"]["value"]
        )

        # Add locations
        for loc_data in data.get("locations", []):
            manifest.add_location(LocationInfo.from_dict(loc_data))

        return manifest