"""Manifest engine for managing component manifests"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..models.manifest import Manifest
from ..models.component import ComponentManifest
from ..constants import MANIFEST_FILE_PATTERN, MANIFEST_VERSION
from ..utils.file_utils import ensure_directory


class ManifestEngine:
    """Engine for managing component manifests"""

    def __init__(self, manifests_dir: Path):
        """Initialize manifest engine

        Args:
            manifests_dir: Directory to store manifests
        """
        self.manifests_dir = manifests_dir
        ensure_directory(self.manifests_dir)

    def _get_manifest_path(self, component_type: str, version: str) -> Path:
        """Get path for a manifest file

        Args:
            component_type: Type of component
            version: Component version

        Returns:
            Path to manifest file
        """
        # Create component subdirectory
        component_dir = self.manifests_dir / component_type
        filename = MANIFEST_FILE_PATTERN.format(
            component=component_type,
            version=version
        )
        return component_dir / filename

    async def save_manifest(self, manifest: Manifest) -> Path:
        """Save manifest to file

        Args:
            manifest: Manifest to save

        Returns:
            Path to saved manifest file
        """
        manifest_path = self._get_manifest_path(
            manifest.component_type,
            manifest.component_version
        )

        # Ensure directory exists
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save
        data = manifest.to_dict()

        # Pretty print JSON for readability
        with open(manifest_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return manifest_path

    async def load_manifest(
        self,
        component_type: str,
        version: str
    ) -> Optional[Manifest]:
        """Load manifest from file

        Args:
            component_type: Type of component
            version: Component version

        Returns:
            Manifest object or None if not found
        """
        manifest_path = self._get_manifest_path(component_type, version)

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)

            return Manifest.from_dict(data)

        except Exception as e:
            # Log error but don't fail
            print(f"Warning: Failed to load manifest {manifest_path}: {str(e)}")
            return None

    async def list_manifests(
        self,
        component_type: Optional[str] = None
    ) -> Dict[str, Manifest]:
        """List all manifests

        Args:
            component_type: Filter by component type (optional)

        Returns:
            Dict mapping version to manifest
        """
        manifests = {}

        if component_type:
            # List manifests for specific component
            component_dir = self.manifests_dir / component_type
            if component_dir.exists():
                for manifest_file in component_dir.glob("*.json"):
                    try:
                        with open(manifest_file, 'r') as f:
                            data = json.load(f)

                        manifest = Manifest.from_dict(data)
                        manifests[manifest.component_version] = manifest

                    except Exception:
                        # Skip invalid manifests
                        continue

        else:
            # List all manifests
            for component_dir in self.manifests_dir.iterdir():
                if component_dir.is_dir():
                    for manifest_file in component_dir.glob("*.json"):
                        try:
                            with open(manifest_file, 'r') as f:
                                data = json.load(f)

                            manifest = Manifest.from_dict(data)
                            key = f"{manifest.component_type}:{manifest.component_version}"
                            manifests[key] = manifest

                        except Exception:
                            # Skip invalid manifests
                            continue

        return manifests

    async def get_latest_version(
        self,
        component_type: str
    ) -> Optional[str]:
        """Get latest version for a component type

        Args:
            component_type: Type of component

        Returns:
            Latest version string or None
        """
        manifests = await self.list_manifests(component_type)

        if not manifests:
            return None

        # Simple string comparison for now
        # TODO: Use proper semantic versioning
        versions = list(manifests.keys())
        return sorted(versions)[-1]

    async def get_component_types(self) -> List[str]:
        """Get all component types with manifests

        Returns:
            List of component types
        """
        types = []

        if self.manifests_dir.exists():
            for component_dir in self.manifests_dir.iterdir():
                if component_dir.is_dir() and any(component_dir.glob("*.json")):
                    types.append(component_dir.name)

        return sorted(types)

    async def delete_manifest(
        self,
        component_type: str,
        version: str
    ) -> bool:
        """Delete a manifest file

        Args:
            component_type: Type of component
            version: Component version

        Returns:
            True if deleted, False if not found
        """
        manifest_path = self._get_manifest_path(component_type, version)

        if manifest_path.exists():
            manifest_path.unlink()

            # Remove empty component directory
            component_dir = manifest_path.parent
            if not any(component_dir.iterdir()):
                component_dir.rmdir()

            return True

        return False

    async def validate_manifest(self, manifest: Manifest) -> List[str]:
        """Validate a manifest

        Args:
            manifest: Manifest to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        if not manifest.component_type:
            errors.append("Component type is required")

        if not manifest.component_version:
            errors.append("Component version is required")

        if not manifest.package:
            errors.append("Package information is required")
        else:
            if not manifest.package.file:
                errors.append("Package file name is required")

            if manifest.package.size <= 0:
                errors.append("Package size must be positive")

            if not manifest.package.checksum:
                errors.append("Package checksum is required")

        # Check version format
        if manifest.version != MANIFEST_VERSION:
            errors.append(f"Unsupported manifest version: {manifest.version}")

        return errors

    async def search_manifests(
        self,
        query: str,
        component_type: Optional[str] = None
    ) -> List[Manifest]:
        """Search manifests by query

        Args:
            query: Search query (matches version or metadata)
            component_type: Filter by component type

        Returns:
            List of matching manifests
        """
        all_manifests = await self.list_manifests(component_type)
        matches = []

        query_lower = query.lower()

        for manifest in all_manifests.values():
            # Search in version
            if query_lower in manifest.component_version.lower():
                matches.append(manifest)
                continue

            # Search in metadata
            if manifest.metadata:
                metadata_str = json.dumps(manifest.metadata).lower()
                if query_lower in metadata_str:
                    matches.append(manifest)

        return matches

    async def get_manifest_stats(self) -> Dict[str, Any]:
        """Get statistics about manifests

        Returns:
            Statistics dictionary
        """
        stats = {
            "total_manifests": 0,
            "component_types": {},
            "total_size": 0,
            "latest_update": None
        }

        all_manifests = await self.list_manifests()

        for manifest in all_manifests.values():
            stats["total_manifests"] += 1

            # Count by component type
            if manifest.component_type not in stats["component_types"]:
                stats["component_types"][manifest.component_type] = {
                    "count": 0,
                    "total_size": 0,
                    "versions": []
                }

            type_stats = stats["component_types"][manifest.component_type]
            type_stats["count"] += 1
            type_stats["versions"].append(manifest.component_version)

            # Add package size
            if manifest.package:
                size = manifest.package.size
                type_stats["total_size"] += size
                stats["total_size"] += size

            # Track latest update
            if stats["latest_update"] is None or manifest.created_at > stats["latest_update"]:
                stats["latest_update"] = manifest.created_at

        return stats

    async def export_manifests(
        self,
        output_file: Path,
        component_type: Optional[str] = None
    ) -> int:
        """Export manifests to a single JSON file

        Args:
            output_file: Output file path
            component_type: Filter by component type

        Returns:
            Number of exported manifests
        """
        manifests = await self.list_manifests(component_type)

        export_data = {
            "version": MANIFEST_VERSION,
            "exported_at": datetime.utcnow().isoformat(),
            "manifests": []
        }

        for manifest in manifests.values():
            export_data["manifests"].append(manifest.to_dict())

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return len(export_data["manifests"])

    async def import_manifests(
        self,
        input_file: Path,
        overwrite: bool = False
    ) -> Dict[str, int]:
        """Import manifests from a JSON file

        Args:
            input_file: Input file path
            overwrite: Whether to overwrite existing manifests

        Returns:
            Dict with import statistics
        """
        with open(input_file, 'r') as f:
            data = json.load(f)

        stats = {
            "imported": 0,
            "skipped": 0,
            "errors": 0
        }

        for manifest_data in data.get("manifests", []):
            try:
                manifest = Manifest.from_dict(manifest_data)

                # Check if already exists
                existing = await self.load_manifest(
                    manifest.component_type,
                    manifest.component_version
                )

                if existing and not overwrite:
                    stats["skipped"] += 1
                    continue

                # Save manifest
                await self.save_manifest(manifest)
                stats["imported"] += 1

            except Exception:
                stats["errors"] += 1

        return stats