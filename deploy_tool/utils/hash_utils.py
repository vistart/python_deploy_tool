"""Hash calculation utilities"""

import hashlib
from pathlib import Path
from typing import Dict, Optional, BinaryIO


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


from typing import Tuple