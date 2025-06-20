"""Utility functions for deploy-tool"""

from .file_utils import (
    # Core file operations
    calculate_file_checksum,
    calculate_file_hash,
    get_file_size,
    ensure_directory,
    safe_remove,
    format_size,
    format_bytes,
    is_binary_file,
    count_files,
    scan_directory,
    copy_with_progress,
<<<<<<< Updated upstream
    safe_remove,
    ensure_parent_dir,
    get_relative_paths,
    create_archive,
    find_files_by_extension,
    get_mime_type,
    detect_file_types,
    atomic_write,
    read_file_lines,
    normalize_path,
    # File information
    get_file_info,
    get_file_metadata,  # Added this
    get_directory_size,
    format_timestamp,
    # Directory analysis
    calculate_directory_stats,
    list_directory_tree,
    compare_directories,
    find_duplicate_files,
=======
    create_archive,
    create_temp_directory,
    extract_archive,
    find_files,
    get_relative_paths,
    atomic_write,
    read_file_lines,
    get_directory_size,
>>>>>>> Stashed changes
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
    calculate_file_hash as calculate_file_hash_from_hash_utils,
    calculate_file_hash_async,
    calculate_content_hash,
    calculate_string_hash,
    calculate_directory_hash,
    verify_multiple_checksums,
    compare_files,
    generate_checksum_file,
    verify_checksum_file,
    stream_hash,
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
    from ..core import ComponentRegistry, ManifestEngine
    path_resolver = PathResolver()
    manifest_engine = ManifestEngine(path_resolver)
    registry = ComponentRegistry(path_resolver, manifest_engine)

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
    releases = query.releases(limit=limit)
    return [r['version'] for r in releases] if releases else []


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
        # Basic validation - check if archive exists
        archive_path = path_resolver.resolve(manifest.archive.get('location', ''))
        return archive_path.exists()
    except Exception:
        return False


__all__ = [
    # File utilities
    'calculate_file_checksum',
    'calculate_file_hash',
    'get_file_size',
    'format_size',
    'format_bytes',
    'is_binary_file',
    'count_files',
    'scan_directory',
    'copy_with_progress',
    'safe_remove',
    'ensure_parent_dir',
    'get_relative_paths',
    'create_archive',
    'find_files_by_extension',
    'get_mime_type',
    'detect_file_types',
    'atomic_write',
    'read_file_lines',
    'normalize_path',
    'get_file_info',
    'get_file_metadata',  # Added this
    'get_directory_size',
    'format_timestamp',
    'calculate_directory_stats',
    'list_directory_tree',
    'compare_directories',
    'find_duplicate_files',

    # Git utilities
    'is_git_repository',
    'get_current_branch',
    'get_git_status',
    'is_file_tracked',
    'get_remote_url',
    'check_git_status',
    'get_uncommitted_files',
    'suggest_git_commands',
    'get_last_commit_date',
    'get_file_history',
    'is_dirty',
    'get_ahead_behind',
    'add_files',
    'init_git_repo',

    # Template utilities
    'render_template',
    'load_template',
    'get_template_path',
    'substitute_variables',

    # Version utilities
    'parse_version',
    'suggest_version',
    'increment_version',
    'compare_versions',
    'is_valid_version',

    # Hash utilities
    'calculate_sha256',
    'calculate_md5',
    'verify_checksum',
    'generate_file_fingerprint',
    'calculate_file_hash_from_hash_utils',
    'calculate_file_hash_async',
    'calculate_content_hash',
    'calculate_string_hash',
    'calculate_directory_hash',
    'verify_multiple_checksums',
    'compare_files',
    'generate_checksum_file',
    'verify_checksum_file',
    'stream_hash',

    # Async utilities
    'run_async',
    'gather_with_progress',
    'timeout_async',

    # Convenience functions
    'find_manifest',
    'list_components',
    'list_releases',
    'verify_component',
]