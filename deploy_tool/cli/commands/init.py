"""Project initialization command"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm

from ..decorators import ensure_no_project
from ...core import ProjectManager
from ...utils.async_utils import run_async

console = Console()


@click.command()
@click.argument('project_path', type=click.Path(), default='.')
@click.option('--name', help='Project name')
@click.option('--type', 'project_type',
              type=click.Choice(['algorithm', 'model', 'service', 'general']),
              default='algorithm',
              help='Project type')
@click.option('--description', help='Project description')
@click.option('--no-git', is_flag=True, help='Skip git initialization')
@click.option('--force', is_flag=True, help='Force initialization even if directory is not empty')
@click.pass_context
@ensure_no_project
def init(ctx, project_path, name, project_type, description, no_git, force):
    """Initialize a new deployment project

    This command creates a new project with the standard directory structure
    and configuration files needed for deployment.

    Examples:

        # Initialize in current directory
        deploy-tool init

        # Initialize with specific name
        deploy-tool init --name my-algo

        # Initialize in a new directory
        deploy-tool init ./my-new-project
    """
    project_path = Path(project_path).resolve()

    # Check if directory exists and has content
    if project_path.exists() and any(project_path.iterdir()) and not force:
        if not Confirm.ask(
                f"[yellow]Directory {project_path} is not empty. Continue?[/yellow]",
                default=False
        ):
            console.print("[red]Initialization cancelled[/red]")
            sys.exit(1)

    try:
        # Create project manager
        project_manager = ProjectManager()

        # Determine if interactive mode
        interactive = not all([name, description])

        # Initialize project - 使用 run_async 运行异步方法
        run_async(project_manager.init_project(
            project_path=project_path,
            project_name=name,
            project_type=project_type,
            description=description,
            interactive=interactive
        ))

        # Git initialization
        if not no_git and project_path.joinpath('.git').exists() is False:
            if Confirm.ask("\n[cyan]Initialize git repository?[/cyan]", default=True):
                from ...utils.git_utils import init_git_repo
                init_git_repo(project_path)
                console.print("[green]✓[/green] Git repository initialized")

        # Success message
        console.print(f"\n[green]✓[/green] Project initialized successfully at {project_path}")
        console.print("\n[cyan]Next steps:[/cyan]")
        console.print("1. cd " + str(project_path))
        console.print("2. deploy-tool pack <source> --type <type> --auto")
        console.print("3. deploy-tool publish --component <type>:<version>")

    except Exception as e:
        console.print(f"[red]Error initializing project:[/red] {e}")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)