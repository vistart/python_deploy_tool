# deploy_tool/services/publish_service.py
"""Publish service implementation"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..api.exceptions import (
    PublishError,
    ComponentNotFoundError,
    FileExistsError,
)
from ..constants import MANIFEST_VERSION
from ..core import (
    ManifestEngine,
    StorageManager,
    ComponentRegistry,
    GitAdvisor,
)
from ..models import (
    PublishResult,
    ComponentPublishResult,
    PublishComponent,
)
from ..models.manifest import ReleaseManifest, ComponentRef


class PublishService:
    """Publishing service implementation"""

    def __init__(self,
                 storage_manager: StorageManager,
                 manifest_engine: ManifestEngine,
                 component_registry: ComponentRegistry):
        """
        Initialize publish service

        Args:
            storage_manager: Storage manager instance
            manifest_engine: Manifest engine instance
            component_registry: Component registry instance
        """
        self.storage_manager = storage_manager
        self.manifest_engine = manifest_engine
        self.component_registry = component_registry
        self.path_resolver = storage_manager.path_resolver
        self.git_advisor = GitAdvisor(self.path_resolver)

    async def publish(self,
                      components: List[PublishComponent],
                      release_version: Optional[str] = None,
                      release_name: Optional[str] = None,
                      options: Optional[Dict[str, Any]] = None) -> PublishResult:
        """
        Publish components workflow

        Args:
            components: Components to publish
            release_version: Release version
            release_name: Release name
            options: Additional options

        Returns:
            PublishResult: Publishing result
        """
        start_time = time.time()
        options = options or {}
        published_components = []
        errors = []

        try:
            # 1. Validate components
            await self._validate_components(components)

            # 2. Check release conflicts
            if release_version:
                await self._check_release_conflicts(release_version, options)

            # 3. Publish each component
            for component in components:
                comp_result = await self._publish_single_component(
                    component,
                    options.get('force', False)
                )
                published_components.append(comp_result)

                if not comp_result.success:
                    errors.append(comp_result.error)
                    if options.get('atomic', True):
                        # Rollback on atomic failure
                        await self._rollback_published(published_components[:-1])
                        raise PublishError(f"Atomic publish failed: {comp_result.error}")

            # 4. Create and save release manifest
            release_manifest_path = None
            if release_version:
                release_manifest = self._create_release_manifest(
                    release_version,
                    release_name,
                    published_components
                )

                release_manifest_path = await self._save_and_upload_release(
                    release_manifest,
                    options
                )

                # 5. Provide Git advice
                self._provide_git_advice(release_version, published_components)

            # 6. Create result
            return PublishResult(
                success=len(errors) == 0,
                release_version=release_version,
                release_manifest=str(release_manifest_path) if release_manifest_path else None,
                components=published_components,
                error=errors[0] if errors else None,
                duration=time.time() - start_time
            )

        except Exception as e:
            return PublishResult(
                success=False,
                release_version=release_version,
                components=published_components,
                error=str(e),
                duration=time.time() - start_time
            )

    async def _validate_components(self, components: List[PublishComponent]) -> None:
        """Validate all components exist"""
        for component in components:
            # Find manifest if not specified
            if not component.manifest_path:
                manifest_path = self.manifest_engine.find_manifest(
                    component.type,
                    component.version
                )

                if not manifest_path:
                    raise ComponentNotFoundError(component.type, component.version)

                component.manifest_path = str(manifest_path)
            else:
                # Verify manifest exists
                manifest_path = Path(component.manifest_path)
                if not manifest_path.exists():
                    raise ComponentNotFoundError(component.type, component.version)

    async def _check_release_conflicts(self,
                                       release_version: str,
                                       options: Dict[str, Any]) -> None:
        """Check for release conflicts"""
        # Check local release
        release_path = self.path_resolver.get_release_path(release_version)
        if release_path.exists() and not options.get('force', False):
            raise FileExistsError(str(release_path))

        # Check remote release
        if await self.storage_manager.release_exists(release_version):
            if not options.get('force', False):
                raise PublishError(
                    f"Release {release_version} already exists in storage. "
                    "Use --force to overwrite."
                )

    async def _publish_single_component(self,
                                        component: PublishComponent,
                                        force: bool) -> ComponentPublishResult:
        """Publish single component"""
        try:
            # Load manifest
            manifest = self.manifest_engine.load_manifest(Path(component.manifest_path))

            # Get archive path
            archive_location = manifest.archive.get('location')
            if not archive_location:
                raise PublishError(f"No archive location in manifest for {component}")

            archive_path = self.path_resolver.resolve(archive_location)
            if not archive_path.exists():
                raise PublishError(f"Archive file not found: {archive_path}")

            # Check if already published
            exists = await self.storage_manager.component_exists(
                component.type,
                component.version
            )

            if exists and not force:
                # Already published, return success
                storage_path = self.storage_manager._path_helper.get_archive_path(
                    component.type,
                    component.version,
                    archive_path.name
                )

                return ComponentPublishResult(
                    component=component,
                    success=True,
                    storage_path=storage_path
                )

            # Upload component with progress
            def progress_callback(uploaded: int, total: int):
                # TODO: Integrate with progress reporting system
                pass

            storage_path = await self.storage_manager.upload_component(
                archive_path,
                component.type,
                component.version,
                callback=progress_callback
            )

            # Upload manifest
            await self.storage_manager.upload_manifest(
                Path(component.manifest_path),
                component.type,
                component.version
            )

            # Update component metadata
            component.archive_path = str(archive_path)
            component.archive_size = archive_path.stat().st_size
            component.storage_path = storage_path

            # Calculate checksum if not present
            if not component.checksum:
                component.checksum = manifest.archive.get('checksum', {}).get('sha256')

            # Register in component registry
            self.component_registry.register_component(Path(component.manifest_path))

            return ComponentPublishResult(
                component=component,
                success=True,
                storage_path=storage_path
            )

        except Exception as e:
            return ComponentPublishResult(
                component=component,
                success=False,
                error=str(e)
            )

    async def _rollback_published(self, components: List[ComponentPublishResult]) -> None:
        """Rollback published components"""
        for comp_result in components:
            if comp_result.success:
                try:
                    await self.storage_manager.delete_component(
                        comp_result.component.type,
                        comp_result.component.version
                    )
                except Exception:
                    # Ignore rollback errors
                    pass

    def _create_release_manifest(self,
                                 release_version: str,
                                 release_name: Optional[str],
                                 components: List[ComponentPublishResult]) -> ReleaseManifest:
        """Create release manifest"""
        # Create component references
        component_refs = []
        for comp_result in components:
            if comp_result.success:
                ref = ComponentRef(
                    type=comp_result.component.type,
                    version=comp_result.component.version,
                    manifest=comp_result.component.manifest_path
                )
                component_refs.append(ref)

        # Create release info
        release_info = {
            'version': release_version,
            'created_at': datetime.now().isoformat(),
            'component_count': len(component_refs),
        }

        if release_name:
            release_info['name'] = release_name

        # Add metadata
        metadata = {
            'total_size': sum(
                c.component.archive_size
                for c in components
                if c.success and c.component.archive_size
            ),
            'published_by': self._get_publisher_info(),
        }

        return ReleaseManifest(
            manifest_version=MANIFEST_VERSION,
            release=release_info,
            components=component_refs,
            metadata=metadata
        )

    async def _save_and_upload_release(self,
                                       release_manifest: ReleaseManifest,
                                       options: Dict[str, Any]) -> Path:
        """Save and upload release manifest"""
        # Save locally
        release_path = self.path_resolver.get_release_path(
            release_manifest.release['version']
        )

        release_path.parent.mkdir(parents=True, exist_ok=True)

        import json
        with open(release_path, 'w') as f:
            json.dump(release_manifest.to_dict(), f, indent=2, ensure_ascii=False)

        # Upload to storage
        await self.storage_manager.upload_release(
            release_path,
            release_manifest.release['version']
        )

        return release_path

    def _provide_git_advice(self,
                            release_version: str,
                            components: List[ComponentPublishResult]) -> None:
        """Provide Git operation advice"""
        manifest_paths = [
            Path(c.component.manifest_path)
            for c in components
            if c.success
        ]

        self.git_advisor.provide_post_publish_advice(
            release_version,
            manifest_paths
        )

    def _get_publisher_info(self) -> Dict[str, str]:
        """Get publisher information"""
        import os
        import socket

        return {
            'user': os.environ.get('USER', 'unknown'),
            'host': socket.gethostname(),
            'timestamp': datetime.now().isoformat(),
        }