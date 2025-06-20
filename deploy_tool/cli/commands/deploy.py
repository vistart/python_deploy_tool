"""Deploy command implementation with failover support"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

import click
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.tree import Tree

<<<<<<< Updated upstream
from ..decorators import require_project, dual_mode_command
from ..utils.output import format_deploy_result
from ...api import Deployer
from ...api.exceptions import DeployError, ReleaseNotFoundError, ComponentNotFoundError
from ...utils.async_utils import run_async

console = Console()


@click.command()
@click.option('--release', help='Deploy a release version')
@click.option('--component', help='Deploy a single component (format: type:version)')
@click.option('--target', required=True, help='Deployment target (path or server name)')
@click.option('--method', type=click.Choice(['filesystem', 'bos', 's3']),
              default='filesystem', help='Storage method to download from')
@click.option('--bucket', help='Storage bucket (for S3/BOS)')
@click.option('--releases-dir', help='Releases directory (for filesystem method)')
@click.option('--env', type=click.Choice(['dev', 'staging', 'production']),
              help='Target environment')
@click.option('--verify/--no-verify', default=True, help='Verify after deployment')
@click.option('--rollback/--no-rollback', default=True,
              help='Enable rollback on failure')
@click.option('--force', is_flag=True, help='Force deployment even if already deployed')
@click.option('--dry-run', is_flag=True, help='Simulate deployment')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
@require_project
@dual_mode_command
def deploy(ctx, release, component, target, method, bucket, releases_dir,
           env, verify, rollback, force, dry_run, no_confirm):
    """Deploy components to target environment

    Deploy packaged components or complete releases to local directories
    or remote servers. Supports automatic versioning with symbolic links
    for easy version switching.

    The deployment creates a versioned directory structure:

        target/
        ├── model -> releases/2024.01.20/model/1.0.0/
        ├── config -> releases/2024.01.20/config/1.0.0/
        └── releases/
            └── 2024.01.20/
                ├── model/1.0.0/
                ├── config/1.0.0/
                └── runtime/3.10.0/

    Examples:

<<<<<<< HEAD
        # Deploy release from filesystem
        deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod

        # Deploy from S3
        deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod \
            --method s3 --bucket my-releases
=======
        # Deploy release version
        deploy-tool deploy --release 2024.01.20 --target production

        # Deploy to local directory
        deploy-tool deploy --release 2024.01.20 --target ~/deployments/
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

        # Deploy single component
        deploy-tool deploy --component model:1.0.1 --target dev-server

<<<<<<< HEAD
        # Force redeployment
        deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod --force
