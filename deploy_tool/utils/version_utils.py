"""Version management utilities"""

import re
from typing import Optional, Tuple, List

from packaging.version import parse, Version, InvalidVersion

from ..constants import VERSION_PATTERN


def parse_version(version_str: str) -> Optional[Version]:
    """
    Parse version string

    Args:
        version_str: Version string

    Returns:
        Version object or None if invalid
    """
    try:
        return parse(version_str)
    except InvalidVersion:
        return None


def suggest_version(current_version: str = None,
                    bump_type: str = "patch") -> str:
    """
    Suggest next version

    Args:
        current_version: Current version (optional)
        bump_type: Type of bump (major, minor, patch)

    Returns:
        Suggested version string
    """
    if not current_version:
        return "0.1.0"

    # Parse current version
    match = VERSION_PATTERN.match(current_version)
    if not match:
        # If not valid semver, just increment
        try:
            parts = current_version.split('.')
            if len(parts) >= 3:
                parts[-1] = str(int(parts[-1]) + 1)
                return '.'.join(parts)
        except:
            pass
        return "0.1.0"

    major = int(match.group('major'))
    minor = int(match.group('minor'))
    patch = int(match.group('patch'))

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def increment_version(version: str,
                      component: str = "patch") -> str:
    """
    Increment version component

    Args:
        version: Version string
        component: Component to increment (major, minor, patch)

    Returns:
        New version string
    """
    return suggest_version(version, component)


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two versions

    Args:
        version1: First version
        version2: Second version

    Returns:
        -1 if version1 < version2
        0 if version1 == version2
        1 if version1 > version2
    """
    try:
        v1 = parse(version1)
        v2 = parse(version2)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    except InvalidVersion:
        # Fallback to string comparison
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0


def is_valid_version(version: str) -> bool:
    """
    Check if version string is valid

    Args:
        version: Version string

    Returns:
        True if valid
    """
    return VERSION_PATTERN.match(version) is not None


def extract_version_parts(version: str) -> Tuple[int, int, int, str, str]:
    """
    Extract version parts

    Args:
        version: Version string

    Returns:
        Tuple of (major, minor, patch, prerelease, build)
    """
    match = VERSION_PATTERN.match(version)
    if not match:
        raise ValueError(f"Invalid version: {version}")

    major = int(match.group('major'))
    minor = int(match.group('minor'))
    patch = int(match.group('patch'))
    prerelease = match.group('prerelease') or ""
    build = match.group('build') or ""

    return major, minor, patch, prerelease, build


def sort_versions(versions: List[str], reverse: bool = True) -> List[str]:
    """
    Sort version strings

    Args:
        versions: List of version strings
        reverse: Sort in descending order

    Returns:
        Sorted list
    """

    def version_key(v: str):
        try:
            return parse(v)
        except InvalidVersion:
            # Put invalid versions at the end
            return parse("0.0.0")

    return sorted(versions, key=version_key, reverse=reverse)


def get_latest_version(versions: List[str]) -> Optional[str]:
    """
    Get latest version from list

    Args:
        versions: List of version strings

    Returns:
        Latest version or None
    """
    if not versions:
        return None

    sorted_versions = sort_versions(versions, reverse=True)
    return sorted_versions[0] if sorted_versions else None


def version_in_range(version: str,
                     min_version: Optional[str] = None,
                     max_version: Optional[str] = None) -> bool:
    """
    Check if version is in range

    Args:
        version: Version to check
        min_version: Minimum version (inclusive)
        max_version: Maximum version (inclusive)

    Returns:
        True if in range
    """
    try:
        v = parse(version)

        if min_version:
            if v < parse(min_version):
                return False

        if max_version:
            if v > parse(max_version):
                return False

        return True

    except InvalidVersion:
        return False


def normalize_version(version: str) -> str:
    """
    Normalize version string

    Args:
        version: Version string

    Returns:
        Normalized version
    """
    # Remove common prefixes
    version = version.lstrip('v')
    version = version.lstrip('V')

    # Ensure it's valid semver
    if not is_valid_version(version):
        # Try to make it valid
        parts = version.split('.')

        # Pad with zeros if needed
        while len(parts) < 3:
            parts.append('0')

        # Take only first 3 parts for base version
        version = '.'.join(parts[:3])

        # Add back any suffix
        if len(parts) > 3:
            version += '-' + '.'.join(parts[3:])

    return version


def generate_version_tag(version: str, prefix: str = "v") -> str:
    """
    Generate version tag for git

    Args:
        version: Version string
        prefix: Tag prefix

    Returns:
        Version tag
    """
    normalized = normalize_version(version)
    return f"{prefix}{normalized}"