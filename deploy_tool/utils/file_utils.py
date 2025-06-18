"""File operation utilities"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Callable, Tuple, Any, Union


def calculate_file_checksum(file_path: Path,
                            algorithm: str = "sha256",
                            chunk_size: int = 8192) -> str:
    """
    Calculate file checksum

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, sha1)
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes

    Args:
        file_path: Path to file

    Returns:
        Size in bytes
    """
    return file_path.stat().st_size


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


def is_binary_file(file_path: Path, sample_size: int = 512) -> bool:
    """
    Check if file is binary

    Args:
        file_path: Path to file
        sample_size: Bytes to sample

    Returns:
        True if file appears to be binary
    """
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)

        # Check for null bytes
        if b'\0' in sample:
            return True

        # Check if mostly printable
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        non_text = sample.translate(None, text_chars)

        # If more than 30% non-text, consider binary
        return len(non_text) / len(sample) > 0.3

    except Exception:
        return True


def count_files(directory: Path,
                pattern: str = "*",
                recursive: bool = True) -> int:
    """
    Count files in directory

    Args:
        directory: Directory path
        pattern: File pattern
        recursive: Whether to count recursively

    Returns:
        Number of files
    """
    if recursive:
        return sum(1 for _ in directory.rglob(pattern) if _.is_file())
    else:
        return sum(1 for _ in directory.glob(pattern) if _.is_file())


def scan_directory(directory: Path,
                   excludes: Optional[List[str]] = None,
                   includes: Optional[List[str]] = None) -> List[Tuple[Path, Dict[str, Any]]]:
    """
    Scan directory and return file information

    Args:
        directory: Directory to scan
        excludes: Patterns to exclude
        includes: Patterns to include (if specified, only these are included)

    Returns:
        List of (path, info) tuples
    """
    import fnmatch

    excludes = excludes or []
    includes = includes or ['*']

    results = []

    for file_path in directory.rglob('*'):
        if not file_path.is_file():
            continue

        # Get relative path
        rel_path = file_path.relative_to(directory)
        rel_str = str(rel_path)

        # Check excludes
        excluded = False
        for pattern in excludes:
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                excluded = True
                break

        if excluded:
            continue

        # Check includes
        included = False
        for pattern in includes:
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                included = True
                break

        if not included and includes != ['*']:
            continue

        # Get file info
        stat = file_path.stat()
        info = {
            'size': stat.st_size,
            'mtime': stat.st_mtime,
            'is_binary': is_binary_file(file_path),
            'extension': file_path.suffix.lower(),
        }

        results.append((file_path, info))

    return results


def copy_with_progress(src: Path,
                       dst: Path,
                       callback: Optional[Callable[[int, int], None]] = None,
                       chunk_size: int = 1024 * 1024) -> None:
    """
    Copy file with progress callback

    Args:
        src: Source file
        dst: Destination file
        callback: Progress callback(copied_bytes, total_bytes)
        chunk_size: Copy chunk size
    """
    # Ensure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)

    total_size = src.stat().st_size
    copied = 0

    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            while chunk := fsrc.read(chunk_size):
                fdst.write(chunk)
                copied += len(chunk)

                if callback:
                    callback(copied, total_size)

    # Copy file permissions
    shutil.copystat(src, dst)


def safe_remove(path: Path) -> bool:
    """
    Safely remove file or directory

    Args:
        path: Path to remove

    Returns:
        True if removed successfully
    """
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        return True
    except Exception:
        return False


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists

    Args:
        path: Directory path

    Returns:
        The path
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_directory_size(directory: Path) -> int:
    """
    Get total size of directory

    Args:
        directory: Directory path

    Returns:
        Total size in bytes
    """
    total = 0
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            total += file_path.stat().st_size
    return total


def find_files(directory: Path,
               pattern: str,
               recursive: bool = True) -> List[Path]:
    """
    Find files matching pattern

    Args:
        directory: Directory to search
        pattern: File pattern (supports wildcards)
        recursive: Whether to search recursively

    Returns:
        List of matching file paths
    """
    if recursive:
        return [p for p in directory.rglob(pattern) if p.is_file()]
    else:
        return [p for p in directory.glob(pattern) if p.is_file()]


def atomic_write(file_path: Path,
                 content: Union[str, bytes],
                 mode: str = 'w') -> None:
    """
    Write file atomically (write to temp, then rename)

    Args:
        file_path: Target file path
        content: Content to write
        mode: Write mode
    """
    import tempfile

    # Write to temporary file in same directory
    temp_fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=f".{file_path.name}.",
        suffix='.tmp'
    )

    try:
        with os.fdopen(temp_fd, mode) as f:
            f.write(content)

        # Atomic rename
        Path(temp_path).replace(file_path)

    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise


from typing import Union