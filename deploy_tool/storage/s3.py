<<<<<<< Updated upstream
"""Amazon S3 storage backend implementation"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
=======
"""AWS S3 storage backend implementation"""

import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
>>>>>>> Stashed changes

from .base import StorageBackend
from ..utils.file_utils import get_file_size
from ..constants import DEFAULT_CHUNK_SIZE

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_S3 = True
except ImportError:
    HAS_S3 = False
    ClientError = Exception
    NoCredentialsError = Exception


class S3Storage(StorageBackend):
<<<<<<< Updated upstream
    """Amazon S3 storage implementation"""
=======
    """AWS S3 storage backend"""
>>>>>>> Stashed changes

    def __init__(self, config: Dict[str, Any]):
        """Initialize S3 storage backend

        Args:
<<<<<<< Updated upstream
            config: S3 configuration including:
                - access_key_id: AWS access key ID
                - secret_access_key: AWS secret access key
                - bucket: S3 bucket name
                - region: AWS region
                - endpoint_url: Custom endpoint URL (optional)
=======
            config: S3 configuration
>>>>>>> Stashed changes
        """
        if not HAS_S3:
            raise ImportError(
                "boto3 not installed. Install with: pip install boto3"
            )

        super().__init__(config)
<<<<<<< Updated upstream
        self.client = None
        self.bucket = config.get('bucket', 'deploy-tool-storage')
        self.region = config.get('region', 'us-east-1')

    async def _do_initialize(self) -> None:
        """Initialize S3 connection"""
        try:
            import aioboto3

            # Create async session
            self.session = aioboto3.Session(
                aws_access_key_id=self.config.get('access_key_id'),
                aws_secret_access_key=self.config.get('secret_access_key'),
                region_name=self.region
            )

            # Test connection by checking if bucket exists
            async with self.session.client('s3') as s3:
                await s3.head_bucket(Bucket=self.bucket)

        except ImportError:
            raise RuntimeError(
                "S3 storage backend requires 'aioboto3' package. "
                "Install with: pip install aioboto3"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize S3 storage: {e}")

    async def upload(self,
                     local_path: Path,
                     remote_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Upload file to S3"""
        try:
            await self.initialize()

            file_size = local_path.stat().st_size

            async with self.session.client('s3') as s3:
                # Upload with progress callback
                def progress_callback(bytes_amount):
                    if callback:
                        callback(bytes_amount, file_size)

                with open(local_path, 'rb') as f:
                    await s3.upload_fileobj(
                        f,
                        self.bucket,
                        remote_path,
                        Callback=progress_callback if callback else None
                    )

                return True

        except Exception as e:
            import logging
            logging.error(f"S3 upload failed: {e}")
            return False

    async def download(self,
                       remote_path: str,
                       local_path: Path,
                       callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download file from S3"""
        try:
            await self.initialize()

            # Ensure local directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            async with self.session.client('s3') as s3:
                # Get object size first
                response = await s3.head_object(Bucket=self.bucket, Key=remote_path)
                file_size = response['ContentLength']

                # Download with progress callback
                def progress_callback(bytes_amount):
                    if callback:
                        callback(bytes_amount, file_size)

                with open(local_path, 'wb') as f:
                    await s3.download_fileobj(
                        self.bucket,
                        remote_path,
                        f,
                        Callback=progress_callback if callback else None
                    )

                return True

        except Exception as e:
            import logging
            logging.error(f"S3 download failed: {e}")
            return False

    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            await self.initialize()

            async with self.session.client('s3') as s3:
                await s3.head_object(Bucket=self.bucket, Key=remote_path)
                return True

        except:
            return False

    async def delete(self, remote_path: str) -> bool:
        """Delete file from S3"""
        try:
            await self.initialize()

            async with self.session.client('s3') as s3:
                await s3.delete_object(Bucket=self.bucket, Key=remote_path)
                return True

        except Exception as e:
            import logging
            logging.error(f"S3 delete failed: {e}")
            return False

    async def list(self, prefix: str = "") -> List[str]:
        """List files in S3 with prefix"""
        try:
            await self.initialize()

            files = []

            async with self.session.client('s3') as s3:
                paginator = s3.get_paginator('list_objects_v2')

                async for page in paginator.paginate(
                    Bucket=self.bucket,
                    Prefix=prefix
                ):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            files.append(obj['Key'])

            return sorted(files)

        except Exception as e:
            import logging
            logging.error(f"S3 list failed: {e}")
            return []

    async def get_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from S3"""
        try:
            await self.initialize()

            async with self.session.client('s3') as s3:
                response = await s3.head_object(Bucket=self.bucket, Key=remote_path)

                return {
                    'size': response['ContentLength'],
                    'modified': response['LastModified'].timestamp(),
                    'etag': response.get('ETag', '').strip('"'),
                    'content_type': response.get('ContentType'),
                    'metadata': response.get('Metadata', {}),
                    'storage_class': response.get('StorageClass'),
                }

        except:
            return None

    def get_post_publish_instructions(self,
                                      release_version: str,
                                      published_path: Path) -> List[str]:
        """
        Get S3-specific post-publish instructions

        Args:
            release_version: Version that was published
            published_path: Local path where files were published

        Returns:
            List of instruction strings
        """
        endpoint = self.config.get('endpoint_url', f"https://s3.{self.region}.amazonaws.com")

        instructions = [
            "✅ Files automatically uploaded to S3!",
            "",
            f"Bucket: {self.bucket}",
            f"Region: {self.region}",
            f"Endpoint: {endpoint}",
            f"Release: {release_version}",
            "",
            "📋 Next steps:",
            "",
            "1. Add release manifest to Git:",
            f"   git add deployment/releases/{release_version}.release.json",
            f"   git commit -m \"Release version {release_version}\"",
            "   git push",
            "",
            "2. Deploy from S3 on target server:",
            f"   deploy-tool deploy \\",
            f"     --release {release_version} \\",
            f"     --target /opt/ml-apps/my-project \\",
            f"     --method s3 \\",
            f"     --bucket {self.bucket} \\",
            f"     --region {self.region}",
            "",
            "No manual file transfer needed! Files are already in S3.",
            "",
            "💡 Tips:",
            "- Ensure target server has AWS credentials configured",
            "- Use IAM roles for EC2 instances for secure access",
            "- Consider S3 lifecycle policies for cost optimization"
        ]

        return instructions

    async def _do_close(self) -> None:
        """Close S3 connection"""
        # aioboto3 handles connection pooling automatically
        pass
=======

        # Initialize S3 client
        self.client = boto3.client(
            's3',
            region_name=self.config['region'],
            aws_access_key_id=self.config.get('access_key'),
            aws_secret_access_key=self.config.get('secret_key')
        )

        self.bucket = self.config['bucket']

        # Thread pool for sync operations
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _validate_config(self) -> None:
        """Validate S3 configuration"""
        required_fields = ['region', 'bucket']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"S3 storage requires '{field}' configuration")

        # Access keys are optional (can use IAM roles)
        if 'access_key' in self.config and 'secret_key' not in self.config:
            raise ValueError("S3 storage requires both 'access_key' and 'secret_key' or neither")

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
        """Upload a file to S3

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
            loop = asyncio.get_event_loop()

            def _upload():
                with open(source, 'rb') as f:
                    self.client.upload_fileobj(
                        f,
                        self.bucket,
                        key,
                        Callback=self._create_progress_callback(
                            file_size, progress_callback, loop
                        ) if progress_callback else None
                    )

            await loop.run_in_executor(self._executor, _upload)

            result = {
                "key": key,
                "size": file_size,
                "bucket": self.bucket
            }

        result["uploaded_at"] = datetime.utcnow().isoformat()
        result["region"] = self.config['region']

        return result

    def _create_progress_callback(self, total_size, async_callback, loop):
        """Create a sync progress callback that calls async callback

        Args:
            total_size: Total file size
            async_callback: Async callback function
            loop: Event loop

        Returns:
            Sync callback function
        """
        bytes_transferred = 0

        def callback(chunk_size):
            nonlocal bytes_transferred
            bytes_transferred += chunk_size

            # Run async callback in event loop
            future = asyncio.run_coroutine_threadsafe(
                async_callback(bytes_transferred, total_size),
                loop
            )
            future.result()

        return callback

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

        # Calculate part size (10MB per part)
        part_size = 10 * 1024 * 1024

        # Use S3 transfer manager for multipart upload
        loop = asyncio.get_event_loop()

        def _multipart_upload():
            from boto3.s3.transfer import TransferConfig

            config = TransferConfig(
                multipart_threshold=part_size,
                multipart_chunksize=part_size,
                use_threads=True
            )

            self.client.upload_file(
                str(source),
                self.bucket,
                key,
                Config=config,
                Callback=self._create_progress_callback(
                    file_size, progress_callback, loop
                ) if progress_callback else None
            )

        await loop.run_in_executor(self._executor, _multipart_upload)

        return {
            "key": key,
            "size": file_size,
            "bucket": self.bucket
        }

    async def download(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Download a file from S3

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
            try:
                response = self.client.head_object(
                    Bucket=self.bucket,
                    Key=key
                )
                return response['ContentLength']
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    raise FileNotFoundError(f"Object not found: {key}")
                raise

        file_size = await loop.run_in_executor(self._executor, _get_metadata)

        # Download file
        def _download():
            self.client.download_file(
                self.bucket,
                key,
                str(dest),
                Callback=self._create_progress_callback(
                    file_size, progress_callback, loop
                ) if progress_callback else None
            )

        await loop.run_in_executor(self._executor, _download)

        return {
            "path": str(dest),
            "size": file_size,
            "downloaded_at": datetime.utcnow().isoformat()
        }

    async def exists(self, remote_path: str) -> bool:
        """Check if an object exists in S3

        Args:
            remote_path: Remote object key

        Returns:
            True if object exists, False otherwise
        """
        key = self._normalize_key(remote_path)
        loop = asyncio.get_event_loop()

        def _check_exists():
            try:
                self.client.head_object(
                    Bucket=self.bucket,
                    Key=key
                )
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                raise

        return await loop.run_in_executor(self._executor, _check_exists)

    async def delete(self, remote_path: str) -> bool:
        """Delete an object from S3

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
                    Bucket=self.bucket,
                    Key=key
                )
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                raise

        return await loop.run_in_executor(self._executor, _delete)

    async def list_objects(
        self,
        prefix: str = "",
        recursive: bool = True,
        max_keys: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List objects in S3

        Args:
            prefix: Filter objects by prefix
            recursive: List recursively (always True for S3)
            max_keys: Maximum number of objects to return

        Returns:
            List of object metadata
        """
        prefix = self._normalize_key(prefix) if prefix else ""
        loop = asyncio.get_event_loop()

        def _list_objects():
            objects = []

            # Create paginator
            paginator = self.client.get_paginator('list_objects_v2')

            # Configure pagination
            page_config = {
                'Bucket': self.bucket,
                'Prefix': prefix
            }

            if max_keys and max_keys < 1000:
                page_config['MaxKeys'] = max_keys

            # Iterate through pages
            for page in paginator.paginate(**page_config):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    objects.append({
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "modified": obj['LastModified'].isoformat(),
                        "etag": obj['ETag'].strip('"'),
                        "storage_class": obj.get('StorageClass', 'STANDARD')
                    })

                    if max_keys and len(objects) >= max_keys:
                        return objects[:max_keys]

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
            try:
                response = self.client.head_object(
                    Bucket=self.bucket,
                    Key=key
                )

                return {
                    "key": key,
                    "size": response['ContentLength'],
                    "content_type": response.get('ContentType'),
                    "etag": response['ETag'].strip('"'),
                    "last_modified": response['LastModified'].isoformat(),
                    "metadata": response.get('Metadata', {}),
                    "storage_class": response.get('StorageClass', 'STANDARD')
                }
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    raise FileNotFoundError(f"Object not found: {key}")
                raise

        return await loop.run_in_executor(self._executor, _get_metadata)

    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get public URL for an object

        Args:
            remote_path: Remote object key

        Returns:
            Public URL (if bucket is public)
        """
        key = self._normalize_key(remote_path)
        return f"https://{self.bucket}.s3.{self.config['region']}.amazonaws.com/{key}"

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

        # Map method to S3 operation
        operation_map = {
            "GET": "get_object",
            "PUT": "put_object",
            "DELETE": "delete_object",
            "HEAD": "head_object"
        }

        operation = operation_map.get(method.upper(), "get_object")

        # Generate presigned URL
        url = self.client.generate_presigned_url(
            ClientMethod=operation,
            Params={
                'Bucket': self.bucket,
                'Key': key
            },
            ExpiresIn=expires_in
        )

        return url

    async def copy(
        self,
        source_path: str,
        dest_path: str
    ) -> Dict[str, Any]:
        """Copy an object within S3

        Args:
            source_path: Source key
            dest_path: Destination key

        Returns:
            Copy result metadata
        """
        source_key = self._normalize_key(source_path)
        dest_key = self._normalize_key(dest_path)

        loop = asyncio.get_event_loop()

        def _copy():
            copy_source = {
                'Bucket': self.bucket,
                'Key': source_key
            }

            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=dest_key
            )

        await loop.run_in_executor(self._executor, _copy)

        return {
            "source": source_key,
            "destination": dest_key,
            "copied_at": datetime.utcnow().isoformat()
        }

    async def close(self) -> None:
        """Close storage connections"""
        self._executor.shutdown(wait=True)
>>>>>>> Stashed changes
