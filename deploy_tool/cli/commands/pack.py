"""Pack command implementation"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from ...api import Packer, pack
from ...api.exceptions import PackError, MissingTypeError, MissingVersionError
from ..decorators import require_project, dual_mode_command
from ..utils.interactive import PackWizard
from ..utils.output import format_pack_result, show_git_advice

console = Console()


@click.command()
@click.argument('source', type=click.Path(exists=True), required=False)
@click.option('--type', 'package_type', help='Package type (required for auto mode)')
@click.option('--version', help='Version number (required for auto mode)')
@click.option('--auto', is_flag=True, help='Auto-generate config and pack')
@click.option('--wizard', is_flag=True, help='Interactive wizard mode')
@click.option('--config', type=click.Path(exists=True), help='Use existing config file')
@click.option('--output', type=click.Path(), help='Output directory')
@click.option('--compress', type=click.Choice(['gzip', 'bzip2', 'xz', 'lz4']),
              default='gzip', help='Compression algorithm')
@click.option('--level', type=click.IntRange(1, 9), default=6, help='Compression level')
@click.option('--force', is_flag=True, help='Force overwrite existing files')
@click.option('--save-config', is_flag=True, help='Save auto-generated config')
@click.option('--dry-run', is_flag=True, help='Simulate without actual packing')
@click.option('--batch', type=click.Path(exists=True), help='Batch pack config file')
@click.pass_context
@require_project
@dual_mode_command
async def pack(ctx, source, package_type, version, auto, wizard, config, output,
               compress, level, force, save_config, dry_run, batch):
    """Pack files or directories into deployment packages

    This command packages non-code resources like models, configs, and data
    for deployment. Code files are managed through Git and don't need packing.

    Examples:

        # Auto mode with required parameters
        deploy-tool pack ./models --auto --type model --version 1.0.1

        # Interactive wizard
        deploy-tool pack --wizard

        # Using config file
        deploy-tool pack --config deployment/package-configs/model.yaml

        # Batch packing
        deploy-tool pack --batch deployment/batch-pack.yaml
    """
    try:
        packer = Packer(path_resolver=ctx.obj.path_resolver)

        # Handle different modes
        if batch:
            # Batch mode
            results = await packer.pack_batch(batch, dry_run=dry_run)
            for result in results:
                format_pack_result(result)
            return

        if wizard:
            # Interactive wizard mode
            wizard_helper = PackWizard(console)
            config_data = await wizard_helper.run(source)

            if config_data.get('save_config'):
                config_path = await packer.save_config(config_data)
                console.print(f"✓ Config saved to: {config_path}")

            result = await packer.pack_with_config(config_data, dry_run=dry_run)

        elif auto:
            # Auto mode - requires type and version
            if not package_type:
                raise MissingTypeError("--type is required for auto mode")
            if not version:
                raise MissingVersionError("--version is required for auto mode")

            result = await packer.auto_pack(
                source_path=source or '.',
                package_type=package_type,
                version=version,
                output_dir=output,
                compression_type=compress,
                compression_level=level,
                force=force,
                save_config=save_config,
                dry_run=dry_run
            )

        elif config:
            # Config file mode
            result = await packer.pack_with_config(config, dry_run=dry_run)

        else:
            # Show help if no mode specified
            console.print("[yellow]Please specify a mode:[/yellow]")
            console.print("  --auto    : Auto-generate config (requires --type and --version)")
            console.print("  --wizard  : Interactive mode")
            console.print("  --config  : Use existing config file")
            console.print("  --batch   : Batch pack multiple components")
            ctx.exit(1)

        # Display result
        format_pack_result(result)

        # Show git advice
        if not dry_run and result.manifest_path:
            show_git_advice(result.manifest_path)

    except (PackError, MissingTypeError, MissingVersionError) as e:
        console.print(f"[red]Pack error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Pack cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)