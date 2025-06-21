# deploy_tool/cli/utils/output.py
"""Output formatting utilities"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

from ...models import PackResult, PublishResult, DeployResult

console = Console()


def format_pack_result(result: PackResult) -> None:
    """Format and display pack operation result"""
    if result.success:
        # Success panel
        lines = [
            f"[green]✓[/green] Package created successfully!",
            f"",
            f"[bold]Type:[/bold] {result.package_type}",
            f"[bold]Version:[/bold] {result.version}",
            f"[bold]Archive:[/bold] {result.archive_path}",
        ]

        if result.archive_size:
            lines.append(f"[bold]Size:[/bold] {_format_size(result.archive_size)}")

        if result.manifest_path:
            lines.append(f"[bold]Manifest:[/bold] {result.manifest_path}")

        if result.metadata.get('compression_ratio'):
            lines.append(f"[bold]Compression:[/bold] {result.metadata['compression_ratio']:.1%}")

        panel = Panel(
            "\n".join(lines),
            title="Pack Result",
            border_style="green"
        )
        console.print(panel)

        if result.git_suggestions:
            console.print("\n[bold yellow]Git Operation Suggestions:[/bold yellow]")
            for suggestion in result.git_suggestions:
                console.print(f"  • {suggestion}")

    else:
        # Error panel
        panel = Panel(
            f"[red]✗ Pack failed:[/red] {result.error}",
            title="Pack Error",
            border_style="red"
        )
        console.print(panel)


def format_publish_result(result: PublishResult) -> None:
    """Format and display publish operation result"""
    if result.success:
        lines = [
            f"[green]✓[/green] Publishing completed successfully!",
            f"",
            f"[bold]Components:[/bold] {len(result.components)}",
        ]

        if result.release_version:
            lines.append(f"[bold]Release:[/bold] {result.release_version}")

        # Component list
        if result.components:
            lines.append("")
            lines.append("[bold]Published:[/bold]")
            for comp in result.components:
                lines.append(f"  • {comp.component.type}:{comp.component.version}")

        panel = Panel(
            "\n".join(lines),
            title="Publish Result",
            border_style="green"
        )
        console.print(panel)

    else:
        panel = Panel(
            f"[red]✗ Publish failed:[/red] {result.error}",
            title="Publish Error",
            border_style="red"
        )
        console.print(panel)


def format_deploy_result(result: DeployResult) -> None:
    """Format and display deploy operation result"""
    if result.success:
        lines = [
            f"[green]✓[/green] Deployment completed successfully!",
            f"",
            f"[bold]Target:[/bold] {result.deploy_target}",
            f"[bold]Components:[/bold] {len(result.deployed_components)}",
        ]

        # Add deployment type info
        if hasattr(result, 'deploy_type'):
            lines.append(f"[bold]Type:[/bold] {result.deploy_type}")

        # Verification status
        if result.verification:
            status = "[green]Passed[/green]" if result.verification.success else "[red]Failed[/red]"
            lines.append(f"[bold]Verification:[/bold] {status}")

            # If verification failed, show errors
            if not result.verification.success:
                # Show main error
                if result.verification.error:
                    lines.append(f"  [red]• {result.verification.error}[/red]")
                # Show issues (if any)
                if hasattr(result.verification, 'issues') and result.verification.issues:
                    for issue in result.verification.issues[:3]:  # Show max 3 issues
                        lines.append(f"  [red]• {issue}[/red]")

        panel = Panel(
            "\n".join(lines),
            title="Deploy Result",
            border_style="green"
        )
        console.print(panel)

    else:
        lines = [f"[red]✗ Deploy failed:[/red] {result.error}"]

        # If deployment failed but some components were deployed, show info
        if result.deployed_components:
            lines.append("")
            lines.append(f"[yellow]Partially deployed: {len(result.deployed_components)} components[/yellow]")

        panel = Panel(
            "\n".join(lines),
            title="Deploy Error",
            border_style="red"
        )
        console.print(panel)


def show_git_advice(manifest_path: Path) -> None:
    """Show Git operation advice after creating manifests"""
    advice = f"""
[yellow]Git Operations:[/yellow]

The following manifest was created and should be committed:
  {manifest_path}

Suggested Git workflow:
  1. git add {manifest_path}
  2. git commit -m "Add manifest for ..."
  3. git push

