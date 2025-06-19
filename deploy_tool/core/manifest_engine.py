"""Manifest engine for generating and validating manifest files"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .path_resolver import PathResolver
from ..constants import MANIFEST_VERSION, PROJECT_CONFIG_FILE
from ..models.manifest import Manifest, ComponentManifest, FileEntry


class ManifestEngine:
    """Generate and validate manifest files"""

    def __init__(self, path_resolver: Optional[PathResolver] = None):
        self.path_resolver = path_resolver or PathResolver()
        self._hash_algorithms = ['sha256']  # Default algorithms

    def create_manifest(self,
                        package_type: str,
                        package_name: str,
                        version: str,
                        source_path: Path,
                        archive_path: Path,
                        metadata: Optional[Dict[str, Any]] = None) -> Manifest:
        """
        Create a new manifest

        Args:
            package_type: Type of package
            package_name: Name of package
            version: Version string
            source_path: Source directory/file path
            archive_path: Generated archive path
            metadata: Additional metadata

        Returns:
            Manifest object
        """
        # Convert paths to relative for portability
        source_path_rel = self._to_relative_path(source_path)
        archive_path_rel = self._to_relative_path(archive_path)

        # Calculate archive checksum
        archive_checksum = self._calculate_file_checksum(archive_path)
        archive_size = archive_path.stat().st_size

        # Create manifest
        manifest = Manifest(
            manifest_version=MANIFEST_VERSION,
            project={
                'root': '.',
                'name': self._get_project_name(),
                'config': PROJECT_CONFIG_FILE
            },
            package={
                'type': package_type,
                'name': package_name,
                'version': version,
                'created_at': datetime.now().isoformat(),
                'source': str(source_path_rel)  # Use relative path
            },
            archive={
                'filename': archive_path.name,
                'location': str(archive_path_rel),  # Use relative path
                'size': archive_size,
                'checksum': {
                    'sha256': archive_checksum
                }
            },
            build={
                'host': self._get_hostname(),
                'user': self._get_username(),
                'cwd': str(self._to_relative_path(Path.cwd())),  # Use relative path
                'tool_version': self._get_tool_version()
            }
        )

        # Add metadata if provided
        if metadata:
            manifest.metadata = metadata

        return manifest

    def _to_relative_path(self, path: Path) -> Path:
        """Convert path to relative from project root

        Args:
            path: Path to convert

        Returns:
            Relative path from project root, or original if outside project
        """
        if not path.is_absolute():
            return path

        try:
            # Try to make relative to project root
            rel_path = path.relative_to(self.path_resolver.project_root)
            return Path(".") / rel_path  # Ensure it starts with ./
        except ValueError:
            # Path is outside project root
            import logging
            logging.warning(
                f"Path {path} is outside project root {self.path_resolver.project_root}. "
                "This may affect portability."
            )
            return path

    def save_manifest(self, manifest: Manifest, output_path: Optional[Path] = None) -> Path:
        """
        Save manifest to file

        Args:
            manifest: Manifest object
            output_path: Output path (auto-generate if None)

        Returns:
            Path to saved manifest file
        """
        if output_path is None:
            output_path = self.path_resolver.get_manifest_path(
                manifest.package['type'],
                manifest.package['version']
            )

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save
        manifest_dict = manifest.to_dict()

        with open(output_path, 'w') as f:
            json.dump(manifest_dict, f, indent=2, ensure_ascii=False)

        return output_path

    def load_manifest(self, manifest_path: Path) -> Manifest:
        """
        Load manifest from file

        Args:
            manifest_path: Path to manifest file

        Returns:
            Manifest object

        Raises:
            ValidationError: If manifest is invalid
        """
        from ..api.exceptions import ValidationError

        if not manifest_path.exists():
            raise ValidationError(f"Manifest file not found: {manifest_path}")

        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)

            return Manifest.from_dict(data)
        except Exception as e:
            raise ValidationError(f"Invalid manifest file: {e}")

    def validate_manifest(self, manifest: Manifest,
                          archive_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
        """
        Validate manifest integrity

        Args:
            manifest: Manifest to validate
            archive_path: Archive file path (for checksum validation)

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check manifest version
        if manifest.manifest_version != MANIFEST_VERSION:
            errors.append(f"Unsupported manifest version: {manifest.manifest_version}")

        # Check required fields
        required_fields = [
            ('package.type', manifest.package.get('type')),
            ('package.version', manifest.package.get('version')),
            ('archive.filename', manifest.archive.get('filename')),
            ('archive.checksum', manifest.archive.get('checksum'))
        ]

        for field_name, field_value in required_fields:
            if not field_value:
                errors.append(f"Missing required field: {field_name}")

        # Validate paths are relative (warning only)
        if 'source' in manifest.package and Path(manifest.package['source']).is_absolute():
            errors.append("Warning: Source path is absolute, which may affect portability")

        if 'location' in manifest.archive and Path(manifest.archive['location']).is_absolute():
            errors.append("Warning: Archive location is absolute, which may affect portability")

        # Validate archive if provided
        if archive_path and archive_path.exists():
            # Check size
            actual_size = archive_path.stat().st_size
            expected_size = manifest.archive.get('size', 0)
            if actual_size != expected_size:
                errors.append(
                    f"Archive size mismatch: expected {expected_size}, got {actual_size}"
                )

            # Check checksum
            if 'checksum' in manifest.archive:
                for algo, expected_hash in manifest.archive['checksum'].items():
                    if algo == 'sha256':
                        actual_hash = self._calculate_file_checksum(archive_path)
                        if actual_hash != expected_hash:
                            errors.append(
                                f"Archive checksum mismatch ({algo}): "
                                f"expected {expected_hash}, got {actual_hash}"
                            )

        return len(errors) == 0, errors

    def verify_manifest_signature(self, manifest: Manifest) -> bool:
        """
        Verify manifest signature (if present)

        Args:
            manifest: Manifest to verify

        Returns:
            True if signature is valid or not present
        """
        if 'signature' not in manifest.__dict__ or not manifest.signature:
            # No signature to verify
            return True

        # TODO: Implement signature verification
        # For now, just return True
        return True

    def create_component_manifest(self,
                                  component_type: str,
                                  version: str,
                                  files: List[FileEntry],
                                  metadata: Optional[Dict[str, Any]] = None) -> ComponentManifest:
        """
        Create a component manifest with file details

        Args:
            component_type: Type of component
            version: Component version
            files: List of files in the component
            metadata: Additional metadata

        Returns:
            ComponentManifest object
        """
        # Ensure file entries use relative paths
        processed_files = []
        for file_entry in files:
            if hasattr(file_entry, 'path'):
                file_path = Path(file_entry.path)
                if file_path.is_absolute():
                    try:
                        rel_path = file_path.relative_to(self.path_resolver.project_root)
                        file_entry.path = str(rel_path)
                    except ValueError:
                        pass  # Keep absolute path if outside project
            processed_files.append(file_entry)

        manifest = ComponentManifest(
            manifest_version=MANIFEST_VERSION,
            component={
                'type': component_type,
                'version': version,
                'created_at': datetime.now().isoformat()
            },
            files=[f.to_dict() for f in processed_files],
            metadata=metadata or {}
        )

        # Calculate total size
        manifest.component['total_size'] = sum(f.size for f in files)
        manifest.component['file_count'] = len(files)

        return manifest

    def _calculate_file_checksum(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate file checksum"""
        hash_func = hashlib.new(algorithm)

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    def _get_project_name(self) -> str:
        """Get project name from config or directory"""
        try:
            from .project_manager import ProjectManager
            pm = ProjectManager(self.path_resolver)
            config = pm.load_project_config()
            return config.name
        except:
            return self.path_resolver.project_root.name

    def _get_hostname(self) -> str:
        """Get hostname"""
        import socket
        try:
            return socket.gethostname()
        except:
            return "unknown"

    def _get_username(self) -> str:
        """Get current username"""
        import os
        try:
            return os.getlogin()
        except:
            return os.environ.get('USER', 'unknown')

    def _get_tool_version(self) -> str:
        """Get tool version"""
        from .. import __version__
        return __version__

    def find_manifest(self, component_type: str, version: str) -> Optional[Path]:
        """
        Find manifest file for a component

        Args:
            component_type: Component type
            version: Component version

        Returns:
            Path to manifest file if found, None otherwise
        """
        manifest_path = self.path_resolver.get_manifest_path(component_type, version)

        if manifest_path.exists():
            return manifest_path

        # Try to find in manifests directory
        manifests_dir = self.path_resolver.get_manifests_dir()
        if manifests_dir.exists():
            # Try different naming patterns
            patterns = [
                f"{component_type}-{version}.manifest.json",
                f"{component_type}_{version}.manifest.json",
                f"{component_type}-v{version}.manifest.json",
            ]

            for pattern in patterns:
                candidate = manifests_dir / pattern
                if candidate.exists():
                    return candidate

        return None

    def list_manifests(self, component_type: Optional[str] = None) -> List[Tuple[str, str, Path]]:
        """
        List all manifests

        Args:
            component_type: Filter by component type (optional)

        Returns:
            List of (component_type, version, path) tuples
        """
        manifests = []
        manifests_dir = self.path_resolver.get_manifests_dir()

        if not manifests_dir.exists():
            return manifests

        for manifest_file in manifests_dir.glob("*.manifest.json"):
            try:
                manifest = self.load_manifest(manifest_file)
                comp_type = manifest.package['type']
                version = manifest.package['version']

                if component_type is None or comp_type == component_type:
                    manifests.append((comp_type, version, manifest_file))
            except:
                # Skip invalid manifests
                continue

        # Sort by type and version
        manifests.sort(key=lambda x: (x[0], x[1]))

        return manifests