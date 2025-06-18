"""Query API for querying deployment information"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from ..core import (
    PathResolver,
    ComponentRegistry,
    StorageManager,
)
from ..models import Component


class QueryInterface:
    """Query interface for deployment information"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize query interface

        Args:
            config: Configuration
        """
        self.config = config or {}
        self.path_resolver = PathResolver()
        self.component_registry = ComponentRegistry(self.path_resolver)

        # Initialize storage if configured
        storage_config = self.config.get('storage', {})
        if storage_config:
            storage_type = storage_config.get('type', 'filesystem')
            self.storage_manager = StorageManager(
                storage_type=storage_type,
                config=storage_config,
                path_resolver=self.path_resolver
            )
        else:
            self.storage_manager = None

    def components(self,
                   type: Optional[str] = None,
                   version_pattern: Optional[str] = None,
                   sort_by: str = "version",
                   limit: Optional[int] = None) -> List[Component]:
        """
        Query components

        Args:
            type: Filter by component type
            version_pattern: Version pattern (supports wildcards)
            sort_by: Sort field (version|date)
            limit: Result limit

        Returns:
            List of components
        """
        # Get components from registry
        components = self.component_registry.list_components(
            component_type=type,
            limit=limit
        )

        # Filter by version pattern if specified
        if version_pattern:
            import fnmatch
            filtered = []
            for comp in components:
                if fnmatch.fnmatch(comp.version, version_pattern):
                    filtered.append(comp)
            components = filtered

        # Sort
        if sort_by == "version":
            from packaging.version import parse
            components.sort(key=lambda c: parse(c.version), reverse=True)
        elif sort_by == "date":
            # Would need to load manifests to get creation date
            # For now, just return as-is
            pass

        return components[:limit] if limit else components

    def releases(self,
                 from_date: Optional[str] = None,
                 to_date: Optional[str] = None,
                 contains_component: Optional[str] = None,
                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query releases

        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            contains_component: Filter by component (type:version)
            limit: Result limit

        Returns:
            List of release information
        """
        releases = []
        releases_dir = self.path_resolver.get_releases_dir()

        if not releases_dir.exists():
            return releases

        # Parse date filters
        from_dt = datetime.fromisoformat(from_date) if from_date else None
        to_dt = datetime.fromisoformat(to_date) if to_date else None

        # Parse component filter
        filter_type = None
        filter_version = None
        if contains_component and ':' in contains_component:
            filter_type, filter_version = contains_component.split(':', 1)

        # Scan release files
        for release_file in releases_dir.glob("*.release.json"):
            try:
                import json
                with open(release_file, 'r') as f:
                    release_data = json.load(f)

                # Check date filter
                created_at = release_data['release'].get('created_at')
                if created_at:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                    if from_dt and created_dt < from_dt:
                        continue
                    if to_dt and created_dt > to_dt:
                        continue

                # Check component filter
                if filter_type:
                    contains = False
                    for comp in release_data.get('components', []):
                        if comp['type'] == filter_type:
                            if not filter_version or comp['version'] == filter_version:
                                contains = True
                                break

                    if not contains:
                        continue

                # Add to results
                releases.append({
                    'version': release_data['release']['version'],
                    'created_at': created_at,
                    'name': release_data['release'].get('name'),
                    'components': [
                        f"{c['type']}:{c['version']}"
                        for c in release_data.get('components', [])
                    ],
                    'file': str(release_file)
                })

            except Exception:
                # Skip invalid release files
                continue

        # Sort by date (newest first)
        releases.sort(
            key=lambda r: r.get('created_at', ''),
            reverse=True
        )

        return releases[:limit] if limit else releases

    def deployment_status(self, target: str = "default") -> Dict[str, Any]:
        """
        Query deployment status

        Args:
            target: Deployment target

        Returns:
            Deployment status information
        """
        # This would need to connect to actual deployment targets
        # For now, return basic info
        status = {
            'target': target,
            'status': 'unknown',
            'components': [],
            'last_updated': None
        }

        # Check if we have storage manager to query remote status
        if self.storage_manager:
            # Could query remote deployment status
            pass

        return status

    def search(self, query: str, limit: int = 20) -> Dict[str, List[Any]]:
        """
        Search across all resources

        Args:
            query: Search query
            limit: Result limit

        Returns:
            Search results grouped by type
        """
        results = {
            'components': [],
            'releases': [],
        }

        # Search components
        components = self.component_registry.search_components(query)
        results['components'] = components[:limit]

        # Search releases
        releases = self.releases()
        for release in releases:
            if (query.lower() in release['version'].lower() or
                (release.get('name') and query.lower() in release['name'].lower())):
                results['releases'].append(release)
                if len(results['releases']) >= limit:
                    break

        return results

    def statistics(self) -> Dict[str, Any]:
        """
        Get deployment statistics

        Returns:
            Statistics dictionary
        """
        stats = self.component_registry.get_component_stats()

        # Add release stats
        releases = self.releases()
        stats['releases'] = {
            'total': len(releases),
            'latest': releases[0] if releases else None
        }

        # Add storage info if available
        if self.storage_manager:
            stats['storage'] = self.storage_manager.get_storage_info()

        return stats


# Global query instance
_query_instance = None


def query() -> QueryInterface:
    """
    Get query interface (singleton)

    Returns:
        QueryInterface instance
    """
    global _query_instance
    if _query_instance is None:
        _query_instance = QueryInterface()
    return _query_instance