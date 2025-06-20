"""Configuration management service"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from ..models.config import Config, PublishTarget
from ..models.result import Result, OperationStatus
from ..core.storage_manager import StorageManager
from ..utils.output import console
from ..constants import (
    ErrorCode,
    StorageType,
    PROJECT_CONFIG_FILE,
    EMOJI_SUCCESS,
    EMOJI_ERROR,
    EMOJI_WARNING
)


class ConfigService:
    """Service for managing project configuration"""

    def __init__(self, project_root: Path):
        """Initialize config service

        Args:
            project_root: Project root directory
        """
        self.project_root = project_root
        self.config_path = project_root / PROJECT_CONFIG_FILE
        self._config: Optional[Config] = None

    @property
    def config(self) -> Config:
        """Get current configuration (lazy load)"""
        if self._config is None:
            self.load_config()
        return self._config

    def load_config(self) -> Config:
        """Load configuration from file

        Returns:
            Loaded configuration
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        # Expand environment variables in the file
        with open(self.config_path, 'r') as f:
            content = f.read()

        # Simple environment variable expansion
        content = os.path.expandvars(content)

        # Parse YAML
        data = yaml.safe_load(content)

        # Create Config object
        self._config = Config.from_dict(data)

        return self._config

    def save_config(self, config: Optional[Config] = None) -> None:
        """Save configuration to file

        Args:
            config: Configuration to save (uses current if not provided)
        """
        if config:
            self._config = config

        if not self._config:
            raise ValueError("No configuration to save")

        # Create backup
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix('.yaml.bak')
            shutil.copy2(self.config_path, backup_path)

        # Convert to dict and save
        data = self._config.to_dict()

        with open(self.config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"{EMOJI_SUCCESS} Configuration saved to {self.config_path}")

    def add_target(
            self,
            name: str,
            target_type: str,
            **kwargs
    ) -> Result:
        """Add a new publish target

        Args:
            name: Target name
            target_type: Target type (filesystem, bos, s3)
            **kwargs: Target-specific configuration

        Returns:
            Result of the operation
        """
        result = Result(status=OperationStatus.IN_PROGRESS)

        try:
            # Validate target type
            try:
                storage_type = StorageType(target_type)
            except ValueError:
                result.add_error(
                    ErrorCode.CONFIG_FORMAT_ERROR,
                    f"Invalid target type: {target_type}"
                )
                result.complete(OperationStatus.FAILED)
                return result

            # Check if target already exists
            if self.config.get_target(name):
                result.add_warning(f"Target '{name}' already exists, updating configuration")

            # Create target based on type
            if storage_type == StorageType.FILESYSTEM:
                target = PublishTarget(
                    name=name,
                    type=target_type,
                    path=kwargs.get('path'),
                    description=kwargs.get('description')
                )
            elif storage_type == StorageType.BOS:
                target = PublishTarget(
                    name=name,
                    type=target_type,
                    bos_endpoint=kwargs.get('endpoint'),
                    bos_bucket=kwargs.get('bucket'),
                    bos_access_key=kwargs.get('access_key'),
                    bos_secret_key=kwargs.get('secret_key'),
                    description=kwargs.get('description')
                )
            elif storage_type == StorageType.S3:
                target = PublishTarget(
                    name=name,
                    type=target_type,
                    s3_region=kwargs.get('region'),
                    s3_bucket=kwargs.get('bucket'),
                    s3_access_key=kwargs.get('access_key'),
                    s3_secret_key=kwargs.get('secret_key'),
                    description=kwargs.get('description')
                )
            else:
                result.add_error(
                    ErrorCode.CONFIG_FORMAT_ERROR,
                    f"Unsupported target type: {target_type}"
                )
                result.complete(OperationStatus.FAILED)
                return result

            # Add to config
            self.config.add_target(target)

            # Save config
            self.save_config()

            result.message = f"Successfully added target '{name}'"
            result.complete(OperationStatus.SUCCESS)

        except Exception as e:
            result.add_error(
                ErrorCode.CONFIG_FORMAT_ERROR,
                f"Failed to add target: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)

        return result

    def update_target(
            self,
            name: str,
            **kwargs
    ) -> Result:
        """Update an existing publish target

        Args:
            name: Target name
            **kwargs: Fields to update

        Returns:
            Result of the operation
        """
        result = Result(status=OperationStatus.IN_PROGRESS)

        try:
            # Get existing target
            target = self.config.get_target(name)
            if not target:
                result.add_error(
                    ErrorCode.COMPONENT_NOT_FOUND,
                    f"Target '{name}' not found"
                )
                result.complete(OperationStatus.FAILED)
                return result

            # Update fields
            for key, value in kwargs.items():
                if hasattr(target, key):
                    setattr(target, key, value)
                elif key in ['endpoint', 'bucket', 'access_key', 'secret_key', 'region']:
                    # Handle storage-specific fields
                    if target.storage_type == StorageType.BOS:
                        setattr(target, f"bos_{key}", value)
                    elif target.storage_type == StorageType.S3:
                        setattr(target, f"s3_{key}", value)
                else:
                    result.add_warning(f"Unknown field: {key}")

            # Save config
            self.save_config()

            result.message = f"Successfully updated target '{name}'"
            result.complete(OperationStatus.SUCCESS)

        except Exception as e:
            result.add_error(
                ErrorCode.CONFIG_FORMAT_ERROR,
                f"Failed to update target: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)

        return result

    def remove_target(self, name: str) -> Result:
        """Remove a publish target

        Args:
            name: Target name

        Returns:
            Result of the operation
        """
        result = Result(status=OperationStatus.IN_PROGRESS)

        try:
            if self.config.remove_target(name):
                self.save_config()
                result.message = f"Successfully removed target '{name}'"
                result.complete(OperationStatus.SUCCESS)
            else:
                result.add_error(
                    ErrorCode.COMPONENT_NOT_FOUND,
                    f"Target '{name}' not found"
                )
                result.complete(OperationStatus.FAILED)

        except Exception as e:
            result.add_error(
                ErrorCode.CONFIG_FORMAT_ERROR,
                f"Failed to remove target: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)

        return result

    def list_targets(self) -> List[Dict[str, Any]]:
        """List all configured targets

        Returns:
            List of target information
        """
        targets = []

        for name, target in self.config.publish_targets.items():
            info = {
                "name": name,
                "type": target.type,
                "enabled": target.enabled,
                "description": target.description,
                "display_info": target.get_display_info()
            }

            # Add status info
            if name in self.config.default_targets:
                info["is_default"] = True

            if name in self.config.deploy.source_priority:
                priority = self.config.deploy.source_priority.index(name) + 1
                info["deploy_priority"] = priority

            targets.append(info)

        return targets

    async def test_target(
            self,
            name: str,
            storage_manager: StorageManager
    ) -> Result:
        """Test connectivity to a target

        Args:
            name: Target name
            storage_manager: Storage manager instance

        Returns:
            Result of the test
        """
        result = Result(status=OperationStatus.IN_PROGRESS)

        try:
            # Get target
            target = self.config.get_target(name)
            if not target:
                result.add_error(
                    ErrorCode.COMPONENT_NOT_FOUND,
                    f"Target '{name}' not found"
                )
                result.complete(OperationStatus.FAILED)
                return result

            # Get storage backend
            storage = storage_manager.get_storage(name)

            # Test based on type
            if target.storage_type == StorageType.FILESYSTEM:
                # Test filesystem access
                path = Path(target.path)
                if not path.exists():
                    result.add_error(
                        ErrorCode.SOURCE_NOT_FOUND,
                        f"Path does not exist: {path}"
                    )
                    result.complete(OperationStatus.FAILED)
                elif not os.access(path, os.W_OK):
                    result.add_error(
                        ErrorCode.PERMISSION_DENIED,
                        f"No write permission: {path}"
                    )
                    result.complete(OperationStatus.FAILED)
                else:
                    result.message = f"Filesystem target is accessible: {path}"
                    result.complete(OperationStatus.SUCCESS)

            else:
                # Test remote storage
                console.print(f"Testing connection to {target.get_display_info()}...")

                # Try to list objects (lightweight test)
                test_prefix = f"deploy-tool-test-{datetime.utcnow().timestamp()}"
                await storage.list_objects(test_prefix, max_keys=1)

                result.message = f"Successfully connected to {target.get_display_info()}"
                result.complete(OperationStatus.SUCCESS)

        except Exception as e:
            result.add_error(
                ErrorCode.STORAGE_CONNECTION_FAILED,
                f"Connection test failed: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)

        return result

    def set_default_targets(self, target_names: List[str]) -> Result:
        """Set default publish targets

        Args:
            target_names: List of target names

        Returns:
            Result of the operation
        """
        result = Result(status=OperationStatus.IN_PROGRESS)

        try:
            # Validate all targets exist
            for name in target_names:
                if not self.config.get_target(name):
                    result.add_error(
                        ErrorCode.COMPONENT_NOT_FOUND,
                        f"Target '{name}' not found"
                    )
                    result.complete(OperationStatus.FAILED)
                    return result

            # Update default targets
            self.config.default_targets = target_names

            # Save config
            self.save_config()

            result.message = f"Set default targets: {', '.join(target_names)}"
            result.complete(OperationStatus.SUCCESS)

        except Exception as e:
            result.add_error(
                ErrorCode.CONFIG_FORMAT_ERROR,
                f"Failed to set default targets: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)

        return result

    def set_deploy_priority(self, target_names: List[str]) -> Result:
        """Set deployment source priority

        Args:
            target_names: Ordered list of target names

        Returns:
            Result of the operation
        """
        result = Result(status=OperationStatus.IN_PROGRESS)

        try:
            # Validate all targets exist
            for name in target_names:
                if not self.config.get_target(name):
                    result.add_error(
                        ErrorCode.COMPONENT_NOT_FOUND,
                        f"Target '{name}' not found"
                    )
                    result.complete(OperationStatus.FAILED)
                    return result

            # Update source priority
            self.config.deploy.source_priority = target_names

            # Save config
            self.save_config()

            result.message = f"Set deployment priority: {' -> '.join(target_names)}"
            result.complete(OperationStatus.SUCCESS)

        except Exception as e:
            result.add_error(
                ErrorCode.CONFIG_FORMAT_ERROR,
                f"Failed to set deployment priority: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)

        return result