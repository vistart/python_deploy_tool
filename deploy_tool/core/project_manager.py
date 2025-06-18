"""Project lifecycle management"""

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.tree import Tree

from .path_resolver import PathResolver
from .validation_engine import ValidationEngine, ValidationResult
from ..constants import (
    PROJECT_CONFIG_FILE,
    CONFIG_VERSION,
    GIT_IGNORE_TEMPLATE
)


@dataclass
class ProjectConfig:
    """Project configuration data"""
    version: str = CONFIG_VERSION
    name: str = ""
    type: str = "general"
    description: str = ""
    paths: Dict[str, str] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectConfig':
        """Create from dictionary"""
        return cls(
            version=data.get('version', CONFIG_VERSION),
            name=data.get('project', {}).get('name', ''),
            type=data.get('project', {}).get('type', 'general'),
            description=data.get('project', {}).get('description', ''),
            paths=data.get('paths', {}),
            defaults=data.get('defaults', {}),
            environments=data.get('environments', {})
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'version': self.version,
            'project': {
                'name': self.name,
                'type': self.type,
                'description': self.description
            },
            'paths': self.paths,
            'defaults': self.defaults,
            'environments': self.environments
        }


class ProjectManager:
    """Project lifecycle management"""

    def __init__(self, path_resolver: Optional[PathResolver] = None):
        self.path_resolver = path_resolver or PathResolver()
        self.console = Console()
        self.validation_engine = ValidationEngine()

    async def init_project(self,
                           project_path: Path,
                           project_name: Optional[str] = None,
                           interactive: bool = True) -> None:
        """
        Initialize new project

        Args:
            project_path: Path to project directory
            project_name: Project name (optional)
            interactive: Whether to run in interactive mode
        """
        project_path = Path(project_path).resolve()

        # Check if already initialized
        config_file = project_path / PROJECT_CONFIG_FILE
        if config_file.exists():
            self.console.print(f"[red]Project already initialized at {project_path}[/red]")
            return

        # Interactive mode
        if interactive:
            config = await self._interactive_init(project_path, project_name)
        else:
            # Use defaults
            config = ProjectConfig(
                name=project_name or project_path.name,
                type="algorithm",
                description=f"Deployment project for {project_name or project_path.name}"
            )

        # Create directory structure
        self._create_project_structure(project_path)

        # Save configuration
        self._save_config(config_file, config)

        # Create .gitignore if needed
        self._create_gitignore(project_path)

        # Show summary
        self._show_init_summary(project_path, config)

    async def _interactive_init(self, project_path: Path,
                                project_name: Optional[str] = None) -> ProjectConfig:
        """Interactive project initialization"""
        self.console.print("[bold cyan]Deploy Tool Project Initialization[/bold cyan]\n")

        # Get project info
        name = project_name or Prompt.ask(
            "Project name",
            default=project_path.name
        )

        project_type = Prompt.ask(
            "Project type",
            choices=["algorithm", "model", "service", "general"],
            default="algorithm"
        )

        description = Prompt.ask(
            "Project description",
            default=f"Deployment project for {name}"
        )

        # Ask about directory structure
        use_defaults = Confirm.ask(
            "Use default directory structure?",
            default=True
        )

        paths = {}
        if not use_defaults:
            paths['deployment'] = Prompt.ask(
                "Deployment directory",
                default="./deployment"
            )
            paths['dist'] = Prompt.ask(
                "Output directory",
                default="./dist"
            )

        return ProjectConfig(
            name=name,
            type=project_type,
            description=description,
            paths=paths
        )

    def _create_project_structure(self, project_path: Path) -> None:
        """Create standard project directory structure"""
        dirs = [
            "src",
            "deployment/package-configs",
            "deployment/manifests",
            "deployment/releases",
            "dist",
        ]

        for dir_path in dirs:
            (project_path / dir_path).mkdir(parents=True, exist_ok=True)

        # Create README if not exists
        readme = project_path / "README.md"
        if not readme.exists():
            readme.write_text(f"# {project_path.name}\n\nDeployment project managed by deploy-tool.\n")

    def _save_config(self, config_file: Path, config: ProjectConfig) -> None:
        """Save project configuration"""
        config_dict = config.to_dict()

        # Add header comment
        yaml_content = f"""# Deploy Tool Project Configuration
# Generated at: {datetime.now().isoformat()}

"""
        yaml_content += yaml.dump(config_dict, default_flow_style=False, sort_keys=False)

        config_file.write_text(yaml_content)

    def _create_gitignore(self, project_path: Path) -> None:
        """Create or update .gitignore"""
        gitignore = project_path / ".gitignore"

        if gitignore.exists():
            content = gitignore.read_text()
            if "deploy-tool" not in content:
                # Append our section
                content += f"\n\n# Deploy Tool\n{GIT_IGNORE_TEMPLATE}"
                gitignore.write_text(content)
        else:
            gitignore.write_text(GIT_IGNORE_TEMPLATE)

    def _show_init_summary(self, project_path: Path, config: ProjectConfig) -> None:
        """Show initialization summary"""
        tree = Tree(f"[bold green]✓ Project initialized: {config.name}[/bold green]")

        root = tree.add(f"[cyan]{project_path}[/cyan]")
        root.add(f"[yellow]{PROJECT_CONFIG_FILE}[/yellow] - Project configuration")
        root.add("[yellow].gitignore[/yellow] - Git ignore rules")

        deployment = root.add("[blue]deployment/[/blue] - Deployment files")
        deployment.add("[blue]package-configs/[/blue] - Package configurations")
        deployment.add("[blue]manifests/[/blue] - Component manifests")
        deployment.add("[blue]releases/[/blue] - Release records")

        root.add("[blue]dist/[/blue] - Package outputs")
        root.add("[blue]src/[/blue] - Source code")

        self.console.print(tree)
        self.console.print("\n[green]Next steps:[/green]")
        self.console.print("1. Add your code to the src/ directory")
        self.console.print("2. Add components to models/, configs/, etc.")
        self.console.print("3. Run 'deploy-tool pack' to package components")

    def load_project_config(self) -> ProjectConfig:
        """
        Load project configuration

        Returns:
            ProjectConfig object

        Raises:
            ConfigError: If configuration is invalid
        """
        from ..api.exceptions import ConfigError

        config_file = self.path_resolver.project_root / PROJECT_CONFIG_FILE

        if not config_file.exists():
            # Return default config
            return ProjectConfig(
                name=self.path_resolver.project_root.name,
                type="general"
            )

        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)

            return ProjectConfig.from_dict(data)
        except Exception as e:
            raise ConfigError(f"Failed to load project configuration: {e}")

    def save_project_config(self, config: ProjectConfig) -> None:
        """Save project configuration"""
        config_file = self.path_resolver.project_root / PROJECT_CONFIG_FILE
        self._save_config(config_file, config)

    def validate_project_structure(self) -> ValidationResult:
        """
        Validate project structure

        Returns:
            ValidationResult with details
        """
        result = ValidationResult()

        # Check project config
        config_file = self.path_resolver.project_root / PROJECT_CONFIG_FILE
        if config_file.exists():
            result.add_success("Project configuration found")
            try:
                config = self.load_project_config()
                result.add_success(f"Project: {config.name} ({config.type})")
            except Exception as e:
                result.add_error(f"Invalid project configuration: {e}")
        else:
            result.add_warning("No project configuration file")

        # Check directories
        required_dirs = [
            (self.path_resolver.get_deployment_dir(), "Deployment directory"),
            (self.path_resolver.get_configs_dir(), "Package configs directory"),
        ]

        for dir_path, name in required_dirs:
            if dir_path.exists():
                result.add_success(f"{name} exists")
            else:
                result.add_warning(f"{name} missing (will be created when needed)")

        # Check Git
        git_dir = self.path_resolver.project_root / ".git"
        if git_dir.exists():
            result.add_success("Git repository initialized")
        else:
            result.add_warning("Not a Git repository")

        # Check for manifests
        manifests_dir = self.path_resolver.get_manifests_dir()
        if manifests_dir.exists():
            manifest_count = len(list(manifests_dir.glob("*.manifest.json")))
            if manifest_count > 0:
                result.add_info(f"Found {manifest_count} component manifest(s)")

        return result

    async def migrate_project(self, from_version: Optional[str] = None) -> None:
        """
        Migrate project from older version

        Args:
            from_version: Source version (auto-detect if None)
        """
        self.console.print("[cyan]Checking for migration needs...[/cyan]")

        config = self.load_project_config()
        current_version = config.version

        if current_version == CONFIG_VERSION:
            self.console.print("[green]Project is already up to date[/green]")
            return

        self.console.print(f"[yellow]Migrating from version {current_version} to {CONFIG_VERSION}[/yellow]")

        # Backup current config
        config_file = self.path_resolver.project_root / PROJECT_CONFIG_FILE
        backup_file = config_file.with_suffix('.yaml.backup')
        shutil.copy2(config_file, backup_file)
        self.console.print(f"[cyan]Configuration backed up to {backup_file}[/cyan]")

        # Perform migration (version-specific logic would go here)
        config.version = CONFIG_VERSION

        # Update paths to relative format if needed
        if config.paths:
            updated_paths = {}
            for key, value in config.paths.items():
                if Path(value).is_absolute():
                    # Convert to relative
                    try:
                        rel_path = Path(value).relative_to(self.path_resolver.project_root)
                        updated_paths[key] = f"./{rel_path}"
                        self.console.print(f"[yellow]Converted path {key}: {value} → ./{rel_path}[/yellow]")
                    except ValueError:
                        updated_paths[key] = value
                else:
                    updated_paths[key] = value
            config.paths = updated_paths

        # Save updated config
        self.save_project_config(config)

        self.console.print("[green]✓ Migration completed successfully[/green]")

    def get_project_info(self) -> Dict[str, Any]:
        """Get project information summary"""
        config = self.load_project_config()

        return {
            'name': config.name,
            'type': config.type,
            'description': config.description,
            'root': str(self.path_resolver.project_root),
            'version': config.version,
            'paths': {
                'deployment': str(self.path_resolver.get_deployment_dir()),
                'manifests': str(self.path_resolver.get_manifests_dir()),
                'configs': str(self.path_resolver.get_configs_dir()),
                'dist': str(self.path_resolver.get_dist_dir()),
            }
        }