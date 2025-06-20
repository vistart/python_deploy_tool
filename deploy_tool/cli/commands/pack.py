"""Pack command implementation"""

from pathlib import Path
from typing import Optional

import click
from rich.prompt import Prompt, Confirm

from ..decorators import dual_mode_command, project_required
from ..utils.interactive import select_from_list
from ..utils.output import console, create_progress, print_success, print_error
from ...constants import (
    EMOJI_SUCCESS,
    EMOJI_WARNING,
    EMOJI_PACKAGE
)
from ...core.path_resolver import PathResolver
from ...services.package_service import PackageService, PackageConfig


@click.command()
@click.argument('source_path', required=False)
@click.option(
    '--type', '-t', 'component_type',
    help='Component type (e.g., model, config, runtime)'
)
@click.option(
    '--version', '-v',
    help='Component version (e.g., 1.0.0)'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output directory (default: dist/)'
)
@click.option(
    '--compression', '-c',
    type=click.Choice(['gzip', 'bzip2', 'xz', 'lz4', 'none']),
    default='gzip',
    help='Compression algorithm'
)
@click.option(
    '--level', '-l',
    type=click.IntRange(1, 9),
    default=6,
    help='Compression level (1-9)'
)
@click.option(
    '--exclude', '-e',
    multiple=True,
    help='Exclude patterns (can be specified multiple times)'
)
@click.option(
    '--auto', '-a',
    is_flag=True,
    help='Auto-generate package configuration'
)
@click.option(
    '--yes', '-y',
    is_flag=True,
    help='Skip confirmation prompts'
)
@dual_mode_command
@project_required
async def pack(ctx, source_path, component_type, version, output, compression,
               level, exclude, auto, yes):
    """Package a component for deployment

    Examples:
        deploy-tool pack ./models --type model --version 1.0.0
        deploy-tool pack ./configs --auto --type config --version 1.0.0
        deploy-tool pack ./runtime -t runtime -v 3.10.0 -c xz -l 9
    """
    # Initialize services
    path_resolver = PathResolver(ctx.project_root)
    package_service = PackageService(path_resolver)

    # Get source path
    if not source_path:
        if ctx.interactive:
            source_path = await get_source_path_interactive(ctx.project)
            if not source_path:
                ctx.exit(0)
        else:
            print_error("Source path required")
            ctx.exit(1)

    # Resolve source path
    source_path = path_resolver.resolve(source_path)
    if not source_path.exists():
        print_error(f"Source path not found: {source_path}")
        ctx.exit(1)

    # Get component type
    if not component_type:
        if ctx.interactive:
            component_type = await get_component_type_interactive(ctx.project, source_path)
            if not component_type:
                ctx.exit(0)
        else:
            print_error("Component type required (use --type)")
            ctx.exit(1)

    # Get version
    if not version:
        if ctx.interactive:
            version = await get_version_interactive(component_type)
            if not version:
                ctx.exit(0)
        else:
            print_error("Version required (use --version)")
            ctx.exit(1)

    # Validate version format
    if not validate_version_format(version):
        print_error(f"Invalid version format: {version}")
        console.print("Use semantic versioning format: MAJOR.MINOR.PATCH (e.g., 1.0.0)")
        ctx.exit(1)

    # Determine output directory
    if not output:
        output = ctx.project_root / "dist"

    # Create package configuration
    config = PackageConfig(
        type=component_type,
        version=version,
        source_path=source_path,
        output_path=output,
        compression_algorithm=compression,
        compression_level=level,
        exclude_patterns=list(exclude) if exclude else None
    )

    # Show package plan
    show_package_plan(config, auto)

    # Confirm
    if not yes and ctx.interactive:
        if not Confirm.ask("\nProceed with packaging?"):
            ctx.exit(0)

    # Execute packaging
    console.print(f"\n{EMOJI_PACKAGE} Packaging {component_type}:{version}...")

    with create_progress() as progress:
        task = progress.add_task(
            f"Packaging {source_path.name}...",
            total=None
        )

        # Package component
        result = await package_service.package_component(
            config=config,
            progress_callback=lambda current, total: progress.update(
                task,
                completed=current,
                total=total
            )
        )

    # Show results
    if result.is_success:
        print_success(f"Package created: {result.package_path}")

        # Show package details
        console.print(f"\n[bold]Package Details:[/bold]")
        console.print(f"  Type: {result.component_type}")
        console.print(f"  Version: {result.component_version}")
        console.print(f"  Size: {format_size(result.package_size)}")
        console.print(f"  Compression: {result.compression_algorithm}")
        console.print(f"  Checksum: {result.checksum[:16]}...")

        if result.manifest_path:
            console.print(f"  Manifest: {path_resolver.make_relative(result.manifest_path)}")

        # Show next steps
        console.print(f"\n{EMOJI_SUCCESS} Next steps:")
        console.print(f"1. Review the package: tar -tzf {result.package_path} | head -20")
        console.print(f"2. Publish the package: deploy-tool publish {component_type}:{version}")

        # Git reminder
        if result.manifest_path:
            manifest_rel = path_resolver.make_relative(result.manifest_path)
            console.print(f"\n{EMOJI_WARNING} Don't forget to commit the manifest:")
            console.print(f"  git add {manifest_rel}")
            console.print(f"  git commit -m \"Add {component_type} version {version}\"")

    else:
        print_error("Packaging failed!")
        for error in result.errors:
            print_error(f"  {error.message}")
        ctx.exit(1)


