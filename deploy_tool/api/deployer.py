"""Deployer API for deployment operations"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from ..core import (
    PathResolver,
    ManifestEngine,
    StorageManager,
    ValidationEngine,
    ComponentRegistry,
)
from ..core.compression import TarProcessor
from ..models import (
    DeployResult,
    VerifyResult,
    Component,
)
from ..models.manifest import ReleaseManifest
from .exceptions import (
    DeployError,
    ReleaseNotFoundError,
    ComponentNotFoundError,
    ValidationError,
)


class Deployer:
    """Deployer class for deployment operations"""

    def __init__(self, target_config: Optional[Dict[str, Any]] = None):
        """
        Initialize deployer

        Args:
            target_config: Deployment target configuration
        """
        self.target_config = target_config or {}
        self.path_resolver = PathResolver()
        self.manifest_engine = ManifestEngine(self.path_resolver)
        self.validation_engine = ValidationEngine()
        self.component_registry = ComponentRegistry(
            self.path_resolver,
            self.manifest_engine
        )

        # Initialize storage manager
        storage_config = self.target_config.get('storage', {})
        storage_type = storage_config.get('type', 'filesystem')
        self.storage_manager = StorageManager(
            storage_type=storage_type,
            config=storage_config,
            path_resolver=self.path_resolver
        )

    def deploy_release(self,
                       release_version: str,
                       target: str = "default",
                       verify: bool = True,
                       rollback_on_failure: bool = True) -> DeployResult:
        """
        Deploy release version

        Args:
            release_version: Release version
            target: Deployment target
            verify: Whether to verify after deployment
            rollback_on_failure: Whether to rollback on failure

        Returns:
            DeployResult: Deployment result

        Raises:
            ReleaseNotFoundError: If release not found
            DeployError: If deployment fails
        """
        return asyncio.run(self._async_deploy_release(
            release_version,
            target,
            verify,
            rollback_on_failure
        ))

    def deploy_component(self,
                         component_type: str,
                         component_version: str,
                         target: str = "default",
                         **options) -> DeployResult:
        """
        Deploy single component

        Args:
            component_type: Component type
            component_version: Component version
            target: Deployment target
            **options: Additional options

        Returns:
            DeployResult: Deployment result
        """
        component = Component(
            type=component_type,
            version=component_version
        )

        return asyncio.run(self._async_deploy_components(
            [component],
            target,
            deploy_type="component",
            **options
        ))

    def rollback(self,
                 to_release: str = None,
                 to_component: Tuple[str, str] = None,
                 target: str = "default") -> DeployResult:
        """
        Rollback to specified version

        Args:
            to_release: Target release version
            to_component: Target component (type, version)
            target: Deployment target

        Returns:
            DeployResult: Rollback result
        """
        if to_release:
            return self.deploy_release(to_release, target)
        elif to_component:
            return self.deploy_component(
                to_component[0],
                to_component[1],
                target
            )
        else:
            raise DeployError("Must specify either release or component to rollback")

    async def _async_deploy_release(self,
                                    release_version: str,
                                    target: str,
                                    verify: bool,
                                    rollback_on_failure: bool) -> DeployResult:
        """Async deploy release implementation"""
        start_time = time.time()

        try:
            # Get release manifest
            release_manifest = await self._get_release_manifest(release_version)

            # Extract components
            components = []
            for comp_ref in release_manifest.components:
                component = Component(
                    type=comp_ref.type,
                    version=comp_ref.version,
                    manifest_path=comp_ref.manifest
                )
                components.append(component)

            # Deploy components
            return await self._async_deploy_components(
                components,
                target,
                deploy_type="release",
                verify=verify,
                rollback_on_failure=rollback_on_failure,
                release_version=release_version
            )

        except Exception as e:
            return DeployResult(
                success=False,
                deploy_type="release",
                deploy_target=target,
                error=str(e),
                duration=time.time() - start_time
            )

    async def _async_deploy_components(self,
                                       components: List[Component],
                                       target: str,
                                       deploy_type: str,
                                       verify: bool = True,
                                       rollback_on_failure: bool = True,
                                       release_version: str = None) -> DeployResult:
        """Deploy multiple components"""
        start_time = time.time()
        deployed_components = []
        deploy_path = self._get_deploy_path(target)

        try:
            # Ensure deploy path exists
            deploy_path.mkdir(parents=True, exist_ok=True)

            # Deploy each component
            for component in components:
                try:
                    await self._deploy_single_component(
                        component,
                        deploy_path
                    )
                    deployed_components.append(component)

                except Exception as e:
                    if rollback_on_failure and deployed_components:
                        # Rollback deployed components
                        await self._rollback_components(
                            deployed_components,
                            deploy_path
                        )

                    raise DeployError(
                        f"Failed to deploy {component}: {str(e)}"
                    )

            # Verify deployment if requested
            verification = None
            if verify:
                verification = await self._verify_deployment(
                    deployed_components,
                    deploy_path
                )

                if not verification.success and rollback_on_failure:
                    # Rollback if verification failed
                    await self._rollback_components(
                        deployed_components,
                        deploy_path
                    )
                    raise DeployError(
                        f"Deployment verification failed: {verification.errors[0]}"
                    )

            # Create result
            return DeployResult(
                success=True,
                deploy_type=deploy_type,
                deploy_target=target,
                deployed_components=deployed_components,
                duration=time.time() - start_time,
                verification=verification
            )

        except Exception as e:
            return DeployResult(
                success=False,
                deploy_type=deploy_type,
                deploy_target=target,
                deployed_components=deployed_components,
                error=str(e),
                duration=time.time() - start_time
            )

    async def _get_release_manifest(self, release_version: str) -> ReleaseManifest:
        """Get release manifest"""
        # Try local first
        release_path = self.path_resolver.get_release_path(release_version)

        if not release_path.exists():
            # Try to download from storage
            success = await self.storage_manager.download_release(
                release_version,
                release_path
            )

            if not success:
                raise ReleaseNotFoundError(release_version)

        # Load manifest
        with open(release_path, 'r') as f:
            data = json.load(f)

        return ReleaseManifest.from_dict(data)

    async def _deploy_single_component(self,
                                       component: Component,
                                       deploy_path: Path):
        """Deploy single component"""
        # Find manifest
        if component.manifest_path:
            manifest_path = Path(component.manifest_path)
        else:
            # Try local
            manifest_path = self.manifest_engine.find_manifest(
                component.type,
                component.version
            )

            if not manifest_path:
                # Try to download
                temp_manifest = deploy_path / ".manifests" / f"{component.type}-{component.version}.manifest.json"
                temp_manifest.parent.mkdir(parents=True, exist_ok=True)

                success = await self.storage_manager.download_manifest(
                    component.type,
                    component.version,
                    temp_manifest
                )

                if not success:
                    raise ComponentNotFoundError(
                        component.type,
                        component.version
                    )

                manifest_path = temp_manifest

        # Load manifest
        manifest = self.manifest_engine.load_manifest(manifest_path)

        # Get archive info
        archive_filename = manifest.archive['filename']

        # Download archive if not exists
        archive_path = deploy_path / ".archives" / archive_filename
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        if not archive_path.exists():
            def progress_callback(downloaded: int, total: int):
                # TODO: Add progress reporting
                pass

            success = await self.storage_manager.download_component(
                component.type,
                component.version,
                archive_filename,
                archive_path,
                callback=progress_callback
            )

            if not success:
                raise DeployError(
                    f"Failed to download component {component}"
                )

        # Verify archive integrity
        validation_result = self.validation_engine.validate_archive_integrity(
            archive_path,
            manifest.archive['checksum']['sha256']
        )

        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors[0])

        # Extract archive
        component_path = deploy_path / component.type / component.version
        component_path.mkdir(parents=True, exist_ok=True)

        # Use TarProcessor to extract
        processor = TarProcessor()
        success = await processor.extract_with_progress(
            archive_path,
            component_path
        )

        if not success:
            raise DeployError(
                f"Failed to extract component {component}"
            )

    async def _verify_deployment(self,
                                 components: List[Component],
                                 deploy_path: Path) -> VerifyResult:
        """Verify deployment"""
        errors = []
        warnings = []
        verified_files = 0
        total_files = 0

        for component in components:
            component_path = deploy_path / component.type / component.version

            if not component_path.exists():
                errors.append(
                    f"Component path not found: {component_path}"
                )
                continue

            # Count files
            for file_path in component_path.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    # Simple existence check
                    if file_path.exists():
                        verified_files += 1
                    else:
                        errors.append(
                            f"File missing: {file_path}"
                        )

        return VerifyResult(
            success=len(errors) == 0,
            target_type="deployment",
            errors=errors,
            warnings=warnings,
            verified_files=verified_files,
            total_files=total_files
        )

    async def _rollback_components(self,
                                   components: List[Component],
                                   deploy_path: Path):
        """Rollback deployed components"""
        for component in components:
            component_path = deploy_path / component.type / component.version

            if component_path.exists():
                # Remove component directory
                import shutil
                shutil.rmtree(component_path, ignore_errors=True)

    def _get_deploy_path(self, target: str) -> Path:
        """Get deployment path for target"""
        if target == "default":
            # Use configured default path
            default_path = self.target_config.get('default_path', './deploy')
            return self.path_resolver.resolve(default_path)
        else:
            # Target could be a path or a named target
            if Path(target).is_absolute() or target.startswith(('./', '../')):
                # It's a path
                return self.path_resolver.resolve(target)
            else:
                # It's a named target
                targets = self.target_config.get('targets', {})
                if target in targets:
                    target_path = targets[target].get('path', f'./deploy/{target}')
                    return self.path_resolver.resolve(target_path)
                else:
                    # Default to subdirectory
                    return self.path_resolver.resolve(f'./deploy/{target}')


# Convenience function
def deploy(**options) -> DeployResult:
    """
    Deploy components or release (convenience function)

    Args:
        **options: Options
            - release: Release version to deploy
            - component: Single component to deploy (type:version)
            - target: Deployment target
            - verify: Whether to verify deployment
            - target_config: Target configuration

    Returns:
        DeployResult: Deployment result
    """
    # Get target config
    target_config = options.pop('target_config', None)

    deployer = Deployer(target_config)

    if 'release' in options:
        return deployer.deploy_release(
            release_version=options.pop('release'),
            **options
        )
    elif 'component' in options:
        comp_spec = options.pop('component')
        if isinstance(comp_spec, str) and ':' in comp_spec:
            # Parse "type:version" format
            comp_type, version = comp_spec.split(':', 1)
            return deployer.deploy_component(
                component_type=comp_type,
                component_version=version,
                **options
            )
        else:
            raise DeployError("Invalid component specification")
    else:
        raise DeployError("Must specify either release or component to deploy")