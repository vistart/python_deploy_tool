# deploy_tool/core/compression/adapters.py
"""Compression adapter interfaces"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from .tar_processor import CompressionType


class CompressionAdapter(ABC):
    """Abstract base class for compression adapters"""

    @abstractmethod
    def get_compression_type(self) -> CompressionType:
        """Get compression type"""
        pass

    @abstractmethod
    def get_extension(self) -> str:
        """Get file extension"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get compression description"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if compression is available"""
        pass

    @abstractmethod
    def get_default_level(self) -> int:
        """Get default compression level"""
        pass

    @abstractmethod
    def validate_level(self, level: int) -> bool:
        """Validate compression level"""
        pass


class GzipAdapter(CompressionAdapter):
    """GZIP compression adapter"""

    def get_compression_type(self) -> CompressionType:
        return CompressionType.GZIP

    def get_extension(self) -> str:
        return ".gz"

    def get_description(self) -> str:
        return "GZIP compression - balanced speed and ratio"

    def is_available(self) -> bool:
        from .tar_processor import TarProcessor
        return TarProcessor.is_compression_supported(CompressionType.GZIP)

    def get_default_level(self) -> int:
        return 6

    def validate_level(self, level: int) -> bool:
        return 1 <= level <= 9


class Bzip2Adapter(CompressionAdapter):
    """BZIP2 compression adapter"""

    def get_compression_type(self) -> CompressionType:
        return CompressionType.BZIP2

    def get_extension(self) -> str:
        return ".bz2"

    def get_description(self) -> str:
        return "BZIP2 compression - high compression ratio, slower"

    def is_available(self) -> bool:
        from .tar_processor import TarProcessor
        return TarProcessor.is_compression_supported(CompressionType.BZIP2)

    def get_default_level(self) -> int:
        return 9

    def validate_level(self, level: int) -> bool:
        return 1 <= level <= 9


class XzAdapter(CompressionAdapter):
    """XZ/LZMA compression adapter"""

    def get_compression_type(self) -> CompressionType:
        return CompressionType.XZ

    def get_extension(self) -> str:
        return ".xz"

    def get_description(self) -> str:
        return "XZ/LZMA compression - highest compression ratio, slowest"

    def is_available(self) -> bool:
        from .tar_processor import TarProcessor
        return TarProcessor.is_compression_supported(CompressionType.XZ)

    def get_default_level(self) -> int:
        return 6

    def validate_level(self, level: int) -> bool:
        return 0 <= level <= 9


class Lz4Adapter(CompressionAdapter):
    """LZ4 compression adapter"""

    def get_compression_type(self) -> CompressionType:
        return CompressionType.LZ4

    def get_extension(self) -> str:
        return ".lz4"

    def get_description(self) -> str:
        return "LZ4 compression - extremely fast, lower compression ratio"

    def is_available(self) -> bool:
        from .tar_processor import TarProcessor
        return TarProcessor.is_compression_supported(CompressionType.LZ4)

    def get_default_level(self) -> int:
        return 1

    def validate_level(self, level: int) -> bool:
        return 1 <= level <= 12


class NoCompressionAdapter(CompressionAdapter):
    """No compression adapter"""

    def get_compression_type(self) -> CompressionType:
        return CompressionType.NONE

    def get_extension(self) -> str:
        return ""

    def get_description(self) -> str:
        return "No compression - archive only"

    def is_available(self) -> bool:
        return True

    def get_default_level(self) -> int:
        return 0

    def validate_level(self, level: int) -> bool:
        return level == 0


# Registry of compression adapters
COMPRESSION_ADAPTERS: Dict[str, CompressionAdapter] = {
    "gzip": GzipAdapter(),
    "gz": GzipAdapter(),
    "bzip2": Bzip2Adapter(),
    "bz2": Bzip2Adapter(),
    "xz": XzAdapter(),
    "lzma": XzAdapter(),
    "lz4": Lz4Adapter(),
    "none": NoCompressionAdapter(),
    "": NoCompressionAdapter(),
}


def get_compression_adapter(name: str) -> Optional[CompressionAdapter]:
    """
    Get compression adapter by name

    Args:
        name: Compression name (gzip, bzip2, xz, lz4, none)

    Returns:
        Compression adapter or None
    """
    return COMPRESSION_ADAPTERS.get(name.lower())


def get_available_compressions() -> Dict[str, CompressionAdapter]:
    """
    Get all available compression adapters

    Returns:
        Dictionary of available adapters
    """
    available = {}

    for name, adapter in COMPRESSION_ADAPTERS.items():
        if adapter.is_available() and name not in available.values():
            # Avoid duplicates (gz/gzip, etc)
            available[adapter.get_compression_type().value] = adapter

    return available


def suggest_compression(file_stats: Dict[str, Any]) -> CompressionAdapter:
    """
    Suggest best compression based on file statistics

    Args:
        file_stats: Dictionary with file statistics

    Returns:
        Suggested compression adapter
    """
    binary_ratio = file_stats.get('binary_ratio', 0)
    total_size = file_stats.get('total_size', 0)

    # For mostly binary files, use fast compression
    if binary_ratio > 0.8:
        if COMPRESSION_ADAPTERS['lz4'].is_available():
            return COMPRESSION_ADAPTERS['lz4']
        else:
            return COMPRESSION_ADAPTERS['gzip']

    # For large text files, use high compression
    if total_size > 100 * 1024 * 1024 and binary_ratio < 0.2:  # > 100MB text
        if COMPRESSION_ADAPTERS['xz'].is_available():
            return COMPRESSION_ADAPTERS['xz']
        elif COMPRESSION_ADAPTERS['bzip2'].is_available():
            return COMPRESSION_ADAPTERS['bzip2']

    # Default to gzip for balanced performance
    return COMPRESSION_ADAPTERS['gzip']