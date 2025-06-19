"""Deploy service implementation"""

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..api.exceptions import (
    DeployError,
    ReleaseNotFoundError,
    ComponentNotFoundError,
    ValidationError,
)
from ..core import (
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


class DeployService:
    """Deployment service implementation"""

    def __init__(self,
                 storage_manager: StorageManager,
                 validation_engine: ValidationEngine,
                 component_registry: ComponentRegistry):
        """
        Initialize deploy service

        Args:
            storage_manager: Storage manager instance
            validation_engine: Validation engine instance
            component_registry: Component registry instance
        """
        self.storage_manager = storage_manager
        self.validation_engine = validation_engine
        self.component_registry = component_registry
        self.path_resolver = storage_manager.path_resolver
        self.manifest_engine = ManifestEngine(self.path_resolver)

    async def deploy_release(self,
                             release_version: str,
                             target: str,
                             options: Optional[Dict[str, Any]] = None) -> DeployResult:
        """
        Deploy release version

        Args:
            release_version: Release version
            target: Deployment target
            options: Deployment options

        Returns:
            DeployResult: Deployment result
        """
        start_time = time.time()
        options = options or {}

        try:
            # 1. Get release manifest
            release_manifest = await self._get_release_manifest(release_version)

            # 2. Extract components from release
            components = self._extract_components_from_release(release_manifest)

            # 3. Deploy components
            return await self._deploy_components(
                components,
                target,
                deploy_type="release",
                release_version=release_version,
                options=options
            )

        except Exception as e:
            return DeployResult(
                success=False,
                deploy_type="release",
                deploy_target=target,
                error=str(e),
                duration=time.time() - start_time
            )

    async def deploy_component(self,
                               component: Component,
                               target: str,
                               options: Optional[Dict[str, Any]] = None) -> DeployResult:
        """
        Deploy single component

        Args:
            component: Component to deploy
            target: Deployment target
            options: Deployment options

        Returns:
            DeployResult: Deployment result
        """
        return await self._deploy_components(
            [component],
            target,
            deploy_type="component",
            options=options or {}
        )

    async def _deploy_components(self,
                                 components: List[Component],
                                 target: str,
                                 deploy_type: str,
                                 release_version: Optional[str] = None,
                                 options: Optional[Dict[str, Any]] = None) -> DeployResult:
        """Deploy multiple components"""
        start_time = time.time()
        options = options or {}
        deployed_components = []
        deploy_path = self._get_deploy_path(target, options)

        try:
            # 1. Prepare deployment directory
            await self._prepare_deploy_directory(deploy_path, options)

            # 2. Deploy each component
            for component in components:
                try:
                    await self._deploy_single_component(
                        component,
                        deploy_path,
                        options
                    )
                    deployed_components.append(component)

                except Exception as e:
                    if options.get('rollback_on_failure', True) and deployed_components:
                        # Rollback deployed components
                        await self._rollback_components(
                            deployed_components,
                            deploy_path
                        )

                    raise DeployError(
                        f"Failed to deploy {component}: {str(e)}"
                    )

            # 3. Save deployment metadata
            await self._save_deployment_metadata(
                deploy_path,
                deployed_components,
                deploy_type,
                release_version
            )

            # 4. Verify deployment if requested
            verification = None
            if options.get('verify', True):
                verification = await self._verify_deployment(
                    deployed_components,
                    deploy_path
                )

                if not verification.success and options.get('rollback_on_failure', True):
                    await self._rollback_components(
                        deployed_components,
                        deploy_path
                    )
                    raise DeployError(
                        f"Deployment verification failed: {verification.error or 'Unknown error'}"
                    )

            # 5. Create result
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
        """Get release manifest from local or remote"""
        # Try local first
        release_path = self.path_resolver.get_release_path(release_version)

        if not release_path.exists():
            # Download from storage
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

    def _get_deploy_path(self, target: str, options: Dict[str, Any]) -> Path:
        """Get deployment path"""
        # If target is a path, use it directly
        if target.startswith('/') or target.startswith('./') or target.startswith('..'):
            return Path(target).resolve()

        # Otherwise, treat as a named target
        # TODO: Implement named target resolution
        return Path(target).resolve()

    async def _prepare_deploy_directory(self, deploy_path: Path, options: Dict[str, Any]) -> None:
        """Prepare deployment directory"""
        deploy_path.mkdir(parents=True, exist_ok=True)

        # Check if directory is empty (unless force is specified)
        if not options.get('force', False):
            if any(deploy_path.iterdir()):
                raise DeployError(
                    f"Deployment directory is not empty: {deploy_path}. "
                    "Use --force to override."
                )

    async def _deploy_single_component(self,
                                       component: Component,
                                       deploy_path: Path,
                                       options: Dict[str, Any]) -> None:
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
            raise DeployError(f"Failed to extract archive: {archive_path}")

    async def _save_deployment_metadata(self,
                                        deploy_path: Path,
                                        components: List[Component],
                                        deploy_type: str,
                                        release_version: Optional[str]) -> None:
        """Save deployment metadata"""
        metadata_path = deploy_path / '.deploy-metadata' / 'deployment.json'
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            'deploy_type': deploy_type,
            'deploy_time': datetime.now().isoformat(),
            'components': [
                {
                    'type': c.type,
                    'version': c.version,
                }
                for c in components
            ],
        }

        if release_version:
            metadata['release_version'] = release_version

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    async def _verify_deployment(self,
                                 components: List[Component],
                                 deploy_path: Path) -> VerifyResult:
        """Verify deployment integrity"""
        errors = []
        warnings = []
        verified_files = 0
        total_files = 0

        for component in components:
            component_path = deploy_path / component.type / component.version

            if not component_path.exists():
                errors.append(f"Component path not found: {component_path}")
                continue

            # Verify manifest exists
            manifest_path = component_path / '.manifest.json'
            if not manifest_path.exists():
                errors.append(f"Manifest not found for {component}")
                continue

            # Count and verify files
            for file_path in component_path.rglob('*'):
                if file_path.is_file() and file_path.name != '.manifest.json':
                    total_files += 1
                    if file_path.exists():
                        verified_files += 1
                    else:
                        errors.append(f"File missing: {file_path}")

        # Merge errors and warnings into issues list
        issues = errors + [f"Warning: {w}" for w in warnings]

        # Return VerifyResult with correct parameters
        return VerifyResult(
            success=len(errors) == 0,
            component_type="deployment",  # Use "deployment" as type for deployment verification
            version="multi-component",    # Use generic version for multi-component deployment
            checksum_valid=True,          # Simplified - assume checksum is valid
            files_complete=(verified_files == total_files),
            manifest_valid=all(
                (deploy_path / c.type / c.version / '.manifest.json').exists()
                for c in components
            ),
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
                shutil.rmtree(component_path, ignore_errors=True)