"""Project data models"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import Config


@dataclass
class ProjectConfig:
    """Project-specific configuration"""

    name: str
    root: Path
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"

    # Component definitions
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Full configuration
    config: Optional[Config] = None

    def __post_init__(self):
        """Post-initialization processing"""
        if isinstance(self.root, str):
            self.root = Path(self.root)

    @property
    def deployment_dir(self) -> Path:
        """Get deployment directory path"""
        return self.root / "deployment"

    @property
    def manifests_dir(self) -> Path:
        """Get manifests directory path"""
        return self.deployment_dir / "manifests"

    @property
    def configs_dir(self) -> Path:
        """Get package configs directory path"""
        return self.deployment_dir / "package-configs"

    @property
    def dist_dir(self) -> Path:
        """Get dist directory path"""
        return self.root / "dist"

    def get_component_types(self) -> List[str]:
        """Get list of defined component types"""
        return list(self.components.keys())

    def get_component_path(self, component_type: str) -> Optional[Path]:
        """Get path for a component type"""
        comp = self.components.get(component_type)
        if comp and "path" in comp:
            path = Path(comp["path"])
            if not path.is_absolute():
                path = self.root / path
            return path
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "root": str(self.root),
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "components": self.components
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """Create from dictionary"""
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.utcnow()

        return cls(
            name=data["name"],
            root=Path(data["root"]),
            description=data.get("description"),
            created_at=created_at,
            version=data.get("version", "1.0"),
            components=data.get("components", {})
        )


@dataclass
class Project:
    """Complete project representation"""

    config: ProjectConfig
    manifests: Dict[str, Any] = field(default_factory=dict)  # component -> version -> manifest
    is_initialized: bool = True

    @property
    def name(self) -> str:
        """Get project name"""
        return self.config.name

    @property
    def root(self) -> Path:
        """Get project root path"""
        return self.config.root

    @property
    def deployment_dir(self) -> Path:
        """Get deployment directory"""
        return self.config.deployment_dir

    @property
    def manifests_dir(self) -> Path:
        """Get manifests directory"""
        return self.config.manifests_dir

    @property
    def dist_dir(self) -> Path:
        """Get dist directory"""
        return self.config.dist_dir

    def get_component_manifest(self, component_type: str, version: str) -> Optional[Dict[str, Any]]:
        """Get manifest for a specific component version"""
        if component_type in self.manifests:
            return self.manifests[component_type].get(version)
        return None

    def get_component_versions(self, component_type: str) -> List[str]:
        """Get all versions for a component type"""
        if component_type in self.manifests:
            return list(self.manifests[component_type].keys())
        return []

    def get_latest_version(self, component_type: str) -> Optional[str]:
        """Get latest version for a component type"""
        versions = self.get_component_versions(component_type)
        if versions:
            # Simple string comparison for now
            # TODO: Use proper version comparison
            return sorted(versions)[-1]
        return None

    def add_manifest(self, component_type: str, version: str, manifest: Dict[str, Any]) -> None:
        """Add a manifest"""
        if component_type not in self.manifests:
            self.manifests[component_type] = {}
        self.manifests[component_type][version] = manifest

    def validate(self) -> List[str]:
        """Validate project structure and return list of issues"""
        issues = []

        # Check required directories
        if not self.root.exists():
            issues.append(f"Project root does not exist: {self.root}")

        if not self.deployment_dir.exists():
            issues.append(f"Deployment directory does not exist: {self.deployment_dir}")

        # Check component paths
        for comp_type, comp_config in self.config.components.items():
            if "path" in comp_config:
                comp_path = self.config.get_component_path(comp_type)
                if comp_path and not comp_path.exists():
                    issues.append(f"Component path does not exist: {comp_type} -> {comp_path}")

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "config": self.config.to_dict(),
            "manifests": self.manifests,
            "is_initialized": self.is_initialized
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create from dictionary"""
        return cls(
            config=ProjectConfig.from_dict(data["config"]),
            manifests=data.get("manifests", {}),
            is_initialized=data.get("is_initialized", True)
        )