"""Configuration management commands"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

import click
from rich.prompt import Prompt, Confirm
from rich.table import Table

from ..decorators import dual_mode_command, project_required
from ..utils.output import console
from ..utils.interactive import select_from_list, select_multiple_items
from ...services.config_service import ConfigService
from ...core.storage_manager import StorageManager
from ...constants import (
    EMOJI_SUCCESS,
    EMOJI_ERROR,
    EMOJI_WARNING,
    EMOJI_INFO,
    StorageType,
    ENV_BOS_ACCESS_KEY,
    ENV_BOS_SECRET_KEY,
    ENV_S3_ACCESS_KEY,
    ENV_S3_SECRET_KEY
)


@click.group()
def config():
    """Manage deploy-tool configuration"""
    pass


@config.group()
def targets():
    """Manage publish/deploy targets"""
    pass


@targets.command()
@click.option('--type', '-t', 'storage_type', help='Show only targets of specific type')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@project_required
def list(ctx, storage_type, verbose):
    """List configured targets"""
    config_service = ConfigService(ctx.project_root)
    targets = config_service.list_targets()

    if not targets:
        console.print(f"{EMOJI_WARNING} No targets configured")
        return

    # Filter by type if requested
    if storage_type:
        targets = [t for t in targets if t['type'] == storage_type]
        if not targets:
            console.print(f"{EMOJI_WARNING} No {storage_type} targets found")
            return

    # Create table
    table = Table(title="Configured Targets")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Status")
    table.add_column("Details")

    if verbose:
        table.add_column("Configuration")

    for target in targets:
        # Status indicators
        status_parts = []
        if target['enabled']:
            status_parts.append("[green]enabled[/green]")
        else:
            status_parts.append("[red]disabled[/red]")

        if target.get('is_default'):
            status_parts.append("[yellow]default[/yellow]")

        if target.get('deploy_priority'):
            status_parts.append(f"[blue]priority-{target['deploy_priority']}[/blue]")

        status = " ".join(status_parts)

        # Configuration details for verbose mode
        config_details = ""
        if verbose:
            if target['type'] == 'filesystem':
                config_details = f"path: {target.get('path', 'N/A')}"
            elif target['type'] == 'bos':
                config_details = f"bucket: {target.get('bucket', 'N/A')}"
            elif target['type'] == 's3':
                config_details = f"bucket: {target.get('bucket', 'N/A')}, region: {target.get('region', 'N/A')}"

        table.add_row(
            target['name'],
            target['type'],
            status,
            target.get('description', ''),
            config_details if verbose else ""
        )

    console.print(table)

    # Show summary
    console.print(f"\nTotal: {len(targets)} targets")
    enabled_count = sum(1 for t in targets if t['enabled'])
    console.print(f"Enabled: {enabled_count}, Disabled: {len(targets) - enabled_count}")


@targets.command()
@click.argument('name', required=False)
@click.option('--type', '-t', 'storage_type', type=click.Choice(['filesystem', 'bos', 's3']),
              help='Storage type')
@click.option('--path', help='Path for filesystem storage')
@click.option('--endpoint', help='Endpoint for BOS storage')
@click.option('--bucket', help='Bucket name for BOS/S3 storage')
@click.option('--region', help='Region for S3 storage')
@click.option('--access-key', help='Access key for BOS/S3')
@click.option('--secret-key', help='Secret key for BOS/S3')
@click.option('--description', '-d', help='Target description')
@click.option('--set-default', is_flag=True, help='Set as default target')
@dual_mode_command
@project_required
async def add(ctx, name, storage_type, path, endpoint, bucket, region,
              access_key, secret_key, description, set_default):
    """Add a new publish/deploy target"""
    config_service = ConfigService(ctx.project_root)

    # Interactive mode if parameters missing
    if not name or not storage_type:
        name, storage_type, params = await _interactive_add_target(ctx.interactive)
        if not name:
            ctx.exit(0)
    else:
        params = {
            'path': path,
            'endpoint': endpoint,
            'bucket': bucket,
            'region': region,
            'access_key': access_key,
            'secret_key': secret_key,
            'description': description
        }

    # Check for environment variables for credentials
    if storage_type == 'bos':
        if not params.get('access_key'):
            import os
            params['access_key'] = os.environ.get(ENV_BOS_ACCESS_KEY)
        if not params.get('secret_key'):
            import os
            params['secret_key'] = os.environ.get(ENV_BOS_SECRET_KEY)

    elif storage_type == 's3':
        if not params.get('access_key'):
            import os
            params['access_key'] = os.environ.get(ENV_S3_ACCESS_KEY)
        if not params.get('secret_key'):
            import os
            params['secret_key'] = os.environ.get(ENV_S3_SECRET_KEY)

    # Add target
    result = config_service.add_target(name, storage_type, **params)

    if result.is_success:
        console.print(f"{EMOJI_SUCCESS} {result.message}")

        # Set as default if requested
        if set_default:
            defaults = config_service.config.default_targets
            if name not in defaults:
                defaults.append(name)
                config_service.config.default_targets = defaults
                config_service.save_config()
                console.print(f"{EMOJI_SUCCESS} Set as default target")

        # Test connection
        if storage_type != 'filesystem' and Confirm.ask("\nTest connection?"):
            storage_manager = StorageManager(config_service.config)
            test_result = await config_service.test_target(name, storage_manager)

            if test_result.is_success:
                console.print(f"{EMOJI_SUCCESS} {test_result.message}")
            else:
                console.print(f"{EMOJI_ERROR} {test_result.errors[0].message}")

    else:
        console.print(f"{EMOJI_ERROR} {result.errors[0].message}")
        ctx.exit(1)


@targets.command()
@click.argument('name')
@project_required
def remove(ctx, name):
    """Remove a publish/deploy target"""
    config_service = ConfigService(ctx.project_root)

    # Confirm removal
    if not Confirm.ask(f"Remove target '{name}'?"):
        return

    result = config_service.remove_target(name)

    if result.is_success:
        console.print(f"{EMOJI_SUCCESS} {result.message}")
    else:
        console.print(f"{EMOJI_ERROR} {result.errors[0].message}")
        ctx.exit(1)


@targets.command()
@click.argument('name')
@click.option('--enable/--disable', default=None, help='Enable or disable target')
@click.option('--path', help='Update path (filesystem)')
@click.option('--endpoint', help='Update endpoint (BOS)')
@click.option('--bucket', help='Update bucket (BOS/S3)')
@click.option('--region', help='Update region (S3)')
@click.option('--access-key', help='Update access key')
@click.option('--secret-key', help='Update secret key')
@click.option('--description', '-d', help='Update description')
@project_required
def update(ctx, name, enable, path, endpoint, bucket, region,
           access_key, secret_key, description):
    """Update a publish/deploy target"""
    config_service = ConfigService(ctx.project_root)

    # Build update params
    params = {}
    if enable is not None:
        params['enabled'] = enable
    if path:
        params['path'] = path
    if endpoint:
        params['endpoint'] = endpoint
    if bucket:
        params['bucket'] = bucket
    if region:
        params['region'] = region
    if access_key:
        params['access_key'] = access_key
    if secret_key:
        params['secret_key'] = secret_key
    if description:
        params['description'] = description

    if not params:
        console.print(f"{EMOJI_WARNING} No updates specified")
        return

    result = config_service.update_target(name, **params)

    if result.is_success:
        console.print(f"{EMOJI_SUCCESS} {result.message}")
    else:
        console.print(f"{EMOJI_ERROR} {result.errors[0].message}")
        ctx.exit(1)


@targets.command()
@click.argument('name', required=False)
@click.option('--all', 'test_all', is_flag=True, help='Test all targets')
@project_required
async def test(ctx, name, test_all):
    """Test connection to a target"""
    config_service = ConfigService(ctx.project_root)
    storage_manager = StorageManager(config_service.config)

    if test_all:
        # Test all targets
        targets = config_service.list_targets()

        console.print(f"Testing {len(targets)} targets...\n")

        for target in targets:
            if not target['enabled']:
                console.print(f"⏭️  {target['name']}: [yellow]Skipped (disabled)[/yellow]")
                continue

            result = await config_service.test_target(target['name'], storage_manager)

            if result.is_success:
                console.print(f"{EMOJI_SUCCESS} {target['name']}: {result.message}")
            else:
                console.print(f"{EMOJI_ERROR} {target['name']}: {result.errors[0].message}")

    else:
        # Test single target
        if not name:
            # Interactive selection
            targets = config_service.list_targets()
            if not targets:
                console.print(f"{EMOJI_WARNING} No targets configured")
                return

            name = select_from_list(
                "Select target to test",
                [t['name'] for t in targets]
            )

            if not name:
                return

        console.print(f"Testing target '{name}'...")

        result = await config_service.test_target(name, storage_manager)

        if result.is_success:
            console.print(f"\n{EMOJI_SUCCESS} {result.message}")
        else:
            console.print(f"\n{EMOJI_ERROR} {result.errors[0].message}")
            ctx.exit(1)


@config.command()
@click.argument('targets', nargs=-1)
@click.option('--add', is_flag=True, help='Add to existing defaults')
@project_required
def set_defaults(ctx, targets, add):
    """Set default publish targets"""
    config_service = ConfigService(ctx.project_root)

    if not targets:
        # Interactive selection
        all_targets = config_service.list_targets()
        if not all_targets:
            console.print(f"{EMOJI_WARNING} No targets configured")
            return

        current_defaults = config_service.config.default_targets

        selected = select_multiple_items(
            "Select default targets",
            [t['name'] for t in all_targets],
            default_selection=[
                i for i, t in enumerate(all_targets)
                if t['name'] in current_defaults
            ]
        )

        if selected is None:
            return

        targets = [all_targets[i]['name'] for i in selected]

    # Process targets
    if add:
        # Add to existing
        current = config_service.config.default_targets
        for target in targets:
            if target not in current:
                current.append(target)
        targets = current

    result = config_service.set_default_targets(list(targets))

    if result.is_success:
        console.print(f"{EMOJI_SUCCESS} {result.message}")
    else:
        console.print(f"{EMOJI_ERROR} {result.errors[0].message}")
        ctx.exit(1)


@config.command()
@click.argument('targets', nargs=-1)
@project_required
def set_priority(ctx, targets):
    """Set deployment source priority"""
    config_service = ConfigService(ctx.project_root)

    if not targets:
        # Interactive ordering
        all_targets = config_service.list_targets()
        if not all_targets:
            console.print(f"{EMOJI_WARNING} No targets configured")
            return

        current_priority = config_service.config.deploy.source_priority

        # Order targets
        ordered = []
        remaining = [t['name'] for t in all_targets]

        # First add current priority targets in order
        for target in current_priority:
            if target in remaining:
                ordered.append(target)
                remaining.remove(target)

        # Add remaining
        ordered.extend(remaining)

        console.print("[bold]Set deployment source priority[/bold]")
        console.print("(Higher priority sources will be tried first)\n")

        # Allow reordering
        for i in range(len(ordered)):
            console.print(f"\nCurrent order:")
            for j, target in enumerate(ordered, 1):
                marker = " [yellow]<--[/yellow]" if j == i + 1 else ""
                console.print(f"  {j}. {target}{marker}")

            if i < len(ordered) - 1:
                if Confirm.ask(f"\nMove '{ordered[i]}' down?"):
                    ordered[i], ordered[i + 1] = ordered[i + 1], ordered[i]

        targets = ordered

    result = config_service.set_deploy_priority(list(targets))

    if result.is_success:
        console.print(f"\n{EMOJI_SUCCESS} {result.message}")
    else:
        console.print(f"{EMOJI_ERROR} {result.errors[0].message}")
        ctx.exit(1)


async def _interactive_add_target(interactive: bool) -> tuple[str, str, Dict[str, Any]]:
    """Interactive target addition"""
    console.print("[bold]Add New Target[/bold]\n")

    # Get name
    name = Prompt.ask("Target name (e.g., 'local-primary', 'bos-beijing')")
    if not name:
        return None, None, {}

    # Get type
    storage_types = ['filesystem', 'bos', 's3']
    console.print("\nSelect storage type:")
    for i, st in enumerate(storage_types, 1):
        console.print(f"  {i}. {st}")

    choice = Prompt.ask("Enter choice", choices=['1', '2', '3'], default='1')
    storage_type = storage_types[int(choice) - 1]

    # Get description
    description = Prompt.ask("\nDescription (optional)", default="")

    params = {'description': description}

    # Get type-specific parameters
    if storage_type == 'filesystem':
        params['path'] = Prompt.ask("\nStorage path", default="/data/packages")

    elif storage_type == 'bos':
        params['endpoint'] = Prompt.ask("\nBOS endpoint", default="bj.bcebos.com")
        params['bucket'] = Prompt.ask("Bucket name")

        console.print(f"\n{EMOJI_INFO} Credentials can be set via environment variables:")
        console.print(f"  export {ENV_BOS_ACCESS_KEY}=<your-access-key>")
        console.print(f"  export {ENV_BOS_SECRET_KEY}=<your-secret-key>")

        if Confirm.ask("\nEnter credentials now?"):
            params['access_key'] = Prompt.ask("Access key")
            params['secret_key'] = Prompt.ask("Secret key", password=True)

    elif storage_type == 's3':
        params['region'] = Prompt.ask("\nAWS region", default="us-west-2")
        params['bucket'] = Prompt.ask("Bucket name")

        console.print(f"\n{EMOJI_INFO} Credentials can be set via environment variables:")
        console.print(f"  export {ENV_S3_ACCESS_KEY}=<your-access-key>")
        console.print(f"  export {ENV_S3_SECRET_KEY}=<your-secret-key>")

        if Confirm.ask("\nEnter credentials now?"):
            params['access_key'] = Prompt.ask("Access key")
            params['secret_key'] = Prompt.ask("Secret key", password=True)

    return name, storage_type, params