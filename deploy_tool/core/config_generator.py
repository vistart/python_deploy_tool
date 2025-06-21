# deploy_tool/core/config_generator.py
"""Configuration generator for intelligent config creation"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import yaml
from rich.console import Console
from rich.prompt import Prompt

from .path_resolver import PathResolver
from ..constants import (
    DEFAULT_COMPRESSION_ALGORITHM,
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_EXCLUDE_PATTERNS,
)


@dataclass
class FileTypeStats:
    """File type statistics"""
    binary_ratio: float
    text_ratio: float
    total_files: int
    total_size: int
    extensions: Counter


class ConfigGenerator:
    """Intelligent configuration generator"""

    # Binary file extensions
    BINARY_EXTENSIONS = {
        '.pth', '.pt', '.h5', '.hdf5', '.onnx', '.pb', '.tflite',
        '.pkl', '.pickle', '.npy', '.npz', '.model', '.weights',
        '.bin', '.dat', '.db', '.sqlite', '.parquet', '.arrow',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.webp',
        '.mp3', '.mp4', '.avi', '.mkv', '.wav', '.flac',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.so', '.dll', '.dylib', '.exe', '.app',
    }

    # Text file extensions
    TEXT_EXTENSIONS = {
        '.txt', '.md', '.rst', '.json', '.yaml', '.yml', '.xml',
        '.ini', '.conf', '.cfg', '.toml', '.properties',
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp',
        '.css', '.html', '.htm', '.vue', '.jsx', '.tsx',
        '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
        '.log', '.csv', '.tsv',
    }

    def __init__(self, path_resolver: Optional[PathResolver] = None):
        self.path_resolver = path_resolver or PathResolver()
        self.console = Console()

    def generate_config(self,
                        path: Path,
                        options: Dict[str, Any]) -> Tuple[Dict[str, Any], Path]:
        """
        Generate configuration based on directory content

        Args:
            path: Source path
            options: User options

        Returns:
            Tuple of (config_dict, config_path)
        """
        # Get package type
        package_type = options.get('type')
        if not package_type:
            package_type = self.prompt_for_type()

        # Analyze directory
        self.console.print("[cyan]Analyzing directory structure...[/cyan]")
        stats = self.analyze_directory(path)

        # Generate config
        config = self.get_smart_defaults(path, stats)

        # Set package info
        config['package']['type'] = package_type
        config['package']['name'] = self.infer_package_name(path, package_type)
        config['package']['version'] = options.get('version') or self.suggest_version()

        # Set source info
        config['source']['path'] = self.path_resolver.get_relative_to_root(path)
        config['source']['includes'] = self.detect_file_patterns(path, stats)

        # Apply user options
        if 'output' in options:
            config['output']['path'] = options['output']

        if 'compress' in options:
            config['compression']['algorithm'] = options['compress']

        if 'level' in options:
            config['compression']['level'] = options['level']

        # Save config if requested
        config_path = None
        if options.get('save_config', True):
            config_path = self.save_config(config, path, package_type)

        return config, config_path

    def get_smart_defaults(self, path: Path, stats: Optional[FileTypeStats] = None) -> Dict[str, Any]:
        """
        Get smart default configuration

        Args:
            path: Source path
            stats: File type statistics

        Returns:
            Configuration dictionary
        """
        if stats is None:
            stats = self.analyze_directory(path)

        config = {
            'package': {
                'type': '',  # To be filled
                'name': '',  # To be filled
                'version': '',  # To be filled
                'description': '',
            },
            'source': {
                'path': '',  # To be filled
                'includes': ['*'],  # To be updated
                'excludes': list(DEFAULT_EXCLUDE_PATTERNS),
            },
            'compression': {
                'algorithm': DEFAULT_COMPRESSION_ALGORITHM,
                'level': DEFAULT_COMPRESSION_LEVEL,
            },
            'output': {
                'filename': '${package.type}-${package.version}.tar${compression.extension}',
                'path': './dist/',
            },
            'validation': {
                'checksum': ['sha256'],
            }
        }

        # Adjust compression based on file types
        if stats.binary_ratio > 0.8:
            # Mostly binary files, use lower compression
            config['compression']['level'] = 3
            config['compression']['algorithm'] = 'gzip'  # Fast
        elif stats.text_ratio > 0.8:
            # Mostly text files, use higher compression
            config['compression']['level'] = 9
            config['compression']['algorithm'] = 'xz'  # Best compression
        else:
            # Mixed content, use balanced settings
            config['compression']['level'] = 6
            config['compression']['algorithm'] = 'gzip'

        # Add metadata
        config['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'generated_by': 'deploy-tool',
            'auto_generated': True,
        }

        return config

    def analyze_directory(self, path: Path) -> FileTypeStats:
        """
        Analyze directory file types

        Args:
            path: Directory path

        Returns:
            FileTypeStats object
        """
        binary_count = 0
        text_count = 0
        total_count = 0
        total_size = 0
        extensions = Counter()

        if path.is_file():
            # Single file
            total_count = 1
            total_size = path.stat().st_size
            ext = path.suffix.lower()
            extensions[ext] = 1

            if ext in self.BINARY_EXTENSIONS:
                binary_count = 1
            elif ext in self.TEXT_EXTENSIONS:
                text_count = 1
        else:
            # Directory
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    # Skip hidden and cache files
                    if any(part.startswith('.') for part in file_path.parts[len(path.parts):]):
                        continue

                    total_count += 1
                    total_size += file_path.stat().st_size

                    ext = file_path.suffix.lower()
                    extensions[ext] += 1

                    if ext in self.BINARY_EXTENSIONS:
                        binary_count += 1
                    elif ext in self.TEXT_EXTENSIONS:
                        text_count += 1
                    else:
                        # Try to detect by reading first bytes
                        try:
                            with open(file_path, 'rb') as f:
                                chunk = f.read(512)
                                if b'\0' in chunk:
                                    binary_count += 1
                                else:
                                    text_count += 1
                        except:
                            # Assume binary if can't read
                            binary_count += 1

        return FileTypeStats(
            binary_ratio=binary_count / total_count if total_count > 0 else 0,
            text_ratio=text_count / total_count if total_count > 0 else 0,
            total_files=total_count,
            total_size=total_size,
            extensions=extensions
        )

    def detect_file_patterns(self, path: Path, stats: FileTypeStats) -> List[str]:
        """
        Detect file patterns to include

        Args:
            path: Source path
            stats: File type statistics

        Returns:
            List of include patterns
        """
        if path.is_file():
            # Single file, include by name
            return [path.name]

        patterns = []

        # Include by extensions
        for ext, count in stats.extensions.most_common():
            if ext and count >= 1:  # Include all extensions
                patterns.append(f'*{ext}')

        # Include common config files by name
        config_files = ['config.json', 'config.yaml', 'settings.json', 'params.json']
        for config_file in config_files:
            if (path / config_file).exists():
                patterns.append(config_file)

        # Include directories
        subdirs = set()
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                subdirs.add(f"{item.name}/")

        patterns.extend(sorted(subdirs))

        # If no specific patterns, include everything
        if not patterns:
            patterns = ['*']

        return sorted(set(patterns))

    def prompt_for_type(self) -> str:
        """Interactive prompt for package type"""
        self.console.print("\n[yellow]Package type is required[/yellow]")
        self.console.print("This is a user-defined identifier for your package type.")
        self.console.print("Examples: model, config, data, runtime, etc.")

        type_name = Prompt.ask(
            "Enter package type",
            default="package"
        )

        return type_name

    def infer_package_name(self, path: Path, package_type: str) -> str:
        """
        Infer package name from path and type

        Args:
            path: Source path
            package_type: Package type

        Returns:
            Inferred package name
        """
        if path.is_file():
            # Use file name without extension
            base_name = path.stem
        else:
            # Use directory name
            base_name = path.name

        # Clean up name
        base_name = base_name.replace(' ', '_').replace('-', '_').lower()

        # Combine with type if not redundant
        if package_type.lower() not in base_name.lower():
            return f"{base_name}_{package_type}"
        else:
            return base_name

    def suggest_version(self) -> str:
        """Suggest version number"""
        # Look for existing versions
        manifests_dir = self.path_resolver.get_manifests_dir()

        if manifests_dir.exists():
            # Find highest version
            versions = []
            for manifest_file in manifests_dir.glob("*.manifest.json"):
                try:
                    # Extract version from filename
                    parts = manifest_file.stem.split('-')
                    if len(parts) >= 2:
                        version = parts[-1]
                        if version.count('.') >= 2:
                            versions.append(version)
                except:
                    continue

            if versions:
                # Increment patch version
                from packaging.version import parse
                latest = max(versions, key=lambda v: parse(v))
                parts = latest.split('.')
                try:
                    parts[-1] = str(int(parts[-1]) + 1)
                    return '.'.join(parts)
                except:
                    pass

        # Default version
        return "0.1.0"

    def save_config(self, config: Dict[str, Any],
                    source_path: Path,
                    package_type: str) -> Path:
        """
        Save configuration to file

        Args:
            config: Configuration dictionary
            source_path: Source path
            package_type: Package type

        Returns:
            Path to saved config file
        """
        # Determine config filename
        if source_path.is_file():
            config_name = f"{source_path.stem}-{package_type}.yaml"
        else:
            config_name = f"{package_type}.yaml"

        # Check if auto-generated config exists
        auto_config_name = f"{package_type}-auto.yaml"

        config_path = self.path_resolver.get_config_path(auto_config_name)

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Add header
        yaml_content = f"""# Deploy Tool Package Configuration
