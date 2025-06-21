# deploy_tool/templates/__init__.py
"""Built-in templates for deploy-tool"""

from pathlib import Path
from typing import Dict, Optional

# Template directory path
TEMPLATES_DIR = Path(__file__).parent


def get_template_path(category: str, name: str) -> Optional[Path]:
    """
    Get path to a template file

    Args:
        category: Template category (project, package, manifests)
        name: Template name

    Returns:
        Path to template file or None if not found
    """
    template_path = TEMPLATES_DIR / category / name

    if template_path.exists():
        return template_path

    return None


def load_template(category: str, name: str) -> Optional[str]:
    """
    Load template content

    Args:
        category: Template category
        name: Template name

    Returns:
        Template content or None if not found
    """
    template_path = get_template_path(category, name)

    if template_path:
        return template_path.read_text()

    return None


def list_templates() -> Dict[str, list]:
    """
    List all available templates

    Returns:
        Dictionary mapping categories to template names
    """
    templates = {}

    for category_dir in TEMPLATES_DIR.iterdir():
        if category_dir.is_dir() and not category_dir.name.startswith('_'):
            templates[category_dir.name] = []

            for template_file in category_dir.iterdir():
                if template_file.is_file() and not template_file.name.startswith('_'):
                    templates[category_dir.name].append(template_file.name)

    return templates


# Pre-load commonly used templates
PROJECT_CONFIG_TEMPLATE = "project/deploy-tool.yaml"
GITIGNORE_TEMPLATE = "project/gitignore"
PACKAGE_DEFAULT_TEMPLATE = "package/default.yaml"
PACKAGE_AUTO_TEMPLATE = "package/auto.yaml"
MANIFEST_SCHEMA_TEMPLATE = "manifests/schema.json"

__all__ = [
    'TEMPLATES_DIR',
    'get_template_path',
    'load_template',
    'list_templates',
    'PROJECT_CONFIG_TEMPLATE',
    'GITIGNORE_TEMPLATE',
    'PACKAGE_DEFAULT_TEMPLATE',
    'PACKAGE_AUTO_TEMPLATE',
    'MANIFEST_SCHEMA_TEMPLATE',
]