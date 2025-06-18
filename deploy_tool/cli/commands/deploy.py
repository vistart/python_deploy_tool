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
async def deploy(ctx, release, component, target, env, verify, rollback,
                 force, dry_run, no_confirm):
    """Deploy components to target environment

    Deploy packaged components or complete releases to local directories
    or remote servers. Supports verification and rollback.

    Examples:

        # Deploy a complete release
        deploy-tool deploy --release 2024.01.20 --target production

        # Deploy to local directory
        deploy-tool deploy --release 2024.01.20 --target ~/deployments/algo_a/

        # Deploy single component
        deploy-tool deploy --component model:1.0.1 --target ~/models/

        # Deploy with environment specification
        deploy-tool deploy --release 2024.01.20 --target server-01 --env production
    """
    # Validate inputs
    if not release and not component:
        console.print("[red]Error: Either --release or --component must be specified[/red]")
        sys.exit(1)

    if release and component:
        console.print("[red]Error: Cannot specify both --release and --component[/red]")
        sys.exit(1)

    try:
        # Create deployer
        deployer = Deployer(
            path_resolver=ctx.obj.path_resolver,
            environment=env
        )

        # Determine what to deploy
        if release:
            deploy_items = await deployer.get_release_components(release)
            deploy_type = f"Release {release}"
        else:
            comp_type, comp_version = component.split(':', 1)
            deploy_items = [(comp_type, comp_version)]
            deploy_type = f"Component {component}"

        # Show deployment plan
        if not no_confirm and not dry_run:
            table = Table(title=f"Deployment Plan: {deploy_type}")
            table.add_column("Component", style="cyan")
            table.add_column("Version", style="green")
            table.add_column("Target", style="yellow")

            for item in deploy_items:
                if isinstance(item, tuple):
                    table.add_row(item[0], item[1], target)
                else:
                    table.add_row(item.type, item.version, target)

            console.print(table)

            if env:
                console.print(f"Environment: [bold]{env}[/bold]")

            if not Confirm.ask("\n[cyan]Proceed with deployment?[/cyan]", default=True):
                console.print("[yellow]Deployment cancelled[/yellow]")
                sys.exit(0)

        # Execute deployment
        with console.status(f"[bold green]Deploying {deploy_type}...") as status:
            if release:
                result = await deployer.deploy_release(
                    release_version=release,
                    target=target,
                    verify=verify,
                    rollback_enabled=rollback,
                    force=force,
                    dry_run=dry_run
                )
            else:
                result = await deployer.deploy_component(
                    component_type=comp_type,
                    component_version=comp_version,
                    target=target,
                    verify=verify,
                    rollback_enabled=rollback,
                    force=force,
                    dry_run=dry_run
                )

        # Display results
        format_deploy_result(result)

        # Show post-deployment advice
        if result.success and not dry_run:
            console.print("\n[green]✓ Deployment completed successfully[/green]")

            if result.verification_results:
                console.print("\nVerification Results:")
                for check, status in result.verification_results.items():
                    icon = "✓" if status else "✗"
                    color = "green" if status else "red"
                    console.print(f"  [{color}]{icon}[/{color}] {check}")

    except ReleaseNotFoundError as e:
        console.print(f"[red]Release not found: {e}[/red]")
        console.print("\n[yellow]Hint:[/yellow] Use 'deploy-tool release list' to see available releases")
        sys.exit(1)
    except ComponentNotFoundError as e:
        console.print(f"[red]Component not found: {e}[/red]")
        console.print("\n[yellow]Hint:[/yellow] Use 'deploy-tool component list' to see available components")
        sys.exit(1)
    except DeployError as e:
        console.print(f"[red]Deploy error: {e}[/red]")
        if rollback and hasattr(e, 'rollback_performed') and e.rollback_performed:
            console.print("[yellow]Rollback was performed[/yellow]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Deployment cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)