# Auto-generated at: {datetime.now().isoformat()}
# Source: {self.path_resolver.get_relative_to_root(source_path)}

"""

        # Write config
        yaml_content += yaml.dump(config, default_flow_style=False, sort_keys=False)

        config_path.write_text(yaml_content)

        self.console.print(f"[green]✓ Configuration saved to: {config_path}[/green]")

        return config_path

    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from file

        Args:
            config_path: Configuration file path

        Returns:
            Configuration dictionary
        """
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration

        Args:
            config: Configuration dictionary

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check required fields
        if 'package' not in config:
            errors.append("Missing 'package' section")
        else:
            if not config['package'].get('type'):
                errors.append("Missing package.type")
            if not config['package'].get('version'):
                errors.append("Missing package.version")

        if 'source' not in config:
            errors.append("Missing 'source' section")
        else:
            if not config['source'].get('path'):
                errors.append("Missing source.path")

        return errors

    def update_config_version(self, config: Dict[str, Any], new_version: str) -> Dict[str, Any]:
        """
        Update version in configuration

        Args:
            config: Configuration dictionary
            new_version: New version string

        Returns:
            Updated configuration
        """
        if 'package' not in config:
            config['package'] = {}

        config['package']['version'] = new_version

        # Update metadata
        if 'metadata' not in config:
            config['metadata'] = {}

        config['metadata']['updated_at'] = datetime.now().isoformat()
        config['metadata']['auto_generated'] = False

        return config