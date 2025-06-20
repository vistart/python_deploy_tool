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
@click.option('--method', type=click.Choice(['filesystem', 'bos', 's3']),
              default='filesystem', help='Storage method to download from')
@click.option('--bucket', help='Storage bucket (for S3/BOS)')
@click.option('--releases-dir', help='Releases directory (for filesystem method)')
@click.option('--env', type=click.Choice(['dev', 'staging', 'production']),
              help='Target environment')
@click.option('--verify/--no-verify', default=True, help='Verify after deployment')
@click.option('--rollback/--no-rollback', default=True,
              help='Enable rollback on failure')
@click.option('--force', is_flag=True, help='Force deployment even if already deployed')
@click.option('--dry-run', is_flag=True, help='Simulate deployment')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
@require_project
@dual_mode_command
def deploy(ctx, release, component, target, method, bucket, releases_dir,
           env, verify, rollback, force, dry_run, no_confirm):
    """Deploy components to target environment

    Deploy packaged components or complete releases to local directories
    or remote servers. Supports automatic versioning with symbolic links
    for easy version switching.

    The deployment creates a versioned directory structure:

        target/
        ├── model -> releases/2024.01.20/model/1.0.0/
        ├── config -> releases/2024.01.20/config/1.0.0/
        └── releases/
            └── 2024.01.20/
                ├── model/1.0.0/
                ├── config/1.0.0/
                └── runtime/3.10.0/

    Examples:

<<<<<<< HEAD
        # Deploy release from filesystem
        deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod

        # Deploy from S3
        deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod \
            --method s3 --bucket my-releases
=======
        # Deploy release version
        deploy-tool deploy --release 2024.01.20 --target production

        # Deploy to local directory
        deploy-tool deploy --release 2024.01.20 --target ~/deployments/
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

        # Deploy single component
        deploy-tool deploy --component model:1.0.1 --target dev-server

<<<<<<< HEAD
        # Force redeployment
        deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod --force
=======
        # Deploy with rollback enabled
        deploy-tool deploy --release 2024.01.20 --target production --rollback
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
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

<<<<<<< HEAD
            table.add_row("Target", target)
            table.add_row("Method", method)

            if method != 'filesystem':
                table.add_row("Bucket", bucket or "Not specified")
            else:
                table.add_row("Releases Dir", releases_dir or "Default")

=======
            console.print(f"Target: [cyan]{target}[/cyan]")
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
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

            console.print("\n[yellow]Deployment will create:[/yellow]")
            console.print("• Versioned directories under releases/")
            console.print("• Symbolic links at top level for easy access")
            console.print("• Metadata file for tracking deployments")

            if not Confirm.ask("\n[cyan]Proceed with deployment?[/cyan]"):
                console.print("[yellow]Deployment cancelled[/yellow]")
                return

        # Configure storage for download
        storage_config = {}
        if method != 'filesystem':
            if not bucket:
                console.print("[red]Error:[/red] --bucket required for cloud storage")
                sys.exit(1)
            storage_config['bucket'] = bucket
            storage_config['type'] = method
        else:
            if releases_dir:
                storage_config['releases_dir'] = releases_dir

        # Create deployer
        deployer = Deployer(storage_config=storage_config)

        # Build options
        options = {
            'verify': verify,
            'rollback_on_failure': rollback,
            'force': force,
            'dry_run': dry_run,
            'environment': env,
        }

        # Execute deployment
        console.print(f"\n[cyan]Deploying to {target}...[/cyan]")

        if release:
<<<<<<< HEAD
            result = deployer.deploy_release(
                release_version=release,
                target=target,
                **options
            )
        else:
            # Parse component spec
            parts = component.split(':')
            if len(parts) != 2:
                console.print(f"[red]Error:[/red] Invalid component format: {component}")
                sys.exit(1)

            from ...models import Component
            comp = Component(type=parts[0], version=parts[1])

            result = deployer.deploy_component(
                component=comp,
                target=target,
                **options
            )
=======
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
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

        # Display results
        if result.success:
            console.print("\n[green]✓ Deployment completed successfully![/green]")

            # Show deployed components
            if result.deployed_components:
                table = Table(title="Deployed Components")
                table.add_column("Type", style="cyan")
                table.add_column("Version", style="green")
                table.add_column("Status")

                for comp in result.deployed_components:
                    table.add_row(
                        comp.type,
                        comp.version,
                        "✓ Deployed"
                    )

                console.print(table)

            # Show deployment structure
            console.print("\n[bold]Deployment Structure:[/bold]")
            console.print(f"Target: {target}")

            if release:
                console.print(f"\nSymbolic links created:")
                for comp in result.deployed_components:
                    console.print(f"  {comp.type} -> releases/{release}/{comp.type}/{comp.version}/")

            # Show verification results
            if result.verification:
                if result.verification.success:
                    console.print("\n[green]✓ Deployment verification passed[/green]")
                else:
                    console.print("\n[red]✗ Deployment verification failed[/red]")
                    if result.verification.issues:
                        for issue in result.verification.issues:
                            console.print(f"  - {issue}")

            console.print(f"\n[dim]Duration: {result.duration:.2f}s[/dim]")

        else:
            console.print(f"\n[red]✗ Deployment failed: {result.error}[/red]")
            sys.exit(1)

    except (DeployError, ReleaseNotFoundError, ComponentNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Deployment cancelled[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if ctx.obj.debug:
            console.print_exception()
        sys.exit(1)


@click.command()
@click.option('--target', required=True, help='Deployment target')
@click.option('--release', required=True, help='Release version to switch to')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation')
@click.pass_context
@require_project
def switch_version(ctx, target, release, no_confirm):
    """Switch deployed version

    Switch to a different deployed release version using symbolic links.
    This allows instant version switching without re-deployment.

    Example:
        deploy-tool switch-version --target /opt/ml-apps/prod --release 2024.01.19
    """
    try:
        if not no_confirm:
            if not Confirm.ask(f"[cyan]Switch to version {release}?[/cyan]"):
                console.print("[yellow]Version switch cancelled[/yellow]")
                return

        # Create deployer
        deployer = Deployer()

        # Switch version
        console.print(f"\n[cyan]Switching to version {release}...[/cyan]")
        success = deployer.switch_version(target, release)

        if success:
            console.print(f"\n[green]✓ Successfully switched to version {release}![/green]")
        else:
            console.print(f"\n[red]✗ Failed to switch version[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@click.command()
@click.option('--target', required=True, help='Deployment target')
@click.pass_context
@require_project
def list_versions(ctx, target):
    """List deployed versions

    Show all deployed release versions at the target location.

    Example:
        deploy-tool list-versions --target /opt/ml-apps/prod
    """
    try:
        # Create deployer
        deployer = Deployer()

        # List versions
        versions = deployer.list_deployed_versions(target)

        if versions:
            console.print(f"\n[bold]Deployed versions at {target}:[/bold]")
            for version in versions:
                console.print(f"  • {version}")
        else:
            console.print(f"\n[yellow]No deployed versions found at {target}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)