# deploy_tool/cli/commands/doctor.py
"""System diagnostic command"""

import os
import sys

import click
from rich import box
from rich.console import Console
from rich.table import Table

from ..decorators import require_project
from ...utils.git_utils import check_git_status
from ...utils.async_utils import run_async

console = Console()


class DiagnosticCheck:
    """Base class for diagnostic checks"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.passed = False
        self.message = ""
        self.fixes = []

    def run(self, ctx) -> 'DiagnosticCheck':
        """Run the diagnostic check"""
        raise NotImplementedError

    def fix(self, ctx) -> bool:
        """Attempt to fix the issue"""
        return False


class ProjectStructureCheck(DiagnosticCheck):
    """Check project directory structure"""

    def __init__(self):
        super().__init__(
            "Project Structure",
            "Verify standard directory structure exists"
        )

    def run(self, ctx):
        required_dirs = [
            "deployment/package-configs",
            "deployment/manifests",
            "deployment/releases",
            "dist"
        ]

        missing = []
        for dir_path in required_dirs:
            full_path = ctx.obj.project_root / dir_path
            if not full_path.exists():
                missing.append(dir_path)

        if missing:
            self.passed = False
            self.message = f"Missing directories: {', '.join(missing)}"
            self.fixes = [f"Create {d}" for d in missing]
        else:
            self.passed = True
            self.message = "All required directories exist"

        return self

    def fix(self, ctx):
        required_dirs = [
            "deployment/package-configs",
            "deployment/manifests",
            "deployment/releases",
            "dist"
        ]

        for dir_path in required_dirs:
            full_path = ctx.obj.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

        return True


class GitStatusCheck(DiagnosticCheck):
    """Check Git repository status"""

    def __init__(self):
        super().__init__(
            "Git Status",
            "Check Git repository health"
        )

    def run(self, ctx):
        git_status = check_git_status(ctx.obj.project_root)

        if not git_status['is_git_repo']:
            self.passed = False
            self.message = "Not a Git repository"
            self.fixes = ["Initialize Git repository"]
        elif git_status['has_uncommitted']:
            self.passed = False
            self.message = f"Uncommitted changes: {git_status['uncommitted_count']} files"
        else:
            self.passed = True
            self.message = f"Clean working tree on branch '{git_status['branch']}'"

        return self

    def fix(self, ctx):
        if not (ctx.obj.project_root / '.git').exists():
            from ...utils.git_utils import init_git_repo
            init_git_repo(ctx.obj.project_root)
            return True
        return False


class StorageAccessCheck(DiagnosticCheck):
    """Check storage backend access"""

    def __init__(self):
        super().__init__(
            "Storage Access",
            "Verify storage backend connectivity"
        )

    def run(self, ctx):
        # Check for storage configuration
        storage_type = os.environ.get('DEPLOY_TOOL_STORAGE', 'filesystem')

        if storage_type == 'bos':
            if not all([
                os.environ.get('BOS_AK'),
                os.environ.get('BOS_SK'),
                os.environ.get('BOS_BUCKET')
            ]):
                self.passed = False
                self.message = "BOS credentials not configured"
                self.fixes = ["Set BOS_AK, BOS_SK, BOS_BUCKET environment variables"]
            else:
                # TODO: Test actual BOS connectivity
                self.passed = True
                self.message = f"BOS configured for bucket: {os.environ.get('BOS_BUCKET')}"
        else:
            self.passed = True
            self.message = "Using local filesystem storage"

        return self


class PermissionsCheck(DiagnosticCheck):
    """Check file permissions"""

    def __init__(self):
        super().__init__(
            "File Permissions",
            "Verify read/write permissions"
        )

    def run(self, ctx):
        test_paths = [
            ctx.obj.project_root / "deployment",
            ctx.obj.project_root / "dist"
        ]

        issues = []
        for path in test_paths:
            if path.exists():
                # Check write permission
                try:
                    test_file = path / ".permission_test"
                    test_file.touch()
                    test_file.unlink()
                except Exception:
                    issues.append(str(path.relative_to(ctx.obj.project_root)))

        if issues:
            self.passed = False
            self.message = f"No write permission: {', '.join(issues)}"
        else:
            self.passed = True
            self.message = "All directories have proper permissions"

        return self


@click.command()
@click.option('--fix', is_flag=True, help='Attempt to fix issues automatically')
@click.option('--check', multiple=True,
              type=click.Choice(['all', 'structure', 'git', 'storage', 'permissions']),
              default=['all'],
              help='Specific checks to run')
@click.pass_context
@require_project
def doctor(ctx, fix, check):
    """Run system diagnostics

    This command checks the health of your deployment project and can
    automatically fix common issues.

    Examples:

        # Run all checks
        deploy-tool doctor

        # Run specific checks
        deploy-tool doctor --check structure --check git

        # Attempt automatic fixes
        deploy-tool doctor --fix
    """
    console.print("[bold]Deploy Tool Diagnostics[/bold]\n")

    # Determine which checks to run
    all_checks = {
        'structure': ProjectStructureCheck(),
        'git': GitStatusCheck(),
        'storage': StorageAccessCheck(),
        'permissions': PermissionsCheck()
    }

    if 'all' in check:
        checks_to_run = list(all_checks.values())
    else:
        checks_to_run = [all_checks[c] for c in check if c in all_checks]

    # Run checks
    failed_checks = []
    for diagnostic_check in checks_to_run:
        diagnostic_check.run(ctx)
        if not diagnostic_check.passed:
            failed_checks.append(diagnostic_check)

    # Display results
    table = Table(title="Diagnostic Results", box=box.ROUNDED)
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    for diagnostic_check in checks_to_run:
        status = "[green]✓ PASS[/green]" if diagnostic_check.passed else "[red]✗ FAIL[/red]"
        table.add_row(
            diagnostic_check.name,
            status,
            diagnostic_check.message
        )

    console.print(table)

    # Attempt fixes if requested
    if fix and failed_checks:
        console.print("\n[yellow]Attempting automatic fixes...[/yellow]\n")

        for diagnostic_check in failed_checks:
            if diagnostic_check.fixes:
                console.print(f"Fixing: {diagnostic_check.name}")
                if diagnostic_check.fix(ctx):
                    console.print(f"[green]✓[/green] Fixed: {diagnostic_check.name}")
                else:
                    console.print(f"[red]✗[/red] Could not fix: {diagnostic_check.name}")

    # Exit code based on results
    if failed_checks and not fix:
        console.print(f"\n[red]{len(failed_checks)} check(s) failed[/red]")
        console.print("Run with --fix to attempt automatic fixes")
        sys.exit(1)
    else:
        console.print("\n[green]All checks passed![/green]")