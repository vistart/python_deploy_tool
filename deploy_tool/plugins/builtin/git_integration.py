"""Git integration plugin"""

from pathlib import Path
from typing import List, Dict, Any

from ..base import Plugin, PluginInfo, PluginContext, PluginPriority, HookPoint
from ...utils.git_utils import (
    get_git_info,
    check_git_status,
    get_uncommitted_files,
    suggest_git_commands
)


class GitIntegrationPlugin(Plugin):
    """Provides Git integration and automation suggestions"""

    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="git-integration",
            version="1.0.0",
            description="Git integration for deployment workflows",
            author="Deploy Tool Team",
            priority=PluginPriority.HIGH,
            hook_points=[
                HookPoint.PROJECT_INIT_POST,
                HookPoint.PACK_POST,
                HookPoint.PUBLISH_PRE,
                HookPoint.PUBLISH_POST,
            ]
        )

    async def on_project_init_post(self, context: PluginContext) -> PluginContext:
        """Add Git-related files after project initialization"""
        project_path = Path(context.data.get('project_path', '.'))

        # Check if Git is initialized
        git_info = get_git_info(project_path)

        if not git_info['is_git_repo']:
            context.add_warning(
                "Project is not a Git repository. Consider running 'git init'"
            )
        else:
            # Add deployment directories to gitignore if needed
            gitignore_path = project_path / '.gitignore'
            if gitignore_path.exists():
                self._update_gitignore(gitignore_path)

        return context

    async def on_pack_post(self, context: PluginContext) -> PluginContext:
        """Suggest Git operations after packing"""
        manifest_path = context.data.get('manifest_path')

        if manifest_path:
            # Check Git status
            project_root = Path(manifest_path).parent.parent.parent  # Go up to project root
            git_status = check_git_status(project_root)

            if git_status['is_git_repo']:
                # Check if manifest is tracked
                relative_manifest = Path(manifest_path).relative_to(project_root)
                uncommitted = get_uncommitted_files(project_root)

                if str(relative_manifest) in uncommitted:
                    # Add Git suggestions to context
                    suggestions = suggest_git_commands(manifest_path, "pack")
                    context.metadata['git_suggestions'] = suggestions

                    self.logger.info(
                        f"New manifest created: {relative_manifest}. "
                        "Remember to commit it to Git."
                    )

        return context

    async def on_publish_pre(self, context: PluginContext) -> PluginContext:
        """Check Git status before publishing"""
        # Get project root
        project_root = context.data.get('project_root', Path.cwd())

        # Check for uncommitted changes
        git_status = check_git_status(project_root)

        if git_status['is_git_repo'] and git_status['has_uncommitted']:
            uncommitted_count = git_status.get('uncommitted_count', 0)

            # Add warning but don't block
            context.add_warning(
                f"You have {uncommitted_count} uncommitted changes. "
                "Consider committing before publishing."
            )

            # List critical uncommitted files
            uncommitted = get_uncommitted_files(project_root)
            manifest_files = [f for f in uncommitted if f.endswith('.manifest.json')]

            if manifest_files:
                context.add_warning(
                    f"Uncommitted manifests: {', '.join(manifest_files)}"
                )

        return context

    async def on_publish_post(self, context: PluginContext) -> PluginContext:
        """Suggest Git operations after publishing"""
        release_manifest = context.data.get('release_manifest_path')

        if release_manifest:
            # Add Git suggestions
            suggestions = suggest_git_commands(release_manifest, "publish")
            context.metadata['git_suggestions'] = suggestions

            # Tag suggestion
            release_version = context.data.get('release_version')
            if release_version:
                tag_command = f"git tag -a v{release_version} -m 'Release {release_version}'"
                context.metadata['git_tag_suggestion'] = tag_command

        return context

    def _update_gitignore(self, gitignore_path: Path) -> None:
        """Update .gitignore with deployment-specific patterns"""
        patterns_to_add = [
            "# Deploy Tool",
            "/dist/",
            "*.tar.gz",
            "*.tar.bz2",
            "*.tar.xz",
            ".deploy-tool-cache/",
            "",  # Empty line
        ]

        try:
            with open(gitignore_path, 'r') as f:
                content = f.read()

            # Check if patterns already exist
            needs_update = False
            for pattern in patterns_to_add[1:-1]:  # Skip comment and empty line
                if pattern and pattern not in content:
                    needs_update = True
                    break

            if needs_update:
                # Append patterns
                with open(gitignore_path, 'a') as f:
                    if not content.endswith('\n'):
                        f.write('\n')
                    f.write('\n'.join(patterns_to_add))

                self.logger.info("Updated .gitignore with deployment patterns")

        except Exception as e:
            self.logger.warning(f"Failed to update .gitignore: {e}")