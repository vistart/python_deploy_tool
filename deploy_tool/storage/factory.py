"""Storage backend factory"""

from typing import Dict, Any, Type

from .base import StorageBackend
from .filesystem import FilesystemStorage
from .bos import BOSStorage
from .s3 import S3Storage
from ..constants import StorageType
from ..models.config import PublishTarget


class StorageFactory:
    """Factory for creating storage backend instances"""

    # Registry of storage backends
    _backends: Dict[StorageType, Type[StorageBackend]] = {
        StorageType.FILESYSTEM: FilesystemStorage,
        StorageType.BOS: BOSStorage,
        StorageType.S3: S3Storage,
    }

    @classmethod
    def create_from_config(cls, target: PublishTarget) -> StorageBackend:
        """Create storage backend from publish target configuration

        Args:
            target: Publish target configuration

        Returns:
            Storage backend instance

        Raises:
            ValueError: If storage type is not supported
        """
        storage_type = target.storage_type

        if storage_type not in cls._backends:
            raise ValueError(f"Unsupported storage type: {storage_type.value}")

        # Prepare configuration based on storage type
        if storage_type == StorageType.FILESYSTEM:
            config = {
                "path": target.path,
                "name": target.name
            }

        elif storage_type == StorageType.BOS:
            config = {
                "endpoint": target.bos_endpoint,
                "bucket": target.bos_bucket,
                "access_key": target.bos_access_key,
                "secret_key": target.bos_secret_key,
                "name": target.name
            }

        elif storage_type == StorageType.S3:
            config = {
                "region": target.s3_region,
                "bucket": target.s3_bucket,
                "access_key": target.s3_access_key,
                "secret_key": target.s3_secret_key,
                "name": target.name
            }

        else:
            raise ValueError(f"No configuration mapping for storage type: {storage_type.value}")

        # Add any additional options
        if target.options:
            config.update(target.options)

        # Create backend instance
        backend_class = cls._backends[storage_type]
        return backend_class(config)

    @classmethod
    def create_from_dict(cls, storage_type: str, config: Dict[str, Any]) -> StorageBackend:
        """Create storage backend from type and configuration dict

        Args:
            storage_type: Storage type string
            config: Configuration dictionary

        Returns:
            Storage backend instance

        Raises:
            ValueError: If storage type is not supported
        """
        try:
            type_enum = StorageType(storage_type)
        except ValueError:
            raise ValueError(f"Invalid storage type: {storage_type}")

        if type_enum not in cls._backends:
            raise ValueError(f"Unsupported storage type: {storage_type}")

        backend_class = cls._backends[type_enum]
        return backend_class(config)

    @classmethod
    def register_backend(cls, storage_type: StorageType, backend_class: Type[StorageBackend]):
        """Register a new storage backend type

        Args:
            storage_type: Storage type enum
            backend_class: Backend class
        """
        cls._backends[storage_type] = backend_class

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported storage types

        Returns:
            List of supported storage type names
        """
        return [st.value for st in cls._backends.keys()]

    @classmethod
    def is_supported(cls, storage_type: str) -> bool:
        """Check if a storage type is supported

        Args:
            storage_type: Storage type string

        Returns:
            True if supported, False otherwise
        """
        try:
            type_enum = StorageType(storage_type)
            return type_enum in cls._backends
        except ValueError:
            return False