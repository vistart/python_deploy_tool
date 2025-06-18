"""Storage backend factory"""

import os
from typing import Dict, Any

from .base import StorageBackend
from .bos import BOSStorage
from .filesystem import FileSystemStorage
from .s3 import S3Storage
from ..constants import DEFAULT_STORAGE_TYPE
from ..core.path_resolver import PathResolver


class StorageFactory:
    """Factory for creating storage backend instances"""

    # Registry of available storage backends
    _backends = {
        'filesystem': FileSystemStorage,
        'fs': FileSystemStorage,  # Alias
        'local': FileSystemStorage,  # Alias
        'bos': BOSStorage,
        'baidu': BOSStorage,  # Alias
        's3': S3Storage,
        'aws': S3Storage,  # Alias
    }

    @classmethod
    def create(cls,
               storage_type: str = None,
               config: Dict[str, Any] = None,
               path_resolver: PathResolver = None) -> StorageBackend:
        """
        Create storage backend instance

        Args:
            storage_type: Type of storage backend
            config: Backend-specific configuration
            path_resolver: Path resolver instance (for filesystem backend)

        Returns:
            Storage backend instance

        Raises:
            ValueError: If storage type is not supported
        """
        # Determine storage type
        if storage_type is None:
            storage_type = os.environ.get('DEPLOY_TOOL_STORAGE', DEFAULT_STORAGE_TYPE)

        storage_type = storage_type.lower()

        # Validate storage type
        if storage_type not in cls._backends:
            raise ValueError(
                f"Unsupported storage type: {storage_type}. "
                f"Supported types: {', '.join(sorted(set(cls._backends.keys())))}"
            )

        # Create configuration
        if config is None:
            config = cls._load_config_from_env(storage_type)

        # Create backend instance
        backend_class = cls._backends[storage_type]

        if storage_type in ['filesystem', 'fs', 'local']:
            # Filesystem backend needs path resolver
            return backend_class(config, path_resolver)
        else:
            return backend_class(config)

    @classmethod
    def register(cls, name: str, backend_class: type):
        """
        Register custom storage backend

        Args:
            name: Backend name
            backend_class: Backend class (must inherit from StorageBackend)
        """
        if not issubclass(backend_class, StorageBackend):
            raise TypeError(f"{backend_class} must inherit from StorageBackend")

        cls._backends[name.lower()] = backend_class

    @classmethod
    def _load_config_from_env(cls, storage_type: str) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}

        if storage_type in ['bos', 'baidu']:
            # BOS configuration
            config['access_key'] = os.environ.get('BOS_AK') or os.environ.get('BOS_ACCESS_KEY')
            config['secret_key'] = os.environ.get('BOS_SK') or os.environ.get('BOS_SECRET_KEY')
            config['bucket'] = os.environ.get('BOS_BUCKET')
            config['endpoint'] = os.environ.get('BOS_ENDPOINT', 'https://bj.bcebos.com')

        elif storage_type in ['s3', 'aws']:
            # S3 configuration
            config['access_key_id'] = os.environ.get('AWS_ACCESS_KEY_ID')
            config['secret_access_key'] = os.environ.get('AWS_SECRET_ACCESS_KEY')
            config['bucket'] = os.environ.get('S3_BUCKET') or os.environ.get('AWS_S3_BUCKET')
            config['region'] = os.environ.get('AWS_REGION', 'us-east-1')
            config['endpoint_url'] = os.environ.get('S3_ENDPOINT_URL')

        elif storage_type in ['filesystem', 'fs', 'local']:
            # Filesystem configuration
            config['base_path'] = os.environ.get('DEPLOY_TOOL_STORAGE_PATH')

        return config

    @classmethod
    def get_available_backends(cls) -> Dict[str, type]:
        """Get all available storage backends"""
        return cls._backends.copy()