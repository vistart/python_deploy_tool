"""Template processing utilities"""

import os
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def render_template(template: str,
                    variables: Dict[str, Any],
                    safe: bool = True) -> str:
    """
    Render template with variables

    Args:
        template: Template string
        variables: Variables to substitute
        safe: Use safe substitution (ignore missing vars)

    Returns:
        Rendered string
    """
    # Add common variables
    context = {
        'NOW': datetime.now().isoformat(),
        'DATE': datetime.now().strftime('%Y-%m-%d'),
        'TIME': datetime.now().strftime('%H:%M:%S'),
        'YEAR': str(datetime.now().year),
        'MONTH': str(datetime.now().month).zfill(2),
        'DAY': str(datetime.now().day).zfill(2),
        'USER': os.environ.get('USER', 'unknown'),
        'HOME': str(Path.home()),
    }

    # Add environment variables
    for key, value in os.environ.items():
        context[f'ENV_{key}'] = value

    # Override with provided variables
    context.update(variables)

    # Create template
    tmpl = string.Template(template)

    if safe:
        return tmpl.safe_substitute(context)
    else:
        return tmpl.substitute(context)


def load_template(template_path: Path) -> str:
    """
    Load template from file

    Args:
        template_path: Path to template file

    Returns:
        Template content

    Raises:
        FileNotFoundError: If template not found
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    return template_path.read_text(encoding='utf-8')


def get_template_path(name: str,
                      category: str = "default") -> Optional[Path]:
    """
    Get template file path

    Args:
        name: Template name
        category: Template category

    Returns:
        Path to template file or None
    """
    # Check user templates first
    user_template_dir = Path.home() / ".deploy-tool" / "templates" / category
    user_template = user_template_dir / f"{name}.yaml"

    if user_template.exists():
        return user_template

    # Check built-in templates
    import deploy_tool
    package_dir = Path(deploy_tool.__file__).parent
    builtin_template_dir = package_dir / "templates" / category
    builtin_template = builtin_template_dir / f"{name}.yaml"

    if builtin_template.exists():
        return builtin_template

    return None


def substitute_variables(data: Any,
                         variables: Dict[str, Any],
                         safe: bool = True) -> Any:
    """
    Recursively substitute variables in data structure

    Args:
        data: Data structure (dict, list, or string)
        variables: Variables to substitute
        safe: Use safe substitution

    Returns:
        Data with substituted variables
    """
    if isinstance(data, str):
        return render_template(data, variables, safe)

    elif isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Substitute in both key and value
            new_key = render_template(key, variables, safe) if isinstance(key, str) else key
            new_value = substitute_variables(value, variables, safe)
            result[new_key] = new_value
        return result

    elif isinstance(data, list):
        return [substitute_variables(item, variables, safe) for item in data]

    else:
        return data


def expand_path_template(path_template: str,
                         component_type: str,
                         version: str,
                         **kwargs) -> str:
    """
    Expand path template with component information

    Args:
        path_template: Path template string
        component_type: Component type
        version: Component version
        **kwargs: Additional variables

    Returns:
        Expanded path
    """
    variables = {
        'type': component_type,
        'component_type': component_type,
        'version': version,
        'major': version.split('.')[0] if '.' in version else version,
        'minor': version.split('.')[1] if version.count('.') >= 1 else '0',
        'patch': version.split('.')[2] if version.count('.') >= 2 else '0',
    }

    variables.update(kwargs)

    return render_template(path_template, variables)


def create_template_context(package_config: Dict[str, Any],
                            compression_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create template context from configuration

    Args:
        package_config: Package configuration
        compression_config: Compression configuration

    Returns:
        Template context dictionary
    """
    context = {
        'package.type': package_config.get('type', ''),
        'package.name': package_config.get('name', ''),
        'package.version': package_config.get('version', ''),
    }

    if compression_config:
        context['compression.algorithm'] = compression_config.get('algorithm', 'gzip')
        context['compression.level'] = str(compression_config.get('level', 6))

        # Add extension based on algorithm
        extensions = {
            'gzip': '.gz',
            'gz': '.gz',
            'bzip2': '.bz2',
            'bz2': '.bz2',
            'xz': '.xz',
            'lzma': '.xz',
            'lz4': '.lz4',
            'none': '',
        }
        algo = compression_config.get('algorithm', 'gzip').lower()
        context['compression.extension'] = extensions.get(algo, '.gz')

    return context


def merge_templates(base_template: Dict[str, Any],
                    override_template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two template dictionaries

    Args:
        base_template: Base template
        override_template: Override template

    Returns:
        Merged template
    """
    import copy

    result = copy.deepcopy(base_template)

    def deep_merge(target: dict, source: dict):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge(target[key], value)
            else:
                target[key] = copy.deepcopy(value)

    deep_merge(result, override_template)

    return result


def validate_template_syntax(template: str) -> Tuple[bool, Optional[str]]:
    """
    Validate template syntax

    Args:
        template: Template string

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Try to parse template
        tmpl = string.Template(template)
        # Try a safe substitute to check syntax
        tmpl.safe_substitute({})
        return True, None
    except Exception as e:
        return False, str(e)


from typing import Tuple