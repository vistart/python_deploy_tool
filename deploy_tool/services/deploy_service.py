"""Deploy service implementation with failover support"""

import asyncio
import os
import shutil
<<<<<<< Updated upstream
import time
=======
import tarfile
import tempfile
from datetime import datetime
>>>>>>> Stashed changes
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models import (
    DeployResult,
    OperationStatus,
    DeploymentState,
    Manifest
)
<<<<<<< Updated upstream
from ..models.manifest import ReleaseManifest
from ..constants import DEPLOYMENT_METADATA_FILE
=======
from ..models.config import Config, PublishTarget
from ..core.storage_manager import StorageManager
from ..core.manifest_engine import ManifestEngine
from ..core.path_resolver import PathResolver
from ..utils.file_utils import calculate_file_checksum, extract_archive
from ..utils.output import console
from ..constants import (
    ErrorCode,
    StorageType,
    COMPONENTS_DIR,
    LINKS_DIR,
    CURRENT_LINK_NAME,
    DEPLOYMENT_STATE_FILE,
    MSG_FAILOVER_RETRY,
    MSG_FAILOVER_SUCCESS,
    MSG_FAILOVER_EXHAUSTED,
    EMOJI_SUCCESS,
    EMOJI_WARNING,
    EMOJI_ERROR,
    EMOJI_LINK
)


class FailoverManager:
    """Manages failover logic for deployment sources"""

    def __init__(self, config: Config):
        self.config = config
        self.failover_config = config.deploy.failover

    def get_ordered_sources(
        self,
        available_sources: List[str],
        preferred_source: Optional[str] = None
    ) -> List[str]:
        """Get ordered list of sources to try

        Args:
            available_sources: List of available source names
            preferred_source: User-preferred source (if any)

        Returns:
            Ordered list of sources to try
        """
        if not self.failover_config.enabled:
            # Failover disabled, only try preferred or first available
            if preferred_source and preferred_source in available_sources:
                return [preferred_source]
            elif available_sources:
                return [available_sources[0]]
            else:
                return []

        # Start with preferred source if specified
        ordered = []
        if preferred_source and preferred_source in available_sources:
            ordered.append(preferred_source)

        # Add sources based on configured priority
        for source in self.config.deploy.source_priority:
            if source in available_sources and source not in ordered:
                ordered.append(source)

        # Add any remaining sources
        for source in available_sources:
            if source not in ordered:
                ordered.append(source)

        return ordered

    def should_retry(self, attempt: int) -> bool:
        """Check if we should retry after a failure"""
        return attempt <= self.failover_config.retry_count

    def get_retry_delay(self, attempt: int) -> float:
        """Get delay before next retry"""
        return self.failover_config.get_retry_delay(attempt)


