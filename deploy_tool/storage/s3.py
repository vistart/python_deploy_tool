"""Amazon S3 storage backend implementation"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from .base import StorageBackend


class S3Storage(StorageBackend):
    """Amazon S3 storage implementation"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize S3 storage

        Args:
            config: S3 configuration including:
                - access_key_id: AWS access key ID
                - secret_access_key: AWS secret access key
                - bucket: S3 bucket name
                - region: AWS region
                - endpoint_url: Custom endpoint URL (optional)
        """
        super().__init__(config)
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