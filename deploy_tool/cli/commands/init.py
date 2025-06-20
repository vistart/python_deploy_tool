"""Initialize command for creating new deploy-tool projects"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

import click
from rich.prompt import Prompt, Confirm

from ..decorators import dual_mode_command
from ..utils.output import console, print_error, print_warning
from ...constants import (
    EMOJI_SUCCESS,
    EMOJI_WARNING,
    EMOJI_ROCKET,
    PROJECT_CONFIG_FILE
)
from ...core.project_manager import ProjectManager


@click.command()
@click.argument('path', required=False, default='.')
@click.option(
    '--name', '-n',
    help='Project name'
)
@click.option(
    '--type', '-t', 'project_type',
    type=click.Choice(['algorithm', 'model', 'service', 'general']),
    default='algorithm',
    help='Project type'
)
@click.option(
    '--description', '-d',
    help='Project description'
)
@click.option(
    '--force', '-f',
    is_flag=True,
    help='Force initialization even if directory is not empty'
)
@click.option(
    '--no-git',
    is_flag=True,
    help='Skip git repository initialization'
)
@dual_mode_command
def init(ctx, path, name, project_type, description, force, no_git):
    """Initialize a new deploy-tool project

    Examples:
        deploy-tool init
        deploy-tool init ./my-project --name "My Project"
        deploy-tool init --type model --description "Image classification model"
    """
    # Resolve project path
    project_path = Path(path).resolve()

    # Check if directory exists and is not empty
    if project_path.exists() and any(project_path.iterdir()) and not force:
        if project_path / PROJECT_CONFIG_FILE:
            console.print(f"{EMOJI_WARNING} Project already initialized in {project_path}")
            ctx.exit(0)

        console.print(f"{EMOJI_WARNING} Directory {project_path} is not empty")

        if ctx.interactive:
            if not Confirm.ask("Initialize anyway?", default=False):
                ctx.exit(0)
        else:
            console.print("Use --force to initialize in non-empty directory")
            ctx.exit(1)

    # Create directory if it doesn't exist
    project_path.mkdir(parents=True, exist_ok=True)

    # Get project details interactively if not provided
    if ctx.interactive and not all([name]):
        name, project_type, description = get_project_details_interactive(
            name, project_type, description, project_path
        )

    # Use directory name as default if name not provided
    if not name:
        name = project_path.name

    # Initialize project
    console.print(f"\n{EMOJI_ROCKET} Initializing deploy-tool project...")

    try:
        # Create project manager
        project_manager = ProjectManager(project_path)

        # Define default components based on project type
        components = get_default_components(project_type)

        # Create project
        project = project_manager.create_project(
            name=name,
            description=description,
            components=components
        )

        # Initialize git repository if requested
        if not no_git and not (project_path / '.git').exists():
            init_git_repository(project_path)

        # Show success message
        console.print(f"\n{EMOJI_SUCCESS} Project initialized successfully!")
        console.print(f"\nProject: {name}")
        console.print(f"Type: {project_type}")
        console.print(f"Location: {project_path}")

        # Show project structure
        show_project_structure(project_path)

        # Show next steps
        console.print(f"\n{EMOJI_SUCCESS} Next steps:")
        console.print("1. cd " + str(project_path))
        console.print("2. Add your components to the configured directories")
        console.print("3. deploy-tool pack <component-path> --type <type> --version <version>")
        console.print("4. deploy-tool publish <component>:<version>")
        console.print("5. deploy-tool deploy <component>:<version>")

    except Exception as e:
        print_error(f"Failed to initialize project: {str(e)}")
        ctx.exit(1)


def get_project_details_interactive(
    name: Optional[str],
    project_type: Optional[str],
    description: Optional[str],
    project_path: Path
) -> tuple[str, str, str]:
    """Get project details interactively"""

    console.print("[bold]Project Setup[/bold]\n")

    # Get project name
    if not name:
        default_name = project_path.name
        name = Prompt.ask(
            "Project name",
            default=default_name
        )

    # Get project type
    if not project_type:
        console.print("\nProject type:")
        console.print("  1. algorithm - Algorithm or ML pipeline project")
        console.print("  2. model - Machine learning model project")
        console.print("  3. service - Service or API project")
        console.print("  4. general - General purpose project")

        choice = Prompt.ask("Select type", choices=["1", "2", "3", "4"], default="1")

        type_map = {
            "1": "algorithm",
            "2": "model",
            "3": "service",
            "4": "general"
        }
        project_type = type_map[choice]

    # Get description
    if not description:
        description = Prompt.ask(
            "\nProject description (optional)",
            default=""
        )

    return name, project_type, description


def get_default_components(project_type: str) -> Dict[str, Dict[str, Any]]:
    """Get default components based on project type"""

    if project_type == "algorithm":
        return {
            "algorithm": {
                "path": "./algorithm",
                "description": "Algorithm implementation"
            },
            "config": {
                "path": "./configs",
                "description": "Configuration files"
            },
            "runtime": {
                "path": "./runtime",
                "description": "Runtime environment"
            }
        }

    elif project_type == "model":
        return {
            "model": {
                "path": "./models",
                "description": "Model files and weights"
            },
            "config": {
                "path": "./configs",
                "description": "Model configuration"
            },
            "preprocessing": {
                "path": "./preprocessing",
                "description": "Data preprocessing code"
            }
        }

    elif project_type == "service":
        return {
            "service": {
                "path": "./service",
                "description": "Service implementation"
            },
            "config": {
                "path": "./configs",
                "description": "Service configuration"
            },
            "dependencies": {
                "path": "./dependencies",
                "description": "Service dependencies"
            }
        }

    else:  # general
        return {
            "main": {
                "path": "./main",
                "description": "Main component"
            },
            "config": {
                "path": "./configs",
                "description": "Configuration files"
            }
        }


def init_git_repository(project_path: Path) -> None:
    """Initialize git repository"""

    try:
        # Initialize git
        subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            check=True
        )

        # Add initial commit
        subprocess.run(
            ["git", "add", "."],
            cwd=project_path,
            capture_output=True,
            check=True
        )

        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=project_path,
            capture_output=True,
            check=True
        )

        console.print(f"{EMOJI_SUCCESS} Initialized git repository")

    except subprocess.CalledProcessError:
        print_warning("Failed to initialize git repository (git not available?)")
    except Exception as e:
        print_warning(f"Failed to initialize git repository: {str(e)}")


def show_project_structure(project_path: Path) -> None:
    """Show created project structure"""

    console.print("\n[bold]Project structure:[/bold]")

    # Show tree structure
    structure = f"""
{project_path.name}/
├── .deploy-tool.yaml      # Project configuration
├── .gitignore            # Git ignore rules
├── deployment/           # Deployment artifacts
│   ├── manifests/       # Component manifests
│   ├── package-configs/ # Packaging configurations
│   └── releases/        # Release records
├── dist/                # Package output (git ignored)
└── src/                 # Source code
    """

    console.print(structure)