# deploy_tool/core/storage_manager.py
"""Storage manager for abstracting storage operations"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from .path_resolver import PathResolver
from ..constants import DEFAULT_STORAGE_TYPE, SUPPORTED_STORAGE_TYPES


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Upload file to storage

        Args:
            local_path: Local file path
            remote_path: Remote path
            callback: Progress callback(bytes_uploaded, total_bytes)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Download file from storage

        Args:
            remote_path: Remote path
            local_path: Local file path
            callback: Progress callback(bytes_downloaded, total_bytes)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def exists(self, remote_path: str) -> bool:
        """
        Check if file exists

        Args:
            remote_path: Remote path

        Returns:
            True if exists
        """
        pass

    @abstractmethod
    async def delete(self, remote_path: str) -> bool:
        """
        Delete file

        Args:
            remote_path: Remote path

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def list(self, prefix: str) -> List[str]:
        """
        List files with prefix

        Args:
            prefix: Path prefix

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
            Metadata dictionary or None
        """
        pass


class StoragePathResolver:
    """Storage path resolution helper"""

    @staticmethod
    def get_component_path(package_type: str, version: str) -> str:
        """
        Get component storage path

        Args:
            package_type: Package type
            version: Version string

        Returns:
            Storage path
        """
        return f"{package_type}/{version}/"

    @staticmethod
    def get_archive_path(package_type: str, version: str, filename: str) -> str:
        """
        Get archive storage path

        Args:
            package_type: Package type
            version: Version string
            filename: Archive filename

        Returns:
            Storage path
        """
        return f"{package_type}/{version}/{filename}"

    @staticmethod
    def get_manifest_path(package_type: str, version: str) -> str:
        """
        Get manifest storage path

        Args:
            package_type: Package type
            version: Version string

        Returns:
            Storage path
        """
        return f"{package_type}/{version}/{package_type}-{version}.manifest.json"

    @staticmethod
    def get_release_path(release_version: str) -> str:
        """
        Get release storage path

        Args:
            release_version: Release version

        Returns:
            Storage path
        """
        return f"releases/{release_version}.release.json"