=======
        # Deploy with rollback enabled
        deploy-tool deploy --release 2024.01.20 --target production --rollback
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
    """
    try:
        # Validate arguments
        if not release and not component:
            console.print("[red]Error: Must specify --release or --component[/red]")
            sys.exit(1)

        if release and component:
            console.print("[red]Error: Cannot specify both --release and --component[/red]")
            sys.exit(1)

        # Show confirmation
        if not no_confirm and not dry_run:
            if release:
                console.print(f"Deploy release: [bold]{release}[/bold]")
            else:
                console.print(f"Deploy component: [bold]{component}[/bold]")

<<<<<<< HEAD
            table.add_row("Target", target)
            table.add_row("Method", method)

            if method != 'filesystem':
                table.add_row("Bucket", bucket or "Not specified")
            else:
                table.add_row("Releases Dir", releases_dir or "Default")

=======
            console.print(f"Target: [cyan]{target}[/cyan]")
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
            if env:
                console.print(f"Environment: [yellow]{env}[/yellow]")

            options = []
            if verify:
                options.append("verify")
            if rollback:
                options.append("rollback on failure")
            if force:
                options.append("force")

            if options:
                console.print(f"Options: {', '.join(options)}")

            console.print("\n[yellow]Deployment will create:[/yellow]")
            console.print("• Versioned directories under releases/")
            console.print("• Symbolic links at top level for easy access")
            console.print("• Metadata file for tracking deployments")

            if not Confirm.ask("\n[cyan]Proceed with deployment?[/cyan]"):
                console.print("[yellow]Deployment cancelled[/yellow]")
                return

        # Configure storage for download
        storage_config = {}
        if method != 'filesystem':
            if not bucket:
                console.print("[red]Error:[/red] --bucket required for cloud storage")
                sys.exit(1)
            storage_config['bucket'] = bucket
            storage_config['type'] = method
        else:
            if releases_dir:
                storage_config['releases_dir'] = releases_dir

        # Create deployer
        deployer = Deployer(storage_config=storage_config)

        # Build options
        options = {
            'verify': verify,
            'rollback_on_failure': rollback,
            'force': force,
            'dry_run': dry_run,
            'environment': env,
        }

        # Execute deployment
        console.print(f"\n[cyan]Deploying to {target}...[/cyan]")

        if release:
<<<<<<< HEAD
            result = deployer.deploy_release(
                release_version=release,
                target=target,
                **options
            )
        else:
            # Parse component spec
            parts = component.split(':')
            if len(parts) != 2:
                console.print(f"[red]Error:[/red] Invalid component format: {component}")
                sys.exit(1)

            from ...models import Component
            comp = Component(type=parts[0], version=parts[1])

            result = deployer.deploy_component(
                component=comp,
                target=target,
                **options
            )
=======
            result = run_async(deployer.deploy_release_async(
                release_version=release,
                target=target,
                verify=verify,
                rollback_on_failure=rollback
            ))
        else:
            # Parse component spec
            comp_type, comp_version = component.split(':', 1)
            result = run_async(deployer.deploy_component_async(
                component_type=comp_type,
                component_version=comp_version,
                target=target,
                verify=verify
            ))
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

        # Display results
        if result.success:
            console.print("\n[green]✓ Deployment completed successfully![/green]")

            # Show deployed components
            if result.deployed_components:
                table = Table(title="Deployed Components")
                table.add_column("Type", style="cyan")
                table.add_column("Version", style="green")
                table.add_column("Status")

                for comp in result.deployed_components:
                    table.add_row(
                        comp.type,
                        comp.version,
                        "✓ Deployed"
                    )

                console.print(table)

            # Show deployment structure
            console.print("\n[bold]Deployment Structure:[/bold]")
            console.print(f"Target: {target}")

            if release:
                console.print(f"\nSymbolic links created:")
                for comp in result.deployed_components:
                    console.print(f"  {comp.type} -> releases/{release}/{comp.type}/{comp.version}/")

            # Show verification results
            if result.verification:
                if result.verification.success:
                    console.print("\n[green]✓ Deployment verification passed[/green]")
                else:
                    console.print("\n[red]✗ Deployment verification failed[/red]")
                    if result.verification.issues:
                        for issue in result.verification.issues:
                            console.print(f"  - {issue}")

            console.print(f"\n[dim]Duration: {result.duration:.2f}s[/dim]")

        else:
            console.print(f"\n[red]✗ Deployment failed: {result.error}[/red]")
            sys.exit(1)

    except (DeployError, ReleaseNotFoundError, ComponentNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Deployment cancelled[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)


@click.command()
@click.option('--target', required=True, help='Deployment target')
@click.option('--release', required=True, help='Release version to switch to')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation')
@click.pass_context
@require_project
def switch_version(ctx, target, release, no_confirm):
    """Switch deployed version

    Switch to a different deployed release version using symbolic links.
    This allows instant version switching without re-deployment.

    Example:
        deploy-tool switch-version --target /opt/ml-apps/prod --release 2024.01.19
    """
    try:
        if not no_confirm:
            if not Confirm.ask(f"[cyan]Switch to version {release}?[/cyan]"):
                console.print("[yellow]Version switch cancelled[/yellow]")
                return

        # Create deployer
        deployer = Deployer()

        # Switch version
        console.print(f"\n[cyan]Switching to version {release}...[/cyan]")
        success = deployer.switch_version(target, release)

        if success:
            console.print(f"\n[green]✓ Successfully switched to version {release}![/green]")
        else:
            console.print(f"\n[red]✗ Failed to switch version[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@click.command()
@click.option('--target', required=True, help='Deployment target')
@click.pass_context
@require_project
def list_versions(ctx, target):
    """List deployed versions

    Show all deployed release versions at the target location.

    Example:
        deploy-tool list-versions --target /opt/ml-apps/prod
    """
    try:
        # Create deployer
        deployer = Deployer()

        # List versions
        versions = deployer.list_deployed_versions(target)

        if versions:
            console.print(f"\n[bold]Deployed versions at {target}:[/bold]")
            for version in versions:
                console.print(f"  • {version}")
        else:
            console.print(f"\n[yellow]No deployed versions found at {target}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
=======
from ..decorators import dual_mode_command, project_required
from ..utils.output import console, create_progress
from ..utils.interactive import select_from_list
from ...services.deploy_service import DeployService
from ...services.config_service import ConfigService
from ...core.storage_manager import StorageManager
from ...core.manifest_engine import ManifestEngine
from ...core.path_resolver import PathResolver
from ...constants import (
    EMOJI_SUCCESS,
    EMOJI_ERROR,
    EMOJI_WARNING,
    EMOJI_ROCKET,
    EMOJI_LINK,
    EMOJI_FOLDER,
    MSG_VERSION_SWITCHED,
    COMPONENTS_DIR,
    LINKS_DIR
)


@click.command()
@click.argument('component_spec', required=False)
@click.option(
    '--source', '-s',
    help='Preferred deployment source (will use failover if unavailable)'
)
@click.option(
    '--force', '-f',
    is_flag=True,
    help='Force redeployment even if version already exists'
)
@click.option(
    '--no-failover',
    is_flag=True,
    help='Disable automatic failover to other sources'
)
@click.option(
    '--switch',
    is_flag=True,
    help='Switch to an already deployed version'
)
@click.option(
    '--list', 'list_versions',
    is_flag=True,
    help='List deployed versions for a component'
)
@dual_mode_command
@project_required
async def deploy(ctx, component_spec, source, force, no_failover, switch, list_versions):
    """Deploy a component with automatic failover

    Examples:
        deploy-tool deploy model:1.0.0
        deploy-tool deploy model:1.0.0 --source bos-beijing
        deploy-tool deploy --switch model:1.0.0
        deploy-tool deploy --list model
    """
    # Initialize services
    config_service = ConfigService(ctx.project_root)
    config = config_service.config

    # Disable failover if requested
    if no_failover:
        config.deploy.failover.enabled = False

    storage_manager = StorageManager(config)
    manifest_engine = ManifestEngine(ctx.project_root / "deployment" / "manifests")
    path_resolver = PathResolver(ctx.project_root)

    deploy_service = DeployService(config, storage_manager, manifest_engine, path_resolver)

    # Handle list command
    if list_versions:
        await handle_list_versions(deploy_service, component_spec)
        ctx.exit(0)

    # Parse component spec or get interactively
    component_type, version = await parse_or_select_component(
        component_spec,
        deploy_service,
        manifest_engine,
        switch,
        ctx.interactive
    )

    if not component_type:
        ctx.exit(0)

    # Handle switch command
    if switch:
        await handle_switch_version(deploy_service, component_type, version)
        ctx.exit(0)

    # Handle normal deployment
    await handle_deployment(
        deploy_service,
        manifest_engine,
        config,
        component_type,
        version,
        source,
        force,
        ctx.interactive
    )


async def parse_or_select_component(
    component_spec: Optional[str],
    deploy_service: DeployService,
    manifest_engine: ManifestEngine,
    is_switch: bool,
    is_interactive: bool
) -> tuple[Optional[str], Optional[str]]:
    """Parse component spec or select interactively

    Returns:
        Tuple of (component_type, version) or (None, None) if cancelled
    """
    if component_spec:
        # Parse provided spec
        if ':' not in component_spec:
            console.print(f"{EMOJI_ERROR} Invalid component spec. Use format: <type>:<version>")
            return None, None

        component_type, version = component_spec.split(':', 1)
        return component_type, version

    elif is_interactive:
        # Interactive selection
        if is_switch:
            return await select_deployed_component(deploy_service)
        else:
            return await select_published_component(manifest_engine)

    else:
        # No spec and not interactive
        console.print(f"{EMOJI_ERROR} Component spec required. Use format: <type>:<version>")
        return None, None


async def handle_list_versions(
    deploy_service: DeployService,
    component_type: Optional[str]
) -> None:
    """Handle listing deployed versions"""

    if not component_type:
        # Select component type interactively
        component_types = await deploy_service.manifest_engine.get_component_types()

        if not component_types:
            console.print(f"{EMOJI_WARNING} No components found")
            return

        component_type = select_from_list(
            "Select component type",
            component_types
        )

        if not component_type:
            return

    # Get deployed versions
    versions = await deploy_service.list_deployed_versions(component_type)

    if not versions:
        console.print(f"{EMOJI_WARNING} No deployed versions found for {component_type}")
        return

    # Display versions table
    table = Table(title=f"Deployed Versions - {component_type}")
    table.add_column("Version", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Deployed At")
    table.add_column("Source")
    table.add_column("Path")

    for version_info in versions:
        status = "[bold green]CURRENT[/bold green]" if version_info['is_current'] else ""

        table.add_row(
            version_info['version'],
            status,
            version_info['deployed_at'].strftime('%Y-%m-%d %H:%M'),
            version_info['deployed_from'],
            version_info['path']
        )

    console.print(table)


async def handle_switch_version(
    deploy_service: DeployService,
    component_type: str,
    version: str
) -> None:
    """Handle version switching"""

    console.print(f"\n{EMOJI_ROCKET} Switching {component_type} to version {version}...")

    result = await deploy_service.switch_version(component_type, version)

    if result.is_success:
        console.print(f"\n{EMOJI_SUCCESS} [bold green]Version switch successful![/bold green]")

        if result.previous_version:
            console.print(
                MSG_VERSION_SWITCHED.format(
                    component=component_type,
                    old_version=result.previous_version,
                    new_version=version
                )
            )

        if result.links_updated:
            console.print(f"\n{EMOJI_LINK} Updated links:")
            for link in result.links_updated:
                console.print(f"  - {link}")

        console.print(f"\n{EMOJI_WARNING} Remember to restart services using {component_type}")

    else:
        console.print(f"\n{EMOJI_ERROR} [bold red]Version switch failed![/bold red]")

        for error in result.errors:
            console.print(f"\n{EMOJI_ERROR} {error.message}")


async def handle_deployment(
    deploy_service: DeployService,
    manifest_engine: ManifestEngine,
    config: Any,
    component_type: str,
    version: str,
    source: Optional[str],
    force: bool,
    is_interactive: bool
) -> None:
    """Handle normal component deployment"""

    # Load manifest
    manifest = await manifest_engine.load_manifest(component_type, version)
    if not manifest:
        console.print(f"{EMOJI_ERROR} No manifest found for {component_type}:{version}")
        console.print(f"\nDid you run 'deploy-tool publish' for this component?")
        return

    # Get available sources
    available_sources = [
        loc.name for loc in manifest.get_successful_locations()
    ]

    if not available_sources:
        console.print(f"{EMOJI_ERROR} No published sources available for {component_type}:{version}")
        console.print(f"\nRun 'deploy-tool publish' to publish this component first.")
        return

    # Validate preferred source
    if source and source not in available_sources:
        console.print(f"{EMOJI_WARNING} Preferred source '{source}' not available")
        console.print(f"Available sources: {', '.join(available_sources)}")

        if not config.deploy.failover.enabled:
            return
        else:
            console.print("Will use failover to other sources...")
            source = None

    # Show deployment plan
    show_deployment_plan(
        component_type,
        version,
        config,
        manifest,
        available_sources,
        source
    )

    # Confirm deployment
    if is_interactive:
        if not Confirm.ask("\nProceed with deployment?"):
            return

    # Execute deployment
    console.print(f"\n{EMOJI_ROCKET} Deploying {component_type}:{version}...")

    result = await deploy_service.deploy_component(
        component_type=component_type,
        version=version,
        source_name=source,
        force=force
    )

    # Show results
    if result.is_success:
        show_deployment_success(result, config, component_type, version)
    else:
        show_deployment_failure(result)


def show_deployment_plan(
    component_type: str,
    version: str,
    config: Any,
    manifest: Any,
    available_sources: List[str],
    preferred_source: Optional[str]
) -> None:
    """Show deployment plan details"""

    console.print(f"\n{EMOJI_ROCKET} [bold]Deployment Plan[/bold]")
    console.print(f"Component: {component_type}:{version}")
    console.print(f"Deploy to: {config.deploy.root}")

    if preferred_source:
        console.print(f"Preferred source: {preferred_source}")

    console.print(f"\nAvailable sources ({len(available_sources)}):")

    # Show sources in priority order
    priority_sources = []
    for src in config.deploy.source_priority:
        if src in available_sources:
            priority_sources.append(src)

    # Add remaining sources
    for src in available_sources:
        if src not in priority_sources:
            priority_sources.append(src)

    for i, src in enumerate(priority_sources, 1):
        location = manifest.get_location(src)
        priority_marker = " [yellow](priority)[/yellow]" if src in config.deploy.source_priority[:3] else ""
        preferred_marker = " [green](preferred)[/green]" if src == preferred_source else ""

        console.print(f"  {i}. {src} - {location.display_path}{priority_marker}{preferred_marker}")

    # Show failover config
    if config.deploy.failover.enabled:
        console.print(f"\nFailover: [green]Enabled[/green]")
        console.print(f"  Max retries: {config.deploy.failover.retry_count}")
        console.print(f"  Retry delay: {config.deploy.failover.retry_delay}s")
    else:
        console.print(f"\nFailover: [red]Disabled[/red]")


def show_deployment_success(
    result: Any,
    config: Any,
    component_type: str,
    version: str
) -> None:
    """Show deployment success details"""

    console.print(f"\n{EMOJI_SUCCESS} [bold green]Deployment successful![/bold green]")

    console.print(f"\nComponent: {component_type}:{version}")
    console.print(f"Deployed to: {result.deploy_path}")
    console.print(f"Source used: {result.source_used}")

    if len(result.sources_tried) > 1:
        console.print(f"Sources tried: {', '.join(result.sources_tried)}")

    if result.version_switched:
        message = MSG_VERSION_SWITCHED.format(
            f"component={component_type}, "
            f"old_version={result.previous_version}, "
            f"new_version={version}"
        )
        console.print(
            f"\n{message}"
        )
    
    # Show updated links
    if result.links_updated:
        console.print(f"\n{EMOJI_LINK} Updated links:")
        for link in result.links_updated:
            console.print(f"  - {link}")

    # Show deployment structure
    show_deployment_structure(config.deploy.root, component_type)

    # Show next steps
    console.print(f"\n{EMOJI_SUCCESS} Next steps:")
    console.print(f"1. Verify deployment: ls -la {result.deploy_path}")
    console.print(f"2. Test access through links: ls -la {config.deploy.root}/{LINKS_DIR}/{component_type}")

    if result.version_switched:
        console.print(f"3. Restart services using {component_type} to load new version")


def show_deployment_failure(result: Any) -> None:
    """Show deployment failure details"""

    console.print(f"\n{EMOJI_ERROR} [bold red]Deployment failed![/bold red]")

    for error in result.errors:
        console.print(f"\n{EMOJI_ERROR} {error.message}")
        if error.context:
            for key, value in error.context.items():
                console.print(f"  {key}: {value}")

    if result.sources_tried:
        console.print(f"\nSources attempted: {', '.join(result.sources_tried)}")


def show_deployment_structure(deploy_root: str, component_type: str) -> None:
    """Show deployment directory structure"""

    root = Path(deploy_root)

    console.print(f"\n{EMOJI_FOLDER} Deployment Structure:")

    tree = Tree(f"[bold]{root}[/bold]")

    # Components directory
    components = tree.add(f"{COMPONENTS_DIR}/")
    comp_dir = components.add(f"{component_type}/")

    # Show versions
    comp_path = root / COMPONENTS_DIR / component_type
    if comp_path.exists():
        for item in sorted(comp_path.iterdir()):
            if item.name == "current":
                if item.is_symlink():
                    target = item.readlink().name
                    comp_dir.add(f"[bold green]current[/bold green] → {target}")
            else:
                comp_dir.add(item.name)

    # Links directory
    links = tree.add(f"{LINKS_DIR}/")
    link_path = root / LINKS_DIR / component_type
    if link_path.exists() and link_path.is_symlink():
        target = link_path.readlink()
        links.add(f"[bold cyan]{component_type}[/bold cyan] → {target}")

    console.print(tree)


async def select_published_component(manifest_engine: ManifestEngine) -> tuple[Optional[str], Optional[str]]:
    """Select a published component interactively"""

    # Get all manifests
    all_manifests = await manifest_engine.list_manifests()

    if not all_manifests:
        console.print(f"{EMOJI_WARNING} No published components found")
        return None, None

    # Group by component type
    components = {}
    for key, manifest in all_manifests.items():
        comp_type = manifest.component_type
        version = manifest.component_version

        if comp_type not in components:
            components[comp_type] = []

        components[comp_type].append({
            'version': version,
            'locations': len(manifest.get_successful_locations()),
            'created_at': manifest.created_at
        })

    # Select component type
    comp_types = sorted(components.keys())

    console.print("\n[bold]Select component type:[/bold]")
    for i, comp_type in enumerate(comp_types, 1):
        versions = components[comp_type]
        console.print(f"  {i}. {comp_type} ({len(versions)} versions)")

    choice = Prompt.ask("Enter choice", default="1")
    if not choice or not choice.isdigit():
        return None, None

    idx = int(choice) - 1
    if idx < 0 or idx >= len(comp_types):
        return None, None

    component_type = comp_types[idx]

    # Select version
    versions = sorted(
        components[component_type],
        key=lambda x: x['version'],
        reverse=True
    )

    console.print(f"\n[bold]Select version for {component_type}:[/bold]")
    for i, ver_info in enumerate(versions, 1):
        sources_text = f"{ver_info['locations']} source{'s' if ver_info['locations'] != 1 else ''}"
        console.print(f"  {i}. {ver_info['version']} ({sources_text})")

    choice = Prompt.ask("Enter choice", default="1")
    if not choice or not choice.isdigit():
        return None, None

    idx = int(choice) - 1
    if idx < 0 or idx >= len(versions):
        return None, None

    version = versions[idx]['version']

    return component_type, version


async def select_deployed_component(deploy_service: DeployService) -> tuple[Optional[str], Optional[str]]:
    """Select a deployed component for version switching"""

    # Get component types with deployed versions
    component_types = []

    deploy_root = Path(deploy_service.deploy_root)
    components_dir = deploy_root / COMPONENTS_DIR

    if components_dir.exists():
        for comp_dir in components_dir.iterdir():
            if comp_dir.is_dir():
                # Check if has any versions
                versions = [
                    d.name for d in comp_dir.iterdir()
                    if d.is_dir() and d.name != "current"
                ]
                if versions:
                    component_types.append((comp_dir.name, versions))

    if not component_types:
        console.print(f"{EMOJI_WARNING} No deployed components found")
        return None, None

    # Select component type
    console.print("\n[bold]Select component type:[/bold]")
    for i, (comp_type, versions) in enumerate(component_types, 1):
        console.print(f"  {i}. {comp_type} ({len(versions)} versions)")

    choice = Prompt.ask("Enter choice", default="1")
    if not choice or not choice.isdigit():
        return None, None

    idx = int(choice) - 1
    if idx < 0 or idx >= len(component_types):
        return None, None

    component_type, versions = component_types[idx]

    # Get current version
    current_link = components_dir / component_type / "current"
    current_version = None
    if current_link.exists() and current_link.is_symlink():
        current_version = current_link.readlink().name

    # Select version
    console.print(f"\n[bold]Select version for {component_type}:[/bold]")

    sorted_versions = sorted(versions, reverse=True)
    for i, version in enumerate(sorted_versions, 1):
        current_marker = " [green](current)[/green]" if version == current_version else ""
        console.print(f"  {i}. {version}{current_marker}")

    choice = Prompt.ask("Enter choice", default="1")
    if not choice or not choice.isdigit():
        return None, None

    idx = int(choice) - 1
    if idx < 0 or idx >= len(sorted_versions):
        return None, None

    version = sorted_versions[idx]

    return component_type, version
>>>>>>> Stashed changes
