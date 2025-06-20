"""Configuration data models"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..constants import StorageType, DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY


@dataclass
class PublishTarget:
    """Configuration for a publish target"""

    name: str
    type: str  # filesystem, bos, s3
    description: Optional[str] = None

    # Common fields
    enabled: bool = True

    # Filesystem specific
    path: Optional[str] = None

    # BOS specific
    bos_endpoint: Optional[str] = None
    bos_bucket: Optional[str] = None
    bos_access_key: Optional[str] = None
    bos_secret_key: Optional[str] = None

    # S3 specific
    s3_region: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

    # Additional options
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate target configuration"""
        storage_type = StorageType(self.type)

        if storage_type == StorageType.FILESYSTEM:
            if not self.path:
                raise ValueError("Filesystem target requires 'path'")
        elif storage_type == StorageType.BOS:
            if not all([self.bos_endpoint, self.bos_bucket]):
                raise ValueError("BOS target requires endpoint and bucket")
        elif storage_type == StorageType.S3:
            if not all([self.s3_region, self.s3_bucket]):
                raise ValueError("S3 target requires region and bucket")

    @property
    def storage_type(self) -> StorageType:
        """Get StorageType enum"""
        return StorageType(self.type)

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote storage target"""
        return self.type in [StorageType.BOS.value, StorageType.S3.value]

    @property
    def requires_transfer(self) -> bool:
        """Check if manual transfer is required"""
        return self.type == StorageType.FILESYSTEM.value

    def get_display_info(self) -> str:
        """Get display information for the target"""
        if self.type == StorageType.FILESYSTEM.value:
            return f"Filesystem: {self.path}"
        elif self.type == StorageType.BOS.value:
            return f"BOS: {self.bos_bucket} ({self.bos_endpoint})"
        elif self.type == StorageType.S3.value:
            return f"S3: {self.s3_bucket} ({self.s3_region})"
        return f"{self.type}: {self.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled
        }

        if self.description:
            data["description"] = self.description

        # Add type-specific fields
        if self.path:
            data["path"] = self.path

        if self.bos_endpoint:
            data["endpoint"] = self.bos_endpoint
        if self.bos_bucket:
            data["bucket"] = self.bos_bucket
        if self.bos_access_key:
            data["access_key"] = self.bos_access_key
        if self.bos_secret_key:
            data["secret_key"] = self.bos_secret_key

        if self.s3_region:
            data["region"] = self.s3_region
        if self.s3_bucket:
            data["bucket"] = self.s3_bucket
        if self.s3_access_key:
            data["access_key"] = self.s3_access_key
        if self.s3_secret_key:
            data["secret_key"] = self.s3_secret_key

        if self.options:
            data["options"] = self.options

        return data

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'PublishTarget':
        """Create from dictionary"""
        return cls(
            name=name,
            type=data["type"],
            description=data.get("description"),
            enabled=data.get("enabled", True),
            path=data.get("path"),
            bos_endpoint=data.get("endpoint"),
            bos_bucket=data.get("bucket") if data.get("type") == "bos" else None,
            bos_access_key=data.get("access_key") if data.get("type") == "bos" else None,
            bos_secret_key=data.get("secret_key") if data.get("type") == "bos" else None,
            s3_region=data.get("region"),
            s3_bucket=data.get("bucket") if data.get("type") == "s3" else None,
            s3_access_key=data.get("access_key") if data.get("type") == "s3" else None,
            s3_secret_key=data.get("secret_key") if data.get("type") == "s3" else None,
            options=data.get("options", {})
        )


@dataclass
class FailoverConfig:
    """Failover configuration"""

    enabled: bool = True
    retry_count: int = DEFAULT_RETRY_COUNT
    retry_delay: int = DEFAULT_RETRY_DELAY
    backoff_multiplier: float = 2.0
    max_retry_delay: int = 300  # 5 minutes

    def get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay for given attempt with exponential backoff"""
        delay = self.retry_delay * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_retry_delay)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "enabled": self.enabled,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "backoff_multiplier": self.backoff_multiplier,
            "max_retry_delay": self.max_retry_delay
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailoverConfig':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class RetentionPolicy:
    """Version retention policy"""

    keep_versions: Optional[int] = None  # Keep last N versions
    keep_days: Optional[int] = None      # Keep versions newer than N days
    keep_tagged: bool = True             # Always keep tagged versions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {"keep_tagged": self.keep_tagged}
        if self.keep_versions is not None:
            data["keep_versions"] = self.keep_versions
        if self.keep_days is not None:
            data["keep_days"] = self.keep_days
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetentionPolicy':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class CacheConfig:
    """Cache configuration"""

    enabled: bool = True
    directory: str = ".deploy-tool-cache"
    max_size: Optional[str] = "10GB"
    ttl: Optional[str] = "7d"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "enabled": self.enabled,
            "directory": self.directory,
            "max_size": self.max_size,
            "ttl": self.ttl
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheConfig':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class DeployConfig:
    """Deployment configuration"""

    root: str = "/opt/deployments"
    source_priority: List[str] = field(default_factory=list)
    failover: FailoverConfig = field(default_factory=FailoverConfig)
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    custom_links: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "root": self.root,
            "source_priority": self.source_priority,
            "failover": self.failover.to_dict(),
            "retention": self.retention.to_dict(),
            "custom_links": self.custom_links
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeployConfig':
        """Create from dictionary"""
        return cls(
            root=data.get("root", "/opt/deployments"),
            source_priority=data.get("source_priority", []),
            failover=FailoverConfig.from_dict(data.get("failover", {})),
            retention=RetentionPolicy.from_dict(data.get("retention", {})),
            custom_links=data.get("custom_links", {})
        )