class StorageManager:
    """Unified storage manager"""

    def __init__(self,
                 storage_type: str = DEFAULT_STORAGE_TYPE,
                 config: Optional[Dict[str, Any]] = None,
                 path_resolver: Optional[PathResolver] = None):
        """
        Initialize storage manager

        Args:
            storage_type: Type of storage backend
            config: Storage configuration
            path_resolver: Path resolver instance
        """
        self.storage_type = storage_type
        self.config = config or {}
        self.path_resolver = path_resolver or PathResolver()
        self._backend: Optional[StorageBackend] = None
        self._path_helper = StoragePathResolver()

    @property
    def backend(self) -> StorageBackend:
        """Get storage backend (lazy initialization)"""
        if self._backend is None:
            self._backend = self._create_backend()
        return self._backend

    def _create_backend(self) -> StorageBackend:
        """Create storage backend instance"""
        if self.storage_type not in SUPPORTED_STORAGE_TYPES:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")

        if self.storage_type == "filesystem":
            from ..storage.filesystem import FileSystemStorage
            return FileSystemStorage(self.config, self.path_resolver)
        elif self.storage_type == "bos":
            from ..storage.bos import BOSStorage
            return BOSStorage(self.config)
        elif self.storage_type == "s3":
            from ..storage.s3 import S3Storage
            return S3Storage(self.config)
        else:
            raise ValueError(f"Storage type not implemented: {self.storage_type}")

    async def upload_component(self,
                               local_path: Path,
                               package_type: str,
                               version: str,
                               callback: Optional[Callable[[int, int], None]] = None) -> str:
        """
        Upload component to storage

        Args:
            local_path: Local file path
            package_type: Package type
            version: Version string
            callback: Progress callback

        Returns:
            Remote storage path
        """
        filename = local_path.name
        remote_path = self._path_helper.get_archive_path(package_type, version, filename)

        success = await self.backend.upload(local_path, remote_path, callback)
        if not success:
            raise RuntimeError(f"Failed to upload {local_path} to {remote_path}")

        return remote_path

    async def download_component(self,
                                 package_type: str,
                                 version: str,
                                 filename: str,
                                 local_path: Path,
                                 callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Download component from storage

        Args:
            package_type: Package type
            version: Version string
            filename: Archive filename
            local_path: Local destination path
            callback: Progress callback

        Returns:
            True if successful
        """
        remote_path = self._path_helper.get_archive_path(package_type, version, filename)

        # Ensure local directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        return await self.backend.download(remote_path, local_path, callback)

    async def upload_manifest(self,
                              manifest_path: Path,
                              package_type: str,
                              version: str) -> str:
        """
        Upload manifest to storage

        Args:
            manifest_path: Local manifest path
            package_type: Package type
            version: Version string

        Returns:
            Remote storage path
        """
        remote_path = self._path_helper.get_manifest_path(package_type, version)

        success = await self.backend.upload(manifest_path, remote_path)
        if not success:
            raise RuntimeError(f"Failed to upload manifest to {remote_path}")

        return remote_path

    async def download_manifest(self,
                                package_type: str,
                                version: str,
                                local_path: Path) -> bool:
        """
        Download manifest from storage

        Args:
            package_type: Package type
            version: Version string
            local_path: Local destination path

        Returns:
            True if successful
        """
        remote_path = self._path_helper.get_manifest_path(package_type, version)

        # Ensure local directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        return await self.backend.download(remote_path, local_path)

    async def upload_release(self,
                             release_path: Path,
                             release_version: str) -> str:
        """
        Upload release manifest to storage

        Args:
            release_path: Local release manifest path
            release_version: Release version

        Returns:
            Remote storage path
        """
        remote_path = self._path_helper.get_release_path(release_version)

        success = await self.backend.upload(release_path, remote_path)
        if not success:
            raise RuntimeError(f"Failed to upload release to {remote_path}")

        return remote_path

    async def download_release(self,
                               release_version: str,
                               local_path: Path) -> bool:
        """
        Download release manifest from storage

        Args:
            release_version: Release version
            local_path: Local destination path

        Returns:
            True if successful
        """
        remote_path = self._path_helper.get_release_path(release_version)

        # Ensure local directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        return await self.backend.download(remote_path, local_path)

    async def list_components(self, package_type: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List available components

        Args:
            package_type: Filter by package type (optional)

        Returns:
            List of component info dicts
        """
        prefix = f"{package_type}/" if package_type else ""
        paths = await self.backend.list(prefix)

        components = []
        seen = set()

        for path in paths:
            # Extract component info from path
            parts = path.split('/')
            if len(parts) >= 2:
                comp_type = parts[0]
                version = parts[1]

                key = f"{comp_type}:{version}"
                if key not in seen:
                    seen.add(key)
                    components.append({
                        'type': comp_type,
                        'version': version,
                        'path': f"{comp_type}/{version}/"
                    })

        return sorted(components, key=lambda x: (x['type'], x['version']))

    async def list_releases(self) -> List[str]:
        """
        List available releases

        Returns:
            List of release versions
        """
        paths = await self.backend.list("releases/")

        releases = []
        for path in paths:
            if path.endswith('.release.json'):
                # Extract version from filename
                filename = path.split('/')[-1]
                version = filename.replace('.release.json', '')
                releases.append(version)

        return sorted(releases)

    async def component_exists(self, package_type: str, version: str) -> bool:
        """
        Check if component exists

        Args:
            package_type: Package type
            version: Version string

        Returns:
            True if exists
        """
        # Check if manifest exists
        manifest_path = self._path_helper.get_manifest_path(package_type, version)
        return await self.backend.exists(manifest_path)

    async def release_exists(self, release_version: str) -> bool:
        """
        Check if release exists

        Args:
            release_version: Release version

        Returns:
            True if exists
        """
        release_path = self._path_helper.get_release_path(release_version)
        return await self.backend.exists(release_path)

    async def delete_component(self, package_type: str, version: str) -> bool:
        """
        Delete component from storage

        Args:
            package_type: Package type
            version: Version string

        Returns:
            True if successful
        """
        # List all files for this component
        prefix = self._path_helper.get_component_path(package_type, version)
        files = await self.backend.list(prefix)

        # Delete all files
        success = True
        for file_path in files:
            if not await self.backend.delete(file_path):
                success = False

        return success

    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage configuration info"""
        return {
            'type': self.storage_type,
            'config': {k: v for k, v in self.config.items() if not k.endswith('_key')},
            'supported_types': SUPPORTED_STORAGE_TYPES
        }