[dim]Note: The tool does not automatically commit files.[/dim]
"""
    console.print(advice)


def format_table(data: List[Dict[str, Any]],
                 columns: List[Tuple[str, str]],
                 title: Optional[str] = None) -> Table:
    """Create a formatted table

    Args:
        data: List of dictionaries with data
        columns: List of (key, header) tuples
        title: Optional table title

    Returns:
        Rich Table object
    """
    table = Table(title=title, box=box.ROUNDED)

    # Add columns
    for key, header in columns:
        table.add_column(header, style="cyan" if key == "name" else None)

    # Add rows
    for item in data:
        row = []
        for key, _ in columns:
            value = item.get(key, "")
            if isinstance(value, (int, float)):
                value = str(value)
            row.append(value)
        table.add_row(*row)

    return table


def format_json(data: Any, title: Optional[str] = None) -> None:
    """Format and display JSON data with syntax highlighting"""
    import json

    json_str = json.dumps(data, indent=2, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)

    if title:
        panel = Panel(syntax, title=title, border_style="blue")
        console.print(panel)
    else:
        console.print(syntax)


def format_yaml(data: Any, title: Optional[str] = None) -> None:
    """Format and display YAML data with syntax highlighting"""
    import yaml

    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)

    if title:
        panel = Panel(syntax, title=title, border_style="blue")
        console.print(panel)
    else:
        console.print(syntax)


def format_component_list(components: List[Dict[str, Any]],
                          title: str = "Components") -> None:
    """Format and display component list"""
    if not components:
        console.print(f"[yellow]No {title.lower()} found[/yellow]")
        return

    table = Table(title=title, box=box.SIMPLE)
    table.add_column("Type", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Created", style="dim")
    table.add_column("Size", style="dim")

    for comp in components:
        table.add_row(
            comp['type'],
            comp['version'],
            comp.get('created_at', 'N/A'),
            _format_size(comp.get('size', 0))
        )

    console.print(table)


def format_release_list(releases: List[Dict[str, Any]]) -> None:
    """Format and display release list"""
    if not releases:
        console.print("[yellow]No releases found[/yellow]")
        return

    table = Table(title="Releases", box=box.SIMPLE)
    table.add_column("Version", style="cyan")
    table.add_column("Components", style="green")
    table.add_column("Created", style="dim")

    for release in releases:
        components = release.get('components', [])
        comp_summary = f"{len(components)} components"
        table.add_row(
            release['version'],
            comp_summary,
            release.get('created_at', 'N/A')
        )

    console.print(table)


def format_status(status: Dict[str, Any]) -> None:
    """Format and display deployment status"""
    panel_content = []

    if 'target' in status:
        panel_content.append(f"[bold]Target:[/bold] {status['target']}")

    if 'environment' in status:
        panel_content.append(f"[bold]Environment:[/bold] {status['environment']}")

    if 'deployed_components' in status:
        panel_content.append(f"[bold]Deployed:[/bold] {len(status['deployed_components'])} components")

    if 'last_deployment' in status:
        panel_content.append(f"[bold]Last deployment:[/bold] {status['last_deployment']}")

    panel = Panel(
        "\n".join(panel_content),
        title="Deployment Status",
        border_style="blue"
    )
    console.print(panel)


def format_verification_result(result: Dict[str, Any]) -> None:
    """Format and display verification result"""
    if result['success']:
        console.print(f"[green]✓ Verification passed[/green]")
    else:
        console.print(f"[red]✗ Verification failed[/red]")

        if 'errors' in result and result['errors']:
            console.print("\n[bold red]Errors:[/bold red]")
            for error in result['errors']:
                console.print(f"  • {error}")

        if 'warnings' in result and result['warnings']:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in result['warnings']:
                console.print(f"  • {warning}")


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0

    while size_bytes >= 1024 and unit_index < len(units) - 1:
        size_bytes /= 1024.0
        unit_index += 1

    return f"{size_bytes:.1f}{units[unit_index]}"


def print_error(message: str, error: Optional[Exception] = None) -> None:
    """Print error message"""
    if error:
        console.print(f"[red]Error:[/red] {message}: {str(error)}")
    else:
        console.print(f"[red]Error:[/red] {message}")


def print_warning(message: str) -> None:
    """Print warning message"""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def print_info(message: str) -> None:
    """Print info message"""
    console.print(f"[blue]Info:[/blue] {message}")


def print_success(message: str) -> None:
    """Print success message"""
    console.print(f"[green]Success:[/green] {message}")