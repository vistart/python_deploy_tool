"""Publish service implementation"""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

<<<<<<< Updated upstream
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
=======
from ..cli.utils.output import console
from ..constants import (
    ErrorCode,
    StorageType,
    EMOJI_SUCCESS,
    EMOJI_CLOUD,
    EMOJI_SERVER
>>>>>>> Stashed changes
)
from ..core.manifest_engine import ManifestEngine
from ..core.storage_manager import StorageManager
from ..models import (
    PublishResult,
    PublishLocationResult,
    OperationStatus,
    ErrorDetail,
    LocationInfo,
    Manifest
)
<<<<<<< Updated upstream
from ..models.manifest import ReleaseManifest, ComponentRef
from ..utils.file_utils import get_directory_size, format_bytes
=======
from ..models.config import Config, PublishTarget
from ..utils.file_utils import calculate_file_checksum, get_file_size
>>>>>>> Stashed changes


class PublishService:
    """Service for publishing components to targets"""

    def __init__(self, config: Config, storage_manager: StorageManager,
                 manifest_engine: ManifestEngine):
        """Initialize publish service

        Args:
            config: Project configuration
            storage_manager: Storage manager instance
            manifest_engine: Manifest engine instance
        """
        self.config = config
        self.storage_manager = storage_manager
        self.manifest_engine = manifest_engine

    async def publish_component(
        self,
        component_type: str,
        version: str,
        package_path: Path,
        target_names: Optional[List[str]] = None,
        interactive: bool = False
    ) -> PublishResult:
        """Publish a component to specified targets

        Args:
            component_type: Type of component
            version: Component version
            package_path: Path to package file
            target_names: List of target names (None for defaults)
            interactive: Whether to show interactive prompts

        Returns:
            PublishResult with status and details
        """
        result = PublishResult(
            status=OperationStatus.IN_PROGRESS,
            component_type=component_type,
            component_version=version
        )

        try:
<<<<<<< Updated upstream
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
=======
            # Validate package exists
            if not package_path.exists():
                result.add_error(
                    ErrorCode.SOURCE_NOT_FOUND,
                    f"Package file not found: {package_path}"
>>>>>>> Stashed changes
                )
                result.complete(OperationStatus.FAILED)
                return result

<<<<<<< Updated upstream
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
=======
            # Load or create manifest
            manifest = await self._load_or_create_manifest(
                component_type, version, package_path
            )

            # Determine targets
            targets = self._determine_targets(target_names)
            if not targets:
                result.add_error(
                    ErrorCode.MISSING_REQUIRED_PARAMETER,
                    "No publish targets specified or configured"
>>>>>>> Stashed changes
                )
                result.complete(OperationStatus.FAILED)
                return result

