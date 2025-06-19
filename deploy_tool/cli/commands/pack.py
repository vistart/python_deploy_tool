"""Pack command implementation"""

import sys
from pathlib import Path

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

        # Interactive wizard mode (recommended for first time)
        deploy-tool pack --wizard

        # Auto mode with minimal input
        deploy-tool pack ./models --auto --type model --version 1.0.0

        # Use existing config file
        deploy-tool pack --config deployment/package-configs/model-v1.yaml

        # Batch processing
        deploy-tool pack --batch deployment/batch-pack.yaml

    Source Priority:
        1. Command argument (e.g., ./models)
        2. Config file source
        3. Interactive selection
    """
    try:
        # Create packer instance
        packer = Packer()

        # Ensure we use relative paths
        if source and Path(source).is_absolute():
            # Convert absolute path to relative
            project_root = ctx.obj.path_resolver.project_root
            try:
                rel_source = Path(source).relative_to(project_root)
                source = str(rel_source)
                console.print(f"[yellow]Converting to relative path: {source}[/yellow]")
            except ValueError:
                console.print(f"[red]Error: Source path '{source}' is outside project root[/red]")
                console.print(f"[yellow]Project root: {project_root}[/yellow]")
                console.print("[yellow]Please use a path within the project[/yellow]")
                sys.exit(1)

        # Handle different modes
        if wizard:
            # Interactive wizard mode - pass console, not path_resolver
            wizard_obj = PackWizard(console)  # Fix: pass console instead of path_resolver
            result = run_async(wizard_obj.run(initial_path=source))
            if not result:
                console.print("[yellow]Wizard cancelled[/yellow]")
                sys.exit(0)

            # Run packing with wizard result
            pack_result = packer.pack(
                source_path=result['source'],
                package_type=result['type'],
                version=result['version'],
                output_path=result.get('output'),
                compress=result.get('compress', compress),
                level=result.get('level', level),
                force=result.get('force', force),
                save_config=result.get('save_config', save_config),
                metadata=result.get('metadata', {})
            )

        elif batch:
            # Batch mode
            results = packer.pack_batch(batch)

            # Display batch results
            console.print(f"\n[green]Batch pack completed: {len(results)} packages[/green]")
            for result in results:
                if result.error:
                    console.print(f"  [red]✗[/red] {result.source_path}: {result.error}")
                else:
                    console.print(f"  [green]✓[/green] {result.source_path}")

            # Check if any failed
            failed = [r for r in results if not r.success]
            if failed:
                sys.exit(1)
            return

        elif config:
            # Config file mode
            pack_result = packer.pack_with_config(
                config_path=config,
                version=version,  # Can override version
                output_path=output,
                force=force,
                dry_run=dry_run
            )

        elif auto:
            # Auto mode - validate required parameters
            if not package_type:
                raise MissingTypeError("--type is required for auto mode")
            if not version:
                raise MissingVersionError("--version is required for auto mode")

            # Use source from argument or current directory
            pack_source = source or '.'

            # Run auto pack
            pack_result = packer.auto_pack(
                source_path=pack_source,
                package_type=package_type,
                version=version,
                save_config=save_config,
                compress=compress,
                level=level,
                force=force,
                output_path=output
            )

        else:
            # Standard mode - need at least source
            if not source:
                console.print("[red]Error: SOURCE argument is required[/red]")
                console.print("\nSpecify a source directory or file to pack:")
                console.print("  deploy-tool pack ./models --type model --version 1.0.0")
                console.print("\nOr use one of these modes:")
                console.print("  --wizard   : Interactive mode (recommended)")
                console.print("  --auto     : Auto mode with config generation")
                console.print("  --config   : Use existing config file")
                console.print("  --batch    : Batch processing")
                sys.exit(1)

            if not package_type:
                console.print("[red]Error: --type is required[/red]")
                console.print("\nSpecify the package type:")
                console.print("  deploy-tool pack ./models --type model --version 1.0.0")
                sys.exit(1)

            if not version:
                console.print("[red]Error: --version is required[/red]")
                console.print("\nSpecify the version:")
                console.print("  deploy-tool pack ./models --type model --version 1.0.0")
                sys.exit(1)

            # Standard pack
            pack_result = packer.pack(
                source_path=source,
                package_type=package_type,
                version=version,
                output_path=output,
                compress=compress,
                level=level,
                force=force,
                save_config=save_config,
                metadata={}
            )

        # Display results
        format_pack_result(pack_result)

        # Show git advice if needed
        if pack_result.manifest_path and not dry_run:
            show_git_advice(pack_result.manifest_path)

        # Show portability reminder
        console.print("\n[dim]💡 Tip: Always use relative paths for better portability across environments[/dim]")

    except (PackError, MissingTypeError, MissingVersionError) as e:
        console.print(f"[red]Pack error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)