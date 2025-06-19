"""Release management commands"""

import sys
from datetime import datetime

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ..decorators import require_project
from ...api import query
from ...api.exceptions import ReleaseNotFoundError
from ...utils.async_utils import run_async

console = Console()


@click.group()
def release():
    """Manage release versions

    This command group provides tools to list, show, and manage
    release versions that contain multiple components.
    """
    pass


@release.command()
@click.option('--limit', type=int, default=10, help='Number of releases to show')
@click.option('--from', 'from_date', type=click.DateTime(), help='Start date')
@click.option('--to', 'to_date', type=click.DateTime(), help='End date')
@click.option('--output', type=click.Choice(['table', 'json', 'brief']),
              default='table', help='Output format')
@click.pass_context
@require_project
def list(ctx, limit, from_date, to_date, output):
    """List release versions

    Shows available release versions with their metadata.

    Examples:

        # List recent releases
        deploy-tool release list

        # List releases in date range
        deploy-tool release list --from 2024-01-01 --to 2024-01-31

        # Show more releases
        deploy-tool release list --limit 50
    """
    try:
        # Query releases
        releases = run_async(query.list_releases_async(
            limit=limit,
            from_date=from_date,
            to_date=to_date
        ))

        if not releases:
            console.print("[yellow]No releases found[/yellow]")
            return

        # Display based on format
        if output == 'json':
            import json
            output_data = [
                {
                    'version': r.version,
                    'name': r.name,
                    'created_at': r.created_at.isoformat(),
                    'component_count': len(r.components)
                }
                for r in releases
            ]
            console.print_json(data=output_data)

        elif output == 'brief':
            for rel in releases:
                console.print(f"{rel.version} - {rel.created_at.strftime('%Y-%m-%d')}")

        else:  # table
            table = Table(title=f"Release Versions (Latest {limit})", box=box.SIMPLE)
            table.add_column("Version", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("Components", justify="center", style="green")
            table.add_column("Created", style="yellow")

            for rel in releases:
                table.add_row(
                    rel.version,
                    rel.name or "-",
                    str(len(rel.components)),
                    rel.created_at.strftime("%Y-%m-%d %H:%M")
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)


@release.command()
@click.argument('release_version', required=True)
@click.option('--output', type=click.Choice(['table', 'tree', 'json']),
              default='table', help='Output format')
@click.pass_context
@require_project
def show(ctx, release_version, output):
    """Show release details

    Display detailed information about a specific release version,
    including all components it contains.

    Arguments:
        RELEASE_VERSION: Release version to show

    Examples:

        # Show release details
        deploy-tool release show 2024.01.20

        # Show as tree view
        deploy-tool release show 2024.01.20 --output tree

        # Get JSON output
        deploy-tool release show 2024.01.20 --output json
    """
    try:
        # Get release details
        rel = run_async(query.get_release_async(release_version))

        # Display header
        panel = Panel(
            f"[bold]{rel.name or 'Unnamed Release'}[/bold]\n"
            f"Created: {rel.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Components: {len(rel.components)}",
            title=f"Release: {release_version}",
            border_style="cyan"
        )
        console.print(panel)

        # Display components based on format
        if output == 'tree':
            # Tree view
            tree = Tree("Components")
            for comp in rel.components:
                node = tree.add(f"[cyan]{comp.type}[/cyan]")
                node.add(f"Version: [green]{comp.version}[/green]")
                node.add(f"Size: [yellow]{comp.size_human}[/yellow]")
                if comp.checksum:
                    node.add(f"SHA256: {comp.checksum[:16]}...")
            console.print(tree)

        elif output == 'json':
            # JSON output
            import json
            output_data = {
                'version': rel.version,
                'name': rel.name,
                'created_at': rel.created_at.isoformat(),
                'components': [
                    {
                        'type': c.type,
                        'version': c.version,
                        'size': c.size,
                        'checksum': c.checksum
                    }
                    for c in rel.components
                ]
            }
            console.print_json(data=output_data)

        else:
            # Table view (default)
            if rel.components:
                table = Table(title="Components", box=box.SIMPLE)
                table.add_column("Type", style="cyan")
                table.add_column("Version", style="green")
                table.add_column("Size", justify="right", style="yellow")
                table.add_column("Checksum", style="dim")

                for comp in rel.components:
                    checksum_short = comp.checksum[:12] + "..." if comp.checksum else "-"
                    table.add_row(
                        comp.type,
                        comp.version,
                        comp.size_human,
                        checksum_short
                    )

                console.print("\n")
                console.print(table)

        # Show manifest location
        if rel.manifest_path:
            console.print(f"\n[dim]Manifest: {rel.manifest_path}[/dim]")

    except ReleaseNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)


@release.command()
@click.option('--component', '-c', multiple=True, required=True,
              help='Component to include (format: type:version)')
@click.option('--version', help='Release version (auto-generated if not provided)')
@click.option('--name', help='Release name/description')
@click.pass_context
def create(ctx, component, version, name):
    """Create a new release (alias for publish)

    This is an alias for 'deploy-tool publish' command.

    Examples:
        # Create release with auto-generated version
        deploy-tool release create \\
            --component model:1.0.1 \\
            --component config:1.0.0

        # Create with specific version
        deploy-tool release create \\
            --component model:1.0.1 \\
            --version 2024.01.20 \\
            --name "January Release"
    """
    # Forward to publish command
    from .publish import publish
    ctx.forward(publish,
                component=component,
                release_version=version,
                release_name=name)


@release.command()
@click.argument('release_version', required=True)
@click.pass_context
@require_project
def verify(ctx, release_version):
    """Verify release integrity

    Arguments:
        RELEASE_VERSION: Release version to verify

    Examples:
        # Verify release
        deploy-tool release verify 2024.01.20
    """
    try:
        console.print(f"Verifying release {release_version}...")

        # Run verification
        result = run_async(query.verify_release_async(release_version))

        # Display overall result
        if result.is_valid:
            console.print(f"[green]✓ Release {release_version} is valid[/green]")
        else:
            console.print(f"[red]✗ Release {release_version} has issues[/red]")

        # Show component verification results
        if result.component_results:
            console.print("\nComponent verification:")
            for comp_spec, comp_result in result.component_results.items():
                icon = "✓" if comp_result.is_valid else "✗"
                color = "green" if comp_result.is_valid else "red"
                console.print(f"  [{color}]{icon}[/{color}] {comp_spec}")

                # Show failed checks
                if not comp_result.is_valid and comp_result.checks:
                    for check_name, check in comp_result.checks.items():
                        if not check.passed:
                            console.print(f"      [red]- {check_name}: {check.message}[/red]")

        # Exit with error code if invalid
        if not result.is_valid:
            sys.exit(1)

    except ReleaseNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)