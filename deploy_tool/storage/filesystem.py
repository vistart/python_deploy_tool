"""Local filesystem storage backend"""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

import aiofiles
import aiofiles.os

from .base import StorageBackend
from ..core.path_resolver import PathResolver
from ..utils.hash_utils import calculate_file_hash_async
from ..constants import DEFAULT_CHUNK_SIZE


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
            self.base_path = self.path_resolver.dist_dir

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
        """Upload file to filesystem storage"""
        try:
            await self.initialize()

            local_path = Path(local_path)
            if not local_path.exists():
                return False

            full_path = self._get_full_path(remote_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Get file size for progress
            total_size = local_path.stat().st_size
            bytes_transferred = 0

            # Copy with progress
            async with aiofiles.open(local_path, 'rb') as src:
                async with aiofiles.open(full_path, 'wb') as dst:
                    while True:
                        chunk = await src.read(DEFAULT_CHUNK_SIZE)
                        if not chunk:
                            break

                        await dst.write(chunk)
                        bytes_transferred += len(chunk)

                        if callback:
                            callback(bytes_transferred, total_size)

            return True

        except Exception as e:
            import logging
            logging.error(f"Upload failed: {e}")
            return False

    async def download(self,
                       remote_path: str,
                       local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download file from filesystem storage"""
        try:
            await self.initialize()

            full_path = self._get_full_path(remote_path)
            if not full_path.exists():
                return False

            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Get file size for progress
            total_size = full_path.stat().st_size
            bytes_transferred = 0

            # Copy with progress
            async with aiofiles.open(full_path, 'rb') as src:
                async with aiofiles.open(local_path, 'wb') as dst:
                    while True:
                        chunk = await src.read(DEFAULT_CHUNK_SIZE)
                        if not chunk:
                            break

                        await dst.write(chunk)
                        bytes_transferred += len(chunk)

                        if callback:
                            callback(bytes_transferred, total_size)

            return True

        except Exception as e:
            import logging
            logging.error(f"Download failed: {e}")
            return False

    async def exists(self, remote_path: str) -> bool:
        """Check if file exists"""
        await self.initialize()
        full_path = self._get_full_path(remote_path)
        return full_path.exists()

    async def delete(self, remote_path: str) -> bool:
        """Delete file"""
        try:
            await self.initialize()
            full_path = self._get_full_path(remote_path)

            if full_path.exists():
                if full_path.is_dir():
                    shutil.rmtree(full_path)
                else:
                    full_path.unlink()
                return True

            return False

        except Exception as e:
            import logging
            logging.error(f"Delete failed: {e}")
            return False

    async def list(self, prefix: str = "") -> List[str]:
        """List files with prefix"""
        await self.initialize()

        search_path = self._get_full_path(prefix)
        results = []

        if search_path.exists():
            if search_path.is_dir():
                # List all files in directory
                for item in search_path.rglob("*"):
                    if item.is_file():
                        # Convert to relative path
                        relative = item.relative_to(self.base_path)
                        results.append(str(relative).replace("\\", "/"))
            elif search_path.is_file():
                # Single file
                relative = search_path.relative_to(self.base_path)
                results.append(str(relative).replace("\\", "/"))

        return sorted(results)

    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata"""
        await self.initialize()

        full_path = self._get_full_path(remote_path)
        if not full_path.exists():
            return None

        stat = full_path.stat()

        # Calculate checksum
        checksum = None
        if full_path.is_file():
            checksum = await calculate_file_hash_async(full_path)

        return {
            'path': remote_path,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'is_dir': full_path.is_dir(),
            'checksum': checksum
        }

    async def _do_close(self) -> None:
        """No cleanup needed for filesystem storage"""
        pass

    def get_local_path(self, remote_path: str) -> Path:
        """Get the actual local path for a remote path (filesystem-specific)"""
        return self._get_full_path(remote_path)