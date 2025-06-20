"""Main CLI entry point for deploy-tool"""

import sys
import os
from pathlib import Path

import click
from rich.console import Console

from .commands import init, pack, publish, deploy, config
from .utils.output import console, setup_logging
from ..constants import EMOJI_ROCKET


# Version info
from .. import __version__


@click.group(invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='Show version and exit')
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.pass_context
def cli(ctx, version, debug, quiet):
    """Deploy Tool - Simplified deployment for ML projects

    A powerful tool for packaging, publishing, and deploying machine learning
    models and algorithms with automatic failover and version management.
    """
    # Setup logging
    if debug:
        setup_logging(level="DEBUG")
    elif quiet:
        setup_logging(level="WARNING")
    else:
        setup_logging(level="INFO")

    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['quiet'] = quiet

    # Show version if requested
    if version:
        console.print(f"deploy-tool version {__version__}")
        ctx.exit(0)

    # Show help if no command
    if ctx.invoked_subcommand is None:
        console.print(f"{EMOJI_ROCKET} [bold]Deploy Tool v{__version__}[/bold]\n")
        console.print("Use 'deploy-tool --help' for usage information.")
        console.print("Use 'deploy-tool <command> --help' for command help.")

        # Show available commands
        console.print("\n[bold]Available commands:[/bold]")
        console.print("  init      - Initialize a new project")
        console.print("  pack      - Package a component")
        console.print("  publish   - Publish to storage targets")
        console.print("  deploy    - Deploy a component")
        console.print("  config    - Manage configuration")

        console.print("\n[bold]Quick start:[/bold]")
        console.print("  1. deploy-tool init")
        console.print("  2. deploy-tool pack ./models --type model --version 1.0.0")
        console.print("  3. deploy-tool publish model:1.0.0")
        console.print("  4. deploy-tool deploy model:1.0.0")


# Register commands
cli.add_command(init.init)
cli.add_command(pack.pack)
cli.add_command(publish.publish)
cli.add_command(deploy.deploy)
cli.add_command(config.config)


# Additional command groups
@cli.group()
def version():
    """Manage deployed versions"""
    pass


@version.command('list')
@click.argument('component_type', required=False)
@click.pass_context
def version_list(ctx, component_type):
    """List deployed versions"""
    # Import here to avoid circular imports
    from .commands.deploy import _list_deployed_versions
    import asyncio

    # This is handled by deploy --list
    ctx.invoke(deploy.deploy, list_versions=True, component_spec=component_type)


@version.command('switch')
@click.argument('component_spec')
@click.pass_context
def version_switch(ctx, component_spec):
    """Switch to a different version"""
    # Use deploy command with switch flag
    from . import deploy as deploy_module
    ctx.invoke(deploy_module.deploy, switch=True, component_spec=component_spec)


@cli.group()
def doctor():
    """Diagnose and fix issues"""
    pass


@doctor.command('check')
@click.option('--fix', is_flag=True, help='Attempt to fix issues')
def doctor_check(fix):
    """Check deployment environment"""
    from .commands.doctor import check_environment
    check_environment(fix)


@doctor.command('clean')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned')
@click.option('--all', 'clean_all', is_flag=True, help='Clean all cache and temp files')
def doctor_clean(dry_run, clean_all):
    """Clean up temporary files and cache"""
    from .commands.doctor import clean_cache
    clean_cache(dry_run, clean_all)


def main():
    """Main entry point"""
    try:
        # Set up environment
        setup_environment()

        # Run CLI
        cli(prog_name='deploy-tool')

    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled by user[/red]")
        sys.exit(1)
    except Exception as e:
        if '--debug' in sys.argv or os.environ.get('DEPLOY_TOOL_DEBUG'):
            # Show full traceback in debug mode
            console.print_exception()
        else:
            # Show clean error message
            console.print(f"\n[red]Error:[/red] {str(e)}")
            console.print("\nRun with --debug for full traceback")
        sys.exit(1)


def setup_environment():
    """Set up runtime environment"""
    # Ensure UTF-8 encoding
    if sys.platform == 'win32':
        # Windows specific
        import locale
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')

    # Disable Python warnings in production
    if not os.environ.get('DEPLOY_TOOL_DEBUG'):
        import warnings
        warnings.filterwarnings('ignore')

    # Set asyncio policy for Windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# Allow running as module
if __name__ == '__main__':
    main()