# deploy_tool/utils/file_utils.py
"""File operation utilities"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Callable, Union


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
        text_characters = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        non_text = len([b for b in sample if b not in text_characters])

        # If more than 30% non-text, consider binary
        return non_text / len(sample) > 0.3 if sample else False

    except Exception:
        return False


def count_files(directory: Path,
                pattern: str = '*',
                recursive: bool = True) -> int:
    """
    Count files in directory

    Args:
        directory: Directory path
        pattern: File pattern
        recursive: Include subdirectories

    Returns:
        Number of files
    """
    if recursive:
        return sum(1 for _ in directory.rglob(pattern) if _.is_file())
    else:
        return sum(1 for _ in directory.glob(pattern) if _.is_file())


def scan_directory(directory: Path,
                   exclude_patterns: Optional[List[str]] = None,
                   include_hidden: bool = False) -> List[Path]:
    """
    Scan directory for files

    Args:
        directory: Directory to scan
        exclude_patterns: Patterns to exclude
        include_hidden: Include hidden files

    Returns:
        List of file paths
    """
    import fnmatch

    exclude_patterns = exclude_patterns or []
    files = []

    for path in directory.rglob('*'):
        if path.is_file():
            # Skip hidden files if requested
            if not include_hidden and any(part.startswith('.') for part in path.parts):
                continue

            # Check exclude patterns
            relative_path = path.relative_to(directory)
            if any(fnmatch.fnmatch(str(relative_path), pattern) for pattern in exclude_patterns):
                continue

            files.append(path)

    return sorted(files)


def copy_with_progress(src: Path,
                       dst: Path,
                       callback: Optional[Callable[[int, int], None]] = None,
                       chunk_size: int = 1024 * 1024) -> None:
    """
    Copy file with progress callback

    Args:
        src: Source file
        dst: Destination file
        callback: Progress callback(bytes_copied, total_bytes)
        chunk_size: Copy chunk size
    """
    total_size = src.stat().st_size
    bytes_copied = 0

    # Ensure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)

    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            while chunk := fsrc.read(chunk_size):
                fdst.write(chunk)
                bytes_copied += len(chunk)

                if callback:
                    callback(bytes_copied, total_size)

    # Copy file permissions
    shutil.copystat(src, dst)


def safe_remove(path: Path) -> bool:
    """
    Safely remove file or directory

    Args:
        path: Path to remove

    Returns:
        True if successful
    """
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        return True
    except Exception:
        return False


def ensure_parent_dir(file_path: Path) -> Path:
    """
    Ensure parent directory exists

    Args:
        file_path: File path

    Returns:
        Parent directory path
    """
    parent = file_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    return parent


def get_relative_paths(directory: Path,
                       files: List[Path]) -> List[str]:
    """
    Get relative paths for files

    Args:
        directory: Base directory
        files: List of file paths

    Returns:
        List of relative path strings
    """
    relative_paths = []

    for file_path in files:
        try:
            rel_path = file_path.relative_to(directory)
            # Always use forward slashes
            relative_paths.append(str(rel_path).replace(os.sep, '/'))
        except ValueError:
            # File is outside directory
            relative_paths.append(str(file_path))

    return relative_paths


def create_archive(source_dir: Path,
                   output_file: Path,
                   format: str = 'gztar',
                   base_dir: Optional[str] = None) -> Path:
    """
    Create archive from directory

    Args:
        source_dir: Source directory
        output_file: Output archive path
        format: Archive format (gztar, bztar, xztar, tar, zip)
        base_dir: Base directory name in archive

    Returns:
        Path to created archive
    """

    # Remove extension from output_file as shutil.make_archive adds it
    base_name = str(output_file.with_suffix(''))

    # Create archive
    archive_path = shutil.make_archive(
        base_name=base_name,
        format=format,
        root_dir=source_dir,
        base_dir=base_dir
    )

    return Path(archive_path)


def extract_archive(archive_path: Path,
                    extract_to: Path,
                    format: Optional[str] = None) -> Path:
    """
    Extract archive

    Args:
        archive_path: Archive file path
        extract_to: Extraction directory
        format: Archive format (auto-detect if None)

    Returns:
        Path to extracted content
    """
    extract_to.mkdir(parents=True, exist_ok=True)

    shutil.unpack_archive(
        filename=str(archive_path),
        extract_dir=str(extract_to),
        format=format
    )

    return extract_to


def calculate_directory_size(directory: Path) -> int:
    """
    Calculate total size of directory

    Args:
        directory: Directory path

    Returns:
        Total size in bytes
    """
    total_size = 0

    for path in directory.rglob('*'):
        if path.is_file():
            total_size += path.stat().st_size

    return total_size


def find_files_by_extension(directory: Path,
                            extensions: List[str],
                            recursive: bool = True) -> List[Path]:
    """
    Find files by extension

    Args:
        directory: Search directory
        extensions: List of extensions (with or without dot)
        recursive: Search recursively

    Returns:
        List of matching files
    """
    # Normalize extensions
    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]

    files = []
    glob_func = directory.rglob if recursive else directory.glob

    for path in glob_func('*'):
        if path.is_file() and path.suffix.lower() in extensions:
            files.append(path)

    return sorted(files)


def get_mime_type(file_path: Path) -> str:
    """
    Get MIME type of file

    Args:
        file_path: File path

    Returns:
        MIME type string
    """
    import mimetypes

    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or 'application/octet-stream'


def detect_file_types(directory: Path) -> Dict[str, List[Path]]:
    """
    Detect and categorize file types in directory

    Args:
        directory: Directory to analyze

    Returns:
        Dictionary mapping file types to file lists
    """
    file_types = {
        'code': [],
        'config': [],
        'data': [],
        'model': [],
        'document': [],
        'image': [],
        'archive': [],
        'other': []
    }

    # Define extensions for each category
    extensions_map = {
        'code': ['.py', '.js', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.ts', '.jsx', '.tsx'],
        'config': ['.yaml', '.yml', '.json', '.xml', '.ini', '.conf', '.cfg', '.toml'],
        'data': ['.csv', '.tsv', '.parquet', '.feather', '.h5', '.hdf5', '.npz', '.npy'],
        'model': ['.pth', '.pt', '.pkl', '.joblib', '.onnx', '.pb', '.h5', '.keras', '.safetensors'],
        'document': ['.md', '.txt', '.rst', '.doc', '.docx', '.pdf', '.tex'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
        'archive': ['.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar']
    }

    # Reverse mapping for efficient lookup
    ext_to_type = {}
    for file_type, extensions in extensions_map.items():
        for ext in extensions:
            ext_to_type[ext.lower()] = file_type

    # Scan and categorize files
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            file_type = ext_to_type.get(suffix, 'other')
            file_types[file_type].append(file_path)

    return file_types


def atomic_write(file_path: Path,
                 content: Union[str, bytes],
                 mode: str = 'w') -> None:
    """
    Write file atomically

    Args:
        file_path: Target file path
        content: Content to write
        mode: Write mode
    """
    import tempfile

    # Write to temporary file first
    temp_fd, temp_path = tempfile.mkstemp(dir=file_path.parent)

    try:
        with os.fdopen(temp_fd, mode) as f:
            f.write(content)

        # Atomic rename
        os.replace(temp_path, file_path)

    except Exception:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise