"""Publish command implementation with improved error handling"""

<<<<<<< Updated upstream
import sys
from typing import List
from pathlib import Path

import click
from rich.console import Console
=======
import asyncio
from pathlib import Path
from typing import List, Optional

import click
from rich.prompt import Prompt, Confirm
>>>>>>> Stashed changes
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

<<<<<<< Updated upstream
from ..decorators import require_project, dual_mode_command
from ..utils.output import format_publish_result
from ...api import Publisher
from ...api.exceptions import PublishError, ComponentNotFoundError
<<<<<<< HEAD
from ...utils.file_utils import format_bytes
from ...models.component import PublishComponent
from ...core import ComponentRegistry, PathResolver, ManifestEngine
=======
from ...models import Component
from ...utils.async_utils import run_async
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

console = Console()


def parse_component_spec(spec: str) -> PublishComponent:
    """Parse component specification string"""
    parts = spec.split(':')
    if len(parts) != 2:
        raise ValueError(f"Invalid component format: {spec}. Use 'type:version'")

    return PublishComponent(type=parts[0], version=parts[1])


def select_components(project_root: Path) -> List[PublishComponent]:
    """Interactive component selection"""
    # Initialize component registry
    path_resolver = PathResolver(project_root)
    manifest_engine = ManifestEngine(path_resolver)
    registry = ComponentRegistry(path_resolver, manifest_engine)

    # Get available components
    available = registry.list_components()

    if not available:
        console.print("[yellow]No components available for publishing[/yellow]")
        return []

    # Display available components
    console.print("\n[bold]Available components:[/bold]")
    table = Table()
    table.add_column("#", style="dim", width=3)
    table.add_column("Type", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Created", style="yellow")

    for i, comp in enumerate(available, 1):
        # Get component info
        info = registry.find_component(comp.type, comp.version)
        created_str = info.created_at.strftime("%Y-%m-%d %H:%M") if info else "Unknown"
        table.add_row(str(i), comp.type, comp.version, created_str)

    console.print(table)

    # Get user selection
    selection = Prompt.ask(
        "\nSelect components to publish (comma-separated numbers or 'all')",
        default="all"
    )

    if selection.lower() == 'all':
        return [PublishComponent(type=c.type, version=c.version) for c in available]

    # Parse selection
    selected = []
    try:
        indices = [int(x.strip()) - 1 for x in selection.split(',')]
        for idx in indices:
            if 0 <= idx < len(available):
                comp = available[idx]
                selected.append(PublishComponent(type=comp.type, version=comp.version))
    except (ValueError, IndexError):
        console.print("[red]Invalid selection[/red]")
        return []

    return selected


@click.command()
@click.option('--component', '-c', multiple=True,
              help='Component to publish (format: type:version)')
@click.option('--release-version', '-r', default=None,
              help='Create release with specified version')
@click.option('--release-name', default=None,
              help='Release name (optional)')
@click.option('--force', '-f', is_flag=True,
              help='Overwrite existing published components')
@click.option('--storage', '-s', default='filesystem',
              type=click.Choice(['filesystem', 'bos', 's3'], case_sensitive=False),
              help='Storage backend to use')
@click.option('--interactive', '-i', is_flag=True,
              help='Interactive component selection')
@click.option('--atomic', is_flag=True, default=True,
              help='Atomic operation (rollback on failure)')
@click.option('--no-atomic', is_flag=True,
              help='Disable atomic operation')
@click.pass_context
@require_project
@dual_mode_command()
def publish(ctx, component, release_version, release_name, force, storage,
            interactive, atomic, no_atomic):
    """Publish components to storage

    This command publishes packaged components to the configured storage backend.
    Components must be packaged before they can be published.

    Examples:
        # Publish a single component
        deploy-tool publish --component model:1.0.0

        # Publish multiple components
        deploy-tool publish -c model:1.0.0 -c config:2.0.0

        # Create a release
        deploy-tool publish -c model:1.0.0 --release v1.0.0

        # Interactive selection
        deploy-tool publish --interactive

        # Use specific storage backend
        deploy-tool publish -c model:1.0.0 --storage bos
    """
    try:
        # Determine atomic mode
        if no_atomic:
            atomic = False

        # Collect components to publish
        components_to_publish = []

        # Interactive mode
        if interactive:
            components_to_publish = select_components(ctx.obj.project_root)
            if not components_to_publish:
                console.print("[yellow]No components selected[/yellow]")
                return

        # Parse command line components
        elif component:
            for comp_spec in component:
                try:
                    comp = parse_component_spec(comp_spec)
                    components_to_publish.append(comp)
                except ValueError as e:
                    error_panel = Panel(
                        f"[red]Invalid component specification:[/red]\n{e}",
                        title="[bold red]Error[/bold red]",
                        border_style="red"
                    )
                    console.print(error_panel)
                    sys.exit(1)

        # No components specified
        else:
            error_panel = Panel(
                "[red]No components specified![/red]\n\n"
                "Use one of the following options:\n"
                "  • --component model:1.0.0  (specify components)\n"
                "  • --interactive           (interactive selection)\n\n"
                "See 'deploy-tool publish --help' for more options.",
                title="[bold red]Usage Error[/bold red]",
                border_style="red"
            )
            console.print(error_panel)
            sys.exit(1)

        # Show what will be published
        console.print("\n[bold]Components to publish:[/bold]")
        for comp in components_to_publish:
            console.print(f"  • {comp.type}:{comp.version}")

        # Get storage configuration
        storage_config = {'type': storage}

        # Additional storage-specific config from environment
        if storage == 'bos':
            import os
            storage_config.update({
                'access_key': os.getenv('BOS_AK'),
                'secret_key': os.getenv('BOS_SK'),
                'bucket': os.getenv('BOS_BUCKET'),
                'endpoint': os.getenv('BOS_ENDPOINT', 'https://bj.bcebos.com')
            })
        elif storage == 's3':
            import os
            storage_config.update({
                'access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
                'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
                'bucket': os.getenv('S3_BUCKET'),
                'region': os.getenv('AWS_REGION', 'us-east-1')
            })

<<<<<<< HEAD
        # Show publishing info
        with console.status("[bold green]Publishing components...[/bold green]"):
            # Create publisher
            publisher = Publisher(storage_config)
=======
        # Publish components
        result = run_async(publisher.publish_async(
            components=components,
            release_version=release_version,
            release_name=release_name,
            force=force,
            atomic=atomic
        ))
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

            # Publish
            result = publisher.publish(
                components=components_to_publish,
                release_version=release_version,
                release_name=release_name,
                force=force,
                atomic=atomic
            )

        # Format and display result
        if result.success:
            console.print(f"\n[green]✓ Publishing completed successfully![/green]")

            # Show published components
            if result.published_components:
                table = Table(title="Published Components")
                table.add_column("Component", style="cyan")
                table.add_column("Status", style="green")
                table.add_column("Location")

                for comp_result in result.published_components:
                    status = "✓ Success" if comp_result.success else "✗ Failed"
                    location = comp_result.remote_path or "N/A"
                    table.add_row(
                        f"{comp_result.component.type}:{comp_result.component.version}",
                        status,
                        location
                    )

                console.print(table)

            # Show release info
            if result.release_version:
                console.print(f"\n[bold]Release Version:[/bold] {result.release_version}")
                if result.release_path:
                    console.print(f"[bold]Release Manifest:[/bold] {result.release_path}")

            # Show post-publish instructions
            if hasattr(result, 'post_publish_instructions') and result.post_publish_instructions:
                console.print("\n")
                instructions_panel = Panel(
                    "\n".join(result.post_publish_instructions),
                    title="[bold cyan]Post-Publish Instructions[/bold cyan]",
                    border_style="cyan"
                )
                console.print(instructions_panel)

        else:
            # Display error in a formatted panel
            error_panel = Panel(
                f"[red]✗ Publishing failed:[/red]\n\n{result.error}",
                title="[bold red]Publish Error[/bold red]",
                border_style="red"
            )
            console.print(error_panel)

            # Show partial results if any
            if result.published_components:
                successful = [c for c in result.published_components if c.success]
                failed = [c for c in result.published_components if not c.success]

                if successful:
                    console.print(f"\n[yellow]Partially published: {len(successful)} components[/yellow]")
                if failed:
                    console.print(f"[red]Failed: {len(failed)} components[/red]")
                    for comp in failed[:3]:  # Show first 3 failures
                        console.print(f"  • {comp.component.type}:{comp.component.version}: {comp.error}")

            sys.exit(1)

    except (PublishError, ComponentNotFoundError) as e:
        # Known errors - display in a nice panel
        error_panel = Panel(
            f"[red]{str(e)}[/red]",
            title="[bold red]Publish Error[/bold red]",
            border_style="red"
        )
        console.print(error_panel)
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Publishing cancelled by user[/yellow]")
        sys.exit(130)

    except Exception as e:
        # Unexpected errors - display with more detail
        error_panel = Panel(
            f"[red]An unexpected error occurred:[/red]\n\n{str(e)}\n\n"
            "[dim]This might be a bug. Please report it if the problem persists.[/dim]",
            title="[bold red]Unexpected Error[/bold red]",
            border_style="red"
        )
        console.print(error_panel)

        if ctx.obj.debug:
            console.print("\n[bold]Debug Information:[/bold]")
            console.print_exception()
        else:
            console.print("\n[dim]Run with --debug for more details[/dim]")

        sys.exit(1)
=======
from ..decorators import dual_mode_command, project_required
from ..utils.output import console, create_progress
from ..utils.interactive import select_multiple_items
from ...services.publish_service import PublishService
from ...services.config_service import ConfigService
from ...core.storage_manager import StorageManager
from ...core.manifest_engine import ManifestEngine
from ...core.path_resolver import PathResolver
from ...constants import (
    EMOJI_SUCCESS,
    EMOJI_ERROR,
    EMOJI_WARNING,
    EMOJI_PACKAGE,
    EMOJI_CLOUD,
    EMOJI_SERVER,
    StorageType
)


@click.command()
@click.argument('component_spec', required=False)
@click.option(
    '--target', '-t',
    multiple=True,
    help='Target to publish to (can be specified multiple times)'
)
@click.option(
    '--all-targets',
    is_flag=True,
    help='Publish to all configured targets'
)
@click.option(
    '--yes', '-y',
    is_flag=True,
    help='Skip confirmation prompts'
)
@dual_mode_command
@project_required
async def publish(ctx, component_spec, target, all_targets, yes):
    """Publish a component to configured targets

    Examples:
        deploy-tool publish model:1.0.0
        deploy-tool publish model:1.0.0 --target local-primary --target bos-beijing
        deploy-tool publish model:1.0.0 --all-targets
    """
    # Initialize services
    config_service = ConfigService(ctx.project_root)
    config = config_service.config

    storage_manager = StorageManager(config)
    manifest_engine = ManifestEngine(ctx.project_root / "deployment" / "manifests")
    path_resolver = PathResolver(ctx.project_root)

    publish_service = PublishService(config, storage_manager, manifest_engine)

    # Parse component spec
    if component_spec:
        if ':' not in component_spec:
            console.print(f"{EMOJI_ERROR} Invalid component spec. Use format: <type>:<version>")
            ctx.exit(1)

        component_type, version = component_spec.split(':', 1)
    else:
        # Interactive mode - select component
        component_type, version = await _select_component(manifest_engine)
        if not component_type:
            ctx.exit(0)

    # Check if package exists
    package_path = ctx.project_root / "dist" / f"{component_type}-{version}.tar.gz"
    if not package_path.exists():
        console.print(f"{EMOJI_ERROR} Package not found: {package_path}")
        console.print(f"\nDid you run 'deploy-tool pack' for {component_type}:{version}?")
        ctx.exit(1)

    # Determine targets
    if all_targets:
        target_names = storage_manager.get_enabled_storages()
    elif target:
        target_names = list(target)
    else:
        # Interactive mode - select targets
        target_names = await _select_targets(config_service, storage_manager)
        if not target_names:
            ctx.exit(0)

    # Validate targets
    invalid_targets = []
    for name in target_names:
        if name not in storage_manager.get_enabled_storages():
            invalid_targets.append(name)

    if invalid_targets:
        console.print(f"{EMOJI_ERROR} Invalid targets: {', '.join(invalid_targets)}")
        console.print("\nAvailable targets:")
        for name in storage_manager.get_enabled_storages():
            console.print(f"  - {name}")
        ctx.exit(1)

    # Show publish plan
    console.print(f"\n{EMOJI_PACKAGE} [bold]Publish Plan[/bold]")
    console.print(f"Component: {component_type}:{version}")
    console.print(f"Package: {package_path.name} ({_format_size(package_path.stat().st_size)})")
    console.print(f"\nTargets:")

    for name in target_names:
        target_config = storage_manager.get_storage_config(name)
        icon = EMOJI_CLOUD if target_config.is_remote else EMOJI_SERVER
        console.print(f"  {icon} {name} - {target_config.get_display_info()}")

    # Confirm
    if not yes and not ctx.interactive:
        if not Confirm.ask("\nProceed with publish?"):
            ctx.exit(0)

    # Execute publish
    console.print(f"\n{EMOJI_PACKAGE} Publishing {component_type}:{version}...")

    with create_progress() as progress:
        task = progress.add_task("Publishing...", total=len(target_names))

        # Create progress callback
        def update_progress(target_name: str, status: str):
            progress.update(
                task,
                advance=1,
                description=f"Publishing to {target_name}... {status}"
            )

        # Run publish
        result = await publish_service.publish_component(
            component_type=component_type,
            version=version,
            package_path=package_path,
            target_names=target_names,
            interactive=ctx.interactive
        )

    # Show results
    console.print(f"\n[bold]Publish Results[/bold]")

    # Group by storage type
    filesystem_results = []
    remote_results = []

    for target_result in result.target_results:
        target_config = storage_manager.get_storage_config(target_result.target_name)

        if target_config.storage_type == StorageType.FILESYSTEM:
            filesystem_results.append((target_result, target_config))
        else:
            remote_results.append((target_result, target_config))

    # Show remote results first
    if remote_results:
        console.print(f"\n{EMOJI_CLOUD} [bold]Remote Storage[/bold]")
        for target_result, target_config in remote_results:
            if target_result.status.value == "success":
                console.print(
                    f"  {EMOJI_SUCCESS} {target_result.target_name}: "
                    f"Uploaded to {target_config.get_display_info()}"
                )
            else:
                console.print(
                    f"  {EMOJI_ERROR} {target_result.target_name}: "
                    f"{target_result.error.message if target_result.error else 'Failed'}"
                )

    # Show filesystem results with transfer instructions
    if filesystem_results:
        console.print(f"\n{EMOJI_SERVER} [bold]Filesystem Targets[/bold]")
        console.print("The following files need to be manually transferred:")

        for target_result, target_config in filesystem_results:
            if target_result.status.value == "success":
                console.print(f"\n  Target: {target_result.target_name}")
                console.print(f"  Local path: {target_result.location_info['path']}")
                console.print(f"  Suggested remote path: {target_config.path}")
                console.print(f"  Transfer command:")
                console.print(
                    f"    rsync -avz {target_result.location_info['path']} "
                    f"server:{target_config.path}/"
                )
            else:
                console.print(
                    f"\n  {EMOJI_ERROR} {target_result.target_name}: "
                    f"{target_result.error.message if target_result.error else 'Failed'}"
                )

    # Summary
    console.print(f"\n[bold]Summary[/bold]")
    if result.successful_targets:
        console.print(
            f"{EMOJI_SUCCESS} Successfully published to: "
            f"{', '.join(result.successful_targets)}"
        )

    if result.failed_targets:
        console.print(
            f"{EMOJI_ERROR} Failed to publish to: "
            f"{', '.join(result.failed_targets)}"
        )

    # Git reminder
    if result.manifest_updated:
        console.print(f"\n{EMOJI_WARNING} Don't forget to commit the updated manifest:")
        console.print(f"  git add deployment/manifests/{component_type}/{version}.json")
        console.print(f"  git commit -m \"Published {component_type}:{version}\"")

    # Exit with appropriate code
    ctx.exit(0 if result.is_success else 1)


async def _select_component(manifest_engine: ManifestEngine) -> tuple[str, str]:
    """Interactive component selection

    Returns:
        Tuple of (component_type, version) or (None, None) if cancelled
    """
    # Get available components
    all_manifests = await manifest_engine.list_manifests()

    if not all_manifests:
        console.print(f"{EMOJI_WARNING} No packaged components found.")
        console.print("\nRun 'deploy-tool pack' to create a component package first.")
        return None, None

    # Group by component type
    components = {}
    for key, manifest in all_manifests.items():
        if ':' in key:
            comp_type, version = key.split(':', 1)
        else:
            comp_type = manifest.component_type
            version = manifest.component_version

        if comp_type not in components:
            components[comp_type] = []
        components[comp_type].append(version)

    # Select component type
    console.print("\n[bold]Select component type:[/bold]")
    comp_types = sorted(components.keys())

    for i, comp_type in enumerate(comp_types, 1):
        versions = sorted(components[comp_type])
        console.print(
            f"  {i}. {comp_type} "
            f"({len(versions)} version{'s' if len(versions) > 1 else ''})"
        )

    choice = Prompt.ask(
        "Enter choice",
        choices=[str(i) for i in range(1, len(comp_types) + 1)],
        default="1"
    )

    if not choice:
        return None, None

    component_type = comp_types[int(choice) - 1]

    # Select version
    versions = sorted(components[component_type], reverse=True)

    if len(versions) == 1:
        version = versions[0]
        console.print(f"\nUsing version: {version}")
    else:
        console.print(f"\n[bold]Select version for {component_type}:[/bold]")

        for i, ver in enumerate(versions, 1):
            console.print(f"  {i}. {ver}")

        choice = Prompt.ask(
            "Enter choice",
            choices=[str(i) for i in range(1, len(versions) + 1)],
            default="1"
        )

        if not choice:
            return None, None

        version = versions[int(choice) - 1]

    return component_type, version


async def _select_targets(
    config_service: ConfigService,
    storage_manager: StorageManager
) -> List[str]:
    """Interactive target selection

    Returns:
        List of selected target names
    """
    # Get available targets
    targets = config_service.list_targets()

    if not targets:
        console.print(f"{EMOJI_WARNING} No publish targets configured.")
        console.print("\nRun 'deploy-tool config targets add' to configure targets.")
        return []

    # Prepare items for selection
    items = []
    for target in targets:
        status = "[green]enabled[/green]" if target['enabled'] else "[red]disabled[/red]"
        default = " [yellow](default)[/yellow]" if target.get('is_default') else ""

        items.append({
            'name': target['name'],
            'display': f"{target['name']} - {target['display_info']} {status}{default}",
            'enabled': target['enabled']
        })

    # Filter enabled targets only
    enabled_items = [item for item in items if item['enabled']]

    if not enabled_items:
        console.print(f"{EMOJI_WARNING} No enabled publish targets.")
        return []

    # Default selection
    default_targets = storage_manager.get_default_storages()
    default_selection = [
        item['name'] for item in enabled_items
        if item['name'] in default_targets
    ]

    # Select targets
    selected = select_multiple_items(
        title="Select publish targets",
        items=[item['display'] for item in enabled_items],
        default_selection=[
            i for i, item in enumerate(enabled_items)
            if item['name'] in default_selection
        ]
    )

    if not selected:
        return []

    # Map back to target names
    return [enabled_items[i]['name'] for i in selected]


def _format_size(size_bytes: int) -> str:
    """Format file size for display"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
>>>>>>> Stashed changes
