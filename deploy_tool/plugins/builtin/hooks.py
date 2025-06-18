"""Lifecycle hooks plugin for custom scripts"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..base import Plugin, PluginInfo, PluginContext, PluginPriority, HookPoint


class LifecycleHooksPlugin(Plugin):
    """Execute custom scripts at various lifecycle points"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Hook scripts configuration
        self.hooks_dir = Path(config.get('hooks_dir', '.deploy-tool/hooks')) if config else Path('.deploy-tool/hooks')
        self.timeout = config.get('timeout', 300) if config else 300  # 5 minutes default
        self.enabled_hooks = config.get('enabled_hooks', []) if config else []

    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="lifecycle-hooks",
            version="1.0.0",
            description="Execute custom scripts at lifecycle points",
            author="Deploy Tool Team",
            priority=PluginPriority.LOW,  # Run after other plugins
            hook_points=list(HookPoint),  # Register for all hooks
            config=self.config
        )

    async def handle_hook(self, context: PluginContext) -> PluginContext:
        """Execute scripts for any hook point"""
        hook_name = context.hook_point.value

        # Check if hook is enabled
        if self.enabled_hooks and hook_name not in self.enabled_hooks:
            return context

        # Find hook scripts
        scripts = self._find_hook_scripts(hook_name)

        for script in scripts:
            try:
                self.logger.info(f"Executing hook script: {script}")
                success = await self._execute_script(script, context)

                if not success:
                    context.add_warning(f"Hook script failed: {script}")

            except Exception as e:
                self.logger.error(f"Error executing hook script {script}: {e}")
                context.add_error(f"Hook script error: {str(e)}")

        return context

    def _find_hook_scripts(self, hook_name: str) -> List[Path]:
        """Find scripts for a specific hook"""
        scripts = []

        # Look in project-specific hooks directory
        if self.hooks_dir.exists():
            # Convert hook.point.name to hook-point-name format
            script_prefix = hook_name.replace('.', '-')

            # Find all matching scripts
            for ext in ['.sh', '.py', '.js', '']:
                script_path = self.hooks_dir / f"{script_prefix}{ext}"
                if script_path.exists() and script_path.is_file():
                    scripts.append(script_path)

            # Also look for numbered scripts (for ordering)
            for script in sorted(self.hooks_dir.glob(f"[0-9][0-9]-{script_prefix}*")):
                if script.is_file():
                    scripts.append(script)

        return sorted(scripts)

    async def _execute_script(self, script_path: Path, context: PluginContext) -> bool:
        """Execute a hook script"""
        # Prepare environment variables
        env = os.environ.copy()

        # Add context data as environment variables
        env['DEPLOY_TOOL_HOOK'] = context.hook_point.value
        env['DEPLOY_TOOL_OPERATION'] = context.operation

        # Add specific context data
        for key, value in context.data.items():
            if isinstance(value, (str, int, float, bool)):
                env_key = f"DEPLOY_TOOL_{key.upper()}"
                env[env_key] = str(value)

        # Determine how to execute the script
        if script_path.suffix == '.py':
            cmd = ['python', str(script_path)]
        elif script_path.suffix == '.js':
            cmd = ['node', str(script_path)]
        elif script_path.suffix == '.sh' or os.access(script_path, os.X_OK):
            cmd = [str(script_path)]
        else:
            # Try to execute as shell script
            cmd = ['sh', str(script_path)]

        try:
            # Execute script
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )

                # Log output
                if stdout:
                    self.logger.info(f"Hook output: {stdout.decode().strip()}")
                if stderr:
                    self.logger.warning(f"Hook error: {stderr.decode().strip()}")

                return process.returncode == 0

            except asyncio.TimeoutError:
                process.kill()
                self.logger.error(f"Hook script timed out after {self.timeout}s")
                return False

        except Exception as e:
            self.logger.error(f"Failed to execute hook script: {e}")
            return False

    def create_hook_template(self, hook_name: str, script_type: str = 'sh') -> Optional[Path]:
        """Create a template hook script"""
        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        # Create script name
        script_name = hook_name.replace('.', '-')
        script_path = self.hooks_dir / f"{script_name}.{script_type}"

        if script_path.exists():
            self.logger.warning(f"Hook script already exists: {script_path}")
            return None

        # Create template based on type
        if script_type == 'sh':
            template = f"""#!/bin/bash
# Hook: {hook_name}
# 
# Available environment variables:
# - DEPLOY_TOOL_HOOK: Current hook point
# - DEPLOY_TOOL_OPERATION: Current operation
# - DEPLOY_TOOL_*: Context data
#
# Exit with non-zero code to indicate failure

echo "Executing {hook_name} hook..."

# Your custom logic here

exit 0
"""
        elif script_type == 'py':
            template = f"""#!/usr/bin/env python3
\"\"\"Hook: {hook_name}\"\"\"

import os
import sys

# Get context from environment
hook = os.environ.get('DEPLOY_TOOL_HOOK')
operation = os.environ.get('DEPLOY_TOOL_OPERATION')

print(f"Executing {{hook}} hook...")

# Your custom logic here

sys.exit(0)
"""
        else:
            template = f"# Hook: {hook_name}\n"

        # Write template
        try:
            script_path.write_text(template)
            script_path.chmod(0o755)  # Make executable
            self.logger.info(f"Created hook template: {script_path}")
            return script_path
        except Exception as e:
            self.logger.error(f"Failed to create hook template: {e}")
            return None