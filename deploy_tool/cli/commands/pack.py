"""Pack command implementation"""

import sys

import click
from rich.console import Console

from ..decorators import require_project, dual_mode_command
from ..utils.interactive import PackWizard
from ..utils.output import format_pack_result, show_git_advice
from ...api import Packer
from ...api.exceptions import PackError, MissingTypeError, MissingVersionError
from ...utils.async_utils import run_async

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
def pack(ctx, source, package_type, version, auto, wizard, config, output,
         compress, level, force, save_config, dry_run, batch):
    """Pack files or directories into deployment packages

    This command packages non-code resources like models, configs, and data
    for deployment. Code files are managed through Git and don't need packing.

    Examples:

        # Auto mode (must specify type and version)
        deploy-tool pack ./models --auto --type model --version 1.0.1

        # Wizard mode (interactive)
        deploy-tool pack --wizard

        # Using config file
        deploy-tool pack --config model.yaml

        # Batch packing
        deploy-tool pack --batch batch-pack.yaml
    """
    try:
        # Handle batch mode
        if batch:
            packer = Packer()
            results = run_async(packer.pack_batch_async(batch))
            for result in results:
                format_pack_result(result)
            return

        # Handle wizard mode
        if wizard:
            wizard = PackWizard()
            config_data = run_async(wizard.run())
            if not config_data:
                console.print("[yellow]Wizard cancelled[/yellow]")
                sys.exit(0)
            config = config_data  # Use wizard result as config

        # Validate required parameters for auto mode
        if auto and not config:
            if not package_type:
                raise MissingTypeError()
            if not version:
                raise MissingVersionError()

        # Create packer
        packer = Packer()

        # Execute packing
        if dry_run:
            console.print("[yellow]Dry run mode - no actual packing[/yellow]")

        if config:
            result = run_async(packer.pack_with_config_async(config))
        elif auto:
            result = run_async(packer.auto_pack_async(
                source_path=source,
                package_type=package_type,
                version=version,
                output_path=output,
                compression_algorithm=compress,
                compression_level=level,
                force=force,
                save_config=save_config
            ))
        else:
            # Show help if no mode specified
            console.print("[red]Error: Must specify --auto, --wizard, or --config[/red]")
            console.print("\nExamples:")
            console.print("  deploy-tool pack ./models --auto --type model --version 1.0.1")
            console.print("  deploy-tool pack --wizard")
            console.print("  deploy-tool pack --config model.yaml")
            sys.exit(1)

        # Display result
        format_pack_result(result)

        # Show git advice if needed
        if result.success and result.manifest_path:
            show_git_advice(result.manifest_path)

    except (PackError, MissingTypeError, MissingVersionError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)