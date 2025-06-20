"""Publish command implementation with improved error handling"""

import sys
from typing import List
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

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