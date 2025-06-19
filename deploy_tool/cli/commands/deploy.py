"""Deploy command implementation"""

import sys

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from ..decorators import require_project, dual_mode_command
from ..utils.output import format_deploy_result
from ...api import Deployer
from ...api.exceptions import DeployError, ReleaseNotFoundError, ComponentNotFoundError
from ...utils.async_utils import run_async

console = Console()


@click.command()
@click.option('--release', help='Deploy a release version')
@click.option('--component', help='Deploy a single component (format: type:version)')
@click.option('--target', required=True, help='Deployment target (path or server name)')
@click.option('--env', type=click.Choice(['dev', 'staging', 'production']),
              help='Target environment')
@click.option('--verify', is_flag=True, default=True, help='Verify after deployment')
@click.option('--rollback', is_flag=True, help='Enable rollback on failure')
@click.option('--force', is_flag=True, help='Force deployment even if already deployed')
@click.option('--dry-run', is_flag=True, help='Simulate deployment')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
@require_project
@dual_mode_command
def deploy(ctx, release, component, target, env, verify, rollback,
           force, dry_run, no_confirm):
    """Deploy components to target environment

    Deploy packaged components or complete releases to local directories
    or remote servers. Supports verification and rollback.

    Examples:

        # Deploy release version
        deploy-tool deploy --release 2024.01.20 --target production

        # Deploy to local directory
        deploy-tool deploy --release 2024.01.20 --target ~/deployments/

        # Deploy single component
        deploy-tool deploy --component model:1.0.1 --target dev-server

        # Deploy with rollback enabled
        deploy-tool deploy --release 2024.01.20 --target production --rollback
    """
    try:
        # Validate arguments
        if not release and not component:
            console.print("[red]Error: Must specify --release or --component[/red]")
            sys.exit(1)

        if release and component:
            console.print("[red]Error: Cannot specify both --release and --component[/red]")
            sys.exit(1)

        # Show confirmation
        if not no_confirm and not dry_run:
            if release:
                console.print(f"Deploy release: [bold]{release}[/bold]")
            else:
                console.print(f"Deploy component: [bold]{component}[/bold]")

            console.print(f"Target: [cyan]{target}[/cyan]")
            if env:
                console.print(f"Environment: [yellow]{env}[/yellow]")

            options = []
            if verify:
                options.append("verify")
            if rollback:
                options.append("rollback on failure")
            if force:
                options.append("force")

            if options:
                console.print(f"Options: {', '.join(options)}")

            if not Confirm.ask("\n[cyan]Proceed with deployment?[/cyan]"):
                console.print("[yellow]Deployment cancelled[/yellow]")
                sys.exit(0)

        # Dry run mode
        if dry_run:
            console.print("[yellow]Dry run mode - no actual deployment[/yellow]")
            return

        # Create deployer
        target_config = {}
        if env:
            target_config['environment'] = env

        deployer = Deployer(target_config=target_config)

        # Execute deployment
        if release:
            result = run_async(deployer.deploy_release_async(
                release_version=release,
                target=target,
                verify=verify,
                rollback_on_failure=rollback
            ))
        else:
            # Parse component spec
            comp_type, comp_version = component.split(':', 1)
            result = run_async(deployer.deploy_component_async(
                component_type=comp_type,
                component_version=comp_version,
                target=target,
                verify=verify
            ))

        # Display result
        format_deploy_result(result)

    except (DeployError, ReleaseNotFoundError, ComponentNotFoundError) as e:
        console.print(f"[red]Deployment error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)