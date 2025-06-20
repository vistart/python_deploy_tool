"""Storage manager for handling multiple storage backends"""

from typing import Dict, Optional, Any
import asyncio

from ..storage import StorageBackend, StorageFactory
from ..models.config import Config, PublishTarget
from ..cli.utils.output import console
from ..constants import EMOJI_WARNING


class StorageManager:
    """Manages multiple storage backend instances"""

    def __init__(self, config: Config):
        """Initialize storage manager

        Args:
            config: Project configuration
        """
        self.config = config
        self._storages: Dict[str, StorageBackend] = {}
        self._storage_configs: Dict[str, PublishTarget] = {}

        # Load all configured targets
        for name, target in config.publish_targets.items():
            if target.enabled:
                self._storage_configs[name] = target

    def get_storage(self, name: str) -> StorageBackend:
        """Get or create storage backend instance

        Args:
            name: Storage target name

        Returns:
            Storage backend instance

        Raises:
            ValueError: If storage target not found or disabled
        """
        # Check if already created
        if name in self._storages:
            return self._storages[name]

        # Check if target exists
        if name not in self._storage_configs:
            raise ValueError(f"Storage target '{name}' not found or disabled")

        # Create storage backend
        target = self._storage_configs[name]

        try:
            storage = StorageFactory.create_from_config(target)
            self._storages[name] = storage
            return storage

        except Exception as e:
            raise ValueError(f"Failed to create storage backend '{name}': {str(e)}")

    async def test_storage(self, name: str) -> bool:
        """Test storage backend connectivity

        Args:
            name: Storage target name

        Returns:
            True if connection successful
        """
        try:
            storage = self.get_storage(name)

            # Simple connectivity test - try to list with non-existent prefix
            test_prefix = f"__deploy_tool_test_{name}__"
            await storage.list_objects(prefix=test_prefix, max_keys=1)

            return True

        except Exception as e:
            console.print(f"{EMOJI_WARNING} Storage test failed for '{name}': {str(e)}")
            return False

    async def test_all_storages(self) -> Dict[str, bool]:
        """Test all configured storage backends

        Returns:
            Dict mapping storage name to test result
        """
        results = {}

        # Test each storage in parallel
        tasks = []
        for name in self._storage_configs:
            task = self.test_storage(name)
            tasks.append((name, task))

        for name, task in tasks:
            try:
                results[name] = await task
            except Exception:
                results[name] = False

        return results

    def list_storages(self) -> Dict[str, Dict[str, Any]]:
        """List all configured storage targets

        Returns:
            Dict of storage information
        """
        storages = {}

        for name, target in self._storage_configs.items():
            storages[name] = {
                "type": target.type,
                "enabled": target.enabled,
                "display_info": target.get_display_info(),
                "is_remote": target.is_remote,
                "requires_transfer": target.requires_transfer,
                "description": target.description
            }

        return storages

    def get_storage_config(self, name: str) -> Optional[PublishTarget]:
        """Get storage target configuration

        Args:
            name: Storage target name

        Returns:
            PublishTarget configuration or None
        """
        return self._storage_configs.get(name)

    def get_enabled_storages(self) -> list[str]:
        """Get list of enabled storage names

        Returns:
            List of enabled storage target names
        """
        return list(self._storage_configs.keys())

    def get_default_storages(self) -> list[str]:
        """Get list of default storage names

        Returns:
            List of default storage target names
        """
        defaults = []
        for name in self.config.default_targets:
            if name in self._storage_configs:
                defaults.append(name)
        return defaults

    def get_remote_storages(self) -> list[str]:
        """Get list of remote storage names

        Returns:
            List of remote storage target names
        """
        remotes = []
        for name, target in self._storage_configs.items():
            if target.is_remote:
                remotes.append(name)
        return remotes

    def get_filesystem_storages(self) -> list[str]:
        """Get list of filesystem storage names

        Returns:
            List of filesystem storage target names
        """
        filesystems = []
        for name, target in self._storage_configs.items():
            if not target.is_remote:
                filesystems.append(name)
        return filesystems

    async def close_all(self) -> None:
        """Close all storage connections"""
        tasks = []

        for storage in self._storages.values():
            tasks.append(storage.close())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._storages.clear()

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close_all()