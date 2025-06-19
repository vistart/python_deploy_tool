"""Local filesystem storage backend"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

import aiofiles
import aiofiles.os

from .base import StorageBackend
from ..constants import DEFAULT_CHUNK_SIZE
from ..core.path_resolver import PathResolver
from ..utils.hash_utils import calculate_file_hash_async


class FileSystemStorage(StorageBackend):
    """Local filesystem storage implementation"""

    def __init__(self, config: Dict[str, Any] = None, path_resolver: PathResolver = None):
        """
        Initialize filesystem storage

        Args:
            config: Configuration with optional 'base_path'
            path_resolver: Path resolver instance
        """
        super().__init__(config)
        self.path_resolver = path_resolver or PathResolver()

        # Base path for storage (defaults to project's dist directory)
        if 'base_path' in self.config:
            self.base_path = Path(self.config['base_path']).resolve()
        else:
            # Use get_dist_dir() method instead of dist_dir attribute
            self.base_path = self.path_resolver.get_dist_dir()

    async def _do_initialize(self) -> None:
        """Initialize filesystem storage"""
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, remote_path: str) -> Path:
        """Convert remote path to full local path"""
        # Remove leading slash if present
        remote_path = remote_path.lstrip('/')
        return self.base_path / remote_path

    async def upload(self,
                     local_path: Path,
                     remote_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Upload file to storage

        Args:
            local_path: Local file path
            remote_path: Remote storage path
            callback: Progress callback

        Returns:
            True if successful
        """
        if not local_path.exists():
            return False

        full_path = self._get_full_path(remote_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Get file size for progress
            file_size = local_path.stat().st_size
            bytes_copied = 0

            # Copy with progress
            async with aiofiles.open(local_path, 'rb') as src:
                async with aiofiles.open(full_path, 'wb') as dst:
                    while True:
                        chunk = await src.read(DEFAULT_CHUNK_SIZE)
                        if not chunk:
                            break
                        await dst.write(chunk)
                        bytes_copied += len(chunk)
                        if callback:
                            callback(bytes_copied, file_size)

            return True
        except Exception:
            return False

    async def download(self,
                       remote_path: str,
                       local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Download file from storage

        Args:
            remote_path: Remote storage path
            local_path: Local file path
            callback: Progress callback

        Returns:
            True if successful
        """
        full_path = self._get_full_path(remote_path)
        if not full_path.exists():
            return False

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Get file size for progress
            file_size = full_path.stat().st_size
            bytes_copied = 0

            # Copy with progress
            async with aiofiles.open(full_path, 'rb') as src:
                async with aiofiles.open(local_path, 'wb') as dst:
                    while True:
                        chunk = await src.read(DEFAULT_CHUNK_SIZE)
                        if not chunk:
                            break
                        await dst.write(chunk)
                        bytes_copied += len(chunk)
                        if callback:
                            callback(bytes_copied, file_size)

            return True
        except Exception:
            return False

    async def exists(self, remote_path: str) -> bool:
        """
        Check if file exists in storage

        Args:
            remote_path: Remote storage path

        Returns:
            True if exists
        """
        full_path = self._get_full_path(remote_path)
        return full_path.exists()

    async def delete(self, remote_path: str) -> bool:
        """
        Delete file from storage

        Args:
            remote_path: Remote storage path

        Returns:
            True if successful
        """
        full_path = self._get_full_path(remote_path)
        if not full_path.exists():
            return False

        try:
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()
            return True
        except Exception:
            return False

    async def list(self, prefix: str = "") -> List[str]:
        """
        List files in storage

        Args:
            prefix: Path prefix to filter results

        Returns:
            List of file paths
        """
        search_path = self._get_full_path(prefix)
        results = []

        if search_path.exists():
            if search_path.is_dir():
                # List all files recursively
                for item in search_path.rglob('*'):
                    if item.is_file():
                        # Get relative path from base
                        try:
                            rel_path = item.relative_to(self.base_path)
                            results.append(str(rel_path))
                        except ValueError:
                            pass
            elif search_path.is_file():
                # Single file
                try:
                    rel_path = search_path.relative_to(self.base_path)
                    results.append(str(rel_path))
                except ValueError:
                    pass

        return sorted(results)

    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata

        Args:
            remote_path: Remote storage path

        Returns:
            File metadata or None if not found
        """
        full_path = self._get_full_path(remote_path)
        if not full_path.exists():
            return None

        stat = full_path.stat()
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'is_dir': full_path.is_dir(),
            'checksum': await calculate_file_hash_async(full_path) if full_path.is_file() else None,
        }

    # Storage-specific methods
    async def get_free_space(self) -> int:
        """Get free space in bytes"""
        import shutil
        stat = shutil.disk_usage(self.base_path)
        return stat.free

    async def cleanup_old_files(self, days: int = 30) -> int:
        """
        Clean up files older than specified days

        Args:
            days: Number of days

        Returns:
            Number of files deleted
        """
        import time
        deleted = 0
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        for item in self.base_path.rglob('*'):
            if item.is_file():
                if item.stat().st_mtime < cutoff_time:
                    try:
                        item.unlink()
                        deleted += 1
                    except Exception:
                        pass

        return deleted