"""Hash calculation utilities"""

import hashlib
from pathlib import Path
from typing import Dict, Optional, BinaryIO, Tuple
import aiofiles


def calculate_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calculate SHA256 hash of file

    Args:
        file_path: Path to file
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def calculate_md5(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash of file

    Args:
        file_path: Path to file
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    md5_hash = hashlib.md5()

    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)

    return md5_hash.hexdigest()


def verify_checksum(file_path: Path,
                    expected_checksum: str,
                    algorithm: str = "sha256") -> bool:
    """
    Verify file checksum

    Args:
        file_path: Path to file
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm

    Returns:
        True if checksum matches
    """
    if algorithm.lower() == "sha256":
        actual = calculate_sha256(file_path)
    elif algorithm.lower() == "md5":
        actual = calculate_md5(file_path)
    else:
        # Generic algorithm
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        actual = hash_func.hexdigest()

    return actual.lower() == expected_checksum.lower()


def generate_file_fingerprint(file_path: Path,
                              algorithms: Optional[list] = None) -> Dict[str, str]:
    """
    Generate multiple checksums for a file

    Args:
        file_path: Path to file
        algorithms: List of hash algorithms (default: sha256, md5)

    Returns:
        Dictionary of algorithm -> checksum
    """
    if algorithms is None:
        algorithms = ["sha256", "md5"]

    fingerprint = {}

    # Read file once and calculate all hashes
    hashers = {}
    for algo in algorithms:
        hashers[algo] = hashlib.new(algo)

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            for hasher in hashers.values():
                hasher.update(chunk)

    for algo, hasher in hashers.items():
        fingerprint[algo] = hasher.hexdigest()

    return fingerprint


def calculate_content_hash(content: bytes, algorithm: str = "sha256") -> str:
    """
    Calculate hash of content bytes

    Args:
        content: Content bytes
        algorithm: Hash algorithm

    Returns:
        Hex digest string
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(content)
    return hash_func.hexdigest()


def calculate_string_hash(text: str,
                          algorithm: str = "sha256",
                          encoding: str = "utf-8") -> str:
    """
    Calculate hash of string

    Args:
        text: Text string
        algorithm: Hash algorithm
        encoding: Text encoding

    Returns:
        Hex digest string
    """
    return calculate_content_hash(text.encode(encoding), algorithm)


def verify_multiple_checksums(file_path: Path,
                              checksums: Dict[str, str]) -> Tuple[bool, Dict[str, bool]]:
    """
    Verify multiple checksums

    Args:
        file_path: Path to file
        checksums: Dictionary of algorithm -> expected checksum

    Returns:
        Tuple of (all_valid, individual_results)
    """
    results = {}
    all_valid = True

    for algo, expected in checksums.items():
        is_valid = verify_checksum(file_path, expected, algo)
        results[algo] = is_valid
        if not is_valid:
            all_valid = False

    return all_valid, results


def calculate_directory_hash(directory: Path,
                             algorithm: str = "sha256",
                             include_hidden: bool = False) -> str:
    """
    Calculate hash of directory contents

    Args:
        directory: Directory path
        algorithm: Hash algorithm
        include_hidden: Include hidden files

    Returns:
        Hex digest of directory structure
    """
    hash_func = hashlib.new(algorithm)

    # Get all files sorted by path
    files = []
    for file_path in sorted(directory.rglob('*')):
        if file_path.is_file():
            # Skip hidden files if requested
            if not include_hidden and any(part.startswith('.') for part in file_path.parts):
                continue

            rel_path = file_path.relative_to(directory)
            files.append((str(rel_path), file_path))

    # Hash each file's path and content
    for rel_path, file_path in files:
        # Hash the relative path
        hash_func.update(rel_path.encode('utf-8'))
        hash_func.update(b'\x00')  # Separator

        # Hash the file content
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)

        hash_func.update(b'\x00')  # File separator

    return hash_func.hexdigest()


def stream_hash(file_obj: BinaryIO,
                algorithm: str = "sha256",
                chunk_size: int = 8192) -> str:
    """
    Calculate hash from file-like object

    Args:
        file_obj: File-like object
        algorithm: Hash algorithm
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    hash_func = hashlib.new(algorithm)

    while chunk := file_obj.read(chunk_size):
        hash_func.update(chunk)

    return hash_func.hexdigest()


def calculate_file_hash(file_path: Path,
                        algorithm: str = "sha256",
                        chunk_size: int = 8192) -> str:
    """
    Calculate file hash (alias for consistency)

    Args:
        file_path: Path to file
        algorithm: Hash algorithm
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    if algorithm.lower() == "sha256":
        return calculate_sha256(file_path, chunk_size)
    elif algorithm.lower() == "md5":
        return calculate_md5(file_path, chunk_size)
    else:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_func.update(chunk)
        return hash_func.hexdigest()


async def calculate_file_hash_async(file_path: Path,
                                    algorithm: str = "sha256",
                                    chunk_size: int = 8192) -> str:
    """
    Calculate file hash asynchronously

    Args:
        file_path: Path to file
        algorithm: Hash algorithm
        chunk_size: Read chunk size

    Returns:
        Hex digest string
    """
    hash_func = hashlib.new(algorithm)

    async with aiofiles.open(file_path, 'rb') as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            hash_func.update(chunk)

    return hash_func.hexdigest()


def compare_files(file1: Path, file2: Path, algorithm: str = "sha256") -> bool:
    """
    Compare two files by hash

    Args:
        file1: First file path
        file2: Second file path
        algorithm: Hash algorithm

    Returns:
        True if files are identical
    """
    # Quick size check first
    if file1.stat().st_size != file2.stat().st_size:
        return False

    # Compare hashes
    hash1 = calculate_file_hash(file1, algorithm)
    hash2 = calculate_file_hash(file2, algorithm)

    return hash1 == hash2


def generate_checksum_file(directory: Path,
                           output_file: Path,
                           algorithm: str = "sha256",
                           pattern: str = "*") -> int:
    """
    Generate checksum file for directory

    Args:
        directory: Directory to scan
        output_file: Output checksum file
        algorithm: Hash algorithm
        pattern: File pattern to match

    Returns:
        Number of files processed
    """
    count = 0

    with open(output_file, 'w') as f:
        for file_path in sorted(directory.rglob(pattern)):
            if file_path.is_file():
                checksum = calculate_file_hash(file_path, algorithm)
                relative_path = file_path.relative_to(directory)
                f.write(f"{checksum}  {relative_path}\n")
                count += 1

    return count


def verify_checksum_file(directory: Path,
                         checksum_file: Path,
                         algorithm: str = "sha256") -> Tuple[int, int, List[str]]:
    """
    Verify files against checksum file

    Args:
        directory: Base directory
        checksum_file: Checksum file path
        algorithm: Hash algorithm

    Returns:
        Tuple of (total_files, valid_files, invalid_files_list)
    """
    total = 0
    valid = 0
    invalid_files = []

    with open(checksum_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split('  ', 1)
            if len(parts) != 2:
                continue

            expected_checksum, relative_path = parts
            file_path = directory / relative_path

            total += 1

            if file_path.exists():
                actual_checksum = calculate_file_hash(file_path, algorithm)
                if actual_checksum == expected_checksum:
                    valid += 1
                else:
                    invalid_files.append(str(relative_path))
            else:
                invalid_files.append(str(relative_path))

    return total, valid, invalid_files