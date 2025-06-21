# deploy_tool/cli/main.py
"""Main CLI entry point for deploy-tool"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from ..constants import APP_NAME, LOG_FORMAT
from ..core import PathResolver, ProjectManager
from ..api.exceptions import ProjectNotFoundError

# Import all commands
from .commands import (
    init,
    pack,
    publish,
    deploy,
    component,
    release,
    doctor,
    paths
)

console = Console()


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Setup logging configuration

    Args:
        verbose: Enable verbose output (INFO level)
        debug: Enable debug output (DEBUG level)
    """
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    # Configure rich handler
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=[
            RichHandler(
                console=console,
                show_time=debug,
                show_path=debug,
                rich_tracebacks=True,
                tracebacks_suppress=[click]
            )
        ]
    )

    # Adjust third-party loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiofiles").setLevel(logging.WARNING)


class Context:
    """CLI context object with lazy project initialization

    This context implements lazy loading for project-related attributes.
    Project root and path resolver are only initialized when accessed
    by commands that require them.
    """

    def __init__(self):
        """Initialize CLI context"""
        self._project_root: Optional[Path] = None
        self._path_resolver: Optional[PathResolver] = None
        self._project_manager: Optional[ProjectManager] = None
        self.verbose: bool = False
        self.debug: bool = False
        self._project_checked: bool = False
        self._project_required: bool = False

    def require_project(self) -> None:
        """Mark that the current command requires a project context"""
        self._project_required = True

    @property
    def project_root(self) -> Optional[Path]:
        """Get project root directory (lazy loading)

        Returns:
            Project root path or None if not in a project
        """
        if self._project_required and not self._project_checked:
            self._check_project()
        return self._project_root

    @property
    def path_resolver(self) -> Optional[PathResolver]:
        """Get path resolver instance (lazy loading)

        Returns:
            PathResolver instance or None if not in a project
        """
        if self._project_required and not self._project_checked:
            self._check_project()
        return self._path_resolver

    def _check_project(self) -> None:
        """Check for project existence and initialize if found

        This method is called only once when a project-requiring command
        is executed. It attempts to find the project root and create
        the necessary instances.
        """
        self._project_checked = True

        try:
            if self._project_manager is None:
                self._project_manager = ProjectManager()

            # Try to find project root without throwing exception
            project_root = self._find_project_root_safe()

            if project_root:
                self._project_root = project_root
                self._path_resolver = PathResolver(project_root)
                if self.debug:
                    console.print(f"[dim]Project root: {project_root}[/dim]")
            else:
                # No project found - commands will handle this
                if self.debug:
                    console.print("[dim]No project found in current directory tree[/dim]")

        except Exception as e:
            # Log error but don't fail - let commands handle it
            if self.debug:
                console.print(f"[dim]Error checking for project: {e}[/dim]")

    def _find_project_root_safe(self) -> Optional[Path]:
        """Find project root without throwing exceptions

        Returns:
            Project root path or None if not found
        """
        try:
            # Create a temporary resolver to search for project
            temp_resolver = PathResolver()
            return temp_resolver.find_project_root()
        except ProjectNotFoundError:
            return None
        except Exception:
            # Any other error, return None
            return None


@click.group(name=APP_NAME)
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output')
@click.option('-q', '--quiet', is_flag=True, help='Suppress all output except errors')
@click.pass_context
def cli(ctx, verbose, debug, quiet):
    """Deploy Tool - Package and deploy non-code resources

    This tool helps you package, publish, and deploy non-code resources
    such as model weights, configuration files, and runtime environments.

    Code files are managed through Git and don't need packaging.
    This tool is designed for binary assets and large files.
    """
    # Setup logging
    if quiet:
        logging.disable(logging.CRITICAL)
    else:
        setup_logging(verbose=verbose, debug=debug)

    # Create context with lazy initialization
    ctx.obj = Context()
    ctx.obj.verbose = verbose
    ctx.obj.debug = debug

    # Don't check for project here - let commands that need it check


# Register commands
cli.add_command(init.init)
cli.add_command(pack.pack)
cli.add_command(publish.publish)
cli.add_command(deploy.deploy)
cli.add_command(component.component)
cli.add_command(release.release)
cli.add_command(doctor.doctor)
cli.add_command(paths.paths)


def main():
    """Main entry point for the CLI application

    This function handles:
    - Auto-help for incomplete commands
    - Keyboard interrupts
    - Unexpected exceptions with proper error display
    """
    try:
        # Handle help for incomplete commands
        if len(sys.argv) == 2 and sys.argv[1] not in [
            '-h', '--help', '-v', '--verbose', '-d', '--debug', '-q', '--quiet'
        ]:
            # If only command name provided, show its help
            sys.argv.append('--help')

        cli(prog_name=APP_NAME)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)

    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if '--debug' in sys.argv or '-d' in sys.argv:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()