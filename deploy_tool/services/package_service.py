# deploy_tool/services/package_service.py
"""Package service implementation"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..api.exceptions import (
    PackError,
    ValidationError,
    FileExistsError,
)
from ..core import (
    PathResolver,
    ManifestEngine,
    ValidationEngine,
    ConfigGenerator,
    GitAdvisor,
)
from ..core.compression import TarProcessor, CompressionType
from ..models import PackResult, PackageConfig, SourceConfig, CompressionConfig, OutputConfig


@dataclass
class FullConfig:
    """Full package configuration combining all config components"""
    package: PackageConfig
    source: SourceConfig
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FullConfig':
        """Create from dictionary"""
        return cls(
            package=PackageConfig.from_dict(data['package']),
            source=SourceConfig.from_dict(data['source']),
            compression=CompressionConfig.from_dict(data.get('compression', {})),
            output=OutputConfig.from_dict(data.get('output', {})),
            metadata=data.get('metadata', {})
        )


class PackageService:
    """Packaging service implementation"""

    def __init__(self,
                 path_resolver: PathResolver,
                 manifest_engine: ManifestEngine,
                 config_generator: ConfigGenerator,
                 validation_engine: ValidationEngine):
        """
        Initialize package service

        Args:
            path_resolver: Path resolver instance
            manifest_engine: Manifest engine instance
            config_generator: Config generator instance
            validation_engine: Validation engine instance
        """
        self.path_resolver = path_resolver
        self.manifest_engine = manifest_engine
        self.config_generator = config_generator
        self.validation_engine = validation_engine
        self.git_advisor = GitAdvisor(path_resolver)

    async def pack(self,
                   source_path: str,
                   package_type: str,
                   version: str,
                   options: Optional[Dict[str, Any]] = None) -> PackResult:
        """
        Execute packaging workflow

        Args:
            source_path: Source path (should be relative)
            package_type: Package type
            version: Version string
            options: Additional options

        Returns:
            PackResult: Packaging result
        """
        start_time = time.time()
        options = options or {}

        try:
            # 1. Validate inputs
            await self._validate_inputs(source_path, package_type, version)

            # 2. Convert to relative path if absolute
            source_path = self._ensure_relative_path(source_path)

            # 3. Resolve path for actual file operations
            source = self.path_resolver.resolve(source_path)

            # 4. Generate or load configuration
            if options.get('config_path'):
                config = self._load_config(options['config_path'])
            else:
                config = await self._generate_config(source, package_type, version, options)

            # 5. Scan files (record relative paths)
            files_info = await self._scan_files(source, config)

            # 6. Execute compression
            archive_path = await self._compress_files(source, config, files_info, options)

            # 7. Generate manifest (with relative paths)
            manifest = self._create_manifest(
                config, source_path, archive_path, files_info, options
            )

            # 8. Save manifest
            manifest_path = self.manifest_engine.save_manifest(manifest)

            # 9. Create result (with relative paths for display)
            result = PackResult(
                success=True,
                package_type=package_type,
                version=version,
                manifest_path=str(self.path_resolver.get_relative_to_root(manifest_path)),
                archive_path=str(self.path_resolver.get_relative_to_root(archive_path)),
                duration=time.time() - start_time,
                metadata={
                    'file_count': len(files_info),
                    'total_size': sum(f['size'] for f in files_info),
                    'compression': config.compression.algorithm,
                }
            )

            # 10. Provide Git suggestions
            if options.get('show_git_suggestions', True):
                self.git_advisor.provide_post_pack_advice(
                    manifest_path,
                    Path(config.get('source_config_path')) if 'source_config_path' in config else None
                )

            return result

        except Exception as e:
            return PackResult(
                success=False,
                package_type=package_type,
                version=version,
                error=str(e),
                duration=time.time() - start_time
            )

    def _ensure_relative_path(self, path: str) -> str:
        """Ensure path is relative to project root

        Args:
            path: Input path (absolute or relative)

        Returns:
            Relative path string
        """
        path_obj = Path(path)

        # If already relative, return as-is
        if not path_obj.is_absolute():
            return path

        # Try to make relative to project root
        try:
            rel_path = path_obj.relative_to(self.path_resolver.project_root)
            return str(rel_path)
        except ValueError:
            raise PackError(
                f"Path '{path}' is outside project root. "
                f"Please use paths within the project for portability."
            )

    async def auto_pack(self,
                        source_path: str,
                        package_type: str,
                        version: str) -> PackResult:
        """
        Auto-generate config and pack

        Args:
            source_path: Source path
            package_type: Package type
            version: Version string

        Returns:
            PackResult: Packaging result
        """
        # Ensure relative path
        source_path = self._ensure_relative_path(source_path)

        # Generate configuration
        source = Path(source_path)
        config_dict, config_path = self.config_generator.generate_config(
            source,
            {'type': package_type, 'version': version, 'save_config': True}
        )

        # Pack with generated config
        result = await self.pack(
            source_path,
            package_type,
            version,
            {'config_path': config_path}
        )

        # Add config path to result
        if config_path:
            result.config_path = str(self.path_resolver.get_relative_to_root(config_path))

        return result

    async def pack_with_config(self, config_path: str) -> PackResult:
        """
        Pack using configuration file

        Args:
            config_path: Configuration file path

        Returns:
            PackResult: Packaging result
        """
        # Load and validate config
        config = self._load_config(config_path)

        # Extract package info
        package_type = config.package.type
        version = config.package.version
        source_path = config.source.path

        # Pack
        return await self.pack(
            source_path,
            package_type,
            version,
            {'config_path': config_path}
        )

    async def _validate_inputs(self,
                               source_path: str,
                               package_type: str,
                               version: str) -> None:
        """Validate packaging inputs"""
        # Validate source path
        source = self.path_resolver.resolve(source_path)
        path_result = self.validation_engine.validate_path(
            source, must_exist=True
        )
        if not path_result.is_valid:
            raise ValidationError(path_result.errors[0])

        # Validate package type
        type_result = self.validation_engine.validate_component_type(package_type)
        if not type_result.is_valid:
            raise ValidationError(type_result.errors[0])

        # Validate version
        version_result = self.validation_engine.validate_version(version)
        if not version_result.is_valid:
            raise ValidationError(version_result.errors[0])

    def _load_config(self, config_path: str) -> FullConfig:
        """Load configuration from file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise PackError(f"Configuration file not found: {config_path}")

        # Load configuration
        config_dict = self.config_generator.load_config(config_file)

        # Validate configuration
        errors = self.config_generator.validate_config(config_dict)
        if errors:
            raise ValidationError(f"Invalid configuration: {', '.join(errors)}")

        return FullConfig.from_dict(config_dict)

    async def _generate_config(self,
                               source: Path,
                               package_type: str,
                               version: str,
                               options: Dict[str, Any]) -> FullConfig:
        """Generate configuration"""
        config_dict, _ = self.config_generator.generate_config(
            source,
            {
                'type': package_type,
                'version': version,
                'save_config': False,
                **options
            }
        )

        return FullConfig.from_dict(config_dict)

    async def _scan_files(self,
                          source: Path,
                          config: FullConfig) -> List[Dict[str, Any]]:
        """Scan files to package (recording relative paths)"""
        from ..utils import scan_directory

        files = []
        project_root = self.path_resolver.project_root

        if source.is_file():
            # Single file - record relative path from project root
            rel_path = source.relative_to(project_root)
            files.append({
                'path': source,
                'rel_path': str(rel_path),
                'size': source.stat().st_size,
                'is_binary': True,  # Assume binary for safety
            })
        else:
            # Directory - scan and record relative paths
            scan_results = scan_directory(
                source,
                excludes=config.source.excludes,
                includes=config.source.includes
            )

            for file_path, info in scan_results:
                # Record relative path from source directory
                rel_path = file_path.relative_to(source)
                files.append({
                    'path': file_path,
                    'rel_path': str(rel_path),
                    'size': info['size'],
                    'is_binary': info['is_binary'],
                })

        return files

    async def _compress_files(self,
                              source: Path,
                              config: FullConfig,
                              files_info: List[Dict[str, Any]],
                              options: Dict[str, Any]) -> Path:
        """Compress files"""
        # Determine output path
        output_dir = self.path_resolver.resolve(config.output.path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Format output filename
        output_filename = config.output.format_filename(
            config.package,
            config.compression
        )
        archive_path = output_dir / output_filename

        # Check if exists
        if archive_path.exists() and not options.get('force', False):
            raise FileExistsError(str(archive_path))

        # Get compression type
        compress_type = self._get_compression_type(config.compression.algorithm)

        # Create tar processor
        processor = TarProcessor(
            compression_type=compress_type,
            manifest_engine=self.manifest_engine
        )

        # Set compression level
        processor._processor.compression_level = config.compression.level

        # Pack with progress - use relative paths in archive
        if source.is_file():
            sources = [source]
        else:
            # For directory, pass the directory itself
            sources = [source]

        archive_path, _ = await processor.pack_with_manifest(
            sources,
            archive_path,
            metadata=config.metadata,
            # Ensure relative paths are used in the archive
            use_relative_paths=True
        )

        return archive_path

    def _create_manifest(self,
                         config: FullConfig,
                         source_path: str,  # Already relative
                         archive_path: Path,
                         files_info: List[Dict[str, Any]],
                         options: Dict[str, Any]) -> Any:
        """Create manifest with relative paths"""
        # Convert archive path to relative
        archive_path_rel = self.path_resolver.get_relative_to_root(archive_path)

        manifest = self.manifest_engine.create_manifest(
            package_type=config.package.type,
            package_name=config.package.name or config.package.type,
            version=config.package.version,
            source_path=Path(source_path),  # Use the already relative path
            archive_path=archive_path,
            metadata={
                **config.metadata,
                'file_count': len(files_info),
                'total_source_size': sum(f['size'] for f in files_info),
                'source_path': source_path,  # Store original relative path
                'archive_path': str(archive_path_rel),  # Store relative archive path
            }
        )

        return manifest

    def _get_compression_type(self, algorithm: str) -> CompressionType:
        """Get compression type from algorithm string"""
        mapping = {
            'gzip': CompressionType.GZIP,
            'gz': CompressionType.GZIP,
            'bzip2': CompressionType.BZIP2,
            'bz2': CompressionType.BZIP2,
            'xz': CompressionType.XZ,
            'lzma': CompressionType.XZ,
            'lz4': CompressionType.LZ4,
            'none': CompressionType.NONE,
            '': CompressionType.NONE,
        }

        algo_lower = algorithm.lower()
        if algo_lower not in mapping:
            raise PackError(f"Unsupported compression algorithm: {algorithm}")

        return mapping[algo_lower]