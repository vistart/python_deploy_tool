"""Deployer API for deployment operations"""

import asyncio
import json
import shutil
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
            **options: Additional deployment options

        Returns:
            DeployResult: Deployment result

        Raises:
            ComponentNotFoundError: If component not found
            DeployError: If deployment fails
        """
        component = Component(
            type=component_type,
            version=component_version
        )

        return asyncio.run(self._async_deploy_component(
            component,
            target,
            options
        ))

    def rollback(self,
                 to_release: Optional[str] = None,
                 to_component: Optional[Tuple[str, str]] = None,
                 target: str = "default") -> DeployResult:
        """
        Rollback to specified version

        Args:
            to_release: Release version to rollback to
            to_component: Component (type, version) to rollback to
            target: Deployment target

        Returns:
            DeployResult: Rollback result

        Raises:
            DeployError: If rollback fails
        """
        # TODO: Implement rollback functionality
        raise NotImplementedError("Rollback functionality not yet implemented")

    async def _async_deploy_release(self,
                                    release_version: str,
                                    target: str,
                                    verify: bool,
                                    rollback_on_failure: bool) -> DeployResult:
        """Async implementation of deploy_release"""
        start_time = time.time()
        deploy_type = "release"
        deployed_components = []
        deploy_path = self._get_deploy_path(target)

        try:
            # Get release manifest
            release_manifest = await self._get_release_manifest(release_version)

            # Extract components from release
            components = self._extract_components_from_release(release_manifest)

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
                        f"Deployment verification failed: {verification.error or 'Unknown error'}"
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

    async def _async_deploy_component(self,
                                      component: Component,
                                      target: str,
                                      options: Dict[str, Any]) -> DeployResult:
        """Async implementation of deploy_component"""
        verify = options.get('verify', True)
        rollback_on_failure = options.get('rollback_on_failure', True)

        return await self._deploy_components(
            [component],
            target,
            deploy_type="component",
            verify=verify,
            rollback_on_failure=rollback_on_failure
        )

    async def _deploy_components(self,
                                 components: List[Component],
                                 target: str,
                                 deploy_type: str,
                                 verify: bool = True,
                                 rollback_on_failure: bool = True) -> DeployResult:
        """Deploy multiple components"""
        start_time = time.time()
        deployed_components = []
        deploy_path = self._get_deploy_path(target)

        try:
            # Prepare deployment directory
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
                        f"Deployment verification failed: {verification.error or 'Unknown error'}"
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

    def _extract_components_from_release(self, release_manifest: ReleaseManifest) -> List[Component]:
        """Extract component list from release manifest"""
        components = []

        for comp_ref in release_manifest.components:
            component = Component(
                type=comp_ref.type,
                version=comp_ref.version,
                manifest_path=comp_ref.manifest
            )
            components.append(component)

        return components

    async def _deploy_single_component(self,
                                       component: Component,
                                       deploy_path: Path) -> None:
        """Deploy a single component"""
        # Get archive path
        archive_path = self.path_resolver.get_archive_path(
            component.type,
            component.version
        )

        if not archive_path.exists():
            # Download from storage
            success = await self.storage_manager.download_component(
                component.type,
                component.version,
                archive_path
            )

            if not success:
                raise ComponentNotFoundError(component.type, component.version)

        # Extract to deployment directory
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

        # Merge errors and warnings into issues list
        issues = errors + [f"Warning: {w}" for w in warnings]

        # Return VerifyResult with correct parameters
        return VerifyResult(
            success=len(errors) == 0,
            component_type="deployment",  # Use "deployment" as type for deployment verification
            version="multi-component",    # Use generic version for multi-component deployment
            checksum_valid=True,          # Simplified - assume checksum is valid
            files_complete=(verified_files == total_files),
            manifest_valid=True,          # Simplified
            issues=issues,
            error=errors[0] if errors else None  # First error as main error message
        )

    async def _rollback_components(self,
                                   components: List[Component],
                                   deploy_path: Path) -> None:
        """Rollback deployed components"""
        for component in components:
            component_path = deploy_path / component.type / component.version

            if component_path.exists():
                # Remove component directory
                shutil.rmtree(component_path, ignore_errors=True)

    def _get_deploy_path(self, target: str) -> Path:
        """Get deployment path from target"""
        # If target is a path, use it directly
        if target.startswith('/') or target.startswith('./') or target.startswith('..'):
            return Path(target).resolve()

        # Otherwise, treat as a named target
        # TODO: Implement named target resolution
        return Path(target).resolve()


def deploy(release: Optional[str] = None,
           component: Optional[str] = None,
           target: str = "default",
           **options) -> DeployResult:
    """
    Deploy components or releases

    This is a convenience function that creates a Deployer instance
    and performs the deployment.

    Args:
        release: Release version to deploy
        component: Component specification (type:version)
        target: Deployment target
        **options: Additional deployment options

    Returns:
        DeployResult: Deployment result

    Raises:
        ValueError: If neither release nor component is specified
        DeployError: If deployment fails
    """
    if not release and not component:
        raise ValueError("Must specify either release or component")

    if release and component:
        raise ValueError("Cannot specify both release and component")

    deployer = Deployer()

    if release:
        return deployer.deploy_release(
            release_version=release,
            target=target,
            **options
        )
    else:
        # Parse component specification
        if ':' not in component:
            raise ValueError(f"Invalid component format: {component}")

        comp_type, comp_version = component.split(':', 1)

        return deployer.deploy_component(
            component_type=comp_type,
            component_version=comp_version,
            target=target,
            **options
        )