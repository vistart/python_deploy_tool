"""Output formatting utilities with improved error handling"""

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
        ]

        if result.archive_size:
            lines.append(f"[bold]Size:[/bold] {_format_size(result.archive_size)}")

        if result.manifest_path:
            lines.append(f"[bold]Manifest:[/bold] {result.manifest_path}")

        if result.metadata.get('compression_ratio'):
            lines.append(f"[bold]Compression:[/bold] {result.metadata['compression_ratio']:.1%}")

        panel = Panel(
            "\n".join(lines),
            title="[bold green]Pack Result[/bold green]",
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
            f"[red]✗ Pack failed:[/red]\n\n{result.error}",
            title="[bold red]Pack Error[/bold red]",
            border_style="red"
        )
        console.print(panel)


def format_publish_result(result: PublishResult) -> None:
    """Format and display publish operation result"""
    if result.success:
        lines = [
            f"[green]✓[/green] Publish completed successfully!",
            f"",
<<<<<<< HEAD
=======
            f"[bold]Components:[/bold] {len(result.published_components)}",
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
        ]

        # Check which attribute exists (for compatibility)
        components = getattr(result, 'published_components', None) or getattr(result, 'components', [])

        # Duration if available
        if hasattr(result, 'duration') and result.duration:
            lines.append(f"[bold]Duration:[/bold] {result.duration:.2f}s")

        # Component count
        if components:
            # Handle both list of ComponentPublishResult and simple components
            if hasattr(components[0], 'success'):
                success_count = sum(1 for c in components if c.success)
                lines.append(f"[bold]Components:[/bold] {success_count} published")
            else:
                lines.append(f"[bold]Components:[/bold] {len(components)}")

        if result.release_version:
            lines.append(f"[bold]Release:[/bold] {result.release_version}")

<<<<<<< HEAD
        # Success panel
=======
        if result.release_name:
            lines.append(f"[bold]Name:[/bold] {result.release_name}")

        # Component list
        if result.published_components:
            lines.append("")
            lines.append("[bold]Published:[/bold]")
            for comp in result.published_components:
                lines.append(f"  • {comp.type}:{comp.version}")

