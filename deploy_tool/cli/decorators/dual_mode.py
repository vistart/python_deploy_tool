"""Dual mode decorator for CLI commands"""

import sys
import asyncio
from functools import wraps
from typing import Callable, Any

import click

from ..utils.output import console
from ...constants import OperationMode, EMOJI_INFO


def dual_mode_command(func: Callable) -> Callable:
    """Decorator that enables dual-mode (interactive/command-line) operation

    This decorator:
    1. Detects if running in TTY (interactive mode)
    2. Validates required parameters
    3. Adds 'interactive' flag to context
    4. Handles async execution

    Args:
        func: Command function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get click context
        ctx = click.get_current_context()

        # Detect TTY
        is_tty = sys.stdin.isatty() and sys.stdout.isatty()

        # Check if all required parameters are provided
        missing_params = []
        for param in ctx.command.params:
            if param.required and param.name not in kwargs:
                missing_params.append(param.name)

        # Determine operation mode
        if is_tty and missing_params:
            # Interactive mode
            ctx.interactive = True
            ctx.operation_mode = OperationMode.INTERACTIVE

            # Show mode indicator
            console.print(f"{EMOJI_INFO} [dim]Running in interactive mode[/dim]\n")

        else:
            # Command-line mode
            ctx.interactive = False
            ctx.operation_mode = OperationMode.COMMAND_LINE

        # Store mode in context for nested commands
        ctx.ensure_object(dict)
        ctx.obj['interactive'] = ctx.interactive
        ctx.obj['operation_mode'] = ctx.operation_mode

        # Handle async functions
        if asyncio.iscoroutinefunction(func):
            # Run async function
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context
                    task = asyncio.create_task(func(*args, **kwargs))
                    return task
                else:
                    # Create new event loop
                    return loop.run_until_complete(func(*args, **kwargs))
            except KeyboardInterrupt:
                console.print("\n[red]Operation cancelled by user[/red]")
                ctx.exit(1)
        else:
            # Run sync function
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                console.print("\n[red]Operation cancelled by user[/red]")
                ctx.exit(1)

    return wrapper


def interactive_option(
    *param_decls,
    prompt: str = None,
    prompt_required: bool = True,
    hide_input: bool = False,
    confirmation_prompt: bool = False,
    value_proc: Callable = None,
    **kwargs
):
    """Create an option that prompts in interactive mode

    Args:
        param_decls: Parameter declarations
        prompt: Prompt text (uses parameter name if not provided)
        prompt_required: Whether to prompt if value not provided
        hide_input: Whether to hide input (for passwords)
        confirmation_prompt: Whether to confirm input
        value_proc: Value processing function
        **kwargs: Additional click.option arguments

    Returns:
        Click option decorator
    """
    def decorator(f):
        # Get parameter name
        param_name = param_decls[0].lstrip('-').replace('-', '_')

        # Original click option
        option_decorator = click.option(*param_decls, **kwargs)

        @wraps(f)
        def wrapper(*args, **kw):
            ctx = click.get_current_context()

            # Check if in interactive mode and value not provided
            if hasattr(ctx, 'interactive') and ctx.interactive:
                if param_name not in kw or kw[param_name] is None:
                    if prompt_required:
                        # Import here to avoid circular imports
                        from rich.prompt import Prompt

                        # Prepare prompt text
                        prompt_text = prompt or param_name.replace('_', ' ').title()

                        # Get default value
                        default = kwargs.get('default')
                        if callable(default):
                            default = default()

                        # Prompt for value
                        if kwargs.get('is_flag'):
                            # Boolean prompt
                            from rich.prompt import Confirm
                            value = Confirm.ask(prompt_text, default=bool(default))
                        else:
                            # Text prompt
                            value = Prompt.ask(
                                prompt_text,
                                default=str(default) if default is not None else None,
                                password=hide_input
                            )

                            # Confirm if requested
                            if confirmation_prompt and value:
                                confirm_value = Prompt.ask(
                                    f"Confirm {prompt_text}",
                                    password=hide_input
                                )
                                if value != confirm_value:
                                    console.print("[red]Values do not match[/red]")
                                    ctx.exit(1)

                        # Process value
                        if value_proc and value is not None:
                            value = value_proc(value)

                        # Set in kwargs
                        kw[param_name] = value

            return f(*args, **kw)

        return option_decorator(wrapper)

    return decorator


def mode_specific(
    interactive_func: Callable = None,
    command_func: Callable = None
):
    """Execute different functions based on operation mode

    Args:
        interactive_func: Function to run in interactive mode
        command_func: Function to run in command-line mode

    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ctx = click.get_current_context()

            if hasattr(ctx, 'interactive') and ctx.interactive:
                # Interactive mode
                if interactive_func:
                    return interactive_func(*args, **kwargs)
            else:
                # Command-line mode
                if command_func:
                    return command_func(*args, **kwargs)

            # Default: run original function
            return f(*args, **kwargs)

        return wrapper

    return decorator


def validate_params(
    validator: Callable[[dict], list]
):
    """Validate command parameters

    Args:
        validator: Function that takes kwargs and returns list of errors

    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Run validator
            errors = validator(kwargs)

            if errors:
                ctx = click.get_current_context()
                console.print("[red]Parameter validation failed:[/red]")
                for error in errors:
                    console.print(f"  - {error}")
                ctx.exit(1)

            return f(*args, **kwargs)

        return wrapper

    return decorator