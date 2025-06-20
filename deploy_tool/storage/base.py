"""Storage backend base interface"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncIterator
import asyncio


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize storage backend

        Args:
            config: Backend-specific configuration
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate backend configuration"""
        pass

    @abstractmethod
    async def upload(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Upload a file to storage

        Args:
            local_path: Local file path
            remote_path: Remote destination path
            progress_callback: Optional callback for progress updates

        Returns:
            Upload result metadata
        """
        pass

    @abstractmethod
    async def download(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Download a file from storage

        Args:
<<<<<<< Updated upstream
            remote_path: Remote path in storage
            local_path: Local file path to save to
            callback: Progress callback (bytes_transferred, total_bytes)
=======
            remote_path: Remote source path
            local_path: Local destination path
            progress_callback: Optional callback for progress updates
>>>>>>> Stashed changes

        Returns:
            Download result metadata
        """
        pass

    @abstractmethod
    async def exists(self, remote_path: str) -> bool:
        """Check if a file exists in storage

        Args:
<<<<<<< Updated upstream
            remote_path: Remote path to check

        Returns:
            True if file exists
=======
            remote_path: Remote file path

        Returns:
            True if file exists, False otherwise
>>>>>>> Stashed changes
        """
        pass

    @abstractmethod
    async def delete(self, remote_path: str) -> bool:
        """Delete a file from storage

        Args:
<<<<<<< Updated upstream
            remote_path: Remote path to delete
=======
            remote_path: Remote file path
>>>>>>> Stashed changes

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
<<<<<<< Updated upstream
    async def list(self, prefix: str = "") -> List[str]:
        """
        List files in storage with given prefix

        Args:
            prefix: Path prefix to filter by
=======
    async def list_objects(
        self,
        prefix: str = "",
        recursive: bool = True,
        max_keys: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List objects in storage

        Args:
            prefix: Filter objects by prefix
            recursive: List recursively
            max_keys: Maximum number of objects to return
>>>>>>> Stashed changes

        Returns:
            List of object metadata
        """
        pass

    @abstractmethod
    async def get_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for an object

        Args:
<<<<<<< Updated upstream
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
=======
            remote_path: Remote file path

        Returns:
            Object metadata
        """
        pass

    async def upload_directory(
        self,
        local_dir: str,
        remote_prefix: str,
        exclude_patterns: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Upload a directory to storage

        Args:
            local_dir: Local directory path
            remote_prefix: Remote destination prefix
            exclude_patterns: Patterns to exclude
            progress_callback: Optional callback for progress updates

        Returns:
            List of upload results
        """
        local_path = Path(local_dir)
        if not local_path.is_dir():
            raise ValueError(f"Not a directory: {local_dir}")

        results = []
        tasks = []

        # Collect files to upload
        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                # Check exclude patterns
                if exclude_patterns and any(
                    file_path.match(pattern) for pattern in exclude_patterns
                ):
                    continue

                # Calculate relative path
                rel_path = file_path.relative_to(local_path)
                remote_path = f"{remote_prefix}/{rel_path}".replace("\\", "/")

                # Create upload task
                task = self.upload(
                    str(file_path),
                    remote_path,
                    progress_callback
                )
                tasks.append(task)

        # Execute uploads
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def download_directory(
        self,
        remote_prefix: str,
        local_dir: str,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Download a directory from storage

        Args:
            remote_prefix: Remote source prefix
            local_dir: Local destination directory
            progress_callback: Optional callback for progress updates

        Returns:
            List of download results
        """
        local_path = Path(local_dir)
        local_path.mkdir(parents=True, exist_ok=True)

        results = []

        # List objects with prefix
        objects = await self.list_objects(prefix=remote_prefix)

        # Download each object
        tasks = []
        for obj in objects:
            remote_path = obj.get("key") or obj.get("path")
            if not remote_path:
                continue

            # Calculate local path
            rel_path = remote_path[len(remote_prefix):].lstrip("/")
            local_file_path = local_path / rel_path

            # Ensure parent directory exists
            local_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create download task
            task = self.download(
                remote_path,
                str(local_file_path),
                progress_callback
            )
            tasks.append(task)

        # Execute downloads
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def copy(
        self,
        source_path: str,
        dest_path: str
    ) -> Dict[str, Any]:
        """Copy an object within storage

        Args:
            source_path: Source path
            dest_path: Destination path

        Returns:
            Copy result metadata
        """
        # Default implementation: download and re-upload
        # Subclasses can override with more efficient methods
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await self.download(source_path, tmp_path)
            result = await self.upload(tmp_path, dest_path)
            return result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def move(
        self,
        source_path: str,
        dest_path: str
    ) -> Dict[str, Any]:
        """Move an object within storage

        Args:
            source_path: Source path
            dest_path: Destination path

        Returns:
            Move result metadata
        """
        # Copy then delete
        result = await self.copy(source_path, dest_path)
        await self.delete(source_path)
        return result

    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get public URL for an object (if supported)

        Args:
            remote_path: Remote file path

        Returns:
            Public URL or None if not supported
        """
        return None

    def get_signed_url(
        self,
        remote_path: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """Get signed URL for temporary access (if supported)

        Args:
            remote_path: Remote file path
            expires_in: Expiration time in seconds
            method: HTTP method (GET, PUT, etc.)

        Returns:
            Signed URL or None if not supported
        """
        return None
>>>>>>> Stashed changes

    async def close(self) -> None:
        """Close storage connections"""
        pass

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()