async def get_source_path_interactive(project) -> Optional[Path]:
    """Get source path interactively"""

    # Get defined components
    component_types = project.config.get_component_types()

    if component_types:
        console.print("\n[bold]Select component to package:[/bold]")

        # Add custom path option
        choices = component_types + ["<custom path>"]

        selected = select_from_list(
            "Select source",
            choices
        )

        if not selected:
            return None

        if selected == "<custom path>":
            # Get custom path
            path_str = Prompt.ask("Enter source path")
            return Path(path_str) if path_str else None
        else:
            # Use component path
            return project.config.get_component_path(selected)

    else:
        # No components defined, get custom path
        path_str = Prompt.ask("\nEnter source path")
        return Path(path_str) if path_str else None


async def get_component_type_interactive(project, source_path: Path) -> Optional[str]:
    """Get component type interactively"""

    # Try to infer from path
    path_name = source_path.name.lower()

    # Common mappings
    type_mappings = {
        'models': 'model',
        'model': 'model',
        'configs': 'config',
        'config': 'config',
        'runtime': 'runtime',
        'algorithm': 'algorithm',
        'service': 'service',
    }

    suggested = type_mappings.get(path_name)

    # Get defined component types
    defined_types = project.config.get_component_types()

    if defined_types:
        console.print("\n[bold]Select component type:[/bold]")

        # If we have a suggestion, make it the default
        if suggested and suggested in defined_types:
            default_idx = defined_types.index(suggested) + 1
        else:
            default_idx = 1

        for i, comp_type in enumerate(defined_types, 1):
            console.print(f"  {i}. {comp_type}")

        console.print(f"  {len(defined_types) + 1}. <custom type>")

        choice = Prompt.ask(
            "Enter choice",
            default=str(default_idx)
        )

        if not choice.isdigit():
            return None

        idx = int(choice) - 1
        if idx < len(defined_types):
            return defined_types[idx]
        else:
            # Custom type
            return Prompt.ask("Enter custom component type")

    else:
        # No defined types, ask for custom
        return Prompt.ask(
            "\nEnter component type",
            default=suggested
        )


async def get_version_interactive(component_type: str) -> Optional[str]:
    """Get version interactively"""

    console.print(f"\n[bold]Version for {component_type}:[/bold]")
    console.print("Use semantic versioning: MAJOR.MINOR.PATCH")
    console.print("Examples: 1.0.0, 2.1.3, 0.1.0-beta")

    version = Prompt.ask(
        "\nEnter version",
        default="1.0.0"
    )

    return version


def validate_version_format(version: str) -> bool:
    """Validate version format"""

    # Basic semantic versioning check
    parts = version.split('.')
    if len(parts) < 3:
        return False

    # Check major.minor.patch are numbers
    try:
        major = int(parts[0])
        minor = int(parts[1])

        # Handle patch with pre-release
        patch_parts = parts[2].split('-')
        patch = int(patch_parts[0])

        return True
    except ValueError:
        return False


def show_package_plan(config: PackageConfig, auto: bool) -> None:
    """Show packaging plan"""

    console.print(f"\n{EMOJI_PACKAGE} [bold]Package Plan[/bold]")
    console.print(f"Source: {config.source_path}")
    console.print(f"Component: {config.type}:{config.version}")
    console.print(f"Output: {config.output_path}")
    console.print(f"Compression: {config.compression_algorithm} (level {config.compression_level})")

    if config.exclude_patterns:
        console.print(f"\nExclude patterns:")
        for pattern in config.exclude_patterns:
            console.print(f"  - {pattern}")

    if auto:
        console.print(f"\n[yellow]Auto mode: Will scan directory and generate configuration[/yellow]")


def format_size(size_bytes: int) -> str:
    """Format file size for display"""

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f} TB"