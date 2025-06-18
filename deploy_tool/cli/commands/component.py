"""Component management command"""

import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

from ...api import query
from ...api.exceptions import ComponentNotFoundError
from ..decorators import require_project

console = Console()


@click.group()
@click.pass_context
def component(ctx):
    """Manage and query components

    This command group provides functionality to list, inspect, and verify
    packaged components.
    """
    pass


@component.command()
@click.option('--type', 'comp_type', help='Filter by component type')
@click.option('--limit', type=int, default=20, help='Limit number of results')
@click.option('--sort', type=click.Choice(['version', 'date']), default='date',
              help='Sort order')
@click.option('--reverse', is_flag=True, help='Reverse sort order')
@click.pass_context
@require_project
async def list(ctx, comp_type, limit, sort, reverse):
    """List available components

    Examples:
        # List all components
        deploy-tool component list

        # List only model components
        deploy-tool component list --type model

        # List latest 5 components
        deploy-tool component list --limit 5
    """
    try:
        # Query components
        components = await query.list_components(
            component_type=comp_type,
            limit=limit,
            sort_by=sort,
            reverse=reverse
        )

        if not components:
            if comp_type:
                console.print(f"[yellow]No components found with type '{comp_type}'[/yellow]")
            else:
                console.print("[yellow]No components found[/yellow]")
            return

        # Display in table
        table = Table(title="Available Components", box=box.ROUNDED)
        table.add_column("Type", style="cyan", no_wrap=True)
        table.add_column("Version", style="green")
        table.add_column("Created", style="dim")
        table.add_column("Size", justify="right", style="yellow")
        table.add_column("Status", style="bold")

        for comp in components:
            status = "[green]✓[/green]" if comp.verified else "[yellow]?[/yellow]"
            table.add_row(
                comp.type,
                comp.version,
                comp.created_at.strftime("%Y-%m-%d %H:%M"),
                comp.size_human,
                status
            )

        console.print(table)

        # Show summary
        if len(components) == limit:
            console.print(f"\n[dim]Showing latest {limit} components. Use --limit to see more.[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing components: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)


@component.command()
@click.argument('component_spec', required=True)
@click.pass_context
@require_project
async def show(ctx, component_spec):
    """Show detailed information about a component

    Arguments:
        COMPONENT_SPEC: Component specification in format 'type:version'

    Examples:
        # Show model version 1.0.1
        deploy-tool component show model:1.0.1
    """
    try:
        # Parse component spec
        if ':' not in component_spec:
            console.print("[red]Error: Invalid format. Use 'type:version' (e.g., model:1.0.1)[/red]")
            sys.exit(1)

        comp_type, comp_version = component_spec.split(':', 1)

        # Get component details
        comp = await query.get_component(comp_type, comp_version)

        if not comp:
            raise ComponentNotFoundError(f"Component {component_spec} not found")

        # Display detailed info
        info_lines = []
        info_lines.append(f"[bold]Type:[/bold] {comp.type}")
        info_lines.append(f"[bold]Version:[/bold] {comp.version}")
        info_lines.append(f"[bold]Created:[/bold] {comp.created_at}")
        info_lines.append(f"[bold]Size:[/bold] {comp.size_human} ({comp.size} bytes)")
        info_lines.append(f"[bold]Archive:[/bold] {comp.archive_filename}")

        if comp.checksum:
            info_lines.append(f"[bold]SHA256:[/bold] {comp.checksum[:16]}...")

        if comp.manifest_path:
            info_lines.append(f"[bold]Manifest:[/bold] {comp.manifest_path}")

        if comp.source_path:
            info_lines.append(f"[bold]Source:[/bold] {comp.source_path}")

        panel = Panel(
            "\n".join(info_lines),
            title=f"Component: {component_spec}",
            border_style="cyan"
        )
        console.print(panel)

        # Show files if available
        if comp.files:
            console.print("\n[bold]Files:[/bold]")
            for file in comp.files[:10]:  # Show first 10 files
                console.print(f"  • {file}")
            if len(comp.files) > 10:
                console.print(f"  ... and {len(comp.files) - 10} more files")

    except ComponentNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)


@component.command()
@click.argument('component_spec', required=True)
@click.option('--fix', is_flag=True, help='Attempt to fix issues')
@click.pass_context
@require_project
async def verify(ctx, component_spec, fix):
    """Verify component integrity

    Arguments:
        COMPONENT_SPEC: Component specification in format 'type:version'

    Examples:
        # Verify model version 1.0.1
        deploy-tool component verify model:1.0.1

        # Verify and fix issues
        deploy-tool component verify model:1.0.1 --fix
    """
    try:
        # Parse component spec
        if ':' not in component_spec:
            console.print("[red]Error: Invalid format. Use 'type:version' (e.g., model:1.0.1)[/red]")
            sys.exit(1)

        comp_type, comp_version = component_spec.split(':', 1)

        console.print(f"Verifying component {component_spec}...")

        # Run verification
        result = await query.verify_component(
            component_type=comp_type,
            component_version=comp_version,
            fix_issues=fix
        )

        # Display results
        if result.is_valid:
            console.print(f"[green]✓ Component {component_spec} is valid[/green]")
        else:
            console.print(f"[red]✗ Component {component_spec} has issues[/red]")

        # Show checks
        if result.checks:
            console.print("\nVerification checks:")
            for check_name, check_result in result.checks.items():
                icon = "✓" if check_result.passed else "✗"
                color = "green" if check_result.passed else "red"
                console.print(f"  [{color}]{icon}[/{color}] {check_name}: {check_result.message}")

        # Show fixes applied
        if fix and result.fixes_applied:
            console.print("\n[yellow]Fixes applied:[/yellow]")
            for fix_msg in result.fixes_applied:
                console.print(f"  • {fix_msg}")

        # Exit with error code if invalid
        if not result.is_valid:
            sys.exit(1)

    except ComponentNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)