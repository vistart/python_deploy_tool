"""Package service implementation"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..constants import (
    DEFAULT_COMPRESSION_ALGORITHM,
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_EXCLUDE_PATTERNS,
    ARCHIVE_FILE_PATTERNS,
    ErrorCode
)
from ..core.path_resolver import PathResolver
from ..models import (
    PackResult,
    OperationStatus,
    Manifest,
    PackageInfo,
    ChecksumInfo
)
from ..utils.file_utils import (
    calculate_file_checksum,
    get_file_size,
    ensure_directory,
    create_archive
)


@dataclass
class PackageConfig:
    """Configuration for packaging operation"""
    type: str
    version: str
    source_path: Path
    output_path: Path
    compression_algorithm: str = DEFAULT_COMPRESSION_ALGORITHM
    compression_level: int = DEFAULT_COMPRESSION_LEVEL
    exclude_patterns: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Post-initialization processing"""
        if self.exclude_patterns is None:
            self.exclude_patterns = DEFAULT_EXCLUDE_PATTERNS.copy()
        if self.metadata is None:
            self.metadata = {}


class PackageService:
    """Service for packaging components"""

    def __init__(self, path_resolver: PathResolver):
        """Initialize package service

        Args:
            path_resolver: Path resolver instance
        """
        self.path_resolver = path_resolver

    async def package_component(
        self,
        config: PackageConfig,
        progress_callback: Optional[callable] = None
    ) -> PackResult:
        """Package a component

        Args:
            config: Package configuration
            progress_callback: Optional progress callback

        Returns:
            PackResult with status and details
        """
        result = PackResult(
            status=OperationStatus.IN_PROGRESS,
            component_type=config.type,
            component_version=config.version
        )

        try:
            # Validate source exists
            if not config.source_path.exists():
                result.add_error(
                    ErrorCode.SOURCE_NOT_FOUND,
                    f"Source directory not found: {config.source_path}"
                )
                result.complete(OperationStatus.FAILED)
                return result

            # Ensure output directory exists
            ensure_directory(config.output_path.parent)

            # Determine archive filename
            ext = self._get_compression_extension(config.compression_algorithm)
            filename_pattern = ARCHIVE_FILE_PATTERNS.get(ext, ARCHIVE_FILE_PATTERNS["gz"])
            filename = filename_pattern.format(
                component=config.type,
                version=config.version,
                ext=ext
            )

            package_path = config.output_path.parent / filename

            # Create archive
            await self._create_archive(
                source_dir=config.source_path,
                output_file=package_path,
                compression=config.compression_algorithm,
                compression_level=config.compression_level,
                exclude_patterns=config.exclude_patterns,
                progress_callback=progress_callback
            )

            # Calculate checksum
            checksum = calculate_file_checksum(package_path)
            file_size = get_file_size(package_path)

            # Set result
            result.package_path = package_path
            result.package_size = file_size
            result.compression_algorithm = config.compression_algorithm
            result.checksum = checksum

            # Create manifest
            manifest_path = await self._create_manifest(
                config=config,
                package_path=package_path,
                checksum=checksum,
                file_size=file_size
            )
            result.manifest_path = manifest_path

            result.message = f"Successfully packaged {config.type}:{config.version}"
            result.complete(OperationStatus.SUCCESS)

        except Exception as e:
            result.add_error(
                ErrorCode.PACK_FAILED,
                f"Failed to package component: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)

        return result

    async def _create_archive(
        self,
        source_dir: Path,
        output_file: Path,
        compression: str,
        compression_level: int,
        exclude_patterns: List[str],
        progress_callback: Optional[callable] = None
    ) -> None:
        """Create compressed archive

        Args:
            source_dir: Source directory
            output_file: Output archive file
            compression: Compression algorithm
            compression_level: Compression level
            exclude_patterns: Patterns to exclude
            progress_callback: Progress callback
        """
        # Map compression names to tar modes
        compression_map = {
            "gzip": "gz",
            "bzip2": "bz2",
            "xz": "xz",
            "lz4": "lz4",
            "none": ""
        }

        tar_compression = compression_map.get(compression, "gz")

        # Use file_utils create_archive function
        create_archive(
            source_dir=source_dir,
            output_file=output_file,
            compression=tar_compression,
            exclude_patterns=exclude_patterns,
            progress_callback=progress_callback
        )

    async def _create_manifest(
        self,
        config: PackageConfig,
        package_path: Path,
        checksum: str,
        file_size: int
    ) -> Path:
        """Create component manifest

        Args:
            config: Package configuration
            package_path: Path to package file
            checksum: Package checksum
            file_size: Package size

        Returns:
            Path to manifest file
        """
        # Create manifest
        manifest = Manifest(
            component_type=config.type,
            component_version=config.version,
            created_at=datetime.utcnow(),
            package=PackageInfo(
                file=package_path.name,
                size=file_size,
                checksum=ChecksumInfo(
                    algorithm="sha256",
                    value=checksum
                ),
                compression_algorithm=config.compression_algorithm
            ),
            metadata=config.metadata
        )

        # Determine manifest path
        manifests_dir = self.path_resolver.get_manifests_dir()
        component_dir = manifests_dir / config.type
        ensure_directory(component_dir)

        manifest_file = component_dir / f"{config.version}.json"

        # Save manifest
        import json
        with open(manifest_file, 'w') as f:
            json.dump(manifest.to_dict(), f, indent=2)

        return manifest_file

    def _get_compression_extension(self, algorithm: str) -> str:
        """Get file extension for compression algorithm

        Args:
            algorithm: Compression algorithm

        Returns:
            File extension
        """
        extension_map = {
            "gzip": "gz",
            "bzip2": "bz2",
            "xz": "xz",
            "lz4": "lz4",
            "none": ""
        }
        return extension_map.get(algorithm, "gz")

    async def validate_package(
        self,
        package_path: Path,
        expected_checksum: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate a package file

        Args:
            package_path: Path to package file
            expected_checksum: Expected checksum (if known)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not package_path.exists():
            return False, f"Package file not found: {package_path}"

        try:
            # Calculate actual checksum
            actual_checksum = calculate_file_checksum(package_path)

            # Compare if expected checksum provided
            if expected_checksum and actual_checksum != expected_checksum:
                return False, f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"

            # TODO: Add more validation (e.g., archive integrity)

            return True, None

        except Exception as e:
            return False, f"Validation failed: {str(e)}"