>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
        panel = Panel(
            "\n".join(lines),
            title="[bold green]Publish Result[/bold green]",
            border_style="green"
        )
        console.print(panel)

        # Component details if we have detailed results
        if components and hasattr(components[0], 'success'):
            table = Table(title="Published Components", box=box.ROUNDED)
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Location", style="dim")

            for comp in components:
                status = "[green]✓ Success[/green]" if comp.success else "[red]✗ Failed[/red]"
                location = getattr(comp, 'remote_path', None) or "N/A"
                if hasattr(comp, 'error') and comp.error:
                    location = f"[red]{comp.error}[/red]"

                table.add_row(
                    f"{comp.component.type}:{comp.component.version}",
                    status,
                    location
                )

            console.print("\n")
            console.print(table)
        # Simple component list
        elif components:
            console.print("\n[bold]Published:[/bold]")
            for comp in components:
                console.print(f"  • {comp.type}:{comp.version}" if hasattr(comp, 'type') else f"  • {comp}")

        # Post-publish instructions
        if hasattr(result, 'post_publish_instructions') and result.post_publish_instructions:
            console.print("\n")
            instructions_panel = Panel(
                "\n".join(result.post_publish_instructions),
                title="[bold cyan]Next Steps[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED
            )
            console.print(instructions_panel)

    else:
        # Error handling with detailed information
        error_lines = [f"[red]✗ Publishing failed[/red]"]

        if result.error:
            error_lines.append("")
            error_lines.append(f"[bold]Error:[/bold] {result.error}")

        if hasattr(result, 'duration') and result.duration:
            error_lines.append(f"[bold]Duration:[/bold] {result.duration:.2f}s")

        # Show partial results if available
        components = getattr(result, 'published_components', None) or getattr(result, 'components', [])
        if components and hasattr(components[0], 'success'):
            success_count = sum(1 for c in components if c.success)
            failed_count = sum(1 for c in components if not c.success)

            if success_count > 0:
                error_lines.append(f"[yellow]Partially published:[/yellow] {success_count} components")
            if failed_count > 0:
                error_lines.append(f"[red]Failed:[/red] {failed_count} components")

        # Error panel
        panel = Panel(
            "\n".join(error_lines),
            title="[bold red]Publish Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(panel)

        # Show failed components details if available
        if components and hasattr(components[0], 'success'):
            failed_components = [c for c in components if not c.success]
            if failed_components:
                console.print("\n[bold red]Failed Components:[/bold red]")
                for comp in failed_components[:5]:  # Show first 5
                    console.print(f"  • {comp.component.type}:{comp.component.version}")
                    if hasattr(comp, 'error') and comp.error:
                        console.print(f"    [dim]{comp.error}[/dim]")

                if len(failed_components) > 5:
                    console.print(f"  [dim]... and {len(failed_components) - 5} more[/dim]")


def format_deploy_result(result: DeployResult) -> None:
    """Format and display deploy operation result"""
    if result.success:
        lines = [
            f"[green]✓[/green] Deployment completed successfully!",
            f"",
<<<<<<< HEAD
            f"[bold]Target:[/bold] {result.target_dir}",
            f"[bold]Release:[/bold] {result.release_version}",
        ]

        # Add component count
        if result.components:
            lines.append(f"[bold]Components:[/bold] {len(result.components)}")

        # Verification status
        if hasattr(result, 'verification') and result.verification:
            if result.verification.get('success'):
                lines.append(f"[bold]Verification:[/bold] [green]Passed[/green]")
            else:
                lines.append(f"[bold]Verification:[/bold] [red]Failed[/red]")
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

        panel = Panel(
            "\n".join(lines),
            title="[bold green]Deploy Result[/bold green]",
            border_style="green"
        )
        console.print(panel)

        # Show deployed components
        if result.components:
            console.print("\n[bold]Deployed Components:[/bold]")
            for comp_type, comp_path in result.components.items():
                console.print(f"  • {comp_type}: {comp_path}")

        # Show symlinks created
        if result.symlinks:
            console.print("\n[bold]Symlinks Created:[/bold]")
            for link, target in result.symlinks.items():
                console.print(f"  • {link} → {target}")

    else:
<<<<<<< HEAD
        # Error panel
=======
        lines = [f"[red]✗ Deploy failed:[/red] {result.error}"]

        if result.rollback_performed:
            lines.append("")
            lines.append("[yellow]Rollback was performed[/yellow]")

>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
        panel = Panel(
            f"[red]✗ Deploy failed:[/red]\n\n{result.error}",
            title="[bold red]Deploy Error[/bold red]",
            border_style="red"
        )
        console.print(panel)


def show_git_advice(manifest_path: Path) -> None:
    """Show Git operation advice after creating manifests"""
    advice_lines = [
        "The following files were created and should be committed:",
        f"  • {manifest_path}",
        "",
        "Suggested Git workflow:",
        f"  [dim]git add {manifest_path}[/dim]",
        f"  [dim]git commit -m \"Add manifest for ...\"[/dim]",
        f"  [dim]git push[/dim]",
        "",
        "[dim]Note: The tool does not automatically commit files.[/dim]"
    ]

    panel = Panel(
        "\n".join(advice_lines),
        title="[bold yellow]Git Operations[/bold yellow]",
        border_style="yellow"
    )
    console.print("\n")
    console.print(panel)


<<<<<<< HEAD
def format_component_info(component: Dict[str, Any]) -> None:
    """Format and display component information"""
    info_lines = []
    info_lines.append(f"[bold]Type:[/bold] {component.get('type', 'N/A')}")
    info_lines.append(f"[bold]Version:[/bold] {component.get('version', 'N/A')}")
=======
[dim]Note: The tool does not automatically commit files.[/dim]
"""
    console.print(Panel(advice, title="Next Steps", border_style="yellow"))
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

    if 'created_at' in component:
        info_lines.append(f"[bold]Created:[/bold] {component['created_at']}")

    if 'size' in component:
        size_str = _format_size(component['size'])
        info_lines.append(f"[bold]Size:[/bold] {size_str}")

    if 'checksum' in component:
        checksum = component['checksum']
        if len(checksum) > 16:
            checksum = f"{checksum[:16]}..."
        info_lines.append(f"[bold]Checksum:[/bold] {checksum}")

    panel = Panel(
        "\n".join(info_lines),
        title=f"Component: {component.get('type', 'Unknown')}:{component.get('version', 'Unknown')}",
        border_style="cyan"
    )
    console.print(panel)


def format_status(status: Dict[str, Any]) -> None:
    """Format and display deployment status"""
    if not status:
        console.print("[yellow]No deployment found[/yellow]")
        return

    panel_content = []
    panel_content.append(f"[bold]Current Release:[/bold] {status.get('release_version', 'None')}")
    panel_content.append(f"[bold]Target Directory:[/bold] {status.get('target_dir', 'N/A')}")

    if 'deployed_at' in status:
        panel_content.append(f"[bold]Deployed At:[/bold] {status['deployed_at']}")

    if 'components' in status:
        panel_content.append(f"[bold]Components:[/bold] {len(status['components'])}")

    if 'last_deployment' in status:
        panel_content.append(f"[bold]Last Deployment:[/bold] {status['last_deployment']}")

    panel = Panel(
        "\n".join(panel_content),
        title="[bold blue]Deployment Status[/bold blue]",
        border_style="blue"
    )
    console.print(panel)


def format_verification_result(result: Dict[str, Any]) -> None:
    """Format and display verification result"""
    if result.get('success'):
        panel = Panel(
            "[green]✓ All verifications passed[/green]",
            title="[bold green]Verification Result[/bold green]",
            border_style="green"
        )
        console.print(panel)
    else:
        error_lines = ["[red]✗ Verification failed[/red]"]

        if 'errors' in result and result['errors']:
            error_lines.append("")
            error_lines.append("[bold]Errors:[/bold]")
            for error in result['errors'][:5]:  # Show first 5
                error_lines.append(f"  • {error}")
            if len(result['errors']) > 5:
                error_lines.append(f"  [dim]... and {len(result['errors']) - 5} more[/dim]")

        if 'warnings' in result and result['warnings']:
            error_lines.append("")
            error_lines.append("[bold yellow]Warnings:[/bold yellow]")
            for warning in result['warnings'][:3]:  # Show first 3
                error_lines.append(f"  • {warning}")

        panel = Panel(
            "\n".join(error_lines),
            title="[bold red]Verification Failed[/bold red]",
            border_style="red"
        )
        console.print(panel)


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
    """Print error message in a formatted panel"""
    if error:
        error_text = f"{message}\n\n[dim]Details:[/dim] {str(error)}"
    else:
        error_text = message

    panel = Panel(
        error_text,
        title="[bold red]Error[/bold red]",
        border_style="red"
    )
    console.print(panel)


def print_warning(message: str) -> None:
    """Print warning message"""
    console.print(f"[yellow]⚠ Warning:[/yellow] {message}")


def print_info(message: str) -> None:
    """Print info message"""
    console.print(f"[blue]ℹ Info:[/blue] {message}")


def print_success(message: str) -> None:
    """Print success message"""
    console.print(f"[green]✓ Success:[/green] {message}")


# Additional functions that were in the original file

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


<<<<<<< HEAD
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
            comp.get('type', 'N/A'),
            comp.get('version', 'N/A'),
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
            release.get('version', 'N/A'),
            comp_summary,
            release.get('created_at', 'N/A')
        )

    console.print(table)
=======
def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
