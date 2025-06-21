# deploy_tool/core/compression/tar_processor.py
"""Tar processor integration for deploy-tool"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Dict, Any

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

try:
    from .tar_compressor import (
        AsyncTarProcessor as _AsyncTarProcessor,
        CompressionType as _CompressionType,
        OperationStats
    )
    HAS_TAR_COMPRESSOR = True
except ImportError:
    HAS_TAR_COMPRESSOR = False
    _AsyncTarProcessor = None
    _CompressionType = None
    OperationStats = None

from ..manifest_engine import ManifestEngine
from ...models.manifest import Manifest

# Re-export CompressionType
if HAS_TAR_COMPRESSOR:
    CompressionType = _CompressionType
else:
    # Fallback enum if tar_compressor not available
    from enum import Enum

    class CompressionType(Enum):
        GZIP = "gz"
        BZIP2 = "bz2"
        XZ = "xz"
        LZ4 = "lz4"
        NONE = ""


class TarProcessor:
    """
    Tar processor wrapper that integrates AsyncTarProcessor with deploy-tool
    """

    def __init__(self,
                 compression_type: CompressionType = CompressionType.GZIP,
                 manifest_engine: Optional[ManifestEngine] = None):
        """
        Initialize tar processor

        Args:
            compression_type: Compression algorithm to use
            manifest_engine: Manifest engine instance
        """
        if not HAS_TAR_COMPRESSOR:
            raise ImportError(
                "tar_compressor module not found. "
                "Please ensure tar_compressor.py is available."
            )

        self.compression_type = compression_type
        self.manifest_engine = manifest_engine
        self._processor = _AsyncTarProcessor(compression_type)
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable[[int, int], None]) -> None:
        """
        Set progress callback

        Args:
            callback: Progress callback function(processed_bytes, total_bytes)
        """
        self._progress_callback = callback

    async def pack_with_manifest(self,
                                 source_paths: List[Path],
                                 output_path: Path,
                                 metadata: Optional[Dict[str, Any]] = None,
                                 use_relative_paths: bool = True) -> Tuple[Path, Optional[Manifest]]:
        """
        Pack files and generate manifest with relative path support

        Args:
            source_paths: List of source paths to pack
            output_path: Output archive path
            metadata: Additional metadata for manifest
            use_relative_paths: Whether to use relative paths in the archive (default: True)

        Returns:
            Tuple of (archive_path, manifest)
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Pack files with relative path support
        success = await self._processor.compress_with_progress(
            source_paths,
            output_path,
            use_relative_paths=use_relative_paths
        )

        if not success:
            raise RuntimeError("Failed to create archive")

        # Get operation stats
        stats = self._processor.stats
        manifest = None

        if self.manifest_engine and stats:
            # Create manifest without detailed file tracking
            # The manifest will be created by the caller with proper parameters
            manifest = None

        return output_path, manifest

    async def verify_archive(self,
                             archive_path: Path,
                             manifest: Optional[Manifest] = None) -> bool:
        """
        Verify archive integrity

        Args:
            archive_path: Path to archive file
            manifest: Optional manifest for checksum verification

        Returns:
            True if archive is valid
        """
        if not archive_path.exists():
            return False

        # List archive contents to verify it's readable
        contents = await self._processor.list_archive_contents(archive_path)
        if contents is None:
            return False

        # If manifest provided, verify checksum
        if manifest and hasattr(manifest, 'archive'):
            archive_info = manifest.archive
            if 'checksum' in archive_info and 'sha256' in archive_info['checksum']:
                expected_checksum = archive_info['checksum']['sha256']
                # Calculate actual checksum
                actual_checksum = self._calculate_file_checksum(archive_path)
                if actual_checksum != expected_checksum:
                    return False

        return True

    async def extract_archive(self,
                              archive_path: Path,
                              output_dir: Path,
                              strip_components: int = 0) -> bool:
        """
        Extract archive contents

        Args:
            archive_path: Path to archive file
            output_dir: Output directory
            strip_components: Number of path components to strip

        Returns:
            True if extraction successful
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        return await self._processor.decompress_with_progress(
            archive_path,
            output_dir,
            strip_components=strip_components
        )

    async def extract_with_progress(self,
                                    archive_path: Path,
                                    output_dir: Path) -> bool:
        """
        Extract archive with progress

        Args:
            archive_path: Archive file path
            output_dir: Output directory

        Returns:
            True if successful
        """
        return await self._processor.decompress_with_progress(
            archive_path,
            output_dir
        )

    async def list_contents(self, archive_path: Path) -> List[Tuple[str, int, bool]]:
        """
        List archive contents

        Args:
            archive_path: Archive file path

        Returns:
            List of (path, size, is_dir) tuples
        """
        contents = await self._processor.list_archive_contents(archive_path)
        return contents or []

    def _calculate_file_checksum(self, filepath: Path, algorithm: str = 'sha256') -> str:
        """
        Calculate file checksum

        Args:
            filepath: Path to file
            algorithm: Hash algorithm to use

        Returns:
            Hex digest of file checksum
        """
        import hashlib

        hash_obj = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    @property
    def compression_level(self) -> int:
        """Get compression level"""
        return self._processor.compression_level

    @compression_level.setter
    def compression_level(self, value: int) -> None:
        """Set compression level"""
        self._processor.compression_level = value

    @property
    def stats(self) -> Optional[OperationStats]:
        """Get operation statistics"""
        return self._processor.stats

    @staticmethod
    def get_file_extension(compression_type: CompressionType) -> str:
        """
        Get file extension for compression type

        Args:
            compression_type: Compression type

        Returns:
            File extension (e.g., '.gz', '.bz2')
        """
        return f".{compression_type.value}" if compression_type.value else ""

    @staticmethod
    def is_compression_supported(compression_type: CompressionType) -> bool:
        """
        Check if compression type is supported

        Args:
            compression_type: Compression type to check

        Returns:
            True if supported
        """
        if not HAS_TAR_COMPRESSOR:
            return False

        return _AsyncTarProcessor.is_algorithm_supported(compression_type)

    @staticmethod
    def get_supported_compressions() -> List[CompressionType]:
        """
        Get list of supported compression types

        Returns:
            List of supported compression types
        """
        if not HAS_TAR_COMPRESSOR:
            return []

        return _AsyncTarProcessor.get_supported_algorithms()

    @staticmethod
    def detect_compression_type(file_path: Path) -> CompressionType:
        """
        Detect compression type from file

        Args:
            file_path: File path

        Returns:
            Detected compression type
        """
        if not HAS_TAR_COMPRESSOR:
            return CompressionType.NONE

        # Use the processor's detection logic
        processor = _AsyncTarProcessor()
        return processor._detect_compression_type(file_path)

    # Convenience methods for common operations
    async def pack_directory(self,
                             directory: Path,
                             output_file: Path,
                             exclude_patterns: Optional[List[str]] = None,
                             use_relative_paths: bool = True) -> bool:
        """
        Pack a directory with relative path support (convenience method)

        Args:
            directory: Directory to pack
            output_file: Output file path
            exclude_patterns: Patterns to exclude
            use_relative_paths: Whether to use relative paths in the archive

        Returns:
            True if successful
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Note: Exclude patterns would need to be implemented
        # For now, pack everything
        return await self._processor.compress_with_progress(
            [directory],
            output_file,
            use_relative_paths=use_relative_paths
        )