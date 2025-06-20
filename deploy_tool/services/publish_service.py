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
from ..constants import MANIFEST_VERSION, STORAGE_OVERHEAD_WARNING_SIZE
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
from ..utils.file_utils import get_directory_size, format_bytes


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

            # 3. Calculate total size and warn about overhead
            total_size = await self._calculate_publish_size(components)
            if total_size > STORAGE_OVERHEAD_WARNING_SIZE:
                self._warn_about_storage_overhead(total_size)

            # 4. Publish each component
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

            # 5. Create release if specified
            release_path = None
            if release_version:
                release_manifest = await self._create_release_manifest(
                    release_version,
                    release_name,
                    published_components,
                    options
                )

                release_path = await self._save_and_upload_release(
                    release_manifest,
                    options
                )

            # 6. Get post-publish instructions
            post_publish_instructions = []
            if release_version and release_path:
                backend = self.storage_manager.backend
                instructions = backend.get_post_publish_instructions(
                    release_version,
                    release_path.parent
                )
                post_publish_instructions = instructions

            # 7. Provide Git advice
            self._provide_git_advice(release_version, published_components)

            return PublishResult(
                success=len(errors) == 0,
                release_version=release_version,
                release_path=str(release_manifest) if release_manifest else None,
                published_components=published_components,
                error=errors[0] if errors else None,
                duration=time.time() - start_time
            )

        except Exception as e:
            return PublishResult(
                success=False,
                release_version=release_version,
                published_components=published_components,
                error=str(e),
                duration=time.time() - start_time
            )

    async def _calculate_publish_size(self, components: List[PublishComponent]) -> int:
        """Calculate total size of components to publish"""
        total_size = 0
        for component in components:
            archive_path = self.path_resolver.get_archive_path(
                component.type,
                component.version
            )
            if archive_path.exists():
                total_size += archive_path.stat().st_size
        return total_size

    def _warn_about_storage_overhead(self, total_size: int) -> None:
        """Warn user about storage overhead"""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        size_str = format_bytes(total_size)

        warning = Panel(
            f"[yellow]⚠️  Publishing will copy {size_str} of data.[/yellow]\n\n"
            "This may require:\n"
            f"• Additional storage space: ~{size_str}\n"
            "• Extra time for copying large files\n\n"
            "Consider using cloud storage (S3/BOS) for large packages.",
            title="[bold yellow]Storage Overhead Warning[/bold yellow]",
            border_style="yellow"
        )
        console.print(warning)

    async def _validate_components(self, components: List[PublishComponent]) -> None:
        """Validate components before publishing"""
        for component in components:
            # Check if manifest exists
            manifest_path = self.path_resolver.get_manifest_path(
                component.type,
                component.version
            )

            if not manifest_path.exists():
                raise ComponentNotFoundError(
                    f"Component manifest not found: {component.type}:{component.version}"
                )

            # Check if archive exists
            archive_path = self.path_resolver.get_archive_path(
                component.type,
                component.version
            )

            if not archive_path.exists():
                raise ComponentNotFoundError(
                    f"Component archive not found: {archive_path}"
                )

    async def _check_release_conflicts(self,
                                       release_version: str,
                                       options: Dict[str, Any]) -> None:
        """Check for release conflicts"""
        release_path = self.path_resolver.get_release_path(release_version)

        if release_path.exists() and not options.get('force', False):
            raise FileExistsError(
                f"Release {release_version} already exists. Use --force to overwrite."
            )

    async def _publish_single_component(self,
                                        component: PublishComponent,
                                        force: bool = False) -> ComponentPublishResult:
        """Publish single component"""
        try:
            # Get archive path
            archive_path = self.path_resolver.get_archive_path(
                component.type,
                component.version
            )

            # Upload to storage
            remote_path = await self.storage_manager.upload_component(
                archive_path,
                component.type,
                component.version
            )

            # Record in registry
            await self.component_registry.register_published(
                component.type,
                component.version,
                remote_path
            )

            return ComponentPublishResult(
                success=True,
                component=component,
                remote_path=remote_path
            )

        except Exception as e:
            return ComponentPublishResult(
                success=False,
                component=component,
                error=str(e)
            )

    async def _rollback_published(self,
                                  published: List[ComponentPublishResult]) -> None:
        """Rollback published components"""
        for comp_result in published:
            if comp_result.success:
                try:
                    # Delete from storage
                    await self.storage_manager.backend.delete(
                        comp_result.remote_path
                    )

                    # Remove from registry
                    await self.component_registry.unregister_published(
                        comp_result.component.type,
                        comp_result.component.version
                    )
                except Exception:
                    # Log error but continue rollback
                    pass

    async def _create_release_manifest(self,
                                       release_version: str,
                                       release_name: Optional[str],
                                       components: List[ComponentPublishResult],
                                       options: Dict[str, Any]) -> ReleaseManifest:
        """Create release manifest"""
        # Build component references
        component_refs = []
        for comp_result in components:
            if comp_result.success:
                manifest_path = self.path_resolver.get_manifest_path(
                    comp_result.component.type,
                    comp_result.component.version
                )

                comp_ref = ComponentRef(
                    type=comp_result.component.type,
                    version=comp_result.component.version,
                    manifest=str(manifest_path.relative_to(self.path_resolver.project_root))
                )
                component_refs.append(comp_ref)

        # Build metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'created_by': self._get_publisher_info(),
            'options': options
        }

        return ReleaseManifest(
            version=MANIFEST_VERSION,
            release={
                'version': release_version,
                'name': release_name or f"Release {release_version}",
                'description': options.get('description', '')
            },
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