# deploy_tool/core/validation_engine.py
"""Validation engine for various validation operations"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..constants import (
    VERSION_PATTERN,
    COMPONENT_TYPE_PATTERN,
    MAX_COMPONENT_TYPE_LENGTH,
    MIN_FILE_SIZE,
    MAX_FILE_SIZE,
    RELEASE_VERSION_DATE_PATTERN,
    RELEASE_VERSION_SEMANTIC_PATTERN
)


@dataclass
class ValidationResult:
    """Validation result container"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add error message"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add warning message"""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add info message"""
        self.info.append(message)

    def add_success(self, message: str) -> None:
        """Add success info message"""
        self.info.append(f"✓ {message}")

    def merge(self, other: 'ValidationResult') -> None:
        """Merge another result into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)
        if not other.is_valid:
            self.is_valid = False

    def __str__(self) -> str:
        """String representation"""
        lines = []

        if self.errors:
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  ✗ {error}")

        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        if self.info:
            lines.append("Info:")
            for info in self.info:
                lines.append(f"  {info}")

        if self.is_valid and not self.errors and not self.warnings:
            lines.append("✓ All validations passed")

        return '\n'.join(lines)


class ValidationEngine:
    """Execute various validation operations"""

    def validate_version(self, version: str) -> ValidationResult:
        """
        Validate version string

        Args:
            version: Version string to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not version:
            result.add_error("Version cannot be empty")
            return result

        # Check semantic version pattern
        match = VERSION_PATTERN.match(version)
        if not match:
            result.add_error(
                f"Invalid version format: '{version}'. "
                "Expected format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]"
            )
            return result

        # Extract parts
        major = int(match.group('major'))
        minor = int(match.group('minor'))
        patch = int(match.group('patch'))

        # Add info about version
        result.add_info(f"Version: {major}.{minor}.{patch}")

        if match.group('prerelease'):
            result.add_info(f"Pre-release: {match.group('prerelease')}")

        if match.group('build'):
            result.add_info(f"Build: {match.group('build')}")

        return result

    def validate_component_type(self, component_type: str) -> ValidationResult:
        """
        Validate component type

        Args:
            component_type: Component type to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not component_type:
            result.add_error("Component type cannot be empty")
            return result

        if len(component_type) > MAX_COMPONENT_TYPE_LENGTH:
            result.add_error(
                f"Component type too long (max {MAX_COMPONENT_TYPE_LENGTH} characters)"
            )

        if not COMPONENT_TYPE_PATTERN.match(component_type):
            result.add_error(
                f"Invalid component type: '{component_type}'. "
                "Must start with a letter and contain only letters, numbers, hyphens, and underscores"
            )

        # Warn about conventions
        if component_type.upper() == component_type:
            result.add_warning("Component types are conventionally lowercase")

        if '_' in component_type and '-' in component_type:
            result.add_warning("Mixing underscores and hyphens is not recommended")

        return result

    def validate_release_version(self, version: str) -> ValidationResult:
        """
        Validate release version

        Args:
            version: Release version to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not version:
            result.add_error("Release version cannot be empty")
            return result

        # Check date pattern (YYYY.MM.DD)
        if RELEASE_VERSION_DATE_PATTERN.match(version):
            result.add_info(f"Date-based release version: {version}")
            # Validate date parts
            parts = version.split('.')
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])

            if year < 2020 or year > 2100:
                result.add_warning(f"Unusual year: {year}")

            if month < 1 or month > 12:
                result.add_error(f"Invalid month: {month}")

            if day < 1 or day > 31:
                result.add_error(f"Invalid day: {day}")

        # Check semantic pattern (v1.0.0)
        elif RELEASE_VERSION_SEMANTIC_PATTERN.match(version):
            result.add_info(f"Semantic release version: {version}")
        else:
            # Custom format, just warn
            result.add_warning(
                f"Non-standard release version format: {version}. "
                "Consider using YYYY.MM.DD or v1.0.0 format"
            )

        return result

    def validate_path(self, path: Path,
                      must_exist: bool = False,
                      must_be_file: bool = False,
                      must_be_dir: bool = False) -> ValidationResult:
        """
        Validate file/directory path

        Args:
            path: Path to validate
            must_exist: Whether path must exist
            must_be_file: Whether path must be a file
            must_be_dir: Whether path must be a directory

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Check existence
        if must_exist and not path.exists():
            result.add_error(f"Path does not exist: {path}")
            return result

        if path.exists():
            # Check type
            if must_be_file and not path.is_file():
                result.add_error(f"Path is not a file: {path}")

            if must_be_dir and not path.is_dir():
                result.add_error(f"Path is not a directory: {path}")

            # Check permissions
            if not os.access(path, os.R_OK):
                result.add_error(f"No read permission: {path}")

            # File-specific checks
            if path.is_file():
                size = path.stat().st_size
                if size < MIN_FILE_SIZE:
                    result.add_error(f"File is empty: {path}")
                elif size > MAX_FILE_SIZE:
                    result.add_error(
                        f"File too large ({size} bytes, max {MAX_FILE_SIZE} bytes)"
                    )

        return result

    def validate_config(self, config: Dict[str, Any],
                        schema: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate configuration dictionary

        Args:
            config: Configuration to validate
            schema: JSON schema (optional)

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Basic validation
        if not config:
            result.add_error("Configuration is empty")
            return result

        # Check required fields for package config
        if 'package' in config:
            package = config['package']

            # Required fields
            if not package.get('type'):
                result.add_error("Missing required field: package.type")
            else:
                type_result = self.validate_component_type(package['type'])
                result.merge(type_result)

            if not package.get('version'):
                result.add_error("Missing required field: package.version")
            else:
                version_result = self.validate_version(package['version'])
                result.merge(version_result)

        if 'source' in config:
            source = config['source']

            if not source.get('path'):
                result.add_error("Missing required field: source.path")

        # Schema validation if provided
        if schema:
            try:
                import jsonschema
                jsonschema.validate(config, schema)
                result.add_info("Configuration validates against schema")
            except jsonschema.ValidationError as e:
                result.add_error(f"Schema validation failed: {e.message}")
            except Exception as e:
                result.add_warning(f"Could not validate schema: {e}")

        return result

    def validate_manifest(self, manifest: Dict[str, Any]) -> ValidationResult:
        """
        Validate manifest structure

        Args:
            manifest: Manifest dictionary to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Check manifest version
        if not manifest.get('manifest_version'):
            result.add_error("Missing manifest version")

        # Check package info
        if 'package' not in manifest:
            result.add_error("Missing package information")
        else:
            package = manifest['package']
            for field in ['type', 'name', 'version', 'created_at']:
                if field not in package:
                    result.add_error(f"Missing package.{field}")

        # Check archive info
        if 'archive' not in manifest:
            result.add_error("Missing archive information")
        else:
            archive = manifest['archive']
            for field in ['filename', 'size', 'checksum']:
                if field not in archive:
                    result.add_error(f"Missing archive.{field}")

            # Check checksum format
            if 'checksum' in archive and isinstance(archive['checksum'], dict):
                if 'sha256' not in archive['checksum']:
                    result.add_warning("Missing SHA256 checksum")

        return result

    def validate_archive_integrity(self, archive_path: Path,
                                   expected_checksum: str,
                                   algorithm: str = 'sha256') -> ValidationResult:
        """
        Validate archive file integrity

        Args:
            archive_path: Path to archive file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm to use

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Check file exists
        if not archive_path.exists():
            result.add_error(f"Archive file not found: {archive_path}")
            return result

        # Calculate actual checksum
        import hashlib
        hash_func = hashlib.new(algorithm)

        try:
            with open(archive_path, 'rb') as f:
                while chunk := f.read(8192):
                    hash_func.update(chunk)

            actual_checksum = hash_func.hexdigest()

            if actual_checksum == expected_checksum:
                result.add_success(f"Archive integrity verified ({algorithm})")
            else:
                result.add_error(
                    f"Archive checksum mismatch: "
                    f"expected {expected_checksum}, got {actual_checksum}"
                )
        except Exception as e:
            result.add_error(f"Failed to calculate checksum: {e}")

        return result

    def validate_deployment(self, deploy_path: Path,
                            expected_files: List[str]) -> ValidationResult:
        """
        Validate deployment result

        Args:
            deploy_path: Deployment target path
            expected_files: List of expected files

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not deploy_path.exists():
            result.add_error(f"Deployment path does not exist: {deploy_path}")
            return result

        # Check expected files
        missing_files = []
        for expected_file in expected_files:
            file_path = deploy_path / expected_file
            if not file_path.exists():
                missing_files.append(expected_file)

        if missing_files:
            result.add_error(f"Missing files: {', '.join(missing_files)}")
        else:
            result.add_success(f"All {len(expected_files)} expected files present")

        # Check for extra files
        actual_files = set()
        for file_path in deploy_path.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(deploy_path)
                actual_files.add(str(rel_path))

        extra_files = actual_files - set(expected_files)
        if extra_files:
            result.add_warning(f"Extra files found: {', '.join(sorted(extra_files))}")

        return result


import os