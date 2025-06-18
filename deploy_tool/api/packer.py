"""Packer API for packaging operations"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from ..core import (
    PathResolver,
    ManifestEngine,
    ValidationEngine,
    ConfigGenerator,
    GitAdvisor,
)
from ..core.compression import TarProcessor, CompressionType
from ..models import PackResult, Component
from ..models.config import FullConfig
from ..constants import DEFAULT_COMPRESSION_ALGORITHM
from .exceptions import (
    PackError,
    MissingTypeError,
    MissingVersionError,
    ConfigError,
    ValidationError,
    FileExistsError,
)


class Packer:
    """Packer class for packaging operations"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize packer

        Args:
            config: Global configuration dictionary
        """
        self.config = config or {}
        self.path_resolver = PathResolver()
        self.manifest_engine = ManifestEngine(self.path_resolver)
        self.validation_engine = ValidationEngine()
        self.config_generator = ConfigGenerator(self.path_resolver)
        self.git_advisor = GitAdvisor(self.path_resolver)

    def pack(self,
             source_path: str,
             package_type: str = None,
             version: str = None,
             output_path: str = None,
             **options) -> PackResult:
        """
        Execute packaging

        Args:
            source_path: Source file path
            package_type: Package type (user-defined) - required
            version: Version string - required
            output_path: Output path (optional)
            **options: Other options
                - compress: Compression algorithm
                - level: Compression level
                - force: Force overwrite
                - save_config: Save generated config
                - metadata: Additional metadata

        Returns:
            PackResult: Packaging result object

        Raises:
            MissingTypeError: If package_type is not provided
            MissingVersionError: If version is not provided
            PackError: If packaging fails

        Note:
            Should not be used for packaging code files,
            code should be managed through Git
        """
        # Validate required parameters
        if not package_type:
            raise MissingTypeError()
        if not version:
            raise MissingVersionError()

        # Run async pack
        return asyncio.run(self._async_pack(
            source_path,
            package_type,
            version,
            output_path,
            **options
        ))

    def auto_pack(self,
                  source_path: str,
                  package_type: str,
                  version: str,
                  save_config: bool = True,
                  **options) -> PackResult:
        """
        Auto-generate config and pack

        Args:
            source_path: Source file path
            package_type: Package type (user-defined) - required
            version: Version string - required
            save_config: Whether to save generated config
            **options: Additional options

        Returns:
            PackResult: Including config path

        Raises:
            MissingTypeError: If package_type is not provided
            MissingVersionError: If version is not provided
        """
        if not package_type:
            raise MissingTypeError()
        if not version:
            raise MissingVersionError()

        # Prepare options for config generation
        gen_options = {
            'type': package_type,
            'version': version,
            'save_config': save_config,
            **options
        }

        # Generate configuration
        source = Path(source_path)
        config_dict, config_path = self.config_generator.generate_config(
            source, gen_options
        )

        # Create full config object
        full_config = FullConfig.from_dict(config_dict)

        # Execute pack with generated config
        result = self._pack_with_config_object(full_config, source)

        # Add config path to result
        if config_path:
            result.config_path = str(config_path)

        return result

    def pack_with_config(self, config_path: str, **options) -> PackResult:
        """
        Pack using configuration file

        Args:
            config_path: Configuration file path
            **options: Override options

        Returns:
            PackResult: Packaging result

        Raises:
            ConfigError: If config is invalid
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        # Load configuration
        config_dict = self.config_generator.load_config(config_file)

        # Validate configuration
        errors = self.config_generator.validate_config(config_dict)
        if errors:
            raise ConfigError(f"Invalid configuration: {', '.join(errors)}")

        # Apply overrides
        if options.get('version'):
            config_dict['package']['version'] = options['version']

        # Create full config object
        full_config = FullConfig.from_dict(config_dict)

        # Get source path
        source_path = self.path_resolver.resolve(full_config.source.path)

        return self._pack_with_config_object(full_config, source_path)

    def pack_batch(self, batch_config: Union[str, Dict]) -> List[PackResult]:
        """
        Batch packaging

        Args:
            batch_config: Batch config file path or config dict

        Returns:
            List[PackResult]: List of packaging results
        """
        if isinstance(batch_config, str):
            # Load from file
            import yaml
            with open(batch_config, 'r') as f:
                config = yaml.safe_load(f)
        else:
            config = batch_config

        results = []
        for package_config in config.get('packages', []):
            try:
                # Create minimal config
                full_config = {
                    'package': {
                        'type': package_config['type'],
                        'version': package_config['version'],
                    },
                    'source': package_config.get('source', {}),
                }

                # Add other fields if present
                for key in ['compression', 'output', 'validation', 'metadata']:
                    if key in package_config:
                        full_config[key] = package_config[key]

                # Pack
                config_obj = FullConfig.from_dict(full_config)
                source_path = self.path_resolver.resolve(config_obj.source.path)
                result = self._pack_with_config_object(config_obj, source_path)
                results.append(result)

            except Exception as e:
                # Create error result
                result = PackResult(
                    success=False,
                    package_type=package_config.get('type', 'unknown'),
                    version=package_config.get('version', 'unknown'),
                    error=str(e)
                )
                results.append(result)

        return results

    async def _async_pack(self,
                          source_path: str,
                          package_type: str,
                          version: str,
                          output_path: str = None,
                          **options) -> PackResult:
        """Async pack implementation"""
        start_time = time.time()

        try:
            # Resolve paths
            source = self.path_resolver.resolve(source_path)

            # Validate source
            validation_result = self.validation_engine.validate_path(
                source, must_exist=True
            )
            if not validation_result.is_valid:
                raise ValidationError(validation_result.errors[0])

            # Validate type and version
            type_result = self.validation_engine.validate_component_type(package_type)
            if not type_result.is_valid:
                raise ValidationError(type_result.errors[0])

            version_result = self.validation_engine.validate_version(version)
            if not version_result.is_valid:
                raise ValidationError(version_result.errors[0])

            # Determine output path
            if output_path:
                output_dir = Path(output_path)
            else:
                output_dir = self.path_resolver.get_dist_dir()

            output_dir.mkdir(parents=True, exist_ok=True)

            # Determine compression
            compress_algo = options.get('compress', DEFAULT_COMPRESSION_ALGORITHM)
            compress_type = self._get_compression_type(compress_algo)

            # Create archive filename
            extension = TarProcessor.get_file_extension(compress_type)
            archive_name = f"{package_type}-{version}.tar{extension}"
            archive_path = output_dir / archive_name

            # Check if exists
            if archive_path.exists() and not options.get('force', False):
                raise FileExistsError(str(archive_path))

            # Create tar processor
            processor = TarProcessor(
                compression_type=compress_type,
                manifest_engine=self.manifest_engine
            )

            # Set compression level if specified
            if 'level' in options:
                processor._processor.compression_level = options['level']

            # Pack with progress
            archive_path, manifest = await processor.pack_with_manifest(
                [source],
                archive_path,
                metadata=options.get('metadata', {})
            )

            # Create manifest
            manifest = self.manifest_engine.create_manifest(
                package_type=package_type,
                package_name=options.get('name', package_type),
                version=version,
                source_path=source,
                archive_path=archive_path,
                metadata=options.get('metadata')
            )

            # Save manifest
            manifest_path = self.manifest_engine.save_manifest(manifest)

            # Create result
            result = PackResult(
                success=True,
                package_type=package_type,
                version=version,
                manifest_path=str(manifest_path),
                archive_path=str(archive_path),
                duration=time.time() - start_time,
                metadata={
                    'compression': compress_algo,
                    'archive_size': archive_path.stat().st_size,
                }
            )

            # Provide git suggestions
            self.git_advisor.provide_post_pack_advice(
                manifest_path,
                options.get('config_path')
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

    def _pack_with_config_object(self,
                                 config: FullConfig,
                                 source_path: Path) -> PackResult:
        """Pack with config object"""
        # Prepare options
        options = {
            'name': config.package.name,
            'compress': config.compression.algorithm,
            'level': config.compression.level,
            'metadata': config.metadata,
        }

        # Format output filename
        output_filename = config.output.format_filename(
            config.package,
            config.compression
        )
        output_dir = self.path_resolver.resolve(config.output.path)
        output_path = output_dir / output_filename

        # Execute pack
        return self.pack(
            source_path=str(source_path),
            package_type=config.package.type,
            version=config.package.version,
            output_path=str(output_dir),
            **options
        )

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


# Convenience function
def pack(source_path: str, **options) -> PackResult:
    """
    Pack files (convenience function)

    Args:
        source_path: Source file path
        **options: Options
            - type: Package type (required)
            - auto: Auto mode
            - version: Version
            - config: Config file path

    Returns:
        PackResult: Packaging result

    Note:
        Code files are managed through Git and should not be packed.
        This tool is for packaging non-code resources like models,
        configs, data, etc.
    """
    packer = Packer()

    # Check if type is specified
    if 'type' not in options and not options.get('config'):
        raise MissingTypeError(
            "Must specify package type (type parameter) or config file"
        )

    if options.get('auto'):
        return packer.auto_pack(source_path, **options)
    elif options.get('config'):
        return packer.pack_with_config(options['config'])
    else:
        return packer.pack(source_path, **options)