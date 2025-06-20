"""Project context decorator for CLI commands"""

import os
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

import click

from ..utils.output import console
from ...core.project_manager import ProjectManager
from ...constants import PROJECT_CONFIG_FILE, EMOJI_ERROR, EMOJI_WARNING


def project_required(func: Callable) -> Callable:
    """Decorator that ensures command runs in a valid project context

    This decorator:
    1. Finds the project root directory
    2. Loads project configuration
    3. Adds project info to click context
    4. Validates project structure

    Args:
        func: Command function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()

        # Find project root
        project_root = find_project_root()

        if not project_root:
            console.print(
                f"{EMOJI_ERROR} Not in a deploy-tool project directory.\n"
                f"Run 'deploy-tool init' to initialize a new project."
            )
            ctx.exit(1)

        # Add to context
        ctx.project_root = project_root
        ctx.ensure_object(dict)
        ctx.obj['project_root'] = project_root

        # Initialize project manager
        try:
            project_manager = ProjectManager(project_root)
            project = project_manager.load_project()

            # Add to context
            ctx.project = project
            ctx.project_manager = project_manager
            ctx.obj['project'] = project
            ctx.obj['project_manager'] = project_manager

        except Exception as e:
            console.print(
                f"{EMOJI_ERROR} Failed to load project: {str(e)}"
            )
            ctx.exit(1)

        # Validate project structure
        issues = project.validate()
        if issues:
            console.print(f"{EMOJI_WARNING} Project validation warnings:")
            for issue in issues:
                console.print(f"  - {issue}")
            console.print()

        # Run the actual command
        return func(*args, **kwargs)

    return wrapper


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the project root directory by looking for marker files

    Args:
        start_path: Starting directory (defaults to current directory)

    Returns:
        Project root path or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path

    # Check each directory up to root
    while current != current.parent:
        # Check for project config file
        if (current / PROJECT_CONFIG_FILE).exists():
            return current

        # Check for deployment directory (legacy projects)
        if (current / "deployment").is_dir():
            # Double-check it's a deploy-tool project
            if (current / "deployment" / "manifests").is_dir():
                return current

        # Move up
        current = current.parent

    # Check root directory
    if (current / PROJECT_CONFIG_FILE).exists():
        return current

    return None


def project_optional(func: Callable) -> Callable:
    """Decorator for commands that can work with or without a project

    Args:
        func: Command function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()

        # Try to find project root
        project_root = find_project_root()

        if project_root:
            # Add to context
            ctx.project_root = project_root
            ctx.ensure_object(dict)
            ctx.obj['project_root'] = project_root

            # Try to load project
            try:
                project_manager = ProjectManager(project_root)
                project = project_manager.load_project()

                ctx.project = project
                ctx.project_manager = project_manager
                ctx.obj['project'] = project
                ctx.obj['project_manager'] = project_manager

            except Exception:
                # Project load failed, but that's OK for optional
                ctx.project = None
                ctx.project_manager = None
        else:
            # No project found
            ctx.project_root = None
            ctx.project = None
            ctx.project_manager = None

        # Run the actual command
        return func(*args, **kwargs)

    return wrapper


def with_project_root(path_arg: str = 'path'):
    """Decorator that accepts a project root path argument

    Args:
        path_arg: Name of the path argument

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            ctx = click.get_current_context()

            # Get path from arguments
            path = kwargs.get(path_arg)

            if path:
                # Use provided path
                project_root = Path(path).resolve()

                # Verify it's a valid project
                if not (project_root / PROJECT_CONFIG_FILE).exists():
                    console.print(
                        f"{EMOJI_ERROR} No project found at: {project_root}"
                    )
                    ctx.exit(1)
            else:
                # Find project root from current directory
                project_root = find_project_root()

                if not project_root:
                    console.print(
                        f"{EMOJI_ERROR} Not in a deploy-tool project directory."
                    )
                    ctx.exit(1)

            # Add to context
            ctx.project_root = project_root
            ctx.ensure_object(dict)
            ctx.obj['project_root'] = project_root

            # Update kwargs with resolved path
            kwargs[path_arg] = project_root

            # Run the actual command
            return func(*args, **kwargs)

        return wrapper

    return decorator


def ensure_project_structure(*required_dirs):
    """Decorator that ensures required project directories exist

    Args:
        *required_dirs: Directory names to check/create

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @project_required
        def wrapper(*args, **kwargs):
            ctx = click.get_current_context()
            project_root = ctx.project_root

            # Check/create required directories
            for dir_name in required_dirs:
                dir_path = project_root / dir_name
                if not dir_path.exists():
                    console.print(
                        f"{EMOJI_WARNING} Creating missing directory: {dir_name}"
                    )
                    dir_path.mkdir(parents=True, exist_ok=True)

            # Run the actual command
            return func(*args, **kwargs)

        return wrapper

    return decorator