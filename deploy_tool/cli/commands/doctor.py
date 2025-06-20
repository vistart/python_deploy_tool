"""Doctor command for diagnosing and fixing issues"""

import shutil
import sys
from pathlib import Path

from rich.table import Table

from ..utils.output import console, print_success, print_warning
from ...constants import (
    EMOJI_SUCCESS,
    EMOJI_INFO,
    DEFAULT_CACHE_DIR
)


def check_environment(fix: bool = False) -> None:
    """Check deployment environment"""

    console.print("[bold]Deploy Tool Environment Check[/bold]\n")

    issues = []

    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        issues.append({
            'level': 'error',
            'component': 'Python',
            'issue': f'Python {python_version.major}.{python_version.minor} is too old',
            'fix': 'Upgrade to Python 3.8 or later'
        })
    else:
        print_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    # Check required Python modules
    required_modules = [
        ('click', 'CLI framework'),
        ('rich', 'Terminal formatting'),
        ('yaml', 'YAML parsing'),
        ('aiofiles', 'Async file operations'),
    ]

    for module_name, description in required_modules:
        try:
            __import__(module_name)
            print_success(f"{module_name} - {description}")
        except ImportError:
            issues.append({
                'level': 'error',
                'component': module_name,
                'issue': f'Module not installed',
                'fix': f'pip install {module_name}'
            })

    # Check optional modules
    optional_modules = [
        ('bce-python-sdk', 'BOS support', 'bce-python-sdk'),
        ('boto3', 'S3 support', 'boto3'),
        ('lz4', 'LZ4 compression', 'lz4'),
    ]

    console.print("\n[bold]Optional Features:[/bold]")
    for module_name, description, pip_name in optional_modules:
        try:
            __import__(module_name.replace('-', '_'))
            print_success(f"{module_name} - {description}")
        except ImportError:
            print_warning(f"{module_name} - {description} (not installed)")
            if fix:
                issues.append({
                    'level': 'warning',
                    'component': module_name,
                    'issue': 'Optional feature not available',
                    'fix': f'pip install {pip_name}'
                })

    # Check compression support
    console.print("\n[bold]Compression Support:[/bold]")

    compression_modules = [
        ('gzip', 'GZIP compression'),
        ('bz2', 'BZIP2 compression'),
        ('lzma', 'XZ compression'),
    ]

    for module_name, description in compression_modules:
        try:
            __import__(module_name)
            print_success(f"{module_name} - {description}")
        except ImportError:
            issues.append({
                'level': 'error',
                'component': module_name,
                'issue': f'{description} not available',
                'fix': 'Rebuild Python with compression support'
            })

    # Check system commands
    console.print("\n[bold]System Commands:[/bold]")

    commands = [
        ('git', 'Version control'),
        ('tar', 'Archive operations'),
        ('rsync', 'File synchronization'),
    ]

    for cmd, description in commands:
        if shutil.which(cmd):
            print_success(f"{cmd} - {description}")
        else:
            level = 'warning' if cmd != 'tar' else 'error'
            issues.append({
                'level': level,
                'component': cmd,
                'issue': f'Command not found',
                'fix': f'Install {cmd} using your package manager'
            })

    # Check file permissions
    console.print("\n[bold]File Permissions:[/bold]")

    # Check if we can write to temp
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
            f.write('test')
        print_success("Temp directory writable")
    except Exception as e:
        issues.append({
            'level': 'error',
            'component': 'Temp directory',
            'issue': 'Cannot write to temp directory',
            'fix': 'Check disk space and permissions'
        })

    # Show issues summary
    if issues:
        console.print(f"\n[bold]Issues Found:[/bold]")

        table = Table(show_header=True)
        table.add_column("Level", style="bold")
        table.add_column("Component")
        table.add_column("Issue")
        table.add_column("Fix")

        for issue in issues:
            style = "red" if issue['level'] == 'error' else "yellow"
            table.add_row(
                f"[{style}]{issue['level'].upper()}[/{style}]",
                issue['component'],
                issue['issue'],
                issue['fix']
            )

        console.print(table)

        # Attempt fixes if requested
        if fix:
            console.print(f"\n{EMOJI_INFO} Attempting to fix issues...")

            for issue in issues:
                if issue['level'] == 'warning' and 'pip install' in issue['fix']:
                    console.print(f"Suggested fix: {issue['fix']}")

    else:
        console.print(f"\n{EMOJI_SUCCESS} All checks passed!")


def clean_cache(dry_run: bool = False, clean_all: bool = False) -> None:
    """Clean up temporary files and cache"""

    console.print("[bold]Deploy Tool Cache Cleanup[/bold]\n")

    # Find cache directories
    cache_dirs = []

    # Check current directory
    local_cache = Path.cwd() / DEFAULT_CACHE_DIR
    if local_cache.exists():
        cache_dirs.append(local_cache)

    # Check home directory
    home_cache = Path.home() / '.deploy-tool' / 'cache'
    if home_cache.exists():
        cache_dirs.append(home_cache)

    # Check temp directory
    temp_patterns = [
        'deploy-tool-*',
        'tmp-deploy-*',
    ]

    import tempfile
    temp_dir = Path(tempfile.gettempdir())

    for pattern in temp_patterns:
        for path in temp_dir.glob(pattern):
            if path.is_dir():
                cache_dirs.append(path)

    if not cache_dirs:
        console.print(f"{EMOJI_INFO} No cache directories found")
        return

    # Show what will be cleaned
    total_size = 0
    file_count = 0

    console.print("Found cache directories:")
    for cache_dir in cache_dirs:
        dir_size = get_directory_size(cache_dir)
        dir_files = count_files(cache_dir)

        total_size += dir_size
        file_count += dir_files

        console.print(f"  - {cache_dir} ({format_size(dir_size)}, {dir_files} files)")

    console.print(f"\nTotal: {format_size(total_size)} in {file_count} files")

    # Clean if not dry run
    if not dry_run:
        if clean_all:
            # Clean everything
            for cache_dir in cache_dirs:
                console.print(f"\nCleaning {cache_dir}...")
                shutil.rmtree(cache_dir, ignore_errors=True)
                print_success(f"Removed {cache_dir}")
        else:
            # Clean only old files (older than 7 days)
            import time
            cutoff_time = time.time() - (7 * 24 * 60 * 60)

            cleaned_size = 0
            cleaned_files = 0

            for cache_dir in cache_dirs:
                for path in cache_dir.rglob('*'):
                    if path.is_file():
                        if path.stat().st_mtime < cutoff_time:
                            size = path.stat().st_size
                            path.unlink()
                            cleaned_size += size
                            cleaned_files += 1

            console.print(f"\n{EMOJI_SUCCESS} Cleaned {format_size(cleaned_size)} in {cleaned_files} old files")

    else:
        console.print(f"\n{EMOJI_INFO} Dry run mode - no files were deleted")
        console.print("Run without --dry-run to actually clean cache")


def get_directory_size(path: Path) -> int:
    """Get total size of directory"""
    total = 0
    for p in path.rglob('*'):
        if p.is_file():
            total += p.stat().st_size
    return total


def count_files(path: Path) -> int:
    """Count files in directory"""
    return sum(1 for p in path.rglob('*') if p.is_file())


def format_size(size_bytes: int) -> str:
    """Format file size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"