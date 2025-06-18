"""Package service implementation"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core import (
    PathResolver,
    ManifestEngine,
    ValidationEngine,
    ConfigGenerator,
    GitAdvisor,
)
from ..core.compression import TarProcessor, CompressionType
from ..models import PackResult
from ..models.config import FullConfig
from ..api.exceptions import (
    PackError,
    ValidationError,
    FileExistsError,
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
            source_path: Source path
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

            # 2. Resolve paths
            source = self.path_resolver.resolve(source_path)

            # 3. Generate or load configuration
            if options.get('config_path'):
                config = self._load_config(options['config_path'])
            else:
                config = await self._generate_config(source, package_type, version, options)

            # 4. Scan files
            files_info = await self._scan_files(source, config)

            # 5. Execute compression
            archive_path = await self._compress_files(source, config, files_info, options)

            # 6. Generate manifest
            manifest = self._create_manifest(
                config, source, archive_path, files_info, options
            )

            # 7. Save manifest
            manifest_path = self.manifest_engine.save_manifest(manifest)

            # 8. Create result
            result = PackResult(
                success=True,
                package_type=package_type,
                version=version,
                manifest_path=str(manifest_path),
                archive_path=str(archive_path),
                duration=time.time() - start_time,
                metadata={
                    'file_count': len(files_info),
                    'total_size': sum(f['size'] for f in files_info),
                    'compression': config.compression.algorithm,
                }
            )

            # 9. Provide Git suggestions
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
            result.config_path = str(config_path)

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
        """Scan files to package"""
        from ..utils import scan_directory

        files = []
        if source.is_file():
            # Single file
            files.append({
                'path': source,
                'rel_path': source.name,
                'size': source.stat().st_size,
                'is_binary': True,  # Assume binary for safety
            })
        else:
            # Directory
            scan_results = scan_directory(
                source,
                excludes=config.source.excludes,
                includes=config.source.includes
            )

            for file_path, info in scan_results:
                files.append({
                    'path': file_path,
                    'rel_path': str(file_path.relative_to(source)),
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

        # Pack with progress
        if source.is_file():
            sources = [source]
        else:
            # For directory, pass the directory itself
            sources = [source]

        archive_path, _ = await processor.pack_with_manifest(
            sources,
            archive_path,
            metadata=config.metadata
        )

        return archive_path

    def _create_manifest(self,
                         config: FullConfig,
                         source: Path,
                         archive_path: Path,
                         files_info: List[Dict[str, Any]],
                         options: Dict[str, Any]) -> Any:
        """Create manifest"""
        manifest = self.manifest_engine.create_manifest(
            package_type=config.package.type,
            package_name=config.package.name or config.package.type,
            version=config.package.version,
            source_path=source,
            archive_path=archive_path,
            metadata={
                **config.metadata,
                'file_count': len(files_info),
                'total_source_size': sum(f['size'] for f in files_info),
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