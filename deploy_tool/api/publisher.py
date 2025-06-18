"""Publisher API for publishing operations"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core import (
    PathResolver,
    ManifestEngine,
    StorageManager,
    ComponentRegistry,
    GitAdvisor,
)
from ..models import (
    PublishResult,
    ComponentPublishResult,
    Component,
    PublishComponent,
)
from ..models.manifest import ReleaseManifest, ComponentRef
from ..constants import MANIFEST_VERSION
from .exceptions import (
    PublishError,
    ComponentNotFoundError,
    ValidationError,
    StorageError,
    FileExistsError,
)


class Publisher:
    """Publisher class for publishing operations"""

    def __init__(self, storage_config: Optional[Dict[str, Any]] = None):
        """
        Initialize publisher

        Args:
            storage_config: Storage configuration
        """
        self.storage_config = storage_config or {}
        self.path_resolver = PathResolver()
        self.manifest_engine = ManifestEngine(self.path_resolver)
        self.component_registry = ComponentRegistry(
            self.path_resolver,
            self.manifest_engine
        )
        self.git_advisor = GitAdvisor(self.path_resolver)

        # Initialize storage manager
        storage_type = self.storage_config.get('type', 'filesystem')
        self.storage_manager = StorageManager(
            storage_type=storage_type,
            config=self.storage_config,
            path_resolver=self.path_resolver
        )

    def publish(self,
                components: List[Component],
                release_version: str = None,
                release_name: str = None,
                force: bool = False,
                atomic: bool = True) -> PublishResult:
        """
        Publish components

        Args:
            components: List of components to publish
            release_version: Release version (optional)
            release_name: Release name (optional)
            force: Force overwrite
            atomic: Atomic operation

        Returns:
            PublishResult: Publishing result

        Raises:
            PublishError: If publishing fails
            ComponentNotFoundError: If component not found
        """
        # Convert to PublishComponent if needed
        publish_components = []
        for comp in components:
            if isinstance(comp, Component):
                publish_comp = PublishComponent(
                    type=comp.type,
                    version=comp.version,
                    manifest_path=comp.manifest_path
                )
            else:
                publish_comp = comp
            publish_components.append(publish_comp)

        # Run async publish
        return asyncio.run(self._async_publish(
            publish_components,
            release_version,
            release_name,
            force,
            atomic
        ))

    def publish_component(self,
                          component_type: str,
                          component_version: str,
                          **options) -> PublishResult:
        """
        Publish single component

        Args:
            component_type: Component type
            component_version: Component version
            **options: Additional options

        Returns:
            PublishResult: Publishing result
        """
        component = Component(
            type=component_type,
            version=component_version
        )

        return self.publish([component], **options)

    async def _async_publish(self,
                             components: List[PublishComponent],
                             release_version: str = None,
                             release_name: str = None,
                             force: bool = False,
                             atomic: bool = True) -> PublishResult:
        """Async publish implementation"""
        start_time = time.time()
        published_components = []
        errors = []

        try:
            # Validate all components exist
            for component in components:
                # Find manifest
                if component.manifest_path:
                    manifest_path = Path(component.manifest_path)
                else:
                    manifest_path = self.manifest_engine.find_manifest(
                        component.type,
                        component.version
                    )

                if not manifest_path or not manifest_path.exists():
                    raise ComponentNotFoundError(
                        component.type,
                        component.version
                    )

                component.manifest_path = str(manifest_path)

            # Check if release already exists
            if release_version:
                release_path = self.path_resolver.get_release_path(release_version)
                if release_path.exists() and not force:
                    raise FileExistsError(str(release_path))

                # Check remote
                if await self.storage_manager.release_exists(release_version):
                    if not force:
                        raise PublishError(
                            f"Release {release_version} already exists. "
                            "Use --force to overwrite."
                        )

            # Publish each component
            for component in components:
                try:
                    result = await self._publish_single_component(
                        component, force
                    )
                    published_components.append(result)

                except Exception as e:
                    error_result = ComponentPublishResult(
                        component=component,
                        success=False,
                        error=str(e)
                    )
                    published_components.append(error_result)
                    errors.append(str(e))

                    if atomic:
                        # Rollback if atomic
                        await self._rollback_published(published_components[:-1])
                        raise PublishError(
                            f"Atomic publish failed: {str(e)}"
                        )

            # Create release manifest if specified
            release_manifest_path = None
            if release_version:
                release_manifest = self._create_release_manifest(
                    release_version,
                    release_name,
                    published_components
                )

                # Save release manifest
                release_manifest_path = self._save_release_manifest(
                    release_manifest
                )

                # Upload release manifest
                await self.storage_manager.upload_release(
                    release_manifest_path,
                    release_version
                )

                # Provide git advice
                self.git_advisor.provide_post_publish_advice(
                    release_version,
                    [Path(c.component.manifest_path) for c in published_components]
                )

            # Create result
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

    async def _publish_single_component(self,
                                        component: PublishComponent,
                                        force: bool) -> ComponentPublishResult:
        """Publish single component"""
        try:
            # Load manifest
            manifest = self.manifest_engine.load_manifest(
                Path(component.manifest_path)
            )

            # Get archive path
            archive_location = manifest.archive.get('location')
            if not archive_location:
                raise PublishError(
                    f"No archive location in manifest for {component}"
                )

            archive_path = self.path_resolver.resolve(archive_location)
            if not archive_path.exists():
                raise PublishError(
                    f"Archive file not found: {archive_path}"
                )

            # Check if already published
            if await self.storage_manager.component_exists(
                component.type,
                component.version
            ):
                if not force:
                    # Already published, return success
                    return ComponentPublishResult(
                        component=component,
                        success=True,
                        storage_path=self.storage_manager._path_helper.get_archive_path(
                            component.type,
                            component.version,
                            archive_path.name
                        )
                    )

            # Upload component
            def progress_callback(uploaded: int, total: int):
                # TODO: Add progress reporting
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

            # Update component info
            component.archive_path = str(archive_path)
            component.archive_size = archive_path.stat().st_size
            component.storage_path = storage_path

            # Register in component registry
            self.component_registry.register_component(
                Path(component.manifest_path)
            )

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

    async def _rollback_published(self,
                                  components: List[ComponentPublishResult]):
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
                                 release_name: str,
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
        }

        if release_name:
            release_info['name'] = release_name

        # Create release manifest
        return ReleaseManifest(
            manifest_version=MANIFEST_VERSION,
            release=release_info,
            components=component_refs
        )

    def _save_release_manifest(self,
                               release_manifest: ReleaseManifest) -> Path:
        """Save release manifest to file"""
        release_path = self.path_resolver.get_release_path(
            release_manifest.release['version']
        )

        # Ensure directory exists
        release_path.parent.mkdir(parents=True, exist_ok=True)

        # Save
        import json
        with open(release_path, 'w') as f:
            json.dump(release_manifest.to_dict(), f, indent=2, ensure_ascii=False)

        return release_path


# Convenience function
def publish(components: List[Component] = None, **options) -> PublishResult:
    """
    Publish components (convenience function)

    Args:
        components: List of components to publish
        **options: Options
            - component: Single component (alternative to components list)
            - release_version: Release version
            - release_name: Release name
            - storage_config: Storage configuration

    Returns:
        PublishResult: Publishing result
    """
    # Handle component vs components
    if components is None:
        components = []

    # Handle single component option
    if 'component' in options:
        comp_spec = options['component']
        if isinstance(comp_spec, str) and ':' in comp_spec:
            # Parse "type:version" format
            comp_type, version = comp_spec.split(':', 1)
            components.append(Component(type=comp_type, version=version))
        else:
            components.append(comp_spec)

    if not components:
        raise PublishError("No components specified for publishing")

    # Get storage config
    storage_config = options.pop('storage_config', None)

    publisher = Publisher(storage_config)
    return publisher.publish(components, **options)