"""Project context decorators"""

import functools
import sys
from typing import Callable

import click
from rich.console import Console

console = Console()


def require_project(func: Callable) -> Callable:
    """Decorator that ensures a valid project context exists

    This decorator:
    1. Marks the context as requiring a project
    2. Triggers lazy loading of project root and path resolver
    3. Checks that a valid project was found
    4. Shows appropriate error messages if no project exists

    Example:
        @click.command()
        @require_project
        def pack(ctx, ...):
            # Can safely use ctx.obj.path_resolver

    Args:
        func: The command function to decorate

    Returns:
        Wrapped function that checks for project context
    """

    @functools.wraps(func)
    def wrapper(ctx: click.Context, *args, **kwargs):
        """Wrapper function that performs project checks"""

        # Mark that this command requires a project
        if hasattr(ctx.obj, 'require_project'):
            ctx.obj.require_project()

        # Access path_resolver to trigger lazy loading
        if ctx.obj.path_resolver is None:
            console.print("[red]Error: No deployment project found[/red]")
            console.print("\nThis command must be run within a deployment project.")
            console.print("Look for a parent directory containing '.deploy-tool.yaml'")
            console.print("\n[yellow]Hint:[/yellow] Run 'deploy-tool init' to create a new project")
            sys.exit(1)

        # Also ensure project root is available
        if ctx.obj.project_root is None:
            console.print("[red]Error: Project root not determined[/red]")
            console.print("\nThis should not happen. Please report this issue.")
            sys.exit(1)

        # Call the original function
        return func(ctx, *args, **kwargs)

    return wrapper


def ensure_no_project(func: Callable) -> Callable:
    """Decorator that ensures NO project context exists (or warns if it does)

    This is used for commands like 'init' that create new projects.
    It warns if running inside an existing project but doesn't block
    the operation (user might want to re-initialize).

    Example:
        @click.command()
        @ensure_no_project
        def init(ctx, ...):
            # Safe to create new project

    Args:
        func: The command function to decorate

    Returns:
        Wrapped function that checks for existing project
    """

    @functools.wraps(func)
    def wrapper(ctx: click.Context, *args, **kwargs):
        """Wrapper function that checks for existing project"""

        # For init command, check if already in a project
        # Note: We don't call require_project() here
        if hasattr(ctx.obj, '_find_project_root_safe'):
            existing_root = ctx.obj._find_project_root_safe()

            if existing_root:
                # Get the target path from args if provided
                target_path = Path(args[0]) if args and len(args) > 0 else Path('.')
                target_path = target_path.resolve()

                # Only warn if trying to init in the current project root
                if existing_root == target_path:
                    console.print("[yellow]Warning: Already in a deployment project[/yellow]")
                    console.print(f"Project root: {existing_root}")
                    console.print()

        return func(ctx, *args, **kwargs)

    return wrapper


def with_project_defaults(func: Callable) -> Callable:
    """Decorator that applies project-specific defaults to command options

    This decorator reads project configuration and applies defaults
    before the command executes. It's useful for commands that have
    options that can be defaulted from project config.

    Example:
        @click.command()
        @click.option('--output', default=None)
        @require_project
        @with_project_defaults
        def pack(ctx, output, ...):
            # output will be set from project config if not provided

    Args:
        func: The command function to decorate

    Returns:
        Wrapped function with defaults applied
    """

    @functools.wraps(func)
    def wrapper(ctx: click.Context, *args, **kwargs):
        """Wrapper function that applies project defaults"""

        # Only apply defaults if we have a project context
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