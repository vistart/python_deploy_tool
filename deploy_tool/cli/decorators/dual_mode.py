# deploy_tool/cli/decorators/dual_mode.py
"""Dual-mode decorator for supporting both CLI and programmatic usage"""

import functools
from typing import Callable, Optional

import click


def dual_mode_command(name: Optional[str] = None):
    """
    Decorator to support both CLI and programmatic calls

    This decorator allows a command to be called both from the CLI
    (with Click context) and programmatically (without context).

    Args:
        name: Optional command name for programmatic calls

    Example:
        @click.command()
        @dual_mode_command()
        def my_command(ctx, arg1, arg2):
            # Can be called as:
            # 1. CLI: deploy-tool my-command --arg1 value1 --arg2 value2
            # 2. Code: my_command(arg1='value1', arg2='value2')
    """

    def decorator(func: Callable) -> Callable:
        # Store original function for programmatic access
        func._original = func
        func._is_dual_mode = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if called with Click context
            if args and isinstance(args[0], click.Context):
                # CLI mode - call normally
                return func(*args, **kwargs)
            else:
                # Programmatic mode - create minimal context
                # This allows the function to work without full CLI setup

                # Create a dummy command for context
                cmd = click.Command(name or func.__name__)

                # Create minimal context
                ctx = click.Context(cmd)

                # Set up basic context attributes
                ctx.obj = type('obj', (), {
                    'project_root': None,
                    'path_resolver': None,
                    'verbose': False,
                    'debug': False
                })()

                # Call function with synthetic context
                return func(ctx, *args, **kwargs)

        # Expose original function for direct access
        wrapper.original = func

        # Preserve Click decorators
        if hasattr(func, '__click_params__'):
            wrapper.__click_params__ = func.__click_params__

        return wrapper

    # Handle both @dual_mode_command and @dual_mode_command()
    if callable(name):
        # Called as @dual_mode_command without parentheses
        func = name
        name = None
        return decorator(func)
    else:
        # Called as @dual_mode_command() or @dual_mode_command(name="...")
        return decorator


def expose_api(cli_function: Callable) -> Callable:
    """
    Create a programmatic API function from a CLI command

    This function extracts the core logic from a CLI command
    and exposes it as a regular Python function.

    Args:
        cli_function: The CLI command function

    Returns:
        A regular Python function without CLI dependencies

    Example:
        # In CLI module
        @click.command()
        @click.option('--type', required=True)
        def pack_command(ctx, type, version):
            # CLI implementation
            pass

        # In API module
        pack = expose_api(pack_command)

        # Now can be used as:
        result = pack(type='model', version='1.0.0')
    """

    @functools.wraps(cli_function)
    def api_wrapper(**kwargs):
        # Check if the function has dual-mode support
        if hasattr(cli_function, '_is_dual_mode'):
            # Call directly with kwargs
            return cli_function(**kwargs)
        else:
            # Create synthetic context for non-dual-mode commands
            cmd = click.Command(cli_function.__name__)
            ctx = click.Context(cmd)

            # Convert kwargs to Click parameters
            return cli_function(ctx, **kwargs)

    return api_wrapper