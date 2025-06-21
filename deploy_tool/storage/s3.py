# deploy_tool/storage/s3.py
"""AWS S3 storage backend - reserved for future implementation"""

from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from .base import StorageBackend


class S3Storage(StorageBackend):
    """AWS S3 storage implementation - reserved for future"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize S3 storage

        Args:
            config: S3 configuration including:
                - access_key_id: AWS access key ID
                - secret_access_key: AWS secret access key
                - bucket: S3 bucket name
                - region: AWS region
                - endpoint_url: Custom endpoint (for S3-compatible services)
        """
        super().__init__(config)
        # Reserved for future implementation

    async def _do_initialize(self) -> None:
        """Initialize S3 connection"""
        # Reserved for future implementation
        raise NotImplementedError("S3 storage backend reserved for future implementation")

    async def upload(self,
                     local_path: Path,
                     remote_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Upload file to S3"""
        raise NotImplementedError("S3 storage backend reserved for future implementation")

    async def download(self,
                       remote_path: str,
                       local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download file from S3"""
        raise NotImplementedError("S3 storage backend reserved for future implementation")

    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in S3"""
        raise NotImplementedError("S3 storage backend reserved for future implementation")

    async def delete(self, remote_path: str) -> bool:
        """Delete file from S3"""
        raise NotImplementedError("S3 storage backend reserved for future implementation")

    async def list(self, prefix: str = "") -> List[str]:
        """List files in S3"""
        raise NotImplementedError("S3 storage backend reserved for future implementation")

    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from S3"""
        raise NotImplementedError("S3 storage backend reserved for future implementation")

    async def _do_close(self) -> None:
        """Close S3 connection"""
        # Reserved for future implementation
        pass