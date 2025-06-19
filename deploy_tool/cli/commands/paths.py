"""Path management command"""

import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ..decorators import require_project

console = Console()


@click.command()
@click.option('--resolve', help='Resolve a specific path')
@click.option('--tree', is_flag=True, help='Show directory tree')
@click.option('--validate', help='Validate if path is within project')
@click.option('--show-config', is_flag=True, help='Show path configuration')
@click.pass_context
@require_project
def paths(ctx, resolve, tree, validate, show_config):
    """Path management utilities

    This command helps debug and manage paths within the deployment project.
    It can resolve paths, show the project structure, and validate path locations.

    Examples:
        # Show all configured paths
        deploy-tool paths

        # Resolve a specific path
        deploy-tool paths --resolve ./models

        # Show directory tree
        deploy-tool paths --tree

        # Validate a path
        deploy-tool paths --validate /absolute/path/to/file
    """
    resolver = ctx.obj.path_resolver

    # Default: show all paths
    if not any([resolve, tree, validate, show_config]):
        show_config = True

    # Show configuration
    if show_config:
        table = Table(title="Project Paths", box=box.ROUNDED)
        table.add_column("Path Type", style="cyan")
        table.add_column("Absolute Path", style="green")
        table.add_column("Relative Path", style="yellow")

        # Project paths - 注意：使用方法调用而不是属性访问
        paths_info = [
            ("Project Root", resolver.project_root, "."),
            ("Deployment", resolver.get_deployment_dir(), "deployment/"),
            ("Manifests", resolver.get_manifests_dir(), "deployment/manifests/"),
            ("Releases", resolver.get_releases_dir(), "deployment/releases/"),
            ("Configs", resolver.get_configs_dir(), "deployment/package-configs/"),
            ("Output", resolver.get_dist_dir(), "dist/"),
        ]

        for name, abs_path, rel_path in paths_info:
            table.add_row(name, str(abs_path), rel_path)

        console.print(table)

        # Show environment info
        console.print("\n[bold]Environment:[/bold]")
        console.print(f"  Current Directory: {Path.cwd()}")
        console.print(f"  Project Config: {resolver.project_root / '.deploy-tool.yaml'}")

    # Resolve specific path
    if resolve:
        try:
            input_path = Path(resolve)
            resolved = resolver.resolve(input_path)
            relative = resolver.to_relative(resolved)

            console.print(f"\n[bold]Path Resolution:[/bold]")
            console.print(f"  Input:     {resolve}")
            console.print(f"  Absolute:  {resolved}")
            console.print(f"  Relative:  {relative}")
            console.print(f"  Exists:    {'Yes' if resolved.exists() else 'No'}")

        except Exception as e:
            console.print(f"[red]Error resolving path: {e}[/red]")
            sys.exit(1)

    # Show directory tree
    if tree:
        def build_tree(path: Path, tree_node: Tree, max_depth: int = 3,
                       current_depth: int = 0):
            """Recursively build directory tree"""
            if current_depth >= max_depth:
                return

            try:
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                for item in items:
                    if item.name.startswith('.') and item.name not in ['.deploy-tool.yaml']:
                        continue

                    if item.is_dir():
                        if item.name in ['__pycache__', 'node_modules', '.git']:
                            continue
                        branch = tree_node.add(f"📁 {item.name}/")
                        build_tree(item, branch, max_depth, current_depth + 1)
                    else:
                        icon = "📄"
                        if item.suffix == '.yaml':
                            icon = "⚙️"
                        elif item.suffix == '.json':
                            icon = "📋"
                        elif item.suffix in ['.tar.gz', '.zip']:
                            icon = "📦"
                        tree_node.add(f"{icon} {item.name}")

            except PermissionError:
                tree_node.add("[red]Permission Denied[/red]")

        project_tree = Tree(f"📁 {resolver.project_root.name}/")
        build_tree(resolver.project_root, project_tree)

        console.print("\n[bold]Project Structure:[/bold]")
        console.print(project_tree)

    # Validate path
    if validate:
        try:
            path_to_validate = Path(validate).resolve()
            is_valid = resolver.validate_path_within_project(path_to_validate)

            console.print(f"\n[bold]Path Validation:[/bold]")
            console.print(f"  Path:         {validate}")
            console.print(f"  Resolved:     {path_to_validate}")
            console.print(f"  Within Project: {'Yes' if is_valid else 'No'}")

            if not is_valid:
                console.print(f"  [yellow]Warning: Path is outside project boundary[/yellow]")
                sys.exit(1)
            else:
                console.print(f"  [green]✓ Path is valid[/green]")

        except Exception as e:
            console.print(f"[red]Error validating path: {e}[/red]")
            sys.exit(1)