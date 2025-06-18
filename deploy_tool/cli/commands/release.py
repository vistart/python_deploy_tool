"""Release management command"""

import sys

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ..decorators import require_project
from ...api import query
from ...api.exceptions import ReleaseNotFoundError

console = Console()


@click.group()
@click.pass_context
def release(ctx):
    """Manage and query releases

    This command group provides functionality to list, inspect, and manage
    release versions that contain multiple components.
    """
    pass


@release.command(name='list')
@click.option('--limit', type=int, default=20, help='Limit number of results')
@click.option('--from-date', type=click.DateTime(), help='Filter releases from date')
@click.option('--to-date', type=click.DateTime(), help='Filter releases to date')
@click.option('--contains', help='Filter releases containing component (type:version)')
@click.pass_context
@require_project
async def list_releases(ctx, limit, from_date, to_date, contains):
    """List available releases

    Examples:
        # List all releases
        deploy-tool release list

        # List releases from last month
        deploy-tool release list --from-date 2024-01-01

        # List releases containing specific component
        deploy-tool release list --contains model:1.0.1
    """
    try:
        # Query releases
        releases = await query.list_releases(
            limit=limit,
            from_date=from_date,
            to_date=to_date,
            contains_component=contains
        )

        if not releases:
            console.print("[yellow]No releases found[/yellow]")
            return

        # Display in table
        table = Table(title="Available Releases", box=box.ROUNDED)
        table.add_column("Version", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Components", justify="center", style="yellow")
        table.add_column("Created", style="dim")
        table.add_column("Status", style="bold")

        for rel in releases:
            status = "[green]✓[/green]" if rel.verified else "[yellow]?[/yellow]"
            name = rel.name or "-"
            if len(name) > 30:
                name = name[:27] + "..."

            table.add_row(
                rel.version,
                name,
                str(len(rel.components)),
                rel.created_at.strftime("%Y-%m-%d %H:%M"),
                status
            )

        console.print(table)

        # Show summary
        if len(releases) == limit:
            console.print(f"\n[dim]Showing latest {limit} releases. Use --limit to see more.[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing releases: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)


@release.command()
@click.argument('release_version', required=True)
@click.option('--format', 'output_format',
              type=click.Choice(['table', 'tree', 'json']),
              default='table',
              help='Output format')
@click.pass_context
@require_project
async def show(ctx, release_version, output_format):
    """Show detailed information about a release

    Arguments:
        RELEASE_VERSION: Release version to show

    Examples:
        # Show release details
        deploy-tool release show 2024.01.20

        # Show as tree structure
        deploy-tool release show 2024.01.20 --format tree
    """
    try:
        # Get release details
        rel = await query.get_release(release_version)

        if not rel:
            raise ReleaseNotFoundError(f"Release {release_version} not found")

        # Display header info
        header_lines = []
        header_lines.append(f"[bold]Version:[/bold] {rel.version}")
        if rel.name:
            header_lines.append(f"[bold]Name:[/bold] {rel.name}")
        header_lines.append(f"[bold]Created:[/bold] {rel.created_at}")
        header_lines.append(f"[bold]Components:[/bold] {len(rel.components)}")

        panel = Panel(
            "\n".join(header_lines),
            title=f"Release: {release_version}",
            border_style="cyan"
        )
        console.print(panel)

        # Display components based on format
        if output_format == 'tree':
            # Tree view
            tree = Tree("Components")
            for comp in rel.components:
                node = tree.add(f"[cyan]{comp.type}[/cyan]")
                node.add(f"Version: [green]{comp.version}[/green]")
                node.add(f"Size: [yellow]{comp.size_human}[/yellow]")
                if comp.checksum:
                    node.add(f"SHA256: {comp.checksum[:16]}...")
            console.print(tree)

        elif output_format == 'json':
            # JSON output
            import json
            output = {
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
            console.print_json(data=output)

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
async def create(ctx, component, version, name):
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
async def verify(ctx, release_version):
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
        result = await query.verify_release(release_version)

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