# deploy_tool/core/project_manager.py
"""Project lifecycle management"""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List

import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm

from .path_resolver import PathResolver
from ..api.exceptions import ConfigError, ProjectNotFoundError
from ..constants import (
    PROJECT_CONFIG_FILE,
    CONFIG_VERSION
)


@dataclass
class ProjectConfig:
    """Project configuration data model

    This represents the configuration stored in .deploy-tool.yaml
    """
    name: str
    type: str = "general"
    description: str = ""
    version: str = CONFIG_VERSION
    paths: Dict[str, str] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """Create ProjectConfig from dictionary

        Args:
            data: Configuration dictionary

        Returns:
            ProjectConfig instance
        """
        # Handle both flat and nested project structure
        project_data = data.get('project', {})

        return cls(
            name=project_data.get('name', ''),
            type=project_data.get('type', 'general'),
            description=project_data.get('description', ''),
            version=data.get('version', CONFIG_VERSION),
            paths=data.get('paths', {}),
            defaults=data.get('defaults', {}),
            environments=data.get('environments', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization

        Returns:
            Dictionary representation
        """
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


@dataclass
class ValidationResult:
    """Result of project validation"""
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add error message"""
        self.errors.append(message)
        self.success = False

    def add_warning(self, message: str) -> None:
        """Add warning message"""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add info message"""
        self.info.append(message)

    def add_success(self, message: str) -> None:
        """Add success message"""
        self.info.append(f"✓ {message}")


class ProjectManager:
    """Manage project lifecycle including creation, validation, and migration

    This class handles all project-level operations with lazy initialization
    of the PathResolver to avoid early project detection.
    """

    def __init__(self, path_resolver: Optional[PathResolver] = None):
        """Initialize project manager

        Args:
            path_resolver: Optional PathResolver instance. If not provided,
                          will be created lazily when needed.
        """
        self._path_resolver = path_resolver
        self.console = Console()

    @property
    def path_resolver(self) -> PathResolver:
        """Get path resolver with lazy initialization

        Returns:
            PathResolver instance
        """
        if self._path_resolver is None:
            self._path_resolver = PathResolver()
        return self._path_resolver

    def find_project_root(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """Find project root directory

        This method returns None instead of raising an exception,
        making it safer for use in contexts where a project might not exist.

        Args:
            start_path: Starting directory for search

        Returns:
            Project root path or None if not found
        """
        try:
            # Create a temporary resolver to search
            temp_resolver = PathResolver()
            return temp_resolver.find_project_root(start_path)
        except ProjectNotFoundError:
            return None
        except Exception:
            # Any other error, return None
            return None

    async def init_project(self,
                          project_path: Path,
                          project_name: Optional[str] = None,
                          project_type: str = "algorithm",
                          description: Optional[str] = None,
                          interactive: bool = True) -> None:
        """Initialize a new deployment project

        Args:
            project_path: Path where to create the project
            project_name: Project name (will prompt if not provided and interactive)
            project_type: Type of project (algorithm, model, service, general)
            description: Project description
            interactive: Whether to run in interactive mode
        """
        # Create project directory if needed
        project_path.mkdir(parents=True, exist_ok=True)

        # Use a resolver with explicit project root for initialization
        self._path_resolver = PathResolver(project_root=project_path)

        # Check if already initialized
        config_file = project_path / PROJECT_CONFIG_FILE
        if config_file.exists():
            if not Confirm.ask(
                f"[yellow]Project already initialized. Overwrite {PROJECT_CONFIG_FILE}?[/yellow]",
                default=False
            ):
                self.console.print("[red]Initialization cancelled[/red]")
                return

        existing_dirs = [d for d in project_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if existing_dirs and interactive:
            self.console.print(f"[yellow]Found existing directories: {', '.join(d.name for d in existing_dirs)}[/yellow]")
            if not Confirm.ask("Continue with initialization?", default=True):
                self.console.print("[red]Initialization cancelled[/red]")
                return

        # Interactive mode
        if interactive:
            config = await self._interactive_init(project_path, project_name)
        else:
            # Use provided parameters or defaults
            config = ProjectConfig(
                name=project_name or project_path.name,
                type=project_type or "algorithm",
                description=description or f"Deployment project for {project_name or project_path.name}"
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
        """Interactive project initialization wizard

        Args:
            project_path: Project directory path
            project_name: Optional pre-filled project name

        Returns:
            ProjectConfig with user inputs
        """
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
        """Create standard project directory structure

        Args:
            project_path: Root directory of the project
        """
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
            readme.write_text(f"# {project_path.name}\n\nDeployment project initialized with deploy-tool.\n")

    def _save_config(self, config_file: Path, config: ProjectConfig) -> None:
        """Save project configuration to file

        Args:
            config_file: Path to configuration file
            config: ProjectConfig object to save
        """
        data = {
            'version': CONFIG_VERSION,
            'project': config.to_dict()
        }

        # Add paths if customized
        if config.paths:
            data['paths'] = config.paths

        with open(config_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def _create_gitignore(self, project_path: Path) -> None:
        """Create .gitignore file with sensible defaults

        Args:
            project_path: Project root directory
        """
        gitignore = project_path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("""# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv

# Deploy Tool
dist/
*.tar.gz
*.tar.bz2
*.tar.xz
*.tar.lz4
.deploy-tool-cache/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
""")

    def _show_init_summary(self, project_path: Path, config: ProjectConfig) -> None:
        """Show initialization summary

        Args:
            project_path: Project root directory
            config: Project configuration
        """
        self.console.print(f"\n[green]✓ Project initialized successfully![/green]")
        self.console.print(f"\nProject: [cyan]{config.name}[/cyan]")
        self.console.print(f"Type: {config.type}")
        self.console.print(f"Location: {project_path}")
        self.console.print("\n[bold]Next steps:[/bold]")
        self.console.print("1. Add your code to the src/ directory")
        self.console.print("2. Add components to models/, configs/, etc.")
        self.console.print("3. Run 'deploy-tool pack' to package components")

    def load_project_config(self) -> ProjectConfig:
        """Load project configuration

        Returns:
            ProjectConfig object

        Raises:
            ConfigError: If configuration is invalid or missing
        """
        config_file = self.path_resolver.project_root / PROJECT_CONFIG_FILE

        if not config_file.exists():
            # Return default config for backward compatibility
            return ProjectConfig(
                name=self.path_resolver.project_root.name,
                type="general"
            )

        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)

            # Support both new and old config format
            if 'project' in data:
                # New format with nested project section
                return ProjectConfig.from_dict(data)
            else:
                # Old format - try to adapt
                return ProjectConfig(
                    name=data.get('name', self.path_resolver.project_root.name),
                    type=data.get('type', 'general'),
                    description=data.get('description', ''),
                    version=data.get('version', CONFIG_VERSION),
                    paths=data.get('paths', {}),
                    defaults=data.get('defaults', {}),
                    environments=data.get('environments', {})
                )
        except Exception as e:
            raise ConfigError(f"Failed to load project configuration: {e}")

    def save_project_config(self, config: ProjectConfig) -> None:
        """Save project configuration

        Args:
            config: ProjectConfig to save
        """
        config_file = self.path_resolver.project_root / PROJECT_CONFIG_FILE
        self._save_config(config_file, config)

    def validate_project_structure(self) -> ValidationResult:
        """Validate project structure and configuration

        Returns:
            ValidationResult with detailed findings
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
        """Migrate project from older version

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
        """Get project information summary

        Returns:
            Dictionary with project information
        """
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