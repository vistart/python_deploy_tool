"""Baidu Object Storage (BOS) backend implementation"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from .base import StorageBackend


class BOSStorage(StorageBackend):
    """Baidu Object Storage implementation"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize BOS storage

        Args:
            config: BOS configuration including:
                - access_key: Access key
                - secret_key: Secret key
                - bucket: Bucket name
                - endpoint: BOS endpoint
        """
        super().__init__(config)
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