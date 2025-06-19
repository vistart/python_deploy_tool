"""Tar processor integration for deploy-tool"""

# Import the existing tar_compressor module
# In real implementation, this would be properly integrated
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
from ...models.manifest import Manifest, FileEntry

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
            # Create file entries from packed files
            file_entries = []

            # Note: In a full implementation, we would track individual files
            # For now, we'll create a summary entry
            for source_path in source_paths:
                if source_path.is_file():
                    entry = FileEntry(
                        path=str(source_path.name),  # Use relative path in manifest
                        size=source_path.stat().st_size,
                        checksum="",  # Would calculate in full implementation
                        # is_binary=True
                    )
                    file_entries.append(entry)
                else:
                    # For directories, would enumerate all files
                    # This is a simplified version
                    entry = FileEntry(
                        path=str(source_path.name),
                        size=stats.total_size,
                        checksum="",
                        # is_binary=True
                    )
                    file_entries.append(entry)

            # Create manifest
            manifest = self.manifest_engine.create_manifest(
                package_type="",  # Would be set by caller
                package_name="",  # Would be set by caller
                version="",  # Would be set by caller
                source_path=source_paths[0] if source_paths else None,
                archive_path=output_path,
                metadata=metadata,
                # files=file_entries
            )

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

        # If we have a manifest, verify checksum
        if manifest and 'checksum' in manifest.archive:
            # This would verify against the manifest checksum
            pass

        return True

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

    @staticmethod
    def detect_compression_type(file_path: Path) -> CompressionType:
        """
        Detect compression type from file

        Args:
            file_path: File path

        Returns:
            Detected compression type
        """
        # Use the processor's detection logic
        processor = _AsyncTarProcessor()
        return processor._detect_compression_type(file_path)

    # Static methods
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

    @property
    def stats(self) -> Optional[OperationStats]:
        """
        Get operation statistics

        Returns:
            Operation statistics or None
        """
        return self._processor.stats if self._processor else None

    def get_stats(self) -> Optional[OperationStats]:
        """Get operation statistics"""
        return self._processor.stats

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


    async def pack_files(self,
                         files: List[Path],
                         output_file: Path,
                         use_relative_paths: bool = True) -> bool:
        """
        Pack multiple files with relative path support (convenience method)

        Args:
            files: List of files to pack
            output_file: Output file path
            use_relative_paths: Whether to use relative paths in the archive

        Returns:
            True if successful
        """
        # Validate all files exist
        for file_path in files:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

        return await self._processor.compress_with_progress(
            files,
            output_file,
            use_relative_paths=use_relative_paths
        )

    def format_size(self, size: int) -> str:
        """Format size in human-readable format"""
        return self._processor._format_size(size)