class LinkManager:
    """Manages symbolic links for deployed components"""

    def __init__(self, deploy_root: Path):
        self.deploy_root = deploy_root
        self.components_dir = deploy_root / COMPONENTS_DIR
        self.links_dir = deploy_root / LINKS_DIR

    def create_version_link(
        self,
        component_type: str,
        version: str
    ) -> Path:
        """Create or update the current version link

        Args:
            component_type: Type of component
            version: Version to link to

        Returns:
            Path to the current link
        """
        component_dir = self.components_dir / component_type
        version_dir = component_dir / version
        current_link = component_dir / CURRENT_LINK_NAME

        if not version_dir.exists():
            raise ValueError(f"Version directory does not exist: {version_dir}")

        # Create atomic symlink update
        temp_link = current_link.with_suffix('.tmp')

        # Remove temp link if it exists
        if temp_link.exists() or temp_link.is_symlink():
            temp_link.unlink()

        # Create new link
        temp_link.symlink_to(version, target_is_directory=True)

        # Atomically replace old link
        temp_link.replace(current_link)

        return current_link

    def create_component_link(self, component_type: str) -> Path:
        """Create or update the component link in links directory

        Args:
            component_type: Type of component

        Returns:
            Path to the component link
        """
        self.links_dir.mkdir(parents=True, exist_ok=True)

        source = Path("..") / COMPONENTS_DIR / component_type / CURRENT_LINK_NAME
        link = self.links_dir / component_type

        # Create atomic symlink update
        temp_link = link.with_suffix('.tmp')

        # Remove temp link if it exists
        if temp_link.exists() or temp_link.is_symlink():
            temp_link.unlink()

        # Create new link
        temp_link.symlink_to(source, target_is_directory=True)

        # Atomically replace old link
        if link.exists() or link.is_symlink():
            temp_link.replace(link)
        else:
            temp_link.rename(link)

        return link

    def update_custom_links(
        self,
        component_type: str,
        custom_links: Dict[str, str]
    ) -> List[str]:
        """Update custom links for a component

        Args:
            component_type: Type of component
            custom_links: Mapping of custom paths to deployment paths

        Returns:
            List of updated link paths
        """
        updated = []

        for custom_path, deploy_path in custom_links.items():
            # Check if this link is for our component
            if component_type in deploy_path:
                custom_link = Path(custom_path)
                custom_link.parent.mkdir(parents=True, exist_ok=True)

                # Determine target
                if deploy_path.endswith(component_type):
                    # Link to component in links dir
                    target = self.links_dir / component_type
                else:
                    # Direct link to component dir
                    target = self.components_dir / component_type / CURRENT_LINK_NAME

                # Create atomic update
                temp_link = custom_link.with_suffix('.tmp')
                if temp_link.exists() or temp_link.is_symlink():
                    temp_link.unlink()

                temp_link.symlink_to(target, target_is_directory=True)

                if custom_link.exists() or custom_link.is_symlink():
                    temp_link.replace(custom_link)
                else:
                    temp_link.rename(custom_link)

                updated.append(str(custom_link))

        return updated
>>>>>>> Stashed changes


class DeployService:
    """Service for deploying components with failover support"""

    def __init__(
        self,
        config: Config,
        storage_manager: StorageManager,
        manifest_engine: ManifestEngine,
        path_resolver: PathResolver
    ):
        """Initialize deploy service

        Args:
            config: Project configuration
            storage_manager: Storage manager instance
            manifest_engine: Manifest engine instance
            path_resolver: Path resolver instance
        """
        self.config = config
        self.storage_manager = storage_manager
        self.manifest_engine = manifest_engine
        self.path_resolver = path_resolver

        self.deploy_root = Path(config.deploy.root)
        self.failover_manager = FailoverManager(config)
        self.link_manager = LinkManager(self.deploy_root)

    async def deploy_component(
        self,
        component_type: str,
        version: str,
        source_name: Optional[str] = None,
        force: bool = False
    ) -> DeployResult:
        """Deploy a component with automatic failover

        Args:
            component_type: Type of component
            version: Component version
            source_name: Preferred source name (optional)
            force: Force redeployment even if version exists

        Returns:
            DeployResult with status and details
        """
        result = DeployResult(
            status=OperationStatus.IN_PROGRESS,
            component_type=component_type,
            component_version=version
        )

        try:
            # Load manifest
            manifest = await self.manifest_engine.load_manifest(component_type, version)
            if not manifest:
                result.add_error(
                    ErrorCode.COMPONENT_NOT_FOUND,
                    f"No manifest found for {component_type}:{version}"
                )
                result.complete(OperationStatus.FAILED)
                return result

            # Check if already deployed
            deploy_path = self.deploy_root / COMPONENTS_DIR / component_type / version
            if deploy_path.exists() and not force:
                console.print(
                    f"{EMOJI_WARNING} Version {version} already deployed at {deploy_path}"
                )
                # Just update links
                await self._update_links(component_type, version, result)
                result.message = f"Version already deployed, updated links"
                result.complete(OperationStatus.SUCCESS)
                return result

            # Get available sources
            available_sources = [
                loc.name for loc in manifest.get_successful_locations()
            ]

            if not available_sources:
                result.add_error(
                    ErrorCode.NO_AVAILABLE_SOURCE,
                    "No published sources available for deployment"
                )
                result.complete(OperationStatus.FAILED)
                return result

            # Get ordered sources for failover
            sources = self.failover_manager.get_ordered_sources(
                available_sources, source_name
            )

            # Try each source with failover
            deployed = False
            for idx, source in enumerate(sources, 1):
                result.sources_tried.append(source)

                console.print(f"\n🔄 Attempting to deploy from {source}...")

