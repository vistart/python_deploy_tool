"""Path resolution module for deploy-tool"""

import os
from pathlib import Path
from typing import Optional, Union

from ..constants import (
    DEFAULT_DEPLOYMENT_DIR,
    DEFAULT_MANIFESTS_DIR,
    DEFAULT_CONFIGS_DIR,
    DEFAULT_DIST_DIR,
    DEFAULT_CACHE_DIR
)


class PathResolver:
    """Resolves paths within a deploy-tool project"""

    def __init__(self, project_root: Union[str, Path]):
        """Initialize path resolver

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root).resolve()

    def resolve(self, path: Union[str, Path]) -> Path:
        """Resolve a path relative to project root

        Args:
            path: Path to resolve (can be relative or absolute)

        Returns:
            Resolved absolute path
        """
        path = Path(path)

        if path.is_absolute():
            return path

        # Resolve relative to project root
        return (self.project_root / path).resolve()

    def get_deployment_dir(self) -> Path:
        """Get deployment directory path

        Returns:
            Path to deployment directory
        """
        return self.project_root / DEFAULT_DEPLOYMENT_DIR

    def get_manifests_dir(self) -> Path:
        """Get manifests directory path

        Returns:
            Path to manifests directory
        """
        return self.project_root / DEFAULT_MANIFESTS_DIR

    def get_configs_dir(self) -> Path:
        """Get package configs directory path

        Returns:
            Path to package configs directory
        """
        return self.project_root / DEFAULT_CONFIGS_DIR

    def get_dist_dir(self) -> Path:
        """Get dist directory path

        Returns:
            Path to dist directory
        """
        return self.project_root / DEFAULT_DIST_DIR

    def get_cache_dir(self) -> Path:
        """Get cache directory path

        Returns:
            Path to cache directory
        """
        # Check environment variable first
        cache_dir = os.environ.get('DEPLOY_TOOL_CACHE')
        if cache_dir:
            return Path(cache_dir).resolve()

        return self.project_root / DEFAULT_CACHE_DIR

    def get_component_manifest_path(
        self,
        component_type: str,
        version: str
    ) -> Path:
        """Get path for a component manifest file

        Args:
            component_type: Type of component
            version: Component version

        Returns:
            Path to manifest file
        """
        return self.get_manifests_dir() / component_type / f"{version}.json"

    def get_package_path(
        self,
        component_type: str,
        version: str,
        compression: str = "gz"
    ) -> Path:
        """Get path for a package file

        Args:
            component_type: Type of component
            version: Component version
            compression: Compression extension

        Returns:
            Path to package file
        """
        if compression:
            filename = f"{component_type}-{version}.tar.{compression}"
        else:
            filename = f"{component_type}-{version}.tar"

        return self.get_dist_dir() / filename

    def get_component_source_path(
        self,
        component_type: str,
        component_config: dict
    ) -> Optional[Path]:
        """Get source path for a component

        Args:
            component_type: Type of component
            component_config: Component configuration dict

        Returns:
            Resolved source path or None
        """
        if 'path' not in component_config:
            return None

        return self.resolve(component_config['path'])

    def make_relative(self, path: Union[str, Path]) -> Path:
        """Make a path relative to project root

        Args:
            path: Path to make relative

        Returns:
            Relative path
        """
        path = Path(path).resolve()

        try:
            return path.relative_to(self.project_root)
        except ValueError:
            # Path is not under project root
            return path

    def is_under_project(self, path: Union[str, Path]) -> bool:
        """Check if a path is under the project root

        Args:
            path: Path to check

        Returns:
            True if path is under project root
        """
        path = Path(path).resolve()

        try:
            path.relative_to(self.project_root)
            return True
        except ValueError:
            return False

    def expand_path(self, path: str) -> Path:
        """Expand a path with environment variables and user home

        Args:
            path: Path string to expand

        Returns:
            Expanded path
        """
        # Expand environment variables
        path = os.path.expandvars(path)

        # Expand user home
        path = os.path.expanduser(path)

        # Resolve to absolute
        return self.resolve(path)