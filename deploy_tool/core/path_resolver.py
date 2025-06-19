"""Path resolver - Core component for unified path management"""

import os
import threading
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Union, Dict

from ..constants import PROJECT_MARKERS, PROJECT_CONFIG_FILE


class PathType(Enum):
    """Path types for resolution"""
    AUTO = auto()  # Automatic detection
    SOURCE = auto()  # Source file path (relative to project root)
    CONFIG = auto()  # Configuration file path
    MANIFEST = auto()  # Manifest file path
    RELEASE = auto()  # Release file path
    DIST = auto()  # Distribution/output path
    CACHE = auto()  # Cache path
    ABSOLUTE = auto()  # Absolute path (no conversion)


class ProjectRootCache:
    """Thread-safe cache for project root directories"""

    def __init__(self):
        self._cache: Dict[str, Path] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Path]:
        """Get cached project root"""
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Path) -> None:
        """Cache project root"""
        with self._lock:
            self._cache[key] = value

    def cache_path_hierarchy(self, start_path: Path, project_root: Path) -> None:
        """Cache all parent directories up to project root"""
        with self._lock:
            current = start_path
            while current != project_root and current != current.parent:
                self._cache[str(current.resolve())] = project_root
                current = current.parent
            self._cache[str(project_root.resolve())] = project_root