<<<<<<< Updated upstream
            # 2. Deploy each component to versioned directory
            for component in components:
                try:
                    await self._deploy_single_component(
                        component,
                        deploy_path,
                        release_version,
                        options
=======
                try:
                    await self._deploy_from_source(
                        manifest, source, deploy_path
>>>>>>> Stashed changes
                    )

                    result.source_used = source
                    deployed = True

                    console.print(
                        MSG_FAILOVER_SUCCESS.format(
                            source=source,
                            attempts=len(result.sources_tried)
                        )
                    )
                    break

                except Exception as e:
<<<<<<< Updated upstream
                    if options.get('rollback_on_failure', True) and deployed_components:
                        # Rollback deployed components
                        await self._rollback_components(
                            deployed_components,
                            deploy_path,
                            release_version
                        )
=======
                    console.print(f"{EMOJI_ERROR} Failed: {str(e)}")
>>>>>>> Stashed changes

                    if idx < len(sources):
                        # More sources to try
                        console.print(MSG_FAILOVER_RETRY.format(source=source))

<<<<<<< Updated upstream
            # 3. Create/update symbolic links
            await self._create_symlinks(
                deployed_components,
                deploy_path,
                release_version,
                options
            )

            # 4. Save deployment metadata
            await self._save_deployment_metadata(
                deploy_path,
                deployed_components,
                deploy_type,
                release_version
            )

            # 5. Verify deployment if requested
            verification = None
            if options.get('verify', True):
                verification = await self._verify_deployment(
                    deployed_components,
                    deploy_path,
                    release_version
=======
                        # Delay before retry (if configured)
                        if self.failover_manager.failover_config.enabled:
                            delay = self.failover_manager.get_retry_delay(idx)
                            if delay > 0:
                                console.print(f"⏳ Waiting {delay}s before retry...")
                                await asyncio.sleep(delay)

            if not deployed:
                result.add_error(
                    ErrorCode.FAILOVER_EXHAUSTED,
                    MSG_FAILOVER_EXHAUSTED
>>>>>>> Stashed changes
                )
                result.complete(OperationStatus.FAILED)
                return result

<<<<<<< Updated upstream
                if not verification.success and options.get('rollback_on_failure', True):
                    # Rollback if verification failed
                    await self._rollback_components(
                        deployed_components,
                        deploy_path,
                        release_version
                    )
                    raise DeployError(
                        f"Deployment verification failed: {verification.errors[0]}"
                    )

            # 6. Create result
            return DeployResult(
                success=True,
                deploy_type=deploy_type,
                deploy_target=target,
                deployed_components=deployed_components,
                duration=time.time() - start_time,
                verification=verification
            )
=======
            # Update deployment state
            await self._update_deployment_state(component_type, version, result.source_used)

            # Update links
            await self._update_links(component_type, version, result)

            # Set result
            result.deploy_path = deploy_path
            result.message = f"Successfully deployed {component_type}:{version}"
            result.complete(OperationStatus.SUCCESS)

            return result
>>>>>>> Stashed changes

        except Exception as e:
            result.add_error(
                ErrorCode.DEPLOY_TARGET_UNREACHABLE,
                f"Unexpected error during deployment: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)
            return result

    async def _deploy_from_source(
        self,
        manifest: Manifest,
        source_name: str,
        deploy_path: Path
    ) -> None:
        """Deploy from a specific source

        Args:
            manifest: Component manifest
            source_name: Source to deploy from
            deploy_path: Destination deployment path
        """
        # Get location info
        location = manifest.get_location(source_name)
        if not location:
            raise ValueError(f"Source {source_name} not found in manifest")

        # Get storage backend
        storage = self.storage_manager.get_storage(source_name)

        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download package
            if location.storage_type == StorageType.FILESYSTEM:
                # Copy from filesystem
                source_file = Path(location.path)
                if not source_file.exists():
                    raise FileNotFoundError(f"Source file not found: {source_file}")

<<<<<<< Updated upstream
    def _extract_components_from_release(self,
                                         release_manifest: ReleaseManifest) -> List[Component]:
        """Extract component list from release manifest"""
        components = []
=======
                download_path = temp_path / source_file.name
                console.print(f"📁 Copying from {source_file}")
                shutil.copy2(source_file, download_path)
>>>>>>> Stashed changes

            else:
                # Download from remote storage
                download_path = temp_path / f"{manifest.component_type}-{manifest.component_version}.tar.gz"
                console.print(f"☁️  Downloading from {location.display_path}")

<<<<<<< Updated upstream
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

<<<<<<< HEAD
        # Create releases subdirectory
        releases_dir = deploy_path / "releases"
        releases_dir.mkdir(exist_ok=True)

        # Check if directory is empty (unless force is specified)
        if not options.get('force', False):
            # Only check non-releases content
            non_releases_content = [p for p in deploy_path.iterdir()
                                    if p.name not in ['releases', DEPLOYMENT_METADATA_FILE]]
            if non_releases_content:
                # Check if symlinks exist
                symlinks_exist = any(p.is_symlink() for p in non_releases_content)
                if not symlinks_exist:
                    raise DeployError(
                        f"Deployment directory contains non-symlink files: {deploy_path}. "
                        "Use --force to override."
                    )
=======
        # Clean if requested
        if options.get('clean', False):
            # Remove all contents except metadata
            for item in deploy_path.iterdir():
                if item.name not in ['.deploy-metadata', '.manifests', '.archives']:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

    async def _deploy_single_component(self,
                                       component: Component,
                                       deploy_path: Path,
                                       release_version: Optional[str],
                                       options: Dict[str, Any]) -> None:
<<<<<<< HEAD
        """Deploy a single component to versioned directory"""
        # Get archive path
        archive_path = self.path_resolver.get_archive_path(
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
            component.type,
            component.version
        )

<<<<<<< HEAD
        if not archive_path.exists():
            # Download from storage
            success = await self.storage_manager.download_component(
                component.type,
                component.version,
                archive_path.name,
                archive_path
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
=======
                await storage.download(
                    location.object_key,
                    str(download_path)
                )

            # Verify checksum
            if manifest.package:
                expected_checksum = manifest.package.checksum.value
                actual_checksum = calculate_file_checksum(download_path)

                if actual_checksum != expected_checksum:
                    raise ValueError(
                        f"Checksum mismatch: expected {expected_checksum}, "
                        f"got {actual_checksum}"
                    )

            # Extract to deployment directory
            deploy_path.parent.mkdir(parents=True, exist_ok=True)

            console.print(f"📦 Extracting to {deploy_path}")
            extract_archive(download_path, deploy_path)

            console.print(f"{EMOJI_SUCCESS} Deployed to {deploy_path}")

    async def _update_deployment_state(
        self,
        component_type: str,
        version: str,
        source: str
    ) -> None:
        """Update deployment state file"""
        state_file = self.deploy_root / DEPLOYMENT_STATE_FILE

        # Load existing state
        states = {}
        if state_file.exists():
            import json
            with open(state_file, 'r') as f:
                data = json.load(f)
                for comp_type, state_data in data.items():
                    states[comp_type] = DeploymentState.from_dict(state_data)

        # Update or create state for component
        if component_type not in states:
            states[component_type] = DeploymentState(component_type=component_type)

        state = states[component_type]
        state.add_version(version, source)
        state.set_current(version)

        # Save updated state
        state_file.parent.mkdir(parents=True, exist_ok=True)

        import json
        with open(state_file, 'w') as f:
            data = {
                comp_type: state.to_dict()
                for comp_type, state in states.items()
            }
            json.dump(data, f, indent=2)

    async def _update_links(
        self,
        component_type: str,
        version: str,
        result: DeployResult
    ) -> None:
        """Update all links for the component"""
        # Get current version before update
        state = await self._get_deployment_state(component_type)
        if state and state.current_version and state.current_version != version:
            result.previous_version = state.current_version
            result.version_switched = True

        # Update version link (current -> version)
        version_link = self.link_manager.create_version_link(component_type, version)
        console.print(f"{EMOJI_LINK} Updated version link: {version_link}")

        # Update component link (links/component -> ../components/component/current)
        component_link = self.link_manager.create_component_link(component_type)
        result.links_updated.append(str(component_link))
        console.print(f"{EMOJI_LINK} Updated component link: {component_link}")

        # Update custom links if configured
        if self.config.deploy.custom_links:
            custom_updated = self.link_manager.update_custom_links(
                component_type,
                self.config.deploy.custom_links
>>>>>>> Stashed changes
            )
            result.links_updated.extend(custom_updated)

<<<<<<< Updated upstream
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

<<<<<<< HEAD
        # Extract to versioned deployment directory
        if release_version:
            # Deploy to releases/release_version/component_type/component_version/
            component_path = deploy_path / "releases" / release_version / component.type / component.version
        else:
            # Direct component deployment: component_type/component_version/
            component_path = deploy_path / component.type / component.version

=======
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
        component_path.mkdir(parents=True, exist_ok=True)
=======
            for link in custom_updated:
                console.print(f"{EMOJI_LINK} Updated custom link: {link}")

    async def _get_deployment_state(self, component_type: str) -> Optional[DeploymentState]:
        """Get deployment state for a component"""
        state_file = self.deploy_root / DEPLOYMENT_STATE_FILE
>>>>>>> Stashed changes

        if not state_file.exists():
            return None

        import json
        with open(state_file, 'r') as f:
            data = json.load(f)

        if component_type in data:
            return DeploymentState.from_dict(data[component_type])

        return None

    async def switch_version(
        self,
        component_type: str,
        version: str
    ) -> DeployResult:
        """Switch to a different deployed version

        Args:
            component_type: Type of component
            version: Version to switch to

        Returns:
            DeployResult with status
        """
        result = DeployResult(
            status=OperationStatus.IN_PROGRESS,
            component_type=component_type,
            component_version=version
        )

        try:
            # Check if version is deployed
            deploy_path = self.deploy_root / COMPONENTS_DIR / component_type / version
            if not deploy_path.exists():
                result.add_error(
                    ErrorCode.VERSION_NOT_FOUND,
                    f"Version {version} is not deployed"
                )
                result.complete(OperationStatus.FAILED)
                return result

<<<<<<< Updated upstream
    async def _create_symlinks(self,
                               components: List[Component],
                               deploy_path: Path,
                               release_version: Optional[str],
                               options: Dict[str, Any]) -> None:
        """Create symbolic links to maintain consistent paths"""
        for component in components:
            # Source: versioned directory
            if release_version:
                source = deploy_path / "releases" / release_version / component.type / component.version
            else:
                source = deploy_path / component.type / component.version

            # Target: top-level symlink
            target = deploy_path / component.type

            # Remove existing symlink if it exists
            if target.exists() or target.is_symlink():
                if target.is_symlink():
                    target.unlink()
                elif options.get('force', False):
                    shutil.rmtree(target)
                else:
                    raise DeployError(
                        f"Directory exists and is not a symlink: {target}. "
                        "Use --force to override."
                    )

            # Create relative symlink
            if release_version:
                relative_source = Path(f"releases/{release_version}/{component.type}/{component.version}")
            else:
                relative_source = Path(f"{component.type}/{component.version}")

            target.symlink_to(relative_source)

    async def _save_deployment_metadata(self,
                                        deploy_path: Path,
                                        components: List[Component],
                                        deploy_type: str,
                                        release_version: Optional[str]) -> None:
        """Save deployment metadata"""
        metadata = {
            'deploy_type': deploy_type,
            'release_version': release_version,
            'deployed_at': datetime.now().isoformat(),
            'components': [
                {
                    'type': c.type,
                    'version': c.version
                }
                for c in components
            ]
        }

        metadata_file = deploy_path / DEPLOYMENT_METADATA_FILE
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    async def _verify_deployment(self,
                                 components: List[Component],
                                 deploy_path: Path,
                                 release_version: Optional[str]) -> VerifyResult:
        """Verify deployment with symlink structure"""
        errors = []
        warnings = []
        verified_files = 0
        total_files = 0

        for component in components:
            # Check versioned directory
            if release_version:
                component_path = deploy_path / "releases" / release_version / component.type / component.version
            else:
                component_path = deploy_path / component.type / component.version

            if not component_path.exists():
                errors.append(
                    f"Component path not found: {component_path}"
                )
                continue

            # Check symlink
            symlink_path = deploy_path / component.type
            if not symlink_path.exists():
                errors.append(
                    f"Symlink not found: {symlink_path}"
                )
            elif not symlink_path.is_symlink():
                warnings.append(
                    f"Path exists but is not a symlink: {symlink_path}"
                )

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
<<<<<<< HEAD
            component_type="deployment",
            version="multi-component",
            checksum_valid=True,
            files_complete=(verified_files == total_files),
            manifest_valid=True,
            issues=issues,
            error=errors[0] if errors else None
=======
            target_type="deployment",
            errors=errors,
            warnings=warnings,
            verified_files=verified_files,
            total_files=total_files
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
        )

    async def _rollback_components(self,
                                   components: List[Component],
                                   deploy_path: Path,
                                   release_version: Optional[str]) -> None:
        """Rollback deployed components"""
        for component in components:
            # Remove versioned directory
            if release_version:
                component_path = deploy_path / "releases" / release_version / component.type / component.version
            else:
                component_path = deploy_path / component.type / component.version

            if component_path.exists():
                shutil.rmtree(component_path, ignore_errors=True)

<<<<<<< HEAD
            # Remove symlink
            symlink_path = deploy_path / component.type
            if symlink_path.is_symlink():
                symlink_path.unlink()

    # Additional methods for version switching
    async def switch_version(self,
                             target: str,
                             release_version: str,
                             options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Switch to a different deployed version

        Args:
            target: Deployment target
            release_version: Release version to switch to
            options: Switch options

        Returns:
            True if successful
        """
        deploy_path = self._get_deploy_path(target, options or {})
        release_path = deploy_path / "releases" / release_version

        if not release_path.exists():
            raise ReleaseNotFoundError(f"Release {release_version} not found in {deploy_path}")

        # Load deployment metadata to get components
        metadata_file = deploy_path / DEPLOYMENT_METADATA_FILE
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Update symlinks for each component
            for component_info in metadata.get('components', []):
                component_type = component_info['type']

                # Find the component version in the target release
                component_dir = release_path / component_type
                if component_dir.exists():
                    versions = [d for d in component_dir.iterdir() if d.is_dir()]
                    if versions:
                        # Use the first (usually only) version
                        version_dir = versions[0]

                        # Update symlink
                        symlink = deploy_path / component_type
                        if symlink.is_symlink():
                            symlink.unlink()

                        relative_source = Path(f"releases/{release_version}/{component_type}/{version_dir.name}")
                        symlink.symlink_to(relative_source)

            # Update metadata with new release version
            metadata['release_version'] = release_version
            metadata['switched_at'] = datetime.now().isoformat()

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            return True

        return False

    async def list_deployed_versions(self, target: str) -> List[str]:
        """
        List all deployed versions at target

        Args:
            target: Deployment target

        Returns:
            List of deployed release versions
        """
        deploy_path = self._get_deploy_path(target, {})
        releases_dir = deploy_path / "releases"

        if not releases_dir.exists():
            return []

        versions = []
        for item in releases_dir.iterdir():
            if item.is_dir():
                versions.append(item.name)

        return sorted(versions)
=======

from datetime import datetime
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
=======
            # Update links
            await self._update_links(component_type, version, result)

            # Update deployment state
            state = await self._get_deployment_state(component_type)
            if state:
                await self._update_deployment_state(
                    component_type,
                    version,
                    state.get_version(version).deployed_from if state.get_version(version) else "unknown"
                )

            result.deploy_path = deploy_path
            result.message = f"Switched to version {version}"
            result.complete(OperationStatus.SUCCESS)

            return result

        except Exception as e:
            result.add_error(
                ErrorCode.LINK_UPDATE_FAILED,
                f"Failed to switch version: {str(e)}"
            )
            result.complete(OperationStatus.FAILED)
            return result

    async def list_deployed_versions(
        self,
        component_type: str
    ) -> List[Dict[str, Any]]:
        """List deployed versions for a component

        Args:
            component_type: Type of component

        Returns:
            List of version information
        """
        versions = []

        # Get deployment state
        state = await self._get_deployment_state(component_type)

        if state:
            for entry in state.versions:
                versions.append({
                    "version": entry.version,
                    "deployed_at": entry.deployed_at,
                    "deployed_from": entry.deployed_from,
                    "is_current": entry.is_current,
                    "path": str(
                        self.deploy_root / COMPONENTS_DIR /
                        component_type / entry.version
                    )
                })

        return versions
>>>>>>> Stashed changes