@dataclass
class Config:
    """Complete configuration"""

    version: str = "1.0"
    project_name: str = ""
    project_root: str = ""
    project_description: Optional[str] = None

    # Components definition
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Packaging configuration
    packaging: Dict[str, Any] = field(default_factory=dict)

    # Publish configuration
    publish_targets: Dict[str, PublishTarget] = field(default_factory=dict)
    default_targets: List[str] = field(default_factory=list)

    # Deploy configuration
    deploy: DeployConfig = field(default_factory=DeployConfig)

    # Cache configuration
    cache: CacheConfig = field(default_factory=CacheConfig)

    # Hooks
    hooks: Dict[str, List[str]] = field(default_factory=dict)

    # Logging
    logging: Dict[str, Any] = field(default_factory=dict)

    def get_component_path(self, component_type: str) -> Optional[Path]:
        """Get path for a component type"""
        comp_config = self.components.get(component_type)
        if comp_config and "path" in comp_config:
            return Path(comp_config["path"])
        return None

    def get_component_description(self, component_type: str) -> Optional[str]:
        """Get description for a component type"""
        comp_config = self.components.get(component_type)
        if comp_config:
            return comp_config.get("description")
        return None

    def get_enabled_targets(self) -> List[PublishTarget]:
        """Get list of enabled publish targets"""
        return [t for t in self.publish_targets.values() if t.enabled]

    def get_target(self, name: str) -> Optional[PublishTarget]:
        """Get publish target by name"""
        return self.publish_targets.get(name)

    def add_target(self, target: PublishTarget) -> None:
        """Add or update a publish target"""
        self.publish_targets[target.name] = target

    def remove_target(self, name: str) -> bool:
        """Remove a publish target"""
        if name in self.publish_targets:
            del self.publish_targets[name]
            # Also remove from default targets
            if name in self.default_targets:
                self.default_targets.remove(name)
            # And from source priority
            if name in self.deploy.source_priority:
                self.deploy.source_priority.remove(name)
            return True
        return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create from dictionary"""
        config = cls(
            version=data.get("version", "1.0")
        )

        # Project info
        project = data.get("project", {})
        config.project_name = project.get("name", "")
        config.project_root = project.get("root", "")
        config.project_description = project.get("description")

        # Components
        config.components = data.get("components", {})

        # Packaging
        config.packaging = data.get("packaging", {})

        # Publish targets
        publish = data.get("publish", {})
        targets_data = publish.get("targets", {})
        for name, target_data in targets_data.items():
            config.publish_targets[name] = PublishTarget.from_dict(name, target_data)

        config.default_targets = publish.get("default_targets", [])

        # Deploy config
        config.deploy = DeployConfig.from_dict(data.get("deploy", {}))

        # Cache config
        config.cache = CacheConfig.from_dict(data.get("cache", {}))

        # Hooks and logging
        config.hooks = data.get("hooks", {})
        config.logging = data.get("logging", {})

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "project": {
                "name": self.project_name,
                "root": self.project_root,
                "description": self.project_description
            },
            "components": self.components,
            "packaging": self.packaging,
            "publish": {
                "default_targets": self.default_targets,
                "targets": {
                    name: target.to_dict()
                    for name, target in self.publish_targets.items()
                }
            },
            "deploy": self.deploy.to_dict(),
            "cache": self.cache.to_dict(),
            "hooks": self.hooks,
            "logging": self.logging
        }