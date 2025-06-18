"""Component registry for managing component versions and dependencies"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from packaging.version import parse

from .manifest_engine import ManifestEngine
from .path_resolver import PathResolver
from ..models.component import Component


@dataclass
class ComponentInfo:
    """Component information"""
    type: str
    version: str
    created_at: str
    manifest_path: Path
    archive_path: Optional[Path] = None
    size: int = 0
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'type': self.type,
            'version': self.version,
            'created_at': self.created_at,
            'manifest_path': str(self.manifest_path),
            'archive_path': str(self.archive_path) if self.archive_path else None,
            'size': self.size,
            'checksum': self.checksum,
            'metadata': self.metadata
        }


@dataclass
class ComponentIndex:
    """Local component index"""
    version: str = "1.0"
    updated_at: str = ""
    components: Dict[str, List[ComponentInfo]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'updated_at': self.updated_at,
            'components': {
                comp_type: [info.to_dict() for info in infos]
                for comp_type, infos in self.components.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ComponentIndex':
        """Create from dictionary"""
        index = cls(
            version=data.get('version', '1.0'),
            updated_at=data.get('updated_at', '')
        )

        for comp_type, infos in data.get('components', {}).items():
            index.components[comp_type] = [
                ComponentInfo(
                    type=info['type'],
                    version=info['version'],
                    created_at=info['created_at'],
                    manifest_path=Path(info['manifest_path']),
                    archive_path=Path(info['archive_path']) if info.get('archive_path') else None,
                    size=info.get('size', 0),
                    checksum=info.get('checksum'),
                    metadata=info.get('metadata', {})
                )
                for info in infos
            ]

        return index


class ComponentRegistry:
    """Manage component versions and dependencies"""

    def __init__(self,
                 path_resolver: Optional[PathResolver] = None,
                 manifest_engine: Optional[ManifestEngine] = None):
        self.path_resolver = path_resolver or PathResolver()
        self.manifest_engine = manifest_engine or ManifestEngine(self.path_resolver)
        self._index: Optional[ComponentIndex] = None
        self._index_path = self.path_resolver.get_cache_dir() / "component_index.json"

    @property
    def index(self) -> ComponentIndex:
        """Get component index (lazy loading)"""
        if self._index is None:
            self._index = self._load_index()
        return self._index

    def _load_index(self) -> ComponentIndex:
        """Load component index from cache"""
        if self._index_path.exists():
            try:
                with open(self._index_path, 'r') as f:
                    data = json.load(f)
                return ComponentIndex.from_dict(data)
            except:
                # Corrupted index, rebuild
                pass

        # Build new index
        return self._rebuild_index()

    def _save_index(self) -> None:
        """Save component index to cache"""
        if self._index is None:
            return

        self._index.updated_at = datetime.now().isoformat()

        with open(self._index_path, 'w') as f:
            json.dump(self._index.to_dict(), f, indent=2)

    def _rebuild_index(self) -> ComponentIndex:
        """Rebuild component index from manifests"""
        index = ComponentIndex(updated_at=datetime.now().isoformat())

        # Scan manifests directory
        manifests_dir = self.path_resolver.get_manifests_dir()
        if not manifests_dir.exists():
            return index

        for manifest_path in manifests_dir.glob("*.manifest.json"):
            try:
                manifest = self.manifest_engine.load_manifest(manifest_path)

                comp_type = manifest.package['type']
                version = manifest.package['version']

                # Create component info
                info = ComponentInfo(
                    type=comp_type,
                    version=version,
                    created_at=manifest.package.get('created_at', ''),
                    manifest_path=manifest_path,
                    size=manifest.archive.get('size', 0),
                    checksum=manifest.archive.get('checksum', {}).get('sha256'),
                    metadata=manifest.metadata
                )

                # Check if archive exists
                archive_location = manifest.archive.get('location')
                if archive_location:
                    archive_path = self.path_resolver.resolve(archive_location)
                    if archive_path.exists():
                        info.archive_path = archive_path

                # Add to index
                if comp_type not in index.components:
                    index.components[comp_type] = []

                index.components[comp_type].append(info)

            except Exception:
                # Skip invalid manifests
                continue

        # Sort versions
        for comp_type in index.components:
            index.components[comp_type].sort(
                key=lambda x: parse(x.version),
                reverse=True
            )

        self._index = index
        self._save_index()

        return index

    def register_component(self, manifest_path: Path) -> None:
        """
        Register a new component

        Args:
            manifest_path: Path to component manifest
        """
        manifest = self.manifest_engine.load_manifest(manifest_path)

        comp_type = manifest.package['type']
        version = manifest.package['version']

        # Create component info
        info = ComponentInfo(
            type=comp_type,
            version=version,
            created_at=manifest.package.get('created_at', datetime.now().isoformat()),
            manifest_path=manifest_path,
            size=manifest.archive.get('size', 0),
            checksum=manifest.archive.get('checksum', {}).get('sha256'),
            metadata=manifest.metadata
        )

        # Check if archive exists
        archive_location = manifest.archive.get('location')
        if archive_location:
            archive_path = self.path_resolver.resolve(archive_location)
            if archive_path.exists():
                info.archive_path = archive_path

        # Add to index
        if comp_type not in self.index.components:
            self.index.components[comp_type] = []

        # Remove existing version if present
        self.index.components[comp_type] = [
            i for i in self.index.components[comp_type]
            if i.version != version
        ]

        # Add new version
        self.index.components[comp_type].append(info)

        # Sort by version
        self.index.components[comp_type].sort(
            key=lambda x: parse(x.version),
            reverse=True
        )

        # Save index
        self._save_index()

    def find_component(self, component_type: str, version: str) -> Optional[ComponentInfo]:
        """
        Find specific component

        Args:
            component_type: Component type
            version: Component version

        Returns:
            ComponentInfo if found, None otherwise
        """
        if component_type not in self.index.components:
            return None

        for info in self.index.components[component_type]:
            if info.version == version:
                return info

        return None

    def list_components(self, component_type: Optional[str] = None,
                        limit: Optional[int] = None) -> List[Component]:
        """
        List available components

        Args:
            component_type: Filter by type (optional)
            limit: Limit number of results

        Returns:
            List of Component objects
        """
        components = []

        if component_type:
            # Single type
            if component_type in self.index.components:
                for info in self.index.components[component_type][:limit]:
                    components.append(Component(
                        type=info.type,
                        version=info.version,
                        manifest_path=str(info.manifest_path)
                    ))
        else:
            # All types
            count = 0
            for comp_type, infos in sorted(self.index.components.items()):
                for info in infos:
                    components.append(Component(
                        type=info.type,
                        version=info.version,
                        manifest_path=str(info.manifest_path)
                    ))
                    count += 1
                    if limit and count >= limit:
                        break
                if limit and count >= limit:
                    break

        return components

    def list_versions(self, component_type: str) -> List[str]:
        """
        List all versions of a component type

        Args:
            component_type: Component type

        Returns:
            List of version strings (sorted, newest first)
        """
        if component_type not in self.index.components:
            return []

        return [info.version for info in self.index.components[component_type]]

    def get_latest_version(self, component_type: str) -> Optional[str]:
        """
        Get latest version of a component type

        Args:
            component_type: Component type

        Returns:
            Latest version string or None
        """
        versions = self.list_versions(component_type)
        return versions[0] if versions else None

    def get_component_types(self) -> List[str]:
        """
        Get all registered component types

        Returns:
            List of component types
        """
        return sorted(self.index.components.keys())

    def refresh_index(self) -> None:
        """Force refresh of component index"""
        self._index = self._rebuild_index()

    def search_components(self, pattern: str) -> List[Component]:
        """
        Search components by pattern

        Args:
            pattern: Search pattern (matches type or version)

        Returns:
            List of matching components
        """
        pattern_lower = pattern.lower()
        matches = []

        for comp_type, infos in self.index.components.items():
            # Check type match
            if pattern_lower in comp_type.lower():
                # Add all versions
                for info in infos:
                    matches.append(Component(
                        type=info.type,
                        version=info.version,
                        manifest_path=str(info.manifest_path)
                    ))
            else:
                # Check version match
                for info in infos:
                    if pattern_lower in info.version.lower():
                        matches.append(Component(
                            type=info.type,
                            version=info.version,
                            manifest_path=str(info.manifest_path)
                        ))

        return matches

    def get_component_stats(self) -> Dict[str, Any]:
        """Get component registry statistics"""
        total_components = 0
        total_size = 0

        for infos in self.index.components.values():
            total_components += len(infos)
            total_size += sum(info.size for info in infos)

        return {
            'total_types': len(self.index.components),
            'total_components': total_components,
            'total_size': total_size,
            'index_updated': self.index.updated_at,
            'types': {
                comp_type: {
                    'count': len(infos),
                    'latest': infos[0].version if infos else None,
                    'size': sum(info.size for info in infos)
                }
                for comp_type, infos in self.index.components.items()
            }
        }

    def validate_dependencies(self, components: List[Tuple[str, str]]) -> Tuple[bool, List[str]]:
        """
        Validate component dependencies

        Args:
            components: List of (type, version) tuples

        Returns:
            Tuple of (all_exist, missing_components)
        """
        missing = []

        for comp_type, version in components:
            if not self.find_component(comp_type, version):
                missing.append(f"{comp_type}:{version}")

        return len(missing) == 0, missing