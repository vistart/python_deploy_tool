"""Interactive wizard utilities using Rich"""

from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table

from ...utils.file_utils import scan_directory

console = Console()


class PackWizard:
    """Interactive wizard for package configuration"""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    async def run(self, initial_path: Optional[str] = None) -> Dict[str, Any]:
        """Run the interactive pack wizard"""
        self.console.print("[bold cyan]Package Configuration Wizard[/bold cyan]\n")

        # Get package type
        package_type = Prompt.ask(
            "Package type (e.g., model, config, data, runtime)",
            default="model"
        )

        # Get source path
        if initial_path:
            source_path = initial_path
            self.console.print(f"Source path: {source_path}")
        else:
            source_path = Prompt.ask(
                "Source path (file or directory)",
                default="."
            )

        # Validate path
        path = Path(source_path)
        if not path.exists():
            self.console.print(f"[red]Error: Path '{source_path}' does not exist[/red]")
            raise ValueError(f"Path does not exist: {source_path}")

        # Get version
        version = Prompt.ask(
            "Version number",
            default="1.0.0"
        )

        # Get package name
        default_name = f"{Path('.').resolve().name}_{package_type}"
        package_name = Prompt.ask(
            "Package name",
            default=default_name
        )

        # Show detected files
        if path.is_dir():
            files = scan_directory(path)
            if files:
                self.console.print(f"\n[cyan]Found {len(files)} files:[/cyan]")
                # Show first 10 files
                for i, file in enumerate(files[:10]):
                    self.console.print(f"  • {file}")
                if len(files) > 10:
                    self.console.print(f"  ... and {len(files) - 10} more files")

        # Compression settings
        use_custom_compression = Confirm.ask(
            "\nCustomize compression settings?",
            default=False
        )

        compression_config = {}
        if use_custom_compression:
            compression_config['algorithm'] = Prompt.ask(
                "Compression algorithm",
                choices=['gzip', 'bzip2', 'xz', 'lz4'],
                default='gzip'
            )
            compression_config['level'] = IntPrompt.ask(
                "Compression level (1-9)",
                default=6
            )

        # Save configuration?
        save_config = Confirm.ask(
            "\nSave configuration for future use?",
            default=True
        )

        config_path = None
        if save_config:
            default_config_path = f"deployment/package-configs/{package_type}.yaml"
            config_path = Prompt.ask(
                "Configuration file path",
                default=default_config_path
            )

        # Build configuration
        config = {
            'package': {
                'type': package_type,
                'name': package_name,
                'version': version
            },
            'source': {
                'path': str(source_path)
            }
        }

        if compression_config:
            config['compression'] = compression_config

        if save_config:
            config['save_config'] = True
            config['config_path'] = config_path

        # Show summary
        self._show_summary(config)

        if not Confirm.ask("\n[cyan]Proceed with this configuration?[/cyan]", default=True):
            raise KeyboardInterrupt("User cancelled")

        return config

    def _show_summary(self, config: Dict[str, Any]) -> None:
        """Show configuration summary"""
        table = Table(title="Package Configuration Summary")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        # Package info
        table.add_row("Type", config['package']['type'])
        table.add_row("Name", config['package']['name'])
        table.add_row("Version", config['package']['version'])
        table.add_row("Source", config['source']['path'])

        # Compression
        comp = config.get('compression', {})
        table.add_row(
            "Compression",
            f"{comp.get('algorithm', 'gzip')} (level {comp.get('level', 6)})"
        )

        # Save config
        if config.get('save_config'):
            table.add_row("Save to", config.get('config_path', 'N/A'))

        self.console.print(table)


class PublishWizard:
    """Interactive wizard for publish configuration"""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    async def select_components(self, available_components: List[Dict]) -> List[str]:
        """Interactive component selection"""
        self.console.print("[bold]Select components to publish:[/bold]\n")

        # Show available components
        table = Table()
        table.add_column("#", style="dim")
        table.add_column("Type", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Created", style="yellow")

        for i, comp in enumerate(available_components, 1):
            table.add_row(
                str(i),
                comp['type'],
                comp['version'],
                comp.get('created', 'Unknown')
            )

        self.console.print(table)

        # Get selections
        selections = Prompt.ask(
            "\nSelect components (comma-separated numbers or 'all')",
            default="all"
        )

        if selections.lower() == 'all':
            return [f"{c['type']}:{c['version']}" for c in available_components]

        # Parse selections
        selected = []
        for num in selections.split(','):
            try:
                idx = int(num.strip()) - 1
                if 0 <= idx < len(available_components):
                    comp = available_components[idx]
                    selected.append(f"{comp['type']}:{comp['version']}")
            except ValueError:
                continue

        return selected