"""Publish command implementation"""

import sys

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from ..decorators import require_project, dual_mode_command
from ..utils.output import format_publish_result
from ...api import Publisher
from ...api.exceptions import PublishError, ComponentNotFoundError
from ...models import Component

console = Console()


def parse_component_spec(spec: str) -> tuple[str, str]:
    """Parse component specification in format 'type:version'"""
    if ':' not in spec:
        raise ValueError(f"Invalid component spec: {spec}. Expected format: type:version")
    parts = spec.split(':', 1)
    return parts[0], parts[1]


@click.command()
@click.option('--component', '-c', multiple=True, required=True,
              help='Component to publish (format: type:version)')
@click.option('--release-version', help='Release version (auto-generated if not provided)')
@click.option('--release-name', help='Release name/description')
@click.option('--config', type=click.Path(exists=True), help='Publish configuration file')
@click.option('--force', is_flag=True, help='Force overwrite existing release')
@click.option('--atomic', is_flag=True, default=True, help='Atomic publish (all or nothing)')
@click.option('--dry-run', is_flag=True, help='Simulate without actual publishing')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
@require_project
@dual_mode_command
def publish(ctx, component, release_version, release_name, config,
            force, atomic, dry_run, no_confirm):
    """Publish components to storage backend

    Publishes one or more packaged components to the configured storage backend
    (BOS, S3, etc.) and creates a release manifest.

    Examples:

        # Publish single component
        deploy-tool publish --component model:1.0.1

        # Publish multiple components as release
        deploy-tool publish \\
            --component model:1.0.1 \\
            --component config:1.0.0 \\
            --release-version 2024.01.20

        # Publish with custom name
        deploy-tool publish \\
            --component model:1.0.1 \\
            --release-version 2024.01.20 \\
            --release-name "January Release"
    """
    try:
        # Parse components
        components = []
        for spec in component:
            comp_type, comp_version = parse_component_spec(spec)
            components.append(Component(
                type=comp_type,
                version=comp_version
            ))

        # Show confirmation
        if not no_confirm and not dry_run:
            table = Table(title="Components to Publish", box=None)
            table.add_column("Type", style="cyan")
            table.add_column("Version", style="green")

            for comp in components:
                table.add_row(comp.type, comp.version)

            console.print(table)

            if release_version:
                console.print(f"\nRelease Version: [bold]{release_version}[/bold]")
            if release_name:
                console.print(f"Release Name: [dim]{release_name}[/dim]")

            if not Confirm.ask("\n[cyan]Proceed with publishing?[/cyan]"):
                console.print("[yellow]Publishing cancelled[/yellow]")
                sys.exit(0)

        # Dry run mode
        if dry_run:
            console.print("[yellow]Dry run mode - no actual publishing[/yellow]")
            return

        # Create publisher
        publisher = Publisher()

        # Use publish() method instead of publish_async()
        result = publisher.publish(
            components=components,
            release_version=release_version,
            release_name=release_name,
            force=force,
            atomic=atomic
        )

        # Display result
        format_publish_result(result)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except (PublishError, ComponentNotFoundError) as e:
        console.print(f"[red]Publishing error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)