"""Formatting utilities for display"""

from typing import Union


def format_size(size_bytes: Union[int, float]) -> str:
    """Format byte size to human readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Human readable size string

    Examples:
        >>> format_size(1024)
        '1.0 KB'
        >>> format_size(1048576)
        '1.0 MB'
    """
    if size_bytes < 0:
        return "Invalid size"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        # Bytes - show as integer
        return f"{int(size)} {units[unit_index]}"
    else:
        # KB and above - show with one decimal
        return f"{size:.1f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Human readable duration string

    Examples:
        >>> format_duration(1.5)
        '1.5s'
        >>> format_duration(65)
        '1m 5s'
    """
    if seconds < 0:
        return "Invalid duration"

    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_percentage(value: float, total: float) -> str:
    """Format percentage value

    Args:
        value: Current value
        total: Total value

    Returns:
        Formatted percentage string
    """
    if total == 0:
        return "0%"

    percentage = (value / total) * 100
    return f"{percentage:.1f}%"


def format_path(path: str, max_length: int = 50) -> str:
    """Format path for display, truncating if needed

    Args:
        path: Path to format
        max_length: Maximum length

    Returns:
        Formatted path string
    """
    if len(path) <= max_length:
        return path

    # Keep beginning and end
    keep_start = max_length // 2 - 2
    keep_end = max_length - keep_start - 3

    return f"{path[:keep_start]}...{path[-keep_end:]}"


def pluralize(count: int, singular: str, plural: str = None) -> str:
    """Pluralize a word based on count

    Args:
        count: Number of items
        singular: Singular form
        plural: Plural form (optional, will add 's' if not provided)

    Returns:
        Pluralized string with count
    """
    if plural is None:
        plural = singular + 's'

    word = singular if count == 1 else plural
    return f"{count} {word}"