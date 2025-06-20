"""Filesystem storage backend implementation"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from .base import StorageBackend
from ..core.path_resolver import PathResolver
from ..utils.file_utils import (
    copy_with_progress,
    calculate_file_hash,
    get_file_metadata
)


class FileSystemStorage(StorageBackend):
    """Local filesystem storage implementation"""

    def __init__(self, config: Dict[str, Any] = None, path_resolver: PathResolver = None):
        """
        Initialize filesystem storage

        Args:
            config: Configuration including:
                - base_path: Base storage path (optional)
            path_resolver: Path resolver instance
        """
        super().__init__(config)
        self.path_resolver = path_resolver or PathResolver()

        # Determine base path for published files
        base_path = config.get('base_path') if config else None
        if base_path:
            self.base_path = Path(base_path)
        else:
<<<<<<< HEAD
            # Default to deployment/published within project
            self.base_path = self.path_resolver.project_root / "deployment" / "published"
=======
            self.base_path = self.path_resolver.dist_dir
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

    async def _do_initialize(self) -> None:
        """Initialize filesystem storage (ensure directories exist)"""
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self,
                     local_path: Path,
                     remote_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
<<<<<<< HEAD
        """
        Copy file to storage location

        Args:
            local_path: Local file path
            remote_path: Remote storage path (relative to base_path)
            callback: Progress callback

        Returns:
            True if successful
        """
        try:
            # Ensure storage is initialized
            await self.initialize()

            # Convert remote path to absolute path
            target_path = self.base_path / remote_path

            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file with progress
            await asyncio.get_event_loop().run_in_executor(
                None,
                copy_with_progress,
                local_path,
                target_path,
                callback
            )
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

            return True

        except Exception as e:
            import logging
            logging.error(f"Upload failed: {e}")
            return False

    async def download(self,
                       remote_path: str,
                       local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
<<<<<<< HEAD
        """
        Copy file from storage location

        Args:
            remote_path: Remote path (relative to base_path)
            local_path: Local file path to save to
            callback: Progress callback

        Returns:
            True if successful
        """
        try:
            # Ensure storage is initialized
            await self.initialize()

            # Convert remote path to absolute path
            source_path = self.base_path / remote_path

            if not source_path.exists():
                return False

            # Ensure local directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file with progress
            await asyncio.get_event_loop().run_in_executor(
                None,
                copy_with_progress,
                source_path,
                local_path,
                callback
            )
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

            return True

        except Exception as e:
            import logging
            logging.error(f"Download failed: {e}")
            return False

    async def exists(self, remote_path: str) -> bool:
<<<<<<< HEAD
        """
        Check if file exists in storage

        Args:
            remote_path: Remote path to check

        Returns:
            True if file exists
        """
        # Ensure storage is initialized
        await self.initialize()

        target_path = self.base_path / remote_path
        return target_path.exists()
=======
        """Check if file exists"""
        await self.initialize()
        full_path = self._get_full_path(remote_path)
        return full_path.exists()
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

    async def delete(self, remote_path: str) -> bool:
        """Delete file"""
        try:
            await self.initialize()
            full_path = self._get_full_path(remote_path)

<<<<<<< HEAD
        Args:
            remote_path: Remote path to delete

        Returns:
            True if successful
        """
        try:
            # Ensure storage is initialized
            await self.initialize()

            target_path = self.base_path / remote_path

            if target_path.exists():
                if target_path.is_file():
                    target_path.unlink()
                elif target_path.is_dir():
                    shutil.rmtree(target_path)
                return True

=======
            if full_path.exists():
                if full_path.is_dir():
                    shutil.rmtree(full_path)
                else:
                    full_path.unlink()
                return True

>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
            return False

        except Exception as e:
            import logging
            logging.error(f"Delete failed: {e}")
            return False

    async def list(self, prefix: str = "") -> List[str]:
<<<<<<< HEAD
        """
        List files in storage with given prefix

        Args:
            prefix: Path prefix to filter by

        Returns:
            List of file paths relative to base_path
        """
        # Ensure storage is initialized
        await self.initialize()

        search_path = self.base_path / prefix
        files = []
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

        if search_path.exists() and search_path.is_dir():
            for path in search_path.rglob("*"):
                if path.is_file():
                    # Return relative paths
                    relative_path = path.relative_to(self.base_path)
                    files.append(str(relative_path))

        return sorted(files)

    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata"""
        await self.initialize()

<<<<<<< HEAD
        Args:
            remote_path: Remote path

        Returns:
            Metadata dictionary or None if not found
        """
        # Ensure storage is initialized
        await self.initialize()

        target_path = self.base_path / remote_path

        if not target_path.exists():
            return None

        # Get basic file metadata
        stat = target_path.stat()

        metadata = {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'mode': stat.st_mode,
            'is_file': target_path.is_file(),
            'is_dir': target_path.is_dir(),
        }

        # Calculate checksum for files
        if target_path.is_file():
            try:
                metadata['checksum'] = await asyncio.get_event_loop().run_in_executor(
                    None,
                    calculate_file_hash,
                    target_path
                )
            except Exception:
                pass

        return metadata

    def get_post_publish_instructions(self,
                                      release_version: str,
                                      published_path: Path) -> List[str]:
        """
        Get filesystem-specific post-publish instructions

        Args:
            release_version: Version that was published
            published_path: Local path where files were published

        Returns:
            List of instruction strings for the user
        """
        instructions = [
            "✅ Components published to local filesystem!",
            "",
            f"Location: {self.base_path}",
            f"Release: {release_version}",
            "",
            "📋 Next steps:",
            "",
            "1. Add release manifest to Git:",
            f"   git add deployment/releases/{release_version}.release.json",
            f"   git commit -m \"Release version {release_version}\"",
            "   git push",
            "",
            "2. Transfer published files to deployment server:",
            "",
            "   Option A - Using rsync (recommended):",
            f"   rsync -avz --progress \\",
            f"     {self.base_path}/ \\",
            f"     user@server:/opt/deployments/",
            "",
            "   Option B - Using scp:",
            f"   scp -r {self.base_path}/* \\",
            f"     user@server:/opt/deployments/",
            "",
            "3. Deploy on target server:",
            f"   deploy-tool deploy \\",
            f"     --release {release_version} \\",
            f"     --target /opt/ml-apps/my-project \\",
            f"     --method local",
            "",
            "💡 Tip: Consider using cloud storage (S3/BOS) for easier deployment."
        ]

        return instructions

    async def _do_close(self) -> None:
        """Close filesystem storage (no-op for filesystem)"""
        pass
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
