# deploy_tool/utils/__init__.py
"""Utility functions for deploy-tool"""

from .file_utils import (
    calculate_file_checksum,
    get_file_size,
    format_size,
    is_binary_file,
    count_files,
    scan_directory,
    copy_with_progress,
)

from .git_utils import (
    is_git_repository,
    get_current_branch,
    get_git_status,
    is_file_tracked,
    get_remote_url,
    check_git_status,
    get_uncommitted_files,
    suggest_git_commands,
    get_last_commit_date,
    get_file_history,
    is_dirty,
    get_ahead_behind,
    add_files,
    init_git_repo,
)

from .template_utils import (
    render_template,
    load_template,
    get_template_path,
    substitute_variables,
)

from .version_utils import (
    parse_version,
    suggest_version,
    increment_version,
    compare_versions,
    is_valid_version,
)

from .hash_utils import (
    calculate_sha256,
    calculate_md5,
    verify_checksum,
    generate_file_fingerprint,
)

from .async_utils import (
    run_async,
    gather_with_progress,
    timeout_async,
)

from typing import List

# Convenience functions exported at package level
from ..core import PathResolver
from ..models import Component


def find_manifest(component_type: str, version: str) -> str:
    """
    Find manifest file for a component

    Args:
        component_type: Component type
        version: Component version

    Returns:
        Path to manifest file or None
    """
    from ..core import ManifestEngine
    path_resolver = PathResolver()
    manifest_engine = ManifestEngine(path_resolver)

    manifest_path = manifest_engine.find_manifest(component_type, version)
    return str(manifest_path) if manifest_path else None


def list_components(component_type: str = None) -> List[Component]:
    """
    List available components

    Args:
        component_type: Filter by type (optional)

    Returns:
        List of components
    """
    from ..core import ComponentRegistry
    path_resolver = PathResolver()
    registry = ComponentRegistry(path_resolver)

    return registry.list_components(component_type)


def list_releases(limit: int = None) -> List[str]:
    """
    List available releases

    Args:
        limit: Limit number of results

    Returns:
        List of release versions
    """
    from ..api.query import query
    q = query()
    releases = q.releases(limit=limit)
    return [r['version'] for r in releases]


def verify_component(component_type: str, version: str) -> bool:
    """
    Verify component integrity

    Args:
        component_type: Component type
        version: Component version

    Returns:
        True if component is valid
    """
    from ..core import ManifestEngine, ValidationEngine
    path_resolver = PathResolver()
    manifest_engine = ManifestEngine(path_resolver)
    validation_engine = ValidationEngine()

    # Find manifest
    manifest_path = manifest_engine.find_manifest(component_type, version)
    if not manifest_path:
        return False

    # Load manifest
    try:
        manifest = manifest_engine.load_manifest(manifest_path)
    except:
        return False

    # Validate
    is_valid, _ = manifest_engine.validate_manifest(manifest)
    return is_valid


__all__ = [
    # File utilities
    "calculate_file_checksum",
    "get_file_size",
    "format_size",
    "is_binary_file",
    "count_files",
    "scan_directory",
    "copy_with_progress",

    # Git utilities
    "is_git_repository",
    "get_current_branch",
    "get_git_status",
    "is_file_tracked",
    "get_remote_url",
    "check_git_status",
    "get_uncommitted_files",
    "suggest_git_commands",
    "get_last_commit_date",
    "get_file_history",
    "is_dirty",
    "get_ahead_behind",
    "add_files",
    "init_git_repo",

    # Template utilities
    "render_template",
    "load_template",
    "get_template_path",
    "substitute_variables",

    # Version utilities
    "parse_version",
    "suggest_version",
    "increment_version",
    "compare_versions",
    "is_valid_version",

    # Hash utilities
    "calculate_sha256",
    "calculate_md5",
    "verify_checksum",
    "generate_file_fingerprint",

    # Async utilities
    "run_async",
    "gather_with_progress",
    "timeout_async",

    # High-level utilities
    "find_manifest",
    "list_components",
    "list_releases",
    "verify_component",
]

# Import List type at module level
from typing import List