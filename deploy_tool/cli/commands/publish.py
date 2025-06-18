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
async def publish(ctx, component, release_version, release_name, config,
                  force, atomic, dry_run, no_confirm):
    """Publish components to storage backend

    Publishes one or more packaged components to the configured storage backend
    (BOS, S3, etc.) and creates a release manifest.

    Examples:

        # Publish single component
        deploy-tool publish --component model:1.0.1

        # Publish multiple components as a release
        deploy-tool publish \\
            --component model:1.0.1 \\
            --component config:1.0.0 \\
            --component python-runtime:3.10.12 \\
            --release-version 2024.01.20

        # With release name
        deploy-tool publish \\
            --component model:1.0.1 \\
            --release-name "January Production Release"
    """
    try:
        # Parse components
        components_to_publish = []
        for comp_spec in component:
            comp_type, comp_version = parse_component_spec(comp_spec)
            components_to_publish.append(Component(
                type=comp_type,
                version=comp_version
            ))

        # Show what will be published
        if not no_confirm and not dry_run:
            table = Table(title="Components to Publish")
            table.add_column("Type", style="cyan")
            table.add_column("Version", style="green")

            for comp in components_to_publish:
                table.add_row(comp.type, comp.version)

            console.print(table)

            if release_version:
                console.print(f"Release Version: [bold]{release_version}[/bold]")
            if release_name:
                console.print(f"Release Name: [italic]{release_name}[/italic]")

            if not Confirm.ask("\n[cyan]Proceed with publish?[/cyan]", default=True):
                console.print("[yellow]Publish cancelled[/yellow]")
                sys.exit(0)

        # Create publisher
        publisher = Publisher(
            path_resolver=ctx.obj.path_resolver,
            storage_config=config
        )

        # Publish with progress
        with console.status("[bold green]Publishing components...") as status:
            result = await publisher.publish(
                components=components_to_publish,
                release_version=release_version,
                release_name=release_name,
                force=force,
                atomic=atomic,
                dry_run=dry_run
            )

        # Display results
        format_publish_result(result)

        # Git advice for release manifest
        if result.release_manifest_path and not dry_run:
            from ..utils.output import show_git_advice
            show_git_advice(result.release_manifest_path)

    except ComponentNotFoundError as e:
        console.print(f"[red]Component not found: {e}[/red]")
        console.print("\n[yellow]Hint:[/yellow] Use 'deploy-tool component list' to see available components")
        sys.exit(1)
    except PublishError as e:
        console.print(f"[red]Publish error: {e}[/red]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Invalid input: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Publish cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)