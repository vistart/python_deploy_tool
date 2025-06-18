"""Main CLI entry point"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .. import __version__
from ..core import PathResolver
from ..api.exceptions import ProjectNotFoundError

# Import commands
from .commands import (
    init,
    pack,
    publish,
    deploy,
    component,
    release,
    doctor,
    paths,
)

console = Console()


class GlobalContext:
    """Global context for CLI"""

    def __init__(self):
        self.project_root: Optional[Path] = None
        self.path_resolver: Optional[PathResolver] = None
        self.verbose: bool = False
        self.debug: bool = False
        self.no_color: bool = False


@click.group(invoke_without_command=True)
@click.option('--version', '-V', is_flag=True, help='Show version and exit')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--debug', is_flag=True, help='Debug mode')
@click.option('--project-root', type=click.Path(exists=True), help='Project root directory')
@click.option('--config', '-c', type=click.Path(exists=True), help='Global configuration file')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.pass_context
def cli(ctx, version, verbose, debug, project_root, config, no_color):
    """Deploy Tool - A powerful deployment tool for ML models and algorithms"""

    # Handle version flag
    if version:
        click.echo(f"deploy-tool version {__version__}")
        ctx.exit(0)

    # Show help if no command
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)

    # Create global context
    global_ctx = GlobalContext()
    global_ctx.verbose = verbose
    global_ctx.debug = debug
    global_ctx.no_color = no_color

    # Handle project root
    if project_root:
        global_ctx.project_root = Path(project_root)
        global_ctx.path_resolver = PathResolver(global_ctx.project_root)
    else:
        # Try to find project root
        try:
            global_ctx.path_resolver = PathResolver()
            global_ctx.project_root = global_ctx.path_resolver.project_root
        except ProjectNotFoundError:
            # Only error if not running init command
            if ctx.invoked_subcommand != 'init':
                global_ctx.path_resolver = None
                global_ctx.project_root = None

    # Store in click context
    ctx.obj = global_ctx

    # Configure console
    if no_color:
        console.no_color = True

    # Show debug info
    if debug and global_ctx.project_root:
        console.print(f"[dim]Project root: {global_ctx.project_root}[/dim]")


# Register commands
cli.add_command(init.init)
cli.add_command(pack.pack)
cli.add_command(publish.publish)
cli.add_command(deploy.deploy)
cli.add_command(component.component)
cli.add_command(release.release)
cli.add_command(doctor.doctor)
cli.add_command(paths.paths)


def main(args=None):
    """Main entry point"""
    try:
        # Handle both CLI and programmatic calls
        if args is None:
            args = sys.argv[1:]

        # Special handling for python -m deploy_tool
        if not args and len(sys.argv) > 0:
            # Show help when no arguments
            cli.main(['--help'])
        else:
            cli.main(args)

    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except ProjectNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[yellow]Hint:[/yellow] Run 'deploy-tool init' to initialize a project")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if '--debug' in sys.argv:
            console.print_exception()
        else:
            console.print(f"[red]Error:[/red] {e}")
            console.print("\n[dim]Run with --debug for full traceback[/dim]")
        sys.exit(1)


if __name__ == '__main__':
    main()