class PathResolver:
    """Unified path resolver - Core of all path operations

    This class provides lazy initialization to avoid early project root detection.
    Project root is only searched when first accessed.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize path resolver

        Args:
            project_root: Explicit project root path. If provided, no search is performed.
        """
        self._project_root = project_root
        self._cache = ProjectRootCache()
        self._paths_config: Optional[Dict[str, str]] = None
        self._project_found = project_root is not None
        self._find_attempted = False

    @property
    def project_root(self) -> Path:
        """Get project root directory with lazy loading

        Returns:
            Path to project root

        Raises:
            ProjectNotFoundError: If no project root can be found
        """
        if self._project_root is None and not self._find_attempted:
            self._find_attempted = True
            self._project_root = self.find_project_root()
            self._project_found = True

        if self._project_root is None:
            from ..api.exceptions import ProjectNotFoundError
            raise ProjectNotFoundError(
                "No project root found. "
                "Please run 'deploy-tool init' or ensure you're in a project directory."
            )

        return self._project_root

    def find_project_root(self, start_path: Optional[Path] = None) -> Path:
        """Find project root directory by looking for marker files

        Args:
            start_path: Starting directory (default: current working directory)

        Returns:
            Path to project root directory

        Raises:
            ProjectNotFoundError: If no project root found
        """
        from ..api.exceptions import ProjectNotFoundError

        start_path = Path(start_path) if start_path else Path.cwd()
        start_path = start_path.resolve()

        # Check cache first
        cached = self._cache.get(str(start_path))
        if cached:
            return cached

        # Search for project markers
        current = start_path
        while current != current.parent:
            for marker in PROJECT_MARKERS:
                marker_path = current / marker
                if marker_path.exists():
                    # Found project root
                    self._cache.cache_path_hierarchy(start_path, current)
                    return current
            current = current.parent

        # No project root found
        raise ProjectNotFoundError(
            f"No project root found from {start_path}. "
            f"Please run 'deploy-tool init' or create {PROJECT_CONFIG_FILE}"
        )

    def resolve(self, path: Union[str, Path],
                path_type: PathType = PathType.AUTO) -> Path:
        """Resolve path to absolute path based on type

        Args:
            path: Path to resolve
            path_type: Type of path for resolution rules

        Returns:
            Resolved absolute path
        """
        path = Path(path)

        # Already absolute
        if path.is_absolute():
            return path

        # ABSOLUTE type doesn't need project root
        if path_type == PathType.ABSOLUTE:
            return path.resolve()

        # Get base directory based on path type
        base = self._get_base_for_type(path_type)
        return (base / path).resolve()

    def _get_base_for_type(self, path_type: PathType) -> Path:
        """Get base directory for path type

        Args:
            path_type: Type of path

        Returns:
            Base directory path
        """
        if path_type == PathType.SOURCE or path_type == PathType.AUTO:
            return self.project_root
        elif path_type == PathType.CONFIG:
            return self.get_configs_dir()
        elif path_type == PathType.MANIFEST:
            return self.get_manifests_dir()
        elif path_type == PathType.RELEASE:
            return self.get_releases_dir()
        elif path_type == PathType.DIST:
            return self.get_dist_dir()
        elif path_type == PathType.CACHE:
            return self.get_cache_dir()
        else:
            return self.project_root

    def to_relative(self, path: Union[str, Path]) -> Path:
        """Convert absolute path to relative path from project root

        Args:
            path: Path to convert

        Returns:
            Relative path from project root
        """
        path = Path(path).resolve()
        try:
            return path.relative_to(self.project_root)
        except ValueError:
            # Path is outside project, return as-is
            return path

    def validate_path_within_project(self, path: Union[str, Path]) -> bool:
        """Check if path is within project boundaries

        Args:
            path: Path to validate

        Returns:
            True if path is within project
        """
        path = Path(path).resolve()
        try:
            path.relative_to(self.project_root)
            return True
        except ValueError:
            return False

    def get_deployment_dir(self) -> Path:
        """Get deployment directory"""
        from ..constants import DEFAULT_DEPLOYMENT_DIR
        return self.resolve(
            self._get_path_config("deployment", DEFAULT_DEPLOYMENT_DIR)
        )

    def get_manifests_dir(self) -> Path:
        """Get manifests directory"""
        from ..constants import DEFAULT_MANIFESTS_DIR
        return self.resolve(
            self._get_path_config("manifests", DEFAULT_MANIFESTS_DIR)
        )

    def get_releases_dir(self) -> Path:
        """Get releases directory"""
        from ..constants import DEFAULT_RELEASES_DIR
        return self.resolve(
            self._get_path_config("releases", DEFAULT_RELEASES_DIR)
        )

    def get_configs_dir(self) -> Path:
        """Get package configs directory"""
        from ..constants import DEFAULT_CONFIGS_DIR
        return self.resolve(
            self._get_path_config("configs", DEFAULT_CONFIGS_DIR)
        )

    def get_dist_dir(self) -> Path:
        """Get distribution/output directory"""
        from ..constants import DEFAULT_DIST_DIR
        return self.resolve(
            self._get_path_config("dist", DEFAULT_DIST_DIR)
        )

    def get_cache_dir(self) -> Path:
        """Get cache directory"""
        from ..constants import DEFAULT_CACHE_DIR
        cache_dir = self.resolve(
            self._get_path_config("cache", DEFAULT_CACHE_DIR)
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_manifest_path(self, component_type: str, version: str) -> Path:
        """Get manifest file path for a component

        Args:
            component_type: Component type
            version: Component version

        Returns:
            Path to manifest file
        """
        from ..constants import MANIFEST_FILE_PATTERN
        filename = MANIFEST_FILE_PATTERN.format(type=component_type, version=version)
        return self.get_manifests_dir() / filename

    def get_release_path(self, version: str) -> Path:
        """Get release file path

        Args:
            version: Release version

        Returns:
            Path to release file
        """
        from ..constants import RELEASE_FILE_PATTERN
        filename = RELEASE_FILE_PATTERN.format(version=version)
        return self.get_releases_dir() / filename

    def get_config_path(self, name: str) -> Path:
        """Get configuration file path

        Args:
            name: Configuration name (without extension)

        Returns:
            Path to configuration file
        """
        if not name.endswith(('.yaml', '.yml', '.json')):
            name = f"{name}.yaml"
        return self.get_configs_dir() / name

    def get_archive_path(self, component_type: str, version: str,
                         compression: str = "gz") -> Path:
        """Get archive file path

        Args:
            component_type: Component type
            version: Component version
            compression: Compression type

        Returns:
            Path to archive file
        """
        from ..constants import ARCHIVE_FILE_PATTERNS
        pattern = ARCHIVE_FILE_PATTERNS.get(compression, ARCHIVE_FILE_PATTERNS["gz"])
        filename = pattern.format(type=component_type, version=version)
        return self.get_dist_dir() / filename

    def _get_path_config(self, key: str, default: str) -> str:
        """Get path configuration value with safe loading

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        if self._paths_config is None:
            self._load_paths_config_safe()

        if self._paths_config and key in self._paths_config:
            return self._paths_config[key]
        return default

    def _load_paths_config_safe(self) -> None:
        """Load paths configuration from project config safely

        This method will not fail if project root is not available.
        It will simply use an empty configuration.
        """
        self._paths_config = {}

        try:
            # Only attempt to load if we have a project root
            if self._project_found and self._project_root:
                config_file = self._project_root / PROJECT_CONFIG_FILE
                if config_file.exists():
                    import yaml
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                        self._paths_config = config.get('paths', {})
        except Exception:
            # Silently ignore errors, use empty config
            pass

    def ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        dirs = [
            self.get_deployment_dir(),
            self.get_manifests_dir(),
            self.get_releases_dir(),
            self.get_configs_dir(),
            self.get_dist_dir(),
            self.get_cache_dir(),
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_relative_to_root(self, path: Union[str, Path]) -> str:
        """Get path relative to project root as string

        Args:
            path: Path to convert

        Returns:
            Relative path string with forward slashes
        """
        rel_path = self.to_relative(path)
        # Always use forward slashes for portability
        return str(rel_path).replace(os.sep, '/')

    def __repr__(self) -> str:
        """String representation"""
        if self._project_root:
            return f"PathResolver(project_root={self._project_root})"
        return "PathResolver(project_root=<not determined>)"