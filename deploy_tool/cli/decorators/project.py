"""Project context decorators"""

import functools
import sys
from typing import Callable

import click
from rich.console import Console

console = Console()


def require_project(func: Callable) -> Callable:
    """
    Decorator that ensures a valid project context exists

    This decorator checks that:
    1. A project root has been found
    2. The path resolver is initialized

    If no project is found, it shows an error and suggests running 'init'.

    Example:
        @click.command()
        @require_project
        def pack(ctx, ...):
            # Can safely use ctx.obj.path_resolver
    """

    @functools.wraps(func)
    def wrapper(ctx: click.Context, *args, **kwargs):
        # Check if we have a valid project context
        if not hasattr(ctx.obj, 'path_resolver') or ctx.obj.path_resolver is None:
            console.print("[red]Error: No deployment project found[/red]")
            console.print("\nThis command must be run within a deployment project.")
            console.print("Look for a parent directory containing '.deploy-tool.yaml'")
            console.print("\n[yellow]Hint:[/yellow] Run 'deploy-tool init' to create a new project")
            sys.exit(1)

        # Ensure project root is set
        if not hasattr(ctx.obj, 'project_root') or ctx.obj.project_root is None:
            console.print("[red]Error: Project root not determined[/red]")
            sys.exit(1)

        # Call the original function
        return func(ctx, *args, **kwargs)

    return wrapper


def ensure_no_project(func: Callable) -> Callable:
    """
    Decorator that ensures NO project context exists

    This is used for commands like 'init' that should not be run
    inside an existing project.

    Example:
        @click.command()
        @ensure_no_project
        def init(ctx, ...):
            # Safe to create new project
    """

    @functools.wraps(func)
    def wrapper(ctx: click.Context, *args, **kwargs):
        # For init command, we check if trying to init in existing project
        # But only warn, don't block (user might want to re-init)
        if hasattr(ctx.obj, 'path_resolver') and ctx.obj.path_resolver is not None:
            project_root = ctx.obj.project_root
            # Get the path argument if provided
            if args and len(args) > 0:
                target_path = args[0]
            else:
                target_path = '.'

            # Only warn if trying to init in the current project root
            if str(project_root) == str(target_path):
                console.print("[yellow]Warning: Already in a deployment project[/yellow]")
                console.print(f"Project root: {project_root}")

        return func(ctx, *args, **kwargs)

    return wrapper


def with_project_defaults(func: Callable) -> Callable:
    """
    Decorator that applies project-specific defaults to command options

    This decorator can read project configuration and apply defaults
    before the command executes.

    Example:
        @click.command()
        @click.option('--output', default=None)
        @require_project
        @with_project_defaults
        def pack(ctx, output, ...):
            # output will be set from project config if not provided
    """

    @functools.wraps(func)
    def wrapper(ctx: click.Context, *args, **kwargs):
        # Load project configuration if available
        if hasattr(ctx.obj, 'path_resolver') and ctx.obj.path_resolver:
            try:
                # Load project config
                config_file = ctx.obj.project_root / '.deploy-tool.yaml'
                if config_file.exists():
                    import yaml
                    with open(config_file) as f:
                        config = yaml.safe_load(f)

                    # Apply defaults from config
                    defaults = config.get('defaults', {})

                    # Update kwargs with defaults if not explicitly provided
                    for key, value in defaults.items():
                        if key in kwargs and kwargs[key] is None:
                            kwargs[key] = value

            except Exception as e:
                if ctx.obj.debug:
                    console.print(f"[yellow]Warning: Could not load project defaults: {e}[/yellow]")

        return func(ctx, *args, **kwargs)

    return wrapper