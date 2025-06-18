"""System diagnostic command"""

import os
import sys

import click
from rich import box
from rich.console import Console
from rich.table import Table

from ..decorators import require_project
from ...utils.git_utils import check_git_status

console = Console()


class DiagnosticCheck:
    """Base class for diagnostic checks"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.passed = False
        self.message = ""
        self.fixes = []

    async def run(self, ctx) -> 'DiagnosticCheck':
        """Run the diagnostic check"""
        raise NotImplementedError

    async def fix(self, ctx) -> bool:
        """Attempt to fix the issue"""
        return False


class ProjectStructureCheck(DiagnosticCheck):
    """Check project directory structure"""

    def __init__(self):
        super().__init__(
            "Project Structure",
            "Verify standard directory structure exists"
        )

    async def run(self, ctx):
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

    async def fix(self, ctx):
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

    async def run(self, ctx):
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

    async def fix(self, ctx):
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

    async def run(self, ctx):
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

    async def run(self, ctx):
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
async def doctor(ctx, fix, check):
    """Run system diagnostics

    This command checks the health of your deployment project and can
    automatically fix common issues.

    Examples:
        # Run all checks
        deploy-tool doctor

        # Run specific checks
        deploy-tool doctor --check git --check permissions

        # Auto-fix issues
        deploy-tool doctor --fix
    """
    console.print("[bold cyan]Deploy Tool Doctor[/bold cyan]")
    console.print(f"Project: {ctx.obj.project_root}\n")

    # Initialize checks
    all_checks = {
        'structure': ProjectStructureCheck(),
        'git': GitStatusCheck(),
        'storage': StorageAccessCheck(),
        'permissions': PermissionsCheck()
    }

    # Determine which checks to run
    if 'all' in check:
        checks_to_run = list(all_checks.values())
    else:
        checks_to_run = [all_checks[c] for c in check if c in all_checks]

    # Run checks
    results = []
    for diagnostic_check in checks_to_run:
        with console.status(f"Checking {diagnostic_check.name}..."):
            result = await diagnostic_check.run(ctx)
            results.append(result)

    # Display results
    table = Table(title="Diagnostic Results", box=box.ROUNDED)
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    issues_found = False
    fixable_issues = []

    for result in results:
        status = "[green]✓ PASS[/green]" if result.passed else "[red]✗ FAIL[/red]"
        table.add_row(result.name, status, result.message)

        if not result.passed:
            issues_found = True
            if result.fixes:
                fixable_issues.append(result)

    console.print(table)

    # Handle fixes
    if fixable_issues and fix:
        console.print("\n[yellow]Attempting to fix issues...[/yellow]")

        for issue in fixable_issues:
            console.print(f"\nFixing: {issue.name}")
            for fix_desc in issue.fixes:
                console.print(f"  • {fix_desc}")

            try:
                success = await issue.fix(ctx)
                if success:
                    console.print(f"  [green]✓ Fixed[/green]")
                else:
                    console.print(f"  [red]✗ Could not fix automatically[/red]")
            except Exception as e:
                console.print(f"  [red]✗ Error: {e}[/red]")

    elif fixable_issues and not fix:
        console.print("\n[yellow]Issues found that can be fixed automatically.[/yellow]")
        console.print("Run 'deploy-tool doctor --fix' to attempt fixes.")

    # Summary
    if not issues_found:
        console.print("\n[green]✓ All checks passed! Your project is healthy.[/green]")
    else:
        console.print("\n[red]✗ Some issues were found. Please review the results above.[/red]")
        sys.exit(1)