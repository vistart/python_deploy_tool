# deploy_tool/services/conflict_resolver.py
"""Conflict resolution service"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from ..utils import format_size, calculate_file_checksum


class ConflictResolver:
    """Handle file conflicts and user interactions"""

    def __init__(self):
        self.console = Console()

    def handle_existing_config(self, existing_path: Path) -> str:
        """
        Handle existing configuration file

        Args:
            existing_path: Path to existing config

        Returns:
            Action to take: 'use_existing', 'update_version', 'regenerate', 'cancel'
        """
        # Load existing config
        import yaml
        with open(existing_path, 'r') as f:
            existing = yaml.safe_load(f)

        # Display existing config info
        self.console.print(f"\n[yellow]Found existing configuration:[/yellow] {existing_path}")

        table = Table(title="Configuration Details")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Type", existing.get('package', {}).get('type', 'N/A'))
        table.add_row("Version", existing.get('package', {}).get('version', 'N/A'))
        table.add_row("Created", datetime.fromtimestamp(
            existing_path.stat().st_mtime
        ).strftime('%Y-%m-%d %H:%M:%S'))
        table.add_row("Size", format_size(existing_path.stat().st_size))

        self.console.print(table)

        # Interactive choice
        choices = [
            "Use existing configuration",
            "Update version number and use",
            "Backup and regenerate",
            "Cancel operation"
        ]

        action = Prompt.ask(
            "\nHow would you like to proceed?",
            choices=choices,
            default=choices[0]
        )

        # Map choice to action
        action_map = {
            choices[0]: "use_existing",
            choices[1]: "update_version",
            choices[2]: "regenerate",
            choices[3]: "cancel"
        }

        result = action_map[action]

        # Handle backup if regenerating
        if result == "regenerate":
            backup_path = self._create_backup(existing_path)
            self.console.print(f"[green]✓ Backed up to:[/green] {backup_path}")

        return result

    def handle_existing_archive(self,
                                archive_path: Path,
                                new_checksum: Optional[str] = None) -> str:
        """
        Handle existing archive file

        Args:
            archive_path: Path to existing archive
            new_checksum: Expected checksum of new archive

        Returns:
            Action to take: 'overwrite', 'rename', 'skip', 'cancel'
        """
        self.console.print(f"\n[yellow]Archive already exists:[/yellow] {archive_path}")

        # Calculate existing checksum
        existing_checksum = calculate_file_checksum(archive_path)

        # Display info
        table = Table(title="Existing Archive Details")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Size", format_size(archive_path.stat().st_size))
        table.add_row("Modified", datetime.fromtimestamp(
            archive_path.stat().st_mtime
        ).strftime('%Y-%m-%d %H:%M:%S'))
        table.add_row("Checksum", existing_checksum[:16] + "...")

        if new_checksum and new_checksum == existing_checksum:
            table.add_row("Status", "[green]Identical to new archive[/green]")
        else:
            table.add_row("Status", "[yellow]Different from new archive[/yellow]")

        self.console.print(table)

        # If identical, suggest skip
        if new_checksum and new_checksum == existing_checksum:
            if Confirm.ask("Archives are identical. Skip packaging?", default=True):
                return "skip"

        # Otherwise ask what to do
        choices = [
            "Overwrite existing archive",
            "Rename new archive",
            "Skip packaging",
            "Cancel operation"
        ]

        action = Prompt.ask(
            "\nHow would you like to proceed?",
            choices=choices,
            default=choices[0]
        )

        action_map = {
            choices[0]: "overwrite",
            choices[1]: "rename",
            choices[2]: "skip",
            choices[3]: "cancel"
        }

        return action_map[action]

    def handle_version_conflict(self,
                                component_type: str,
                                existing_versions: List[str],
                                suggested_version: str) -> str:
        """
        Handle version conflicts

        Args:
            component_type: Component type
            existing_versions: List of existing versions
            suggested_version: Suggested new version

        Returns:
            Selected version
        """
        self.console.print(f"\n[yellow]Existing versions for {component_type}:[/yellow]")

        # Display existing versions
        table = Table(title="Version History")
        table.add_column("Version", style="cyan")
        table.add_column("Status", style="white")

        for version in existing_versions[:5]:  # Show latest 5
            if version == suggested_version:
                table.add_row(version, "[red]Conflict[/red]")
            else:
                table.add_row(version, "Available")

        if len(existing_versions) > 5:
            table.add_row("...", f"({len(existing_versions) - 5} more)")

        self.console.print(table)

        # Suggest alternative
        self.console.print(f"\n[green]Suggested version:[/green] {suggested_version}")

        # Ask for version
        version = Prompt.ask(
            "Enter version number",
            default=suggested_version
        )

        # Validate
        while version in existing_versions:
            self.console.print(f"[red]Version {version} already exists![/red]")
            version = Prompt.ask(
                "Enter a different version number",
                default=self._increment_version(version)
            )

        return version

    def handle_deployment_conflict(self,
                                   deploy_path: Path,
                                   components: List[Tuple[str, str]]) -> str:
        """
        Handle deployment path conflicts

        Args:
            deploy_path: Deployment target path
            components: List of (type, version) tuples

        Returns:
            Action to take: 'overwrite', 'merge', 'backup', 'cancel'
        """
        self.console.print(f"\n[yellow]Deployment target not empty:[/yellow] {deploy_path}")

        # Check what exists
        existing_components = []
        for comp_type, comp_version in components:
            comp_path = deploy_path / comp_type / comp_version
            if comp_path.exists():
                existing_components.append((comp_type, comp_version))

        if existing_components:
            # Show conflicts
            table = Table(title="Existing Components")
            table.add_column("Component", style="cyan")
            table.add_column("Version", style="white")
            table.add_column("Status", style="yellow")

            for comp_type, comp_version in existing_components:
                table.add_row(comp_type, comp_version, "Will be replaced")

            self.console.print(table)

        # Options
        choices = [
            "Overwrite existing deployment",
            "Merge with existing (keep non-conflicting)",
            "Backup existing and deploy",
            "Cancel deployment"
        ]

        action = Prompt.ask(
            "\nHow would you like to proceed?",
            choices=choices,
            default=choices[2]  # Default to backup
        )

        action_map = {
            choices[0]: "overwrite",
            choices[1]: "merge",
            choices[2]: "backup",
            choices[3]: "cancel"
        }

        result = action_map[action]

        # Handle backup if requested
        if result == "backup":
            backup_path = self._create_deployment_backup(deploy_path)
            self.console.print(f"[green]✓ Backed up to:[/green] {backup_path}")

        return result

    def resolve_path_conflict(self,
                              suggested_path: Path,
                              reason: str = "Path already exists") -> Optional[Path]:
        """
        Resolve path conflicts interactively

        Args:
            suggested_path: Suggested path
            reason: Reason for conflict

        Returns:
            Resolved path or None if cancelled
        """
        self.console.print(f"\n[yellow]Path conflict:[/yellow] {reason}")
        self.console.print(f"Suggested path: {suggested_path}")

        choices = [
            "Use suggested path",
            "Enter custom path",
            "Cancel"
        ]

        action = Prompt.ask(
            "\nHow would you like to proceed?",
            choices=choices,
            default=choices[0]
        )

        if action == choices[0]:
            return suggested_path
        elif action == choices[1]:
            custom_path = Prompt.ask("Enter custom path")
            return Path(custom_path)
        else:
            return None

    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.with_suffix(f'.{timestamp}.backup')
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _create_deployment_backup(self, deploy_path: Path) -> Path:
        """Create backup of deployment directory"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = deploy_path.parent / f"{deploy_path.name}_backup_{timestamp}"
        shutil.copytree(deploy_path, backup_path)
        return backup_path

    def _increment_version(self, version: str) -> str:
        """Increment version number"""
        from ..utils import suggest_version
        return suggest_version(version, "patch")

    def confirm_action(self,
                       action: str,
                       details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Confirm an action with the user

        Args:
            action: Action description
            details: Additional details to show

        Returns:
            True if confirmed
        """
        self.console.print(f"\n[bold yellow]Confirm Action:[/bold yellow] {action}")

        if details:
            table = Table(show_header=False)
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="white")

            for key, value in details.items():
                table.add_row(key, str(value))

            self.console.print(table)

        return Confirm.ask("\nProceed?", default=False)