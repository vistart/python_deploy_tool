"""Git advisor for providing Git operation suggestions"""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel

from .manifest_engine import ManifestEngine
from .path_resolver import PathResolver


class GitAdvisor:
    """Provide Git operation suggestions"""

    def __init__(self, path_resolver: Optional[PathResolver] = None):
        self.path_resolver = path_resolver or PathResolver()
        self.console = Console()

    def provide_post_pack_advice(self,
                                 manifest_path: Path,
                                 config_path: Optional[Path] = None) -> None:
        """
        Provide Git advice after packing

        Args:
            manifest_path: Generated manifest file path
            config_path: Generated config file path (optional)
        """
        self.console.print("\n[bold green]Git Operation Suggestions:[/bold green]")
        self.console.print("-" * 50)

        # Basic suggestions
        self.console.print("# 1. Check generated files")
        self.console.print("   [cyan]git status[/cyan]\n")

        # Manifest file (always important)
        rel_manifest = self.path_resolver.get_relative_to_root(manifest_path)
        self.console.print("# 2. Add manifest file (IMPORTANT!)")
        self.console.print(f"   [cyan]git add {rel_manifest}[/cyan]\n")

        # Config file if new
        if config_path and self.is_new_file(config_path):
            rel_config = self.path_resolver.get_relative_to_root(config_path)
            self.console.print("# 3. Add auto-generated config file")
            self.console.print(f"   [cyan]git add {rel_config}[/cyan]\n")
            step = 4
        else:
            step = 3

        # Extract info from manifest
        try:
            engine = ManifestEngine(self.path_resolver)
            manifest = engine.load_manifest(manifest_path)
            version = manifest.package.get('version', 'unknown')
            package_type = manifest.package.get('type', 'package')
        except:
            version = 'unknown'
            package_type = 'package'

        # Commit suggestion
        self.console.print(f"# {step}. Commit changes")
        self.console.print(f'   [cyan]git commit -m "Add {package_type} {version} manifest"[/cyan]\n')
        step += 1

        # Branch and push suggestions
        current_branch = self.get_current_branch()
        if current_branch and self.is_feature_branch(current_branch):
            self.console.print(f"# {step}. Push to remote branch")
            self.console.print(f"   [cyan]git push origin {current_branch}[/cyan]\n")
            step += 1

            # PR suggestion
            pr_url = self.get_pr_url()
            if pr_url:
                self.console.print(f"# {step}. Create Pull Request")
                self.console.print(f"   Visit: {pr_url}\n")
        else:
            self.console.print(f"# {step}. Create feature branch (recommended)")
            branch_name = f"feature/update-{package_type}-{version}".replace('.', '-')
            self.console.print(f"   [cyan]git checkout -b {branch_name}[/cyan]")
            self.console.print(f"   [cyan]git push origin {branch_name}[/cyan]\n")

        self.console.print("[yellow]Note:[/yellow] The tool does not automatically execute Git operations.")
        self.console.print("      Please decide based on your team's workflow.")
        self.console.print("      Code files are managed through Git, not packaged.")

    def provide_post_publish_advice(self,
                                    release_version: str,
                                    manifest_paths: List[Path]) -> None:
        """
        Provide Git advice after publishing

        Args:
            release_version: Release version
            manifest_paths: List of component manifest paths
        """
        self.console.print("\n[bold green]Git Operation Suggestions:[/bold green]")
        self.console.print("-" * 50)

        # Release manifest
        release_manifest = self.path_resolver.get_release_path(release_version)
        if release_manifest.exists():
            rel_path = self.path_resolver.get_relative_to_root(release_manifest)
            self.console.print("# 1. Add release manifest")
            self.console.print(f"   [cyan]git add {rel_path}[/cyan]\n")

            self.console.print("# 2. Commit release")
            self.console.print(f'   [cyan]git commit -m "Release version {release_version}"[/cyan]\n')

            self.console.print("# 3. Tag release")
            self.console.print(f"   [cyan]git tag -a v{release_version} -m \"Release {release_version}\"[/cyan]\n")

            self.console.print("# 4. Push with tags")
            self.console.print(f"   [cyan]git push origin --tags[/cyan]\n")

    def check_git_status(self) -> Dict[str, Any]:
        """
        Check current Git status

        Returns:
            Dictionary with Git status info
        """
        status = {
            'is_git_repo': False,
            'has_changes': False,
            'untracked_files': [],
            'modified_files': [],
            'branch': None,
            'ahead': 0,
            'behind': 0
        }

        git_dir = self.path_resolver.project_root / ".git"
        if not git_dir.exists():
            return status

        status['is_git_repo'] = True

        try:
            # Get current branch
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.path_resolver.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            status['branch'] = result.stdout.strip()

            # Get status
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.path_resolver.project_root,
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.splitlines():
                if line.startswith('??'):
                    status['untracked_files'].append(line[3:])
                elif line.startswith(' M'):
                    status['modified_files'].append(line[3:])

            status['has_changes'] = bool(status['untracked_files'] or status['modified_files'])

            # Get ahead/behind
            result = subprocess.run(
                ['git', 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}'],
                cwd=self.path_resolver.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    status['ahead'] = int(parts[0])
                    status['behind'] = int(parts[1])

        except subprocess.CalledProcessError:
            pass

        return status

    def is_new_file(self, file_path: Path) -> bool:
        """Check if file is new (untracked)"""
        try:
            result = subprocess.run(
                ['git', 'ls-files', '--error-unmatch', str(file_path)],
                cwd=self.path_resolver.project_root,
                capture_output=True,
                text=True
            )
            # If exit code is 0, file is tracked
            return result.returncode != 0
        except:
            return True

    def get_current_branch(self) -> Optional[str]:
        """Get current Git branch"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.path_resolver.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return None

    def is_feature_branch(self, branch_name: Optional[str] = None) -> bool:
        """Check if current branch is a feature branch"""
        if branch_name is None:
            branch_name = self.get_current_branch()

        if not branch_name:
            return False

        # Common main branch names
        main_branches = ['main', 'master', 'develop', 'dev']

        return branch_name not in main_branches

    def get_pr_url(self) -> Optional[str]:
        """Get PR URL based on remote"""
        try:
            # Get remote URL
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=self.path_resolver.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()

            # Convert to PR URL
            if 'github.com' in remote_url:
                # GitHub
                if remote_url.startswith('git@'):
                    parts = remote_url.replace('git@github.com:', '').replace('.git', '')
                    return f"https://github.com/{parts}/pull/new"
                elif remote_url.startswith('https://'):
                    parts = remote_url.replace('https://github.com/', '').replace('.git', '')
                    return f"https://github.com/{parts}/pull/new"
            elif 'gitlab' in remote_url:
                # GitLab
                if remote_url.startswith('git@'):
                    parts = remote_url.split(':')[1].replace('.git', '')
                    host = remote_url.split('@')[1].split(':')[0]
                    return f"https://{host}/{parts}/-/merge_requests/new"

        except:
            pass

        return None

    def show_git_workflow_guide(self) -> None:
        """Show Git workflow guide"""
        guide = """
[bold cyan]Deploy Tool Git Workflow Guide[/bold cyan]

[yellow]1. Before Packaging:[/yellow]
   - Ensure you're on a feature branch
   - Commit all code changes

[yellow]2. After Packaging:[/yellow]
   - Add generated manifest files to Git
   - Commit with descriptive message
   - Push to remote branch

[yellow]3. After Publishing:[/yellow]
   - Add release manifest to Git
   - Create Git tag for release
   - Push tags to remote

[yellow]4. Best Practices:[/yellow]
   - Keep manifests in version control
   - Use semantic versioning
   - Write clear commit messages
   - Create PRs for review

[yellow]5. Important Notes:[/yellow]
   - Code is managed by Git, not packaged
   - Manifests track non-code resources
   - Always commit manifests after packaging
        """

        self.console.print(Panel(guide, title="Git Workflow", border_style="cyan"))

    def suggest_gitignore_updates(self) -> List[str]:
        """Suggest .gitignore updates"""
        suggestions = []

        gitignore_path = self.path_resolver.project_root / ".gitignore"

        if gitignore_path.exists():
            content = gitignore_path.read_text()

            # Check for dist directory
            if '/dist/' not in content and 'dist/' not in content:
                suggestions.append("Add 'dist/' to ignore packaged files")

            # Check for cache
            if '.deploy-tool-cache' not in content:
                suggestions.append("Add '.deploy-tool-cache/' to ignore cache")

            # Check for common patterns
            patterns = ['*.tar.gz', '*.tar.bz2', '*.tar.xz', '*.tar.lz4']
            for pattern in patterns:
                if pattern not in content:
                    suggestions.append(f"Add '{pattern}' to ignore archive files")
        else:
            suggestions.append("Create .gitignore file with deploy-tool patterns")

        return suggestions

    def extract_version_from_manifest(self, manifest_path: Path) -> str:
        """Extract version from manifest file"""
        try:
            engine = ManifestEngine(self.path_resolver)
            manifest = engine.load_manifest(manifest_path)
            return manifest.package.get('version', 'unknown')
        except:
            return 'unknown'

    def extract_type_from_manifest(self, manifest_path: Path) -> str:
        """Extract type from manifest file"""
        try:
            engine = ManifestEngine(self.path_resolver)
            manifest = engine.load_manifest(manifest_path)
            return manifest.package.get('type', 'package')
        except:
            return 'package'