<<<<<<< Updated upstream
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
=======
            # Publish to each target
            tasks = []
            for target in targets:
                task = self._publish_to_target(
                    manifest, package_path, target
                )
                tasks.append(task)

            # Execute all publish tasks
            target_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for target, target_result in zip(targets, target_results):
                if isinstance(target_result, Exception):
                    # Handle exception
                    location_result = PublishLocationResult(
                        target_name=target.name,
                        status=OperationStatus.FAILED,
                        message=str(target_result),
                        error=ErrorDetail(
                            code=ErrorCode.STORAGE_CONNECTION_FAILED,
                            message=str(target_result)
                        )
                    )
                else:
                    location_result = target_result

                result.add_target_result(location_result)

                # Update manifest with successful locations
                if location_result.status == OperationStatus.SUCCESS:
                    location_info = self._create_location_info(
                        target, location_result
                    )
                    manifest.add_location(location_info)

            # Save updated manifest if any successful publishes
            if result.successful_targets:
                await self.manifest_engine.save_manifest(manifest)
                result.manifest_updated = True

            # Show target-specific guidance
            if interactive:
                self._show_publish_guidance(result, targets)

            # Set final status and message
            if result.successful_targets:
                if result.failed_targets:
                    result.message = (
                        f"Published to {len(result.successful_targets)} targets, "
                        f"{len(result.failed_targets)} failed"
                    )
                else:
                    result.message = f"Successfully published to all {len(result.successful_targets)} targets"
            else:
                result.message = "Failed to publish to any target"

            result.complete()
            return result

        except Exception as e:
            result.add_error(
                ErrorCode.STORAGE_CONNECTION_FAILED,
                f"Unexpected error during publish: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)
            return result

    async def _load_or_create_manifest(
        self,
        component_type: str,
        version: str,
        package_path: Path
    ) -> Manifest:
        """Load existing manifest or create new one"""
        # Try to load existing manifest
        manifest = await self.manifest_engine.load_manifest(component_type, version)

        if not manifest:
            # Create new manifest
            package_size = get_file_size(package_path)
            checksum = calculate_file_checksum(package_path)

            manifest = Manifest(
                component_type=component_type,
                component_version=version,
                package={
                    "file": package_path.name,
                    "size": package_size,
                    "checksum": {
                        "algorithm": "sha256",
                        "value": checksum
                    }
                }
            )

        return manifest

    def _determine_targets(self, target_names: Optional[List[str]]) -> List[PublishTarget]:
        """Determine which targets to publish to"""
        if target_names:
            # Use specified targets
            targets = []
            for name in target_names:
                target = self.config.get_target(name)
                if target and target.enabled:
                    targets.append(target)
            return targets
        else:
            # Use default targets
            targets = []
            for name in self.config.default_targets:
                target = self.config.get_target(name)
                if target and target.enabled:
                    targets.append(target)
            return targets

    async def _publish_to_target(
        self,
        manifest: Manifest,
        package_path: Path,
        target: PublishTarget
    ) -> PublishLocationResult:
        """Publish to a single target"""
        result = PublishLocationResult(
            target_name=target.name,
            status=OperationStatus.IN_PROGRESS
        )

        try:
            # Get storage backend
            storage = self.storage_manager.get_storage(target.name)

            # Determine destination path
            dest_path = self._get_destination_path(manifest, target)

            # Upload/copy file
            if target.storage_type == StorageType.FILESYSTEM:
                # For filesystem, just copy
                dest_file = Path(dest_path)
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                console.print(f"Copying to {target.name}: {dest_file}")
                shutil.copy2(package_path, dest_file)

                result.location_info = {
                    "type": "filesystem",
                    "path": str(dest_file)
                }
                result.message = f"Copied to: {dest_file}"

            else:
                # For remote storage, upload
                console.print(f"{EMOJI_CLOUD} Uploading to {target.name}...")

                upload_result = await storage.upload(
                    str(package_path),
                    dest_path
                )

                result.location_info = {
                    "type": target.type,
                    "endpoint": getattr(target, f"{target.type}_endpoint", None),
                    "bucket": getattr(target, f"{target.type}_bucket", None),
                    "object_key": dest_path
                }
                result.message = f"Uploaded to: {target.get_display_info()}"

            result.transfer_size = get_file_size(package_path)
            result.status = OperationStatus.SUCCESS

        except Exception as e:
            result.status = OperationStatus.FAILED
            result.message = f"Failed to publish to {target.name}"
            result.error = ErrorDetail(
                code=ErrorCode.STORAGE_CONNECTION_FAILED,
                message=str(e),
                context={"target": target.name, "type": target.type}
            )

        return result

    def _get_destination_path(self, manifest: Manifest, target: PublishTarget) -> str:
        """Get destination path for the target"""
        filename = f"{manifest.component_type}-{manifest.component_version}.tar.gz"

        if target.storage_type == StorageType.FILESYSTEM:
            # For filesystem, use full path
            base_path = Path(target.path)
            return str(base_path / manifest.component_type / manifest.component_version / filename)
        else:
            # For object storage, use key format
            return f"{manifest.component_type}/{manifest.component_version}/{filename}"

    def _create_location_info(
        self,
        target: PublishTarget,
        result: PublishLocationResult
    ) -> LocationInfo:
        """Create LocationInfo from publish result"""
        info = LocationInfo(
            name=target.name,
            type=target.type,
            status="success" if result.status == OperationStatus.SUCCESS else "failed",
            uploaded_at=datetime.utcnow()
>>>>>>> Stashed changes
        )

        if result.location_info:
            if "path" in result.location_info:
                info.path = result.location_info["path"]
            if "endpoint" in result.location_info:
                info.endpoint = result.location_info["endpoint"]
            if "bucket" in result.location_info:
                info.bucket = result.location_info["bucket"]
            if "object_key" in result.location_info:
                info.object_key = result.location_info["object_key"]

        if result.error:
            info.error = result.error.message

        return info

    def _show_publish_guidance(self, result: PublishResult, targets: List[PublishTarget]):
        """Show guidance based on storage types"""
        # Separate filesystem and remote targets
        fs_results = result.get_filesystem_targets()
        remote_results = [r for r in result.target_results
                         if r.target_name not in [f.target_name for f in fs_results]]

        if fs_results:
            console.print("\n📁 [bold]Filesystem Targets[/bold]")
            console.print("The following files need to be manually transferred:")

            for fs_result in fs_results:
                if fs_result.status == OperationStatus.SUCCESS:
                    console.print(f"\n  {EMOJI_SERVER} {fs_result.target_name}:")
                    console.print(f"    Local path: {fs_result.location_info['path']}")

                    # Find target config
                    target = next((t for t in targets if t.name == fs_result.target_name), None)
                    if target:
                        console.print(f"    Suggested remote path: {target.path}")
                        console.print(f"    Transfer command example:")
                        console.print(f"      rsync -avz {fs_result.location_info['path']} server:{target.path}/")

        if remote_results:
            console.print(f"\n{EMOJI_CLOUD} [bold]Remote Storage Targets[/bold]")
            console.print("The following uploads completed automatically:")

            for remote_result in remote_results:
                if remote_result.status == OperationStatus.SUCCESS:
                    console.print(f"\n  {EMOJI_SUCCESS} {remote_result.target_name}: {remote_result.message}")

    async def list_published_versions(
        self,
        component_type: str
    ) -> Dict[str, List[str]]:
        """List published versions for a component

        Args:
            component_type: Type of component

        Returns:
            Dict mapping version to list of published locations
        """
        versions = {}

        # Load all manifests for the component
        manifests = await self.manifest_engine.list_manifests(component_type)

        for version, manifest in manifests.items():
            locations = []
            for loc in manifest.get_successful_locations():
                locations.append(f"{loc.name} ({loc.type})")

            if locations:
                versions[version] = locations

        return versions