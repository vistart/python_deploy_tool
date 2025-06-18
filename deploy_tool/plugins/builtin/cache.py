"""Caching plugin for deployment operations"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import Plugin, PluginInfo, PluginContext, PluginPriority, HookPoint
from ...utils.hash_utils import calculate_directory_hash, calculate_file_hash
from ...constants import DEFAULT_CACHE_DIR


class CachePlugin(Plugin):
    """Provides caching for expensive operations"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Cache configuration
        self.cache_dir = Path(config.get('cache_dir', DEFAULT_CACHE_DIR)) if config else Path(DEFAULT_CACHE_DIR)
        self.ttl_seconds = config.get('ttl_seconds', 3600) if config else 3600  # 1 hour default
        self.max_cache_size_mb = config.get('max_size_mb', 100) if config else 100

        # Initialize cache
        self._init_cache()

    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="cache",
            version="1.0.0",
            description="Caching for deployment operations",
            author="Deploy Tool Team",
            priority=PluginPriority.HIGH,
            hook_points=[
                HookPoint.PACK_PRE,
                HookPoint.PACK_POST,
                HookPoint.COMPONENT_VALIDATE,
                HookPoint.STORAGE_DOWNLOAD_PRE,
                HookPoint.STORAGE_DOWNLOAD_POST,
            ],
            config=self.config
        )

    def _init_cache(self) -> None:
        """Initialize cache directory and metadata"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_metadata_file = self.cache_dir / ".cache_metadata.json"

        # Load or create metadata
        if self.cache_metadata_file.exists():
            try:
                with open(self.cache_metadata_file, 'r') as f:
                    self.cache_metadata = json.load(f)
            except:
                self.cache_metadata = {}
        else:
            self.cache_metadata = {}

    def _save_metadata(self) -> None:
        """Save cache metadata"""
        try:
            with open(self.cache_metadata_file, 'w') as f:
                json.dump(self.cache_metadata, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache metadata: {e}")

    def _get_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate cache key from operation and parameters"""
        # Create a stable string representation
        param_str = json.dumps(params, sort_keys=True)
        return f"{operation}:{hash(param_str)}"

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        if 'timestamp' not in cache_entry:
            return False

        created = datetime.fromisoformat(cache_entry['timestamp'])
        age = datetime.now() - created

        return age.total_seconds() < self.ttl_seconds

    async def on_pack_pre(self, context: PluginContext) -> PluginContext:
        """Check cache before packing"""
        source_path = context.data.get('source_path')
        package_type = context.data.get('package_type')
        version = context.data.get('version')

        if not all([source_path, package_type, version]):
            return context

        # Calculate source hash
        source_path = Path(source_path)
        if source_path.is_dir():
            source_hash = await calculate_directory_hash(source_path)
        else:
            source_hash = calculate_file_hash(source_path)

        # Check cache
        cache_key = self._get_cache_key('pack', {
            'type': package_type,
            'version': version,
            'source_hash': source_hash
        })

        if cache_key in self.cache_metadata:
            cache_entry = self.cache_metadata[cache_key]

            if self._is_cache_valid(cache_entry):
                cached_archive = self.cache_dir / cache_entry['archive_name']

                if cached_archive.exists():
                    # Found valid cache
                    self.logger.info(f"Cache hit for {package_type}:{version}")
                    context.data['cached_archive'] = str(cached_archive)
                    context.metadata['cache_hit'] = True

                    # Skip packing by adding special flag
                    context.data['skip_pack'] = True

        # Store source hash for post-hook
        context.metadata['source_hash'] = source_hash

        return context

    async def on_pack_post(self, context: PluginContext) -> PluginContext:
        """Update cache after successful packing"""
        if context.has_errors() or context.data.get('skip_pack'):
            return context

        archive_path = context.data.get('archive_path')
        package_type = context.data.get('package_type')
        version = context.data.get('version')
        source_hash = context.metadata.get('source_hash')

        if all([archive_path, package_type, version, source_hash]):
            # Copy to cache
            archive_path = Path(archive_path)
            cache_name = f"{package_type}-{version}-{source_hash[:8]}.tar.gz"
            cached_path = self.cache_dir / cache_name

            try:
                import shutil
                shutil.copy2(archive_path, cached_path)

                # Update metadata
                cache_key = self._get_cache_key('pack', {
                    'type': package_type,
                    'version': version,
                    'source_hash': source_hash
                })

                self.cache_metadata[cache_key] = {
                    'archive_name': cache_name,
                    'timestamp': datetime.now().isoformat(),
                    'size': archive_path.stat().st_size
                }

                self._save_metadata()
                self.logger.info(f"Cached archive for {package_type}:{version}")

                # Clean old cache entries if needed
                await self._cleanup_cache()

            except Exception as e:
                self.logger.warning(f"Failed to cache archive: {e}")

        return context

    async def on_storage_download_pre(self, context: PluginContext) -> PluginContext:
        """Check local cache before downloading"""
        remote_path = context.data.get('remote_path')
        checksum = context.data.get('expected_checksum')

        if remote_path and checksum:
            # Look for cached file by checksum
            for cache_file in self.cache_dir.glob("*.tar.gz"):
                if checksum[:8] in cache_file.name:
                    # Verify full checksum
                    actual_checksum = calculate_file_hash(cache_file)
                    if actual_checksum == checksum:
                        self.logger.info(f"Cache hit for download: {remote_path}")
                        context.data['cached_file'] = str(cache_file)
                        context.data['skip_download'] = True
                        break

        return context

    async def on_storage_download_post(self, context: PluginContext) -> PluginContext:
        """Cache downloaded files"""
        if context.has_errors() or context.data.get('skip_download'):
            return context

        local_path = context.data.get('local_path')
        checksum = context.data.get('checksum')

        if local_path and checksum:
            # Copy to cache
            local_path = Path(local_path)
            cache_name = f"download-{checksum[:8]}-{local_path.name}"
            cached_path = self.cache_dir / cache_name

            try:
                import shutil
                shutil.copy2(local_path, cached_path)
                self.logger.info(f"Cached downloaded file: {local_path.name}")
            except Exception as e:
                self.logger.warning(f"Failed to cache download: {e}")

        return context

    async def _cleanup_cache(self) -> None:
        """Clean up old or oversized cache"""
        try:
            # Calculate total cache size
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
            max_size = self.max_cache_size_mb * 1024 * 1024

            if total_size > max_size:
                # Remove oldest files
                cache_files = sorted(
                    self.cache_dir.glob("*"),
                    key=lambda f: f.stat().st_mtime
                )

                while total_size > max_size * 0.8 and cache_files:  # Keep 80% threshold
                    oldest = cache_files.pop(0)
                    if oldest.is_file() and oldest != self.cache_metadata_file:
                        size = oldest.stat().st_size
                        oldest.unlink()
                        total_size -= size

                        # Remove from metadata
                        for key, entry in list(self.cache_metadata.items()):
                            if entry.get('archive_name') == oldest.name:
                                del self.cache_metadata[key]

                self._save_metadata()
                self.logger.info("Cache cleanup completed")

        except Exception as e:
            self.logger.error(f"Cache cleanup failed: {e}")

    async def clear_cache(self) -> None:
        """Clear all cache"""
        try:
            for cache_file in self.cache_dir.glob("*"):
                if cache_file != self.cache_metadata_file:
                    cache_file.unlink()

            self.cache_metadata.clear()
            self._save_metadata()

            self.logger.info("Cache cleared")

        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")