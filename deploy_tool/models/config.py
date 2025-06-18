"""Configuration models"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class PackageConfig:
    """Package configuration"""
    type: str  # Package type (user-defined)
    version: str  # Version string
    name: Optional[str] = None  # Package name
    description: Optional[str] = None  # Package description

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'type': self.type,
            'version': self.version
        }

        if self.name:
            data['name'] = self.name
        if self.description:
            data['description'] = self.description

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PackageConfig':
        """Create from dictionary"""
        return cls(
            type=data['type'],
            version=data['version'],
            name=data.get('name'),
            description=data.get('description')
        )


@dataclass
class SourceConfig:
    """Source configuration"""
    path: str  # Source path
    includes: List[str] = field(default_factory=lambda: ['*'])
    excludes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'path': self.path,
            'includes': self.includes,
            'excludes': self.excludes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceConfig':
        """Create from dictionary"""
        return cls(
            path=data['path'],
            includes=data.get('includes', ['*']),
            excludes=data.get('excludes', [])
        )


@dataclass
class CompressionConfig:
    """Compression configuration"""
    algorithm: str = 'gzip'  # Compression algorithm
    level: int = 6  # Compression level

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'algorithm': self.algorithm,
            'level': self.level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompressionConfig':
        """Create from dictionary"""
        return cls(
            algorithm=data.get('algorithm', 'gzip'),
            level=data.get('level', 6)
        )

    def get_extension(self) -> str:
        """Get compression extension"""
        extensions = {
            'gzip': '.gz',
            'gz': '.gz',
            'bzip2': '.bz2',
            'bz2': '.bz2',
            'xz': '.xz',
            'lzma': '.xz',
            'lz4': '.lz4',
            'none': '',
            '': ''
        }
        return extensions.get(self.algorithm.lower(), '.gz')


@dataclass
class OutputConfig:
    """Output configuration"""
    filename: str = '${package.type}-${package.version}.tar${compression.extension}'
    path: str = './dist/'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'filename': self.filename,
            'path': self.path
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OutputConfig':
        """Create from dictionary"""
        return cls(
            filename=data.get('filename', '${package.type}-${package.version}.tar${compression.extension}'),
            path=data.get('path', './dist/')
        )

    def format_filename(self, package: PackageConfig, compression: CompressionConfig) -> str:
        """Format output filename with substitutions"""
        import string

        # Create substitution mapping
        mapping = {
            'package.type': package.type,
            'package.version': package.version,
            'package.name': package.name or package.type,
            'compression.extension': compression.get_extension()
        }

        # Use safe substitute to avoid KeyError
        template = string.Template(self.filename)
        return template.safe_substitute(mapping)


@dataclass
class ValidationConfig:
    """Validation configuration"""
    checksum: List[str] = field(default_factory=lambda: ['sha256'])
    min_size: Optional[str] = None
    max_size: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'checksum': self.checksum
        }

        if self.min_size:
            data['min_size'] = self.min_size
        if self.max_size:
            data['max_size'] = self.max_size

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationConfig':
        """Create from dictionary"""
        return cls(
            checksum=data.get('checksum', ['sha256']),
            min_size=data.get('min_size'),
            max_size=data.get('max_size')
        )

    def get_min_size_bytes(self) -> Optional[int]:
        """Get minimum size in bytes"""
        return self._parse_size(self.min_size) if self.min_size else None

    def get_max_size_bytes(self) -> Optional[int]:
        """Get maximum size in bytes"""
        return self._parse_size(self.max_size) if self.max_size else None

    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse size string to bytes"""
        size_str = size_str.strip().upper()

        # Extract number and unit
        import re
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B)?$', size_str)
        if not match:
            raise ValueError(f"Invalid size format: {size_str}")

        number = float(match.group(1))
        unit = match.group(2) or 'B'

        # Convert to bytes
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024
        }

        return int(number * units.get(unit, 1))


@dataclass
class FullConfig:
    """Full package configuration"""
    package: PackageConfig
    source: SourceConfig
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'package': self.package.to_dict(),
            'source': self.source.to_dict(),
            'compression': self.compression.to_dict(),
            'output': self.output.to_dict(),
            'validation': self.validation.to_dict()
        }

        if self.metadata:
            data['metadata'] = self.metadata

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FullConfig':
        """Create from dictionary"""
        return cls(
            package=PackageConfig.from_dict(data['package']),
            source=SourceConfig.from_dict(data['source']),
            compression=CompressionConfig.from_dict(data.get('compression', {})),
            output=OutputConfig.from_dict(data.get('output', {})),
            validation=ValidationConfig.from_dict(data.get('validation', {})),
            metadata=data.get('metadata', {})
        )