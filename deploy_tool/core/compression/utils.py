"""Compression utility functions"""

from pathlib import Path

from .tar_processor import CompressionType


def detect_compression_type(file_path: Path) -> CompressionType:
    """
    Detect compression type from file

    Args:
        file_path: Path to file

    Returns:
        Detected compression type
    """
    name_lower = file_path.name.lower()

    # Check by extension
    if name_lower.endswith('.tar.gz') or name_lower.endswith('.tgz'):
        return CompressionType.GZIP
    elif name_lower.endswith('.tar.bz2') or name_lower.endswith('.tbz') or name_lower.endswith('.tbz2'):
        return CompressionType.BZIP2
    elif name_lower.endswith('.tar.xz') or name_lower.endswith('.txz'):
        return CompressionType.XZ
    elif name_lower.endswith('.tar.lz4') or name_lower.endswith('.tlz4'):
        return CompressionType.LZ4
    elif name_lower.endswith('.tar'):
        return CompressionType.NONE

    # Try to detect from content
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        # Check magic numbers
        if header.startswith(b'\x1f\x8b'):  # gzip
            return CompressionType.GZIP
        elif header.startswith(b'BZh'):  # bzip2
            return CompressionType.BZIP2
        elif header.startswith(b'\xfd7zXZ\x00'):  # xz
            return CompressionType.XZ
        elif header.startswith(b'\x04"M\x18'):  # lz4
            return CompressionType.LZ4
    except:
        pass

    # Default to no compression
    return CompressionType.NONE


def format_size(size: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Calculate compression ratio

    Args:
        original_size: Original size in bytes
        compressed_size: Compressed size in bytes

    Returns:
        Compression ratio (0-100)
    """
    if original_size == 0:
        return 0.0

    return (1 - compressed_size / original_size) * 100


def estimate_compression_time(size: int, compression_type: CompressionType) -> float:
    """
    Estimate compression time (very rough estimate)

    Args:
        size: Size in bytes
        compression_type: Compression type

    Returns:
        Estimated time in seconds
    """
    # Very rough estimates (MB/s)
    speeds = {
        CompressionType.NONE: 500,  # No compression
        CompressionType.LZ4: 300,  # Very fast
        CompressionType.GZIP: 50,  # Moderate
        CompressionType.BZIP2: 10,  # Slow
        CompressionType.XZ: 5,  # Very slow
    }

    speed_mbps = speeds.get(compression_type, 50)
    size_mb = size / (1024 * 1024)

    return max(0.1, size_mb / speed_mbps)


def get_archive_extension(compression_type: CompressionType) -> str:
    """
    Get complete archive extension

    Args:
        compression_type: Compression type

    Returns:
        Complete extension (e.g., '.tar.gz')
    """
    base = '.tar'

    compression_ext = {
        CompressionType.GZIP: '.gz',
        CompressionType.BZIP2: '.bz2',
        CompressionType.XZ: '.xz',
        CompressionType.LZ4: '.lz4',
        CompressionType.NONE: '',
    }

    return base + compression_ext.get(compression_type, '')


def parse_archive_name(filename: str) -> tuple[str, CompressionType]:
    """
    Parse archive filename to extract base name and compression type

    Args:
        filename: Archive filename

    Returns:
        Tuple of (base_name, compression_type)
    """
    name_lower = filename.lower()

    # Check compression extensions
    if name_lower.endswith('.tar.gz') or name_lower.endswith('.tgz'):
        base = filename[:-7] if name_lower.endswith('.tar.gz') else filename[:-4]
        return base, CompressionType.GZIP
    elif name_lower.endswith('.tar.bz2'):
        return filename[:-8], CompressionType.BZIP2
    elif name_lower.endswith('.tar.xz'):
        return filename[:-7], CompressionType.XZ
    elif name_lower.endswith('.tar.lz4'):
        return filename[:-8], CompressionType.LZ4
    elif name_lower.endswith('.tar'):
        return filename[:-4], CompressionType.NONE

    # No recognized extension
    return filename, CompressionType.NONE