"""Project management core functionality"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.project import Project, ProjectConfig
from ..models.config import Config
from ..constants import (
    PROJECT_CONFIG_FILE,
    DEFAULT_DEPLOYMENT_DIR,
    DEFAULT_MANIFESTS_DIR,
    DEFAULT_CONFIGS_DIR,
    DEFAULT_DIST_DIR,
    CONFIG_VERSION
)
from ..utils.file_utils import ensure_directory, atomic_write


class ProjectManager:
    """Manages deploy-tool projects"""

    def __init__(self, project_root: Path):
        """Initialize project manager

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.config_file = self.project_root / PROJECT_CONFIG_FILE

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        components: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Project:
        """Create a new project

        Args:
            name: Project name
            description: Project description
            components: Initial component definitions

        Returns:
            Created project
        """
        # Create project config
        config = ProjectConfig(
            name=name,
            root=self.project_root,
            description=description,
            components=components or {}
        )

        # Create directory structure
        self._create_project_structure()

        # Save initial configuration
        self._save_config(config)

        # Create project
        project = Project(
            config=config,
            manifests={},
            is_initialized=True
        )

        return project

    def load_project(self) -> Project:
        """Load existing project

        Returns:
            Loaded project

        Raises:
            FileNotFoundError: If project config not found
            ValueError: If config is invalid
        """
        if not self.config_file.exists():
            raise FileNotFoundError(f"Project config not found: {self.config_file}")

        # Load configuration
        config = self._load_config()

        # Load manifests
        manifests = self._load_manifests()

        # Create project
        project = Project(
            config=config,
            manifests=manifests,
            is_initialized=True
        )

        return project

    def save_project(self, project: Project) -> None:
        """Save project configuration

        Args:
            project: Project to save
        """
        self._save_config(project.config)

    def _create_project_structure(self) -> None:
        """Create standard project directory structure"""
        # Create directories
        dirs = [
            self.project_root / DEFAULT_DEPLOYMENT_DIR,
            self.project_root / DEFAULT_MANIFESTS_DIR,
            self.project_root / DEFAULT_CONFIGS_DIR,
            self.project_root / DEFAULT_DIST_DIR,
            self.project_root / "src"
        ]

        for dir_path in dirs:
            ensure_directory(dir_path)

        # Create .gitignore if it doesn't exist
        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            from ..constants import GIT_IGNORE_TEMPLATE
            gitignore_path.write_text(GIT_IGNORE_TEMPLATE)

    def _load_config(self) -> ProjectConfig:
        """Load project configuration from file

        Returns:
            Project configuration
        """
        # Read and expand environment variables
        with open(self.config_file, 'r') as f:
            content = f.read()

        # Expand environment variables
        content = os.path.expandvars(content)

        # Parse YAML
        data = yaml.safe_load(content)

        # Create full config
        config = Config.from_dict(data)

        # Extract project-specific config
        project_config = ProjectConfig(
            name=config.project_name,
            root=self.project_root,
            description=config.project_description,
            components=config.components,
            config=config
        )

        return project_config

    def _save_config(self, config: ProjectConfig) -> None:
        """Save project configuration to file

        Args:
            config: Project configuration
        """
        # Build full configuration
        if config.config:
            # Use existing full config
            full_config = config.config
            # Update project info
            full_config.project_name = config.name
            full_config.project_root = str(config.root)
            full_config.project_description = config.description
            full_config.components = config.components
        else:
            # Create minimal config
            full_config = {
                "version": CONFIG_VERSION,
                "project": {
                    "name": config.name,
                    "root": "${PROJECT_ROOT}",
                    "description": config.description
                },
                "components": config.components,
                "packaging": {
                    "compression": {
                        "algorithm": "gzip",
                        "level": 6
                    }
                },
                "publish": {
                    "default_targets": [],
                    "targets": {}
                },
                "deploy": {
                    "root": "${DEPLOY_ROOT:/opt/deployments}",
                    "source_priority": [],
                    "failover": {
                        "enabled": True,
                        "retry_count": 3,
                        "retry_delay": 5
                    }
                }
            }

        # Convert to dict if it's a Config object
        if hasattr(full_config, 'to_dict'):
            data = full_config.to_dict()
        else:
            data = full_config

        # Save with nice formatting
        yaml_content = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            width=80,
            indent=2
        )

        # Add header comment
        header = f"""# Deploy Tool Project Configuration
# Generated at: {datetime.utcnow().isoformat()}

"""

        atomic_write(self.config_file, header + yaml_content)

    def _load_manifests(self) -> Dict[str, Dict[str, Any]]:
        """Load all manifests from manifests directory

        Returns:
            Nested dict of component -> version -> manifest
        """
        manifests = {}
        manifests_dir = self.project_root / DEFAULT_MANIFESTS_DIR

        if not manifests_dir.exists():
            return manifests

        # Scan component directories
        for comp_dir in manifests_dir.iterdir():
            if comp_dir.is_dir():
                component_type = comp_dir.name
                manifests[component_type] = {}

                # Load manifest files
                for manifest_file in comp_dir.glob("*.json"):
                    try:
                        import json
                        with open(manifest_file, 'r') as f:
                            manifest_data = json.load(f)

                        # Extract version from manifest
                        if 'component' in manifest_data:
                            version = manifest_data['component'].get('version')
                            if version:
                                manifests[component_type][version] = manifest_data

                    except Exception:
                        # Skip invalid manifests
                        continue

        return manifests

    def add_component(
        self,
        component_type: str,
        path: str,
        description: Optional[str] = None
    ) -> None:
        """Add a component to the project

        Args:
            component_type: Type of component
            path: Component source path
            description: Component description
        """
        project = self.load_project()

        # Add component
        project.config.components[component_type] = {
            "path": path,
            "description": description or f"{component_type} component"
        }

        # Save project
        self.save_project(project)

    def remove_component(self, component_type: str) -> bool:
        """Remove a component from the project

        Args:
            component_type: Type of component

        Returns:
            True if removed, False if not found
        """
        project = self.load_project()

        if component_type in project.config.components:
            del project.config.components[component_type]
            self.save_project(project)
            return True

        return False

    def validate_project(self) -> List[str]:
        """Validate project structure and configuration

        Returns:
            List of validation issues
        """
        issues = []

        # Check config file
        if not self.config_file.exists():
            issues.append(f"Project config file not found: {PROJECT_CONFIG_FILE}")
            return issues

        # Try to load project
        try:
            project = self.load_project()
            issues.extend(project.validate())
        except Exception as e:
            issues.append(f"Failed to load project: {str(e)}")

        return issues