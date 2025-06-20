"""Interactive utilities for CLI commands"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from ...core import PathResolver, ManifestEngine, ComponentRegistry, ConfigGenerator
from ...models.component import PublishComponent
from ...models.config import PackageConfig, SourceConfig, CompressionConfig

console = Console()


class PackWizard:
    """Interactive wizard for package configuration"""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    def run(self, path_resolver: PathResolver) -> Dict[str, Any]:
        """Run interactive pack wizard"""
        self.console.print("\n[bold cyan]Package Configuration Wizard[/bold cyan]\n")

        # Get package type
        package_type = Prompt.ask(
            "Package type (e.g., model, config, runtime)",
            default="model"
        )

        # Get version
        version = Prompt.ask(
            "Version",
            default="1.0.0"
        )

        # Get source path
        source_path = Prompt.ask(
            "Source path (relative to project root)",
            default="."
        )

        # Validate source path
        abs_source = path_resolver.resolve(source_path)
        if not abs_source.exists():
            self.console.print(f"[red]Error: Path does not exist: {source_path}[/red]")
            raise ValueError(f"Invalid source path: {source_path}")

        # Get package name
        default_name = f"{path_resolver.project_root.name}_{package_type}"
        package_name = Prompt.ask(
            "Package name",
            default=default_name
        )

        # Get description
        description = Prompt.ask(
            "Description (optional)",
            default=""
        )

        # Compression settings
        self.console.print("\n[bold]Compression Settings:[/bold]")
        algorithm = Prompt.ask(
            "Algorithm",
            choices=["gzip", "bzip2", "xz", "lz4", "none"],
            default="gzip"
        )

        level = 6
        if algorithm != "none":
            level = int(Prompt.ask(
                "Compression level (1-9)",
                default="6"
            ))

        # Build configuration
        config = {
            'package': {
                'type': package_type,
                'name': package_name,
                'version': version,
                'description': description
            },
            'source': {
                'path': source_path
            },
            'compression': {
                'algorithm': algorithm,
                'level': level
            }
        }

        # Show summary
        self._show_summary(config)

        # Save config?
        save_config = Confirm.ask(
            "\nSave this configuration for future use?",
            default=True
        )

        if save_config:
            config_name = Prompt.ask(
                "Configuration name",
                default=f"{package_type}.yaml"
            )
            config['save_config'] = True
            config['config_path'] = f"deployment/package-configs/{config_name}"

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

    def select_components(self, path_resolver: PathResolver) -> List[PublishComponent]:
        """Interactive component selection"""
        # Initialize component registry
        manifest_engine = ManifestEngine(path_resolver)
        registry = ComponentRegistry(path_resolver, manifest_engine)

        # Get available components
        available = registry.list_components()

        if not available:
            self.console.print("[yellow]No components available for publishing[/yellow]")
            return []

        # Display available components
        self.console.print("\n[bold]Available components:[/bold]")
        table = Table()
        table.add_column("#", style="dim", width=3)
        table.add_column("Type", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Created", style="yellow")

        for i, comp in enumerate(available, 1):
            # Get component info
            info = registry.find_component(comp.type, comp.version)
            created_str = info.created_at.strftime("%Y-%m-%d %H:%M") if info else "Unknown"
            table.add_row(str(i), comp.type, comp.version, created_str)

        self.console.print(table)

        # Get user selection
        selection = Prompt.ask(
            "\nSelect components to publish (comma-separated numbers or 'all')",
            default="all"
        )

        if selection.lower() == 'all':
            return [PublishComponent(type=c.type, version=c.version) for c in available]

        # Parse selection
        selected = []
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            for idx in indices:
                if 0 <= idx < len(available):
                    comp = available[idx]
                    selected.append(PublishComponent(type=comp.type, version=comp.version))
        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection[/red]")
            return []

        return selected

    def get_release_info(self) -> Dict[str, str]:
        """Get release information interactively"""
        self.console.print("\n[bold]Release Information:[/bold]")

        # Get release version
        from datetime import datetime
        default_version = datetime.now().strftime("%Y.%m.%d")
        release_version = Prompt.ask(
            "Release version",
            default=default_version
        )

        # Get release name
        release_name = Prompt.ask(
            "Release name (optional)",
            default=""
        )

        # Get description
        description = Prompt.ask(
            "Release description (optional)",
            default=""
        )

        return {
            'version': release_version,
            'name': release_name,
            'description': description
        }