"""Output formatting utilities"""

from pathlib import Path
from typing import Optional, List, Dict, Any

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
            f"[bold]Size:[/bold] {_format_size(result.size)}",
        ]

        if result.manifest_path:
            lines.append(f"[bold]Manifest:[/bold] {result.manifest_path}")

        if result.compression_ratio:
            lines.append(f"[bold]Compression:[/bold] {result.compression_ratio:.1%}")

        panel = Panel(
            "\n".join(lines),
            title="Pack Result",
            border_style="green"
        )
        console.print(panel)

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
            f"[green]✓[/green] Publish completed successfully!",
            f"",
            f"[bold]Components:[/bold] {len(result.published_components)}",
        ]

        if result.release_version:
            lines.append(f"[bold]Release:[/bold] {result.release_version}")

        if result.release_name:
            lines.append(f"[bold]Name:[/bold] {result.release_name}")

        # Component list
        if result.published_components:
            lines.append("")
            lines.append("[bold]Published:[/bold]")
            for comp in result.published_components:
                lines.append(f"  • {comp.type}:{comp.version}")

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
            f"[bold]Target:[/bold] {result.target}",
            f"[bold]Components:[/bold] {len(result.deployed_components)}",
        ]

        if result.environment:
            lines.append(f"[bold]Environment:[/bold] {result.environment}")

        # Verification status
        if result.verification_results:
            all_passed = all(result.verification_results.values())
            status = "[green]Passed[/green]" if all_passed else "[yellow]Partial[/yellow]"
            lines.append(f"[bold]Verification:[/bold] {status}")

        panel = Panel(
            "\n".join(lines),
            title="Deploy Result",
            border_style="green"
        )
        console.print(panel)

    else:
        lines = [f"[red]✗ Deploy failed:[/red] {result.error}"]

        if result.rollback_performed:
            lines.append("")
            lines.append("[yellow]Rollback was performed[/yellow]")

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
    console.print(Panel(advice, title="Next Steps", border_style="yellow"))


def format_table(data: List[Dict[str, Any]],
                 columns: List[tuple[str, str]],
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


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"