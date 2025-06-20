"""Baidu Object Storage (BOS) backend implementation"""

<<<<<<< Updated upstream
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
=======
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
>>>>>>> Stashed changes

from .base import StorageBackend
from ..utils.file_utils import get_file_size
from ..constants import DEFAULT_CHUNK_SIZE

try:
    from baidubce.bce_client_configuration import BceClientConfiguration
    from baidubce.auth.bce_credentials import BceCredentials
    from baidubce.services.bos.bos_client import BosClient
    from baidubce.exception import BceError
    HAS_BOS = True
except ImportError:
    HAS_BOS = False
    BceError = Exception


class BOSStorage(StorageBackend):
<<<<<<< Updated upstream
    """Baidu Object Storage implementation"""
=======
    """Baidu Object Storage backend"""
>>>>>>> Stashed changes

    def __init__(self, config: Dict[str, Any]):
        """Initialize BOS storage backend

        Args:
            config: BOS configuration
        """
        if not HAS_BOS:
            raise ImportError(
                "BOS SDK not installed. Install with: pip install bce-python-sdk"
            )

        super().__init__(config)
<<<<<<< Updated upstream
        self.client = None
        self.bucket = config.get('bucket', 'deploy-tool-storage')
        self.endpoint = config.get('endpoint', 'https://bj.bcebos.com')

    async def _do_initialize(self) -> None:
        """Initialize BOS connection"""
        try:
            from baidubce.services.bos.bos_client import BosClient
            from baidubce.bce_client_configuration import BceClientConfiguration
            from baidubce.auth.bce_credentials import BceCredentials

            # Create BOS client configuration
            bos_config = BceClientConfiguration(
                credentials=BceCredentials(
                    self.config.get('access_key'),
                    self.config.get('secret_key')
                ),
                endpoint=self.endpoint
            )

            # Create BOS client
            self.client = BosClient(bos_config)

            # Test connection by checking if bucket exists
            self.client.head_bucket(self.bucket)

        except ImportError:
            raise RuntimeError(
                "BOS storage backend requires 'bce-python-sdk' package. "
                "Install with: pip install bce-python-sdk"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize BOS storage: {e}")

    async def upload(self,
                     local_path: Path,
                     remote_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Upload file to BOS"""
        try:
            await self.initialize()

            file_size = local_path.stat().st_size

            # BOS SDK is synchronous, run in executor
            def _upload():
                with open(local_path, 'rb') as f:
                    # Simple upload for small files
                    if file_size < 5 * 1024 * 1024:  # 5MB
                        self.client.put_object_from_file(
                            self.bucket,
                            remote_path,
                            str(local_path)
                        )
                    else:
                        # Multipart upload for large files
                        self._multipart_upload(
                            local_path,
                            remote_path,
                            callback
                        )
                return True

            return await asyncio.get_event_loop().run_in_executor(
                None, _upload
            )

        except Exception as e:
            import logging
            logging.error(f"BOS upload failed: {e}")
            return False

    def _multipart_upload(self,
                          local_path: Path,
                          remote_path: str,
                          callback: Optional[Callable[[int, int], None]] = None):
        """Perform multipart upload for large files"""
        file_size = local_path.stat().st_size
        chunk_size = 5 * 1024 * 1024  # 5MB chunks

        # Initiate multipart upload
        upload_id = self.client.initiate_multipart_upload(
            self.bucket, remote_path
        ).upload_id

        parts = []
        bytes_uploaded = 0

        try:
            with open(local_path, 'rb') as f:
                part_number = 1
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break

                    # Upload part
                    response = self.client.upload_part_from_string(
                        self.bucket,
                        remote_path,
                        upload_id,
                        part_number,
                        data
                    )

                    parts.append({
                        'partNumber': part_number,
                        'eTag': response.etag
                    })

                    bytes_uploaded += len(data)
                    if callback:
                        callback(bytes_uploaded, file_size)

                    part_number += 1

            # Complete multipart upload
            self.client.complete_multipart_upload(
                self.bucket,
                remote_path,
                upload_id,
                parts
            )

        except Exception:
            # Abort on error
            self.client.abort_multipart_upload(
                self.bucket,
                remote_path,
                upload_id
            )
            raise

    async def download(self,
                       remote_path: str,
                       local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download file from BOS"""
        try:
            await self.initialize()

            # Ensure local directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Get object size
            def _download():
                meta = self.client.get_object_meta_data(self.bucket, remote_path)
                file_size = int(meta.metadata.get('content-length', 0))

                # Download with progress
                bytes_downloaded = 0
                chunk_size = 1024 * 1024  # 1MB chunks

                response = self.client.get_object(self.bucket, remote_path)

                with open(local_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        if callback:
                            callback(bytes_downloaded, file_size)

                return True

            return await asyncio.get_event_loop().run_in_executor(
                None, _download
            )

        except Exception as e:
            import logging
            logging.error(f"BOS download failed: {e}")
            return False

    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in BOS"""
        try:
            await self.initialize()

            def _exists():
                try:
                    self.client.get_object_meta_data(self.bucket, remote_path)
                    return True
                except:
                    return False

            return await asyncio.get_event_loop().run_in_executor(
                None, _exists
            )

        except:
            return False

    async def delete(self, remote_path: str) -> bool:
        """Delete file from BOS"""
        try:
            await self.initialize()

            def _delete():
                self.client.delete_object(self.bucket, remote_path)
                return True

            return await asyncio.get_event_loop().run_in_executor(
                None, _delete
            )

        except Exception as e:
            import logging
            logging.error(f"BOS delete failed: {e}")
            return False

    async def list(self, prefix: str = "") -> List[str]:
        """List files in BOS with prefix"""
        try:
            await self.initialize()

            def _list():
                files = []
                marker = None

                while True:
                    response = self.client.list_objects(
                        self.bucket,
                        prefix=prefix,
                        marker=marker,
                        max_keys=1000
                    )

                    for obj in response.contents:
                        files.append(obj.key)

                    if response.is_truncated:
                        marker = response.next_marker
                    else:
                        break

                return files

            files = await asyncio.get_event_loop().run_in_executor(
                None, _list
            )

            return sorted(files)

        except Exception as e:
            import logging
            logging.error(f"BOS list failed: {e}")
            return []

    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from BOS"""
        try:
            await self.initialize()

            def _get_metadata():
                meta = self.client.get_object_meta_data(self.bucket, remote_path)

                return {
                    'size': int(meta.metadata.get('content-length', 0)),
                    'modified': meta.metadata.get('last-modified'),
                    'etag': meta.metadata.get('etag', '').strip('"'),
                    'content_type': meta.metadata.get('content-type'),
                    'storage_class': meta.metadata.get('x-bce-storage-class'),
                    'metadata': {k: v for k, v in meta.metadata.items()
                                 if k.startswith('x-bce-meta-')}
                }

            return await asyncio.get_event_loop().run_in_executor(
                None, _get_metadata
            )

        except:
            return None

    def get_post_publish_instructions(self,
                                      release_version: str,
                                      published_path: Path) -> List[str]:
        """
        Get BOS-specific post-publish instructions

        Args:
            release_version: Version that was published
            published_path: Local path where files were published

        Returns:
            List of instruction strings
        """
        instructions = [
            "✅ Files automatically uploaded to BOS!",
            "",
            f"Bucket: {self.bucket}",
            f"Endpoint: {self.endpoint}",
            f"Release: {release_version}",
            "",
            "📋 Next steps:",
            "",
            "1. Add release manifest to Git:",
            f"   git add deployment/releases/{release_version}.release.json",
            f"   git commit -m \"Release version {release_version}\"",
            "   git push",
            "",
            "2. Deploy from BOS on target server:",
            f"   deploy-tool deploy \\",
            f"     --release {release_version} \\",
            f"     --target /opt/ml-apps/my-project \\",
            f"     --method bos \\",
            f"     --bucket {self.bucket} \\",
            f"     --endpoint {self.endpoint}",
            "",
            "No manual file transfer needed! Files are already in BOS.",
            "",
            "💡 Tips:",
            "- Ensure target server has BOS credentials configured",
            "- Set BOS_AK and BOS_SK environment variables",
            "- Consider using BOS lifecycle policies for cost optimization"
        ]

        return instructions

    async def _do_close(self) -> None:
        """Close BOS connection"""
        # BOS client doesn't require explicit cleanup
        self.client = None
=======

        # Initialize BOS client
        bos_config = BceClientConfiguration(
            credentials=BceCredentials(
                self.config['access_key'],
                self.config['secret_key']
            ),
            endpoint=self.config['endpoint']
        )

        self.client = BosClient(bos_config)
        self.bucket = self.config['bucket']

        # Thread pool for sync operations
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _validate_config(self) -> None:
        """Validate BOS configuration"""
        required_fields = ['endpoint', 'bucket', 'access_key', 'secret_key']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"BOS storage requires '{field}' configuration")

    def _normalize_key(self, key: str) -> str:
        """Normalize object key

        Args:
            key: Object key

        Returns:
            Normalized key
        """
        # Remove leading slash
        if key.startswith('/'):
            key = key[1:]

        # Ensure forward slashes
        key = key.replace('\\', '/')

        return key

    async def upload(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Upload a file to BOS

        Args:
            local_path: Local file path
            remote_path: Remote object key
            progress_callback: Optional callback for progress updates

        Returns:
            Upload result metadata
        """
        source = Path(local_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {local_path}")

        key = self._normalize_key(remote_path)
        file_size = get_file_size(source)

        # Use multipart upload for large files (>100MB)
        if file_size > 100 * 1024 * 1024:
            result = await self._multipart_upload(
                source, key, progress_callback
            )
        else:
            # Simple upload for small files
            def _upload():
                with open(source, 'rb') as f:
                    self.client.put_object_from_file(
                        bucket_name=self.bucket,
                        key=key,
                        file_name=str(source)
                    )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, _upload)

            if progress_callback:
                await progress_callback(file_size, file_size)

            result = {
                "key": key,
                "size": file_size,
                "bucket": self.bucket
            }

        result["uploaded_at"] = datetime.utcnow().isoformat()
        result["endpoint"] = self.config['endpoint']

        return result

    async def _multipart_upload(
        self,
        source: Path,
        key: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Perform multipart upload for large files

        Args:
            source: Source file path
            key: Object key
            progress_callback: Progress callback

        Returns:
            Upload result
        """
        file_size = get_file_size(source)

        # Initiate multipart upload
        loop = asyncio.get_event_loop()

        def _init_multipart():
            response = self.client.initiate_multipart_upload(
                bucket_name=self.bucket,
                key=key
            )
            return response.upload_id

        upload_id = await loop.run_in_executor(self._executor, _init_multipart)

        # Calculate part size (10MB per part)
        part_size = 10 * 1024 * 1024
        part_count = (file_size + part_size - 1) // part_size

        parts = []
        uploaded_bytes = 0

        try:
            # Upload parts
            with open(source, 'rb') as f:
                for part_number in range(1, part_count + 1):
                    # Read part data
                    part_data = f.read(part_size)
                    if not part_data:
                        break

                    # Upload part
                    def _upload_part(data, part_num):
                        response = self.client.upload_part(
                            bucket_name=self.bucket,
                            key=key,
                            upload_id=upload_id,
                            part_number=part_num,
                            part_data=data
                        )
                        return {
                            'partNumber': part_num,
                            'eTag': response.etag
                        }

                    part_info = await loop.run_in_executor(
                        self._executor,
                        _upload_part,
                        part_data,
                        part_number
                    )
                    parts.append(part_info)

                    uploaded_bytes += len(part_data)
                    if progress_callback:
                        await progress_callback(uploaded_bytes, file_size)

            # Complete multipart upload
            def _complete_multipart():
                self.client.complete_multipart_upload(
                    bucket_name=self.bucket,
                    key=key,
                    upload_id=upload_id,
                    part_list=parts
                )

            await loop.run_in_executor(self._executor, _complete_multipart)

            return {
                "key": key,
                "size": file_size,
                "bucket": self.bucket,
                "parts": len(parts)
            }

        except Exception as e:
            # Abort multipart upload on error
            def _abort_multipart():
                try:
                    self.client.abort_multipart_upload(
                        bucket_name=self.bucket,
                        key=key,
                        upload_id=upload_id
                    )
                except:
                    pass

            await loop.run_in_executor(self._executor, _abort_multipart)
            raise e

    async def download(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Download a file from BOS

        Args:
            remote_path: Remote object key
            local_path: Local destination path
            progress_callback: Optional callback for progress updates

        Returns:
            Download result metadata
        """
        key = self._normalize_key(remote_path)
        dest = Path(local_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Get object metadata first
        loop = asyncio.get_event_loop()

        def _get_metadata():
            response = self.client.get_object_meta_data(
                bucket_name=self.bucket,
                key=key
            )
            return int(response.metadata.content_length)

        try:
            file_size = await loop.run_in_executor(self._executor, _get_metadata)
        except BceError as e:
            if hasattr(e, 'code') and e.code == 'NoSuchKey':
                raise FileNotFoundError(f"Object not found: {key}")
            raise

        # Download file
        downloaded_bytes = 0

        def _download():
            nonlocal downloaded_bytes

            # Stream download with progress
            response = self.client.get_object(
                bucket_name=self.bucket,
                key=key
            )

            with open(dest, 'wb') as f:
                for chunk in response.data.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)

                        if progress_callback:
                            # Run callback in async context
                            future = asyncio.run_coroutine_threadsafe(
                                progress_callback(downloaded_bytes, file_size),
                                loop
                            )
                            future.result()

        await loop.run_in_executor(self._executor, _download)

        return {
            "path": str(dest),
            "size": file_size,
            "downloaded_at": datetime.utcnow().isoformat()
        }

    async def exists(self, remote_path: str) -> bool:
        """Check if an object exists in BOS

        Args:
            remote_path: Remote object key

        Returns:
            True if object exists, False otherwise
        """
        key = self._normalize_key(remote_path)
        loop = asyncio.get_event_loop()

        def _check_exists():
            try:
                self.client.get_object_meta_data(
                    bucket_name=self.bucket,
                    key=key
                )
                return True
            except BceError as e:
                if hasattr(e, 'code') and e.code == 'NoSuchKey':
                    return False
                raise

        return await loop.run_in_executor(self._executor, _check_exists)

    async def delete(self, remote_path: str) -> bool:
        """Delete an object from BOS

        Args:
            remote_path: Remote object key

        Returns:
            True if deleted successfully
        """
        key = self._normalize_key(remote_path)
        loop = asyncio.get_event_loop()

        def _delete():
            try:
                self.client.delete_object(
                    bucket_name=self.bucket,
                    key=key
                )
                return True
            except BceError as e:
                if hasattr(e, 'code') and e.code == 'NoSuchKey':
                    return False
                raise

        return await loop.run_in_executor(self._executor, _delete)

    async def list_objects(
        self,
        prefix: str = "",
        recursive: bool = True,
        max_keys: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List objects in BOS

        Args:
            prefix: Filter objects by prefix
            recursive: List recursively (always True for BOS)
            max_keys: Maximum number of objects to return

        Returns:
            List of object metadata
        """
        prefix = self._normalize_key(prefix) if prefix else ""
        loop = asyncio.get_event_loop()

        def _list_objects():
            objects = []
            marker = None

            while True:
                # List objects
                response = self.client.list_objects(
                    bucket_name=self.bucket,
                    prefix=prefix,
                    marker=marker,
                    max_keys=min(max_keys or 1000, 1000)
                )

                # Process objects
                for obj in response.contents:
                    objects.append({
                        "key": obj.key,
                        "size": obj.size,
                        "modified": obj.last_modified,
                        "etag": obj.etag,
                        "storage_class": obj.storage_class
                    })

                # Check if we have enough objects
                if max_keys and len(objects) >= max_keys:
                    objects = objects[:max_keys]
                    break

                # Check if there are more objects
                if not response.is_truncated:
                    break

                marker = response.next_marker

            return objects

        return await loop.run_in_executor(self._executor, _list_objects)

    async def get_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for an object

        Args:
            remote_path: Remote object key

        Returns:
            Object metadata
        """
        key = self._normalize_key(remote_path)
        loop = asyncio.get_event_loop()

        def _get_metadata():
            response = self.client.get_object_meta_data(
                bucket_name=self.bucket,
                key=key
            )

            return {
                "key": key,
                "size": int(response.metadata.content_length),
                "content_type": response.metadata.content_type,
                "etag": response.metadata.etag,
                "last_modified": response.metadata.last_modified,
                "metadata": response.user_metadata
            }

        try:
            return await loop.run_in_executor(self._executor, _get_metadata)
        except BceError as e:
            if hasattr(e, 'code') and e.code == 'NoSuchKey':
                raise FileNotFoundError(f"Object not found: {key}")
            raise

    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get public URL for an object

        Args:
            remote_path: Remote object key

        Returns:
            Public URL
        """
        key = self._normalize_key(remote_path)
        return f"https://{self.bucket}.{self.config['endpoint']}/{key}"

    def get_signed_url(
        self,
        remote_path: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """Get signed URL for temporary access

        Args:
            remote_path: Remote object key
            expires_in: Expiration time in seconds
            method: HTTP method

        Returns:
            Signed URL
        """
        key = self._normalize_key(remote_path)

        # BOS client generates signed URLs synchronously
        url = self.client.generate_pre_signed_url(
            bucket_name=self.bucket,
            key=key,
            timestamp=int(datetime.utcnow().timestamp()),
            expiration_in_seconds=expires_in,
            method=method.upper()
        )

        return url

    async def close(self) -> None:
        """Close storage connections"""
        self._executor.shutdown(wait=True)
>>>>>>> Stashed changes
