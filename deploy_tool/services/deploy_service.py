"""Deploy service implementation"""

import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

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
from ..api.exceptions import (
    DeployError,
    ReleaseNotFoundError,
    ComponentNotFoundError,
    ValidationError,
)


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
                        f"Deployment verification failed: {verification.errors[0]}"
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

    def _extract_components_from_release(self,
                                         release_manifest: ReleaseManifest) -> List[Component]:
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
        """Get deployment path for target"""
        # Check if target is a path
        if Path(target).is_absolute() or target.startswith(('./', '../')):
            return self.path_resolver.resolve(target)

        # Otherwise treat as named target
        if target == "default":
            default_path = options.get('default_path', './deploy')
            return self.path_resolver.resolve(default_path)
        else:
            # Named target
            return self.path_resolver.resolve(f'./deploy/{target}')

    async def _prepare_deploy_directory(self,
                                        deploy_path: Path,
                                        options: Dict[str, Any]) -> None:
        """Prepare deployment directory"""
        # Create if not exists
        deploy_path.mkdir(parents=True, exist_ok=True)

        # Clean if requested
        if options.get('clean', False):
            # Remove all contents except metadata
            for item in deploy_path.iterdir():
                if item.name not in ['.deploy-metadata', '.manifests', '.archives']:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

    async def _deploy_single_component(self,
                                       component: Component,
                                       deploy_path: Path,
                                       options: Dict[str, Any]) -> None:
        """Deploy single component"""
        # 1. Get manifest
        manifest_path = await self._get_component_manifest(component, deploy_path)
        manifest = self.manifest_engine.load_manifest(manifest_path)

        # 2. Download archive if needed
        archive_path = await self._download_component_archive(
            component,
            manifest,
            deploy_path,
            options
        )

        # 3. Verify archive integrity
        validation_result = self.validation_engine.validate_archive_integrity(
            archive_path,
            manifest.archive['checksum']['sha256']
        )

        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors[0])

        # 4. Extract archive
        component_path = deploy_path / component.type / component.version
        await self._extract_component(
            archive_path,
            component_path,
            options
        )

        # 5. Save component manifest in deployment
        deploy_manifest_path = component_path / '.manifest.json'
        shutil.copy2(manifest_path, deploy_manifest_path)

    async def _get_component_manifest(self,
                                      component: Component,
                                      deploy_path: Path) -> Path:
        """Get component manifest"""
        # Use provided path if available
        if component.manifest_path:
            manifest_path = Path(component.manifest_path)
            if manifest_path.exists():
                return manifest_path

        # Try to find locally
        manifest_path = self.manifest_engine.find_manifest(
            component.type,
            component.version
        )

        if manifest_path:
            return manifest_path

        # Download from storage
        temp_manifest = deploy_path / ".manifests" / f"{component.type}-{component.version}.manifest.json"
        temp_manifest.parent.mkdir(parents=True, exist_ok=True)

        success = await self.storage_manager.download_manifest(
            component.type,
            component.version,
            temp_manifest
        )

        if not success:
            raise ComponentNotFoundError(component.type, component.version)

        return temp_manifest

    async def _download_component_archive(self,
                                          component: Component,
                                          manifest: Any,
                                          deploy_path: Path,
                                          options: Dict[str, Any]) -> Path:
        """Download component archive if needed"""
        archive_filename = manifest.archive['filename']
        archive_path = deploy_path / ".archives" / archive_filename
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if already exists and valid
        if archive_path.exists():
            # Verify checksum
            validation_result = self.validation_engine.validate_archive_integrity(
                archive_path,
                manifest.archive['checksum']['sha256']
            )

            if validation_result.is_valid:
                return archive_path

        # Download with progress
        def progress_callback(downloaded: int, total: int):
            # TODO: Integrate with progress reporting
            pass

        success = await self.storage_manager.download_component(
            component.type,
            component.version,
            archive_filename,
            archive_path,
            callback=progress_callback
        )

        if not success:
            raise DeployError(f"Failed to download component {component}")

        return archive_path

    async def _extract_component(self,
                                 archive_path: Path,
                                 component_path: Path,
                                 options: Dict[str, Any]) -> None:
        """Extract component archive"""
        # Clean existing if requested
        if component_path.exists() and options.get('overwrite', True):
            shutil.rmtree(component_path)

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
                                   deploy_path: Path) -> None:
        """Rollback deployed components"""
        for component in components:
            component_path = deploy_path / component.type / component.version

            if component_path.exists():
                shutil.rmtree(component_path, ignore_errors=True)


from datetime import datetime