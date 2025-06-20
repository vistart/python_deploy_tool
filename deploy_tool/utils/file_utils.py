"""File utility functions"""

<<<<<<< Updated upstream
import fnmatch
import hashlib
=======
>>>>>>> Stashed changes
import os
import hashlib
import shutil
<<<<<<< Updated upstream
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union, Dict, Callable, Any

from ..constants import DEFAULT_EXCLUDE_PATTERNS
=======
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, List, Callable, Union
import fnmatch

from ..constants import DEFAULT_CHUNK_SIZE
>>>>>>> Stashed changes


def calculate_file_checksum(
    file_path: Union[str, Path],
    algorithm: str = "sha256",
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> str:
    """Calculate checksum of a file

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, sha1, md5)
        chunk_size: Size of chunks to read

    Returns:
        Hexadecimal checksum string
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get hash function
    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    # Calculate hash
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)

    return hasher.hexdigest()


<<<<<<< Updated upstream
def calculate_file_hash(file_path: Path,
                        algorithm: str = "sha256",
                        chunk_size: int = 8192) -> str:
    """
    Calculate file hash (alias for calculate_file_checksum)

    This function is provided for backward compatibility.
    It delegates to calculate_file_checksum or imports from hash_utils.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    # Import the more comprehensive implementation from hash_utils
    from ..hash_utils import calculate_file_hash as _calculate_hash
    return _calculate_hash(file_path, algorithm, chunk_size)


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes
=======
def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes
>>>>>>> Stashed changes

    Args:
        file_path: Path to file

    Returns:
        File size in bytes
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path.stat().st_size


def ensure_directory(dir_path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if necessary

    Args:
        dir_path: Directory path

    Returns:
        Path object for the directory
    """
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def safe_remove(path: Union[str, Path]) -> bool:
    """Safely remove file or directory

    Args:
        path: Path to remove

    Returns:
        True if removed, False if didn't exist
    """
    path = Path(path)

    if not path.exists():
        return False

    if path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)

    return True


def copy_with_progress(
    src: Union[str, Path],
    dst: Union[str, Path],
    progress_callback: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> None:
    """Copy file with progress callback

    Args:
        src: Source file path
        dst: Destination file path
        progress_callback: Callback function(bytes_copied, total_bytes)
        chunk_size: Size of chunks to copy
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    # Ensure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)

    total_size = get_file_size(src)
    bytes_copied = 0

    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            while True:
                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break

                fdst.write(chunk)
                bytes_copied += len(chunk)

                if progress_callback:
                    progress_callback(bytes_copied, total_size)

    # Copy file permissions
    shutil.copystat(src, dst)


def create_archive(
    source_dir: Union[str, Path],
    output_file: Union[str, Path],
    compression: str = "gz",
    exclude_patterns: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> None:
    """Create tar archive from directory

    Args:
        source_dir: Source directory to archive
        output_file: Output archive file path
        compression: Compression type (gz, bz2, xz, or empty string)
        exclude_patterns: List of patterns to exclude
        progress_callback: Callback function(current_file)
    """
    source_dir = Path(source_dir)
    output_file = Path(output_file)

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Determine mode
    mode_map = {
        "gz": "w:gz",
        "bz2": "w:bz2",
        "xz": "w:xz",
        "": "w"
    }
    mode = mode_map.get(compression, "w:gz")

    # Create exclude filter
    def exclude_filter(tarinfo):
        if exclude_patterns:
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(tarinfo.name, pattern):
                    return None

        if progress_callback:
            progress_callback(tarinfo.name)

        return tarinfo

    # Create archive
    with tarfile.open(output_file, mode) as tar:
        tar.add(source_dir, arcname=".", filter=exclude_filter)


def extract_archive(
    archive_file: Union[str, Path],
    output_dir: Union[str, Path],
    progress_callback: Optional[Callable[[str], None]] = None
) -> None:
    """Extract tar archive to directory

    Args:
        archive_file: Archive file path
        output_dir: Output directory
        progress_callback: Callback function(current_file)
    """
    archive_file = Path(archive_file)
    output_dir = Path(output_dir)

    if not archive_file.exists():
        raise FileNotFoundError(f"Archive file not found: {archive_file}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract archive
    with tarfile.open(archive_file, 'r:*') as tar:
        for member in tar:
            if progress_callback:
                progress_callback(member.name)

            tar.extract(member, output_dir)


def find_files(
    root_dir: Union[str, Path],
    pattern: str = "*",
    recursive: bool = True,
    include_dirs: bool = False
) -> List[Path]:
    """Find files matching pattern

    Args:
        root_dir: Root directory to search
        pattern: File pattern (glob)
        recursive: Search recursively
        include_dirs: Include directories in results

    Returns:
        List of matching paths
    """
    root_dir = Path(root_dir)

    if not root_dir.exists():
        return []

    matches = []

    if recursive:
        for path in root_dir.rglob(pattern):
            if include_dirs or path.is_file():
                matches.append(path)
    else:
        for path in root_dir.glob(pattern):
            if include_dirs or path.is_file():
                matches.append(path)

    return sorted(matches)


def get_relative_paths(
    paths: List[Union[str, Path]],
    base_dir: Union[str, Path]
) -> List[Path]:
    """Get relative paths from base directory

    Args:
        paths: List of paths
        base_dir: Base directory

    Returns:
        List of relative paths
    """
    base_dir = Path(base_dir).resolve()
    relative_paths = []

    for path in paths:
        path = Path(path).resolve()
        try:
            rel_path = path.relative_to(base_dir)
            relative_paths.append(rel_path)
        except ValueError:
            # Path is not relative to base_dir
            relative_paths.append(path)

    return relative_paths


def create_temp_directory(
    prefix: str = "deploy_tool_",
    cleanup: bool = True
) -> tempfile.TemporaryDirectory:
    """Create a temporary directory

    Args:
        prefix: Directory name prefix
        cleanup: Whether to cleanup on exit

    Returns:
        TemporaryDirectory context manager
    """
    return tempfile.TemporaryDirectory(prefix=prefix, delete=cleanup)


def atomic_write(
    file_path: Union[str, Path],
    content: Union[str, bytes],
    mode: str = 'w',
    encoding: str = 'utf-8'
) -> None:
    """Write file atomically (write to temp, then rename)

    Args:
        file_path: Target file path
        content: Content to write
        mode: File mode
        encoding: Text encoding (for text mode)
    """
    file_path = Path(file_path)

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file
    temp_fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=f".{file_path.name}.",
        suffix=".tmp"
    )

    try:
        with os.fdopen(temp_fd, mode, encoding=encoding if 'b' not in mode else None) as f:
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


def read_file_lines(
    file_path: Union[str, Path],
    strip: bool = True,
    skip_empty: bool = True,
    skip_comments: bool = True,
    comment_char: str = '#'
) -> List[str]:
    """Read file lines with filtering

    Args:
        file_path: File path
        strip: Strip whitespace from lines
        skip_empty: Skip empty lines
        skip_comments: Skip comment lines
        comment_char: Comment character

    Returns:
        List of processed lines
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return []

    lines = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if strip:
                line = line.strip()

            if skip_empty and not line:
                continue

            if skip_comments and line.startswith(comment_char):
                continue

            lines.append(line)

    return lines


def get_directory_size(
    dir_path: Union[str, Path],
    follow_symlinks: bool = False
) -> int:
    """Get total size of directory contents

    Args:
        dir_path: Directory path
        follow_symlinks: Whether to follow symbolic links

    Returns:
        Total size in bytes
    """
    dir_path = Path(dir_path)

    if not dir_path.exists():
        return 0

    total_size = 0

    for path in dir_path.rglob('*'):
        if path.is_file(follow_symlinks=follow_symlinks):
            total_size += path.stat(follow_symlinks=follow_symlinks).st_size

    return total_size


def format_size(size_bytes: int) -> str:
    """Format file size for human readability

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
<<<<<<< Updated upstream
        if size < 1024.0:
            if unit == 'B':
                return f"{size} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
=======
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
>>>>>>> Stashed changes

    return f"{size_bytes:.1f} PB"

def format_bytes(size: int) -> str:
    """
    Format bytes to human readable string

    Args:
        size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            if unit == 'B':
                return f"{size} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def is_binary_file(file_path: Path) -> bool:
    """
    Check if file is binary

    Args:
        file_path: Path to file

    Returns:
        True if file is binary
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            if b'\0' in chunk:
                return True

            # Check for non-text characters
            text_characters = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
            non_text = chunk.translate(None, text_characters)
            return len(non_text) > len(chunk) * 0.3
    except:
        return True

def count_files(directory: Path,
                pattern: str = "*",
                recursive: bool = True) -> int:
    """
    Count files in directory

    Args:
        directory: Directory to count
        pattern: File pattern
        recursive: Count recursively

    Returns:
        Number of files
    """
    count = 0
    if recursive:
        for _ in directory.rglob(pattern):
            count += 1
    else:
        for _ in directory.glob(pattern):
            count += 1
    return count


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
    if exclude_patterns is None:
        exclude_patterns = DEFAULT_EXCLUDE_PATTERNS

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

<<<<<<< Updated upstream
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
        if path.is_file() or path.is_symlink():
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
    shutil.make_archive(
        base_name=base_name,
        format=format,
        root_dir=source_dir.parent,
        base_dir=base_dir or source_dir.name
    )

    # Return actual created file
    return output_file


def find_files_by_extension(directory: Path,
                            extensions: List[str],
                            recursive: bool = True) -> List[Path]:
    """
    Find files by extension

    Args:
        directory: Directory to search
        extensions: List of extensions (with or without dot)
        recursive: Search recursively

    Returns:
        List of matching files
    """
    # Normalize extensions
    extensions = [f'.{ext}' if not ext.startswith('.') else ext for ext in extensions]

    files = []
    if recursive:
        for ext in extensions:
            files.extend(directory.rglob(f'*{ext}'))
    else:
        for ext in extensions:
            files.extend(directory.glob(f'*{ext}'))

    return sorted(set(files))


def get_mime_type(file_path: Path) -> str:
    """
    Get MIME type of file

    Args:
        file_path: Path to file

    Returns:
        MIME type string
    """
    import mimetypes
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or 'application/octet-stream'


def detect_file_types(directory: Path) -> Dict[str, int]:
    """
    Detect file types in directory

    Args:
        directory: Directory to analyze

    Returns:
        Dictionary of extension -> count
    """
    types = {}
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext:
                types[ext] = types.get(ext, 0) + 1
            else:
                types['[no extension]'] = types.get('[no extension]', 0) + 1

    return dict(sorted(types.items()))


def atomic_write(file_path: Path,
                 content: Union[str, bytes],
                 mode: str = 'w') -> None:
    """
    Atomically write to file

    Args:
        file_path: Target file path
        content: Content to write
        mode: Write mode
    """
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


def read_file_lines(file_path: Path,
                    encoding: str = 'utf-8',
                    skip_empty: bool = False,
                    strip: bool = True) -> List[str]:
    """
    Read file lines

    Args:
        file_path: File path
        encoding: File encoding
        skip_empty: Skip empty lines
        strip: Strip whitespace

    Returns:
        List of lines
    """
    lines = []

    with open(file_path, 'r', encoding=encoding) as f:
        for line in f:
            if strip:
                line = line.strip()

            if skip_empty and not line:
                continue

            lines.append(line)

    return lines


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize path to absolute Path object

    Args:
        path: Path string or Path object

    Returns:
        Normalized Path object
    """
    return Path(path).expanduser().resolve()


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """
    Get detailed file information

    Args:
        file_path: Path to file

    Returns:
        Dictionary with file information
    """
    stat = file_path.stat()

    return {
        'name': file_path.name,
        'path': str(file_path),
        'size': stat.st_size,
        'size_human': format_size(stat.st_size),
        'created': datetime.fromtimestamp(stat.st_ctime),
        'modified': datetime.fromtimestamp(stat.st_mtime),
        'is_file': file_path.is_file(),
        'is_dir': file_path.is_dir(),
        'is_symlink': file_path.is_symlink(),
        'suffix': file_path.suffix,
        'mime_type': get_mime_type(file_path) if file_path.is_file() else None,
    }


def get_directory_size(directory: Path) -> int:
    """
    Get total size of directory

    Args:
        directory: Directory path

    Returns:
        Total size in bytes
    """
    total_size = 0

    for path in directory.rglob('*'):
        if path.is_file() and not path.is_symlink():
            total_size += path.stat().st_size

    return total_size


def format_timestamp(timestamp: float,
                     format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format timestamp to string

    Args:
        timestamp: Unix timestamp
        format: Date format string

    Returns:
        Formatted date string
    """
    return datetime.fromtimestamp(timestamp).strftime(format)


def calculate_directory_stats(directory: Path) -> Dict[str, Any]:
    """
    Calculate directory statistics

    Args:
        directory: Directory to analyze

    Returns:
        Dictionary with statistics
    """
    total_size = 0
    file_count = 0
    dir_count = 0
    extensions = {}
    largest_file = None
    largest_size = 0

    for path in directory.rglob('*'):
        if path.is_file():
            file_count += 1
            size = path.stat().st_size
            total_size += size

            # Track largest file
            if size > largest_size:
                largest_size = size
                largest_file = path

            # Track extensions
            ext = path.suffix.lower()
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1

        elif path.is_dir():
            dir_count += 1

    return {
        'total_size': total_size,
        'total_size_human': format_size(total_size),
        'file_count': file_count,
        'dir_count': dir_count,
        'extensions': dict(sorted(extensions.items())),
        'largest_file': str(largest_file) if largest_file else None,
        'largest_size': largest_size,
        'largest_size_human': format_size(largest_size),
    }


def list_directory_tree(directory: Path,
                        max_depth: int = 3,
                        prefix: str = "") -> List[str]:
    """
    Generate directory tree listing

    Args:
        directory: Root directory
        max_depth: Maximum depth to traverse
        prefix: Line prefix for indentation

    Returns:
        List of tree lines
    """
    lines = []

    if max_depth < 0:
        return lines

    try:
        items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, item in enumerate(items):
            is_last = i == len(items) - 1

            if item.is_file():
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{item.name}")
            else:
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{item.name}/")

                if max_depth > 0:
                    extension = "    " if is_last else "│   "
                    sub_lines = list_directory_tree(
                        item,
                        max_depth - 1,
                        prefix + extension
                    )
                    lines.extend(sub_lines)

    except PermissionError:
        lines.append(f"{prefix}[Permission Denied]")

    return lines


def compare_directories(dir1: Path, dir2: Path) -> Dict[str, List[str]]:
    """
    Compare two directories

    Args:
        dir1: First directory
        dir2: Second directory

    Returns:
        Dictionary with differences
    """
    files1 = {str(p.relative_to(dir1)): p for p in dir1.rglob('*') if p.is_file()}
    files2 = {str(p.relative_to(dir2)): p for p in dir2.rglob('*') if p.is_file()}

    only_in_dir1 = sorted(set(files1.keys()) - set(files2.keys()))
    only_in_dir2 = sorted(set(files2.keys()) - set(files1.keys()))
    common_files = sorted(set(files1.keys()) & set(files2.keys()))

    # Check for differences in common files
    different = []
    for rel_path in common_files:
        file1 = files1[rel_path]
        file2 = files2[rel_path]

        if file1.stat().st_size != file2.stat().st_size:
            different.append(rel_path)
        else:
            # Compare checksums
            hash1 = calculate_file_checksum(file1)
            hash2 = calculate_file_checksum(file2)
            if hash1 != hash2:
                different.append(rel_path)

    return {
        'only_in_first': only_in_dir1,
        'only_in_second': only_in_dir2,
        'different': different,
        'identical': [f for f in common_files if f not in different],
    }


def find_duplicate_files(directory: Path,
                         by_content: bool = True) -> Dict[str, List[Path]]:
    """
    Find duplicate files in directory

    Args:
        directory: Directory to scan
        by_content: Compare by content (True) or just by size (False)

    Returns:
        Dictionary of hash/size -> list of duplicate files
    """
    file_map = {}

    for file_path in directory.rglob('*'):
        if file_path.is_file():
            if by_content:
                # Group by content hash
                file_hash = calculate_file_checksum(file_path)
                key = file_hash
            else:
                # Group by size
                key = str(file_path.stat().st_size)

            if key not in file_map:
                file_map[key] = []
            file_map[key].append(file_path)

    # Filter out non-duplicates
    duplicates = {k: v for k, v in file_map.items() if len(v) > 1}

    return duplicates


def get_file_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Get file metadata (for compatibility with storage backends)

    This is an alias/wrapper for get_file_info with additional metadata.

    Args:
        file_path: Path to file

    Returns:
        Dictionary with file metadata or None if file doesn't exist
    """
    if not file_path.exists():
        return None

    try:
        # Get basic file info
        info = get_file_info(file_path)

        # Add additional metadata for compatibility with storage backends
        info.update({
            'path': str(file_path),
            'absolute_path': str(file_path.absolute()),
            'exists': True,
            'readable': os.access(file_path, os.R_OK),
            'writable': os.access(file_path, os.W_OK),
            'executable': os.access(file_path, os.X_OK),
        })

        # Add checksum for files
        if file_path.is_file() and file_path.stat().st_size < 100 * 1024 * 1024:  # Only for files < 100MB
            try:
                info['checksum'] = calculate_file_checksum(file_path)
            except:
                info['checksum'] = None

        return info

    except Exception as e:
        # Return minimal metadata on error
        return {
            'path': str(file_path),
            'exists': file_path.exists(),
            'error': str(e)
        }
=======
    return sorted(files)
>>>>>>> Stashed changes
