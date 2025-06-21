# deploy_tool/storage/base.py
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
            remote_path: Remote storage path
            local_path: Local file path
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
            remote_path: Remote storage path

        Returns:
            True if exists
        """
        pass

    @abstractmethod
    async def delete(self, remote_path: str) -> bool:
        """
        Delete file from storage

        Args:
            remote_path: Remote storage path

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def list(self, prefix: str = "") -> List[str]:
        """
        List files in storage

        Args:
            prefix: Path prefix to filter results

        Returns:
            List of file paths
        """
        pass

    @abstractmethod
    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata

        Args:
            remote_path: Remote storage path

        Returns:
            File metadata or None if not found
        """
        pass

    async def upload_directory(self,
                               local_dir: Path,
                               remote_prefix: str,
                               callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        Upload entire directory to storage

        Args:
            local_dir: Local directory path
            remote_prefix: Remote path prefix
            callback: Progress callback (filename, bytes_transferred, total_bytes)

        Returns:
            True if all uploads successful
        """
        if not local_dir.is_dir():
            raise ValueError(f"Not a directory: {local_dir}")

        success = True
        for local_file in local_dir.rglob("*"):
            if local_file.is_file():
                relative_path = local_file.relative_to(local_dir)
                remote_path = f"{remote_prefix}/{relative_path}".replace("\\", "/")

                file_callback = None
                if callback:
                    file_callback = lambda transferred, total: callback(
                        str(relative_path), transferred, total
                    )

                if not await self.upload(local_file, remote_path, file_callback):
                    success = False

        return success

    async def download_directory(self,
                                 remote_prefix: str,
                                 local_dir: Path,
                                 callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        Download directory from storage

        Args:
            remote_prefix: Remote path prefix
            local_dir: Local directory path
            callback: Progress callback (filename, bytes_transferred, total_bytes)

        Returns:
            True if all downloads successful
        """
        # List all files with prefix
        files = await self.list(remote_prefix)

        success = True
        for remote_path in files:
            # Calculate local path
            relative_path = remote_path[len(remote_prefix):].lstrip("/")
            local_path = local_dir / relative_path

            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            file_callback = None
            if callback:
                file_callback = lambda transferred, total: callback(
                    relative_path, transferred, total
                )

            if not await self.download(remote_path, local_path, file_callback):
                success = False

        return success

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