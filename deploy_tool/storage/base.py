"""Storage backend abstract base class"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable


class StorageBackend(ABC):
    """Abstract base class for all storage backends"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize storage backend

        Args:
            config: Backend-specific configuration
        """
        self.config = config or {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize storage backend (e.g., establish connections)"""
        if not self._initialized:
            await self._do_initialize()
            self._initialized = True

    @abstractmethod
    async def _do_initialize(self) -> None:
        """Actual initialization logic to be implemented by subclasses"""
        pass

    @abstractmethod
    async def upload(self,
                     local_path: Path,
                     remote_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Upload file to storage

        Args:
            local_path: Local file path
            remote_path: Remote storage path
            callback: Progress callback (bytes_transferred, total_bytes)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def download(self,
                       remote_path: str,
                       local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Download file from storage

        Args:
            remote_path: Remote path in storage
            local_path: Local file path to save to
            callback: Progress callback (bytes_transferred, total_bytes)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def exists(self, remote_path: str) -> bool:
        """
        Check if file exists in storage

        Args:
            remote_path: Remote path to check

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    async def delete(self, remote_path: str) -> bool:
        """
        Delete file from storage

        Args:
            remote_path: Remote path to delete

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def list(self, prefix: str = "") -> List[str]:
        """
        List files in storage with given prefix

        Args:
            prefix: Path prefix to filter by

        Returns:
            List of file paths
        """
        pass

    @abstractmethod
    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata

        Args:
            remote_path: Remote path

        Returns:
            Metadata dictionary or None if not found
        """
        pass

    @abstractmethod
    def get_post_publish_instructions(self,
                                      release_version: str,
                                      published_path: Path) -> List[str]:
        """
        Get storage-specific post-publish instructions

        Args:
            release_version: Version that was published
            published_path: Local path where files were published

        Returns:
            List of instruction strings for the user
        """
        pass

    async def close(self) -> None:
        """Close storage backend connections"""
        if self._initialized:
            await self._do_close()
            self._initialized = False

    async def _do_close(self) -> None:
        """Actual cleanup logic to be implemented by subclasses"""
        pass

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()