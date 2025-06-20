<<<<<<< Updated upstream
"""Interactive utilities for CLI commands"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.console import Console
=======
"""Interactive UI utilities for CLI"""

from typing import List, Optional, Any, Dict
>>>>>>> Stashed changes
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

<<<<<<< Updated upstream
from ...core import PathResolver, ManifestEngine, ComponentRegistry, ConfigGenerator
from ...models.component import PublishComponent
from ...models.config import PackageConfig, SourceConfig, CompressionConfig

console = Console()
=======
from .output import console
>>>>>>> Stashed changes


def select_from_list(
    title: str,
    items: List[str],
    default: Optional[str] = None,
    show_cancel: bool = True
) -> Optional[str]:
    """Select a single item from a list

    Args:
        title: Selection title
        items: List of items to choose from
        default: Default selection (item value or index)
        show_cancel: Whether to show cancel option

<<<<<<< Updated upstream
    def run(self, path_resolver: PathResolver) -> Dict[str, Any]:
        """Run interactive pack wizard"""
        self.console.print("\n[bold cyan]Package Configuration Wizard[/bold cyan]\n")

        # Get package type
        package_type = Prompt.ask(
            "Package type (e.g., model, config, runtime)",
            default="model"
        )

        # Get version
        version = Prompt.ask(
            "Version",
            default="1.0.0"
        )

        # Get source path
        source_path = Prompt.ask(
            "Source path (relative to project root)",
            default="."
        )

        # Validate source path
        abs_source = path_resolver.resolve(source_path)
        if not abs_source.exists():
            self.console.print(f"[red]Error: Path does not exist: {source_path}[/red]")
            raise ValueError(f"Invalid source path: {source_path}")

        # Get package name
        default_name = f"{path_resolver.project_root.name}_{package_type}"
        package_name = Prompt.ask(
            "Package name",
            default=default_name
        )

        # Get description
        description = Prompt.ask(
            "Description (optional)",
            default=""
        )

        # Compression settings
        self.console.print("\n[bold]Compression Settings:[/bold]")
        algorithm = Prompt.ask(
            "Algorithm",
            choices=["gzip", "bzip2", "xz", "lz4", "none"],
            default="gzip"
        )

        level = 6
        if algorithm != "none":
            level = int(Prompt.ask(
                "Compression level (1-9)",
                default="6"
            ))

        # Build configuration
        config = {
            'package': {
                'type': package_type,
                'name': package_name,
                'version': version,
                'description': description
            },
            'source': {
                'path': source_path
            },
            'compression': {
                'algorithm': algorithm,
                'level': level
            }
        }

        # Show summary
        self._show_summary(config)

        # Save config?
        save_config = Confirm.ask(
            "\nSave this configuration for future use?",
            default=True
        )

        if save_config:
            config_name = Prompt.ask(
                "Configuration name",
                default=f"{package_type}.yaml"
            )
            config['save_config'] = True
            config['config_path'] = f"deployment/package-configs/{config_name}"

        return config

    def _show_summary(self, config: Dict[str, Any]) -> None:
        """Show configuration summary"""
        table = Table(title="Package Configuration Summary")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        # Package info
        table.add_row("Type", config['package']['type'])
        table.add_row("Name", config['package']['name'])
        table.add_row("Version", config['package']['version'])
        table.add_row("Source", config['source']['path'])

        # Compression
        comp = config.get('compression', {})
        table.add_row(
            "Compression",
            f"{comp.get('algorithm', 'gzip')} (level {comp.get('level', 6)})"
        )

        # Save config
        if config.get('save_config'):
            table.add_row("Save to", config.get('config_path', 'N/A'))

        self.console.print(table)
=======
    Returns:
        Selected item or None if cancelled
    """
    if not items:
        return None

    console.print(f"\n[bold]{title}[/bold]")

    # Find default index
    default_idx = None
    if default:
        if default.isdigit() and 0 < int(default) <= len(items):
            default_idx = default
        elif default in items:
            default_idx = str(items.index(default) + 1)

    # Show options
    for i, item in enumerate(items, 1):
        console.print(f"  {i}. {item}")

    if show_cancel:
        console.print(f"  0. Cancel")

    # Get choice
    choices = [str(i) for i in range(len(items) + 1)]
    if not show_cancel:
        choices = choices[1:]

    choice = Prompt.ask(
        "Enter choice",
        choices=choices,
        default=default_idx or "1"
    )

    if choice == "0" and show_cancel:
        return None

    idx = int(choice) - 1
    return items[idx] if 0 <= idx < len(items) else None
>>>>>>> Stashed changes


def select_multiple_items(
    title: str,
    items: List[str],
    default_selection: Optional[List[int]] = None,
    min_selection: int = 0,
    max_selection: Optional[int] = None
) -> Optional[List[int]]:
    """Select multiple items from a list

    Args:
        title: Selection title
        items: List of items to choose from
        default_selection: List of default selected indices
        min_selection: Minimum number of selections required
        max_selection: Maximum number of selections allowed

<<<<<<< Updated upstream
    def select_components(self, path_resolver: PathResolver) -> List[PublishComponent]:
        """Interactive component selection"""
        # Initialize component registry
        manifest_engine = ManifestEngine(path_resolver)
        registry = ComponentRegistry(path_resolver, manifest_engine)

        # Get available components
        available = registry.list_components()

        if not available:
            self.console.print("[yellow]No components available for publishing[/yellow]")
            return []

        # Display available components
        self.console.print("\n[bold]Available components:[/bold]")
        table = Table()
        table.add_column("#", style="dim", width=3)
        table.add_column("Type", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Created", style="yellow")

        for i, comp in enumerate(available, 1):
            # Get component info
            info = registry.find_component(comp.type, comp.version)
            created_str = info.created_at.strftime("%Y-%m-%d %H:%M") if info else "Unknown"
            table.add_row(str(i), comp.type, comp.version, created_str)
=======
    Returns:
        List of selected indices or None if cancelled
    """
    if not items:
        return []

    selected = set(default_selection or [])

    while True:
        # Clear screen and show current selection
        console.clear()
        console.print(f"[bold]{title}[/bold]")
        console.print(f"(Space to toggle, Enter to confirm, q to cancel)\n")
>>>>>>> Stashed changes

        # Show items with selection status
        for i, item in enumerate(items):
            marker = "[green]✓[/green]" if i in selected else " "
            console.print(f"  {marker} {i + 1}. {item}")

<<<<<<< Updated upstream
        # Get user selection
        selection = Prompt.ask(
            "\nSelect components to publish (comma-separated numbers or 'all')",
            default="all"
        )

        if selection.lower() == 'all':
            return [PublishComponent(type=c.type, version=c.version) for c in available]

        # Parse selection
        selected = []
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            for idx in indices:
                if 0 <= idx < len(available):
                    comp = available[idx]
                    selected.append(PublishComponent(type=comp.type, version=comp.version))
        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection[/red]")
            return []

        return selected

    def get_release_info(self) -> Dict[str, str]:
        """Get release information interactively"""
        self.console.print("\n[bold]Release Information:[/bold]")

        # Get release version
        from datetime import datetime
        default_version = datetime.now().strftime("%Y.%m.%d")
        release_version = Prompt.ask(
            "Release version",
            default=default_version
        )

        # Get release name
        release_name = Prompt.ask(
            "Release name (optional)",
            default=""
        )

        # Get description
        description = Prompt.ask(
            "Release description (optional)",
            default=""
        )

        return {
            'version': release_version,
            'name': release_name,
            'description': description
        }
=======
        # Show selection count
        console.print(f"\nSelected: {len(selected)}")
        if min_selection > 0:
            console.print(f"Minimum required: {min_selection}")
        if max_selection:
            console.print(f"Maximum allowed: {max_selection}")

        # Get input
        console.print("\nCommands: [bold]space[/bold] (toggle), [bold]a[/bold] (all), [bold]n[/bold] (none), [bold]enter[/bold] (confirm), [bold]q[/bold] (cancel)")
        action = Prompt.ask("Action or number", default="")

        if action.lower() == 'q':
            return None

        elif action.lower() == 'a':
            # Select all
            if max_selection:
                selected = set(range(min(len(items), max_selection)))
            else:
                selected = set(range(len(items)))

        elif action.lower() == 'n':
            # Select none
            selected.clear()

        elif action == '' or action.lower() == 'enter':
            # Confirm selection
            if len(selected) < min_selection:
                console.print(f"\n[red]Please select at least {min_selection} items[/red]")
                Prompt.ask("Press Enter to continue")
                continue

            return sorted(list(selected))

        elif action.isdigit():
            # Toggle specific item
            idx = int(action) - 1
            if 0 <= idx < len(items):
                if idx in selected:
                    selected.remove(idx)
                else:
                    if max_selection and len(selected) >= max_selection:
                        console.print(f"\n[red]Maximum {max_selection} selections allowed[/red]")
                        Prompt.ask("Press Enter to continue")
                    else:
                        selected.add(idx)

        elif ' ' in action or ',' in action:
            # Multiple selections
            parts = action.replace(',', ' ').split()
            for part in parts:
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(items):
                        if idx not in selected and (not max_selection or len(selected) < max_selection):
                            selected.add(idx)


def create_selection_table(
    items: List[Dict[str, Any]],
    columns: List[Dict[str, str]],
    selected: Optional[List[int]] = None
) -> Table:
    """Create a table for selection display

    Args:
        items: List of items with data
        columns: Column definitions [{'key': 'field', 'title': 'Title', 'style': 'color'}]
        selected: List of selected indices

    Returns:
        Configured table
    """
    table = Table(show_header=True, header_style="bold")

    # Add selection column
    table.add_column("", width=3)

    # Add data columns
    for col in columns:
        table.add_column(
            col.get('title', col['key']),
            style=col.get('style', 'default')
        )

    # Add rows
    selected = selected or []
    for i, item in enumerate(items):
        marker = "[green]✓[/green]" if i in selected else " "

        row_data = [marker]
        for col in columns:
            value = item.get(col['key'], '')
            row_data.append(str(value))

        table.add_row(*row_data)

    return table


def confirm_action(
    message: str,
    default: bool = False,
    show_details: Optional[str] = None
) -> bool:
    """Confirm an action with optional details

    Args:
        message: Confirmation message
        default: Default answer
        show_details: Optional details to show

    Returns:
        True if confirmed, False otherwise
    """
    if show_details:
        console.print(Panel(show_details, title="Details", expand=False))

    return Confirm.ask(message, default=default)


def get_text_input(
    prompt: str,
    default: Optional[str] = None,
    password: bool = False,
    validator: Optional[callable] = None,
    allow_empty: bool = True
) -> Optional[str]:
    """Get text input with validation

    Args:
        prompt: Input prompt
        default: Default value
        password: Whether to mask input
        validator: Optional validation function
        allow_empty: Whether to allow empty input

    Returns:
        Input value or None
    """
    while True:
        value = Prompt.ask(
            prompt,
            default=default,
            password=password
        )

        # Check empty
        if not value and not allow_empty:
            console.print("[red]Value cannot be empty[/red]")
            continue

        # Validate
        if validator and value:
            try:
                if not validator(value):
                    console.print("[red]Invalid value[/red]")
                    continue
            except Exception as e:
                console.print(f"[red]Validation error: {e}[/red]")
                continue

        return value


def show_key_value_pairs(
    data: Dict[str, Any],
    title: Optional[str] = None,
    style: str = "default"
) -> None:
    """Display key-value pairs in a formatted way

    Args:
        data: Dictionary of key-value pairs
        title: Optional title
        style: Display style
    """
    if title:
        console.print(f"\n[bold]{title}[/bold]")

    # Calculate max key length for alignment
    max_key_len = max(len(str(k)) for k in data.keys()) if data else 0

    for key, value in data.items():
        key_str = f"{key}:".ljust(max_key_len + 1)

        # Format value based on type
        if isinstance(value, bool):
            value_str = "[green]Yes[/green]" if value else "[red]No[/red]"
        elif isinstance(value, (list, tuple)):
            value_str = ", ".join(str(v) for v in value)
        elif value is None:
            value_str = "[dim]Not set[/dim]"
        else:
            value_str = str(value)

        console.print(f"  {key_str} {value_str}")


def create_progress_steps(
    steps: List[str],
    current_step: int = 0
) -> None:
    """Show progress through a series of steps

    Args:
        steps: List of step descriptions
        current_step: Current step index (0-based)
    """
    console.print("\n[bold]Progress[/bold]")

    for i, step in enumerate(steps):
        if i < current_step:
            # Completed
            marker = "[green]✓[/green]"
            style = "dim"
        elif i == current_step:
            # Current
            marker = "[yellow]→[/yellow]"
            style = "bold yellow"
        else:
            # Pending
            marker = " "
            style = "dim"

        console.print(f"  {marker} {i + 1}. [{style}]{step}[/{style}]")


def show_diff(
    old_value: Any,
    new_value: Any,
    label: str = "Value"
) -> None:
    """Show difference between old and new values

    Args:
        old_value: Original value
        new_value: New value
        label: Value label
    """
    console.print(f"\n[bold]{label} Change:[/bold]")
    console.print(f"  [red]- {old_value}[/red]")
    console.print(f"  [green]+ {new_value}[/green]")


def create_tree_view(
    data: Dict[str, Any],
    title: Optional[str] = None,
    expanded: bool = True
) -> None:
    """Create a tree view of hierarchical data

    Args:
        data: Hierarchical data
        title: Optional title
        expanded: Whether to expand all nodes
    """
    from rich.tree import Tree

    def add_nodes(tree_node, data_node):
        """Recursively add nodes to tree"""
        if isinstance(data_node, dict):
            for key, value in data_node.items():
                if isinstance(value, (dict, list)) and value:
                    branch = tree_node.add(f"[bold]{key}[/bold]")
                    add_nodes(branch, value)
                else:
                    tree_node.add(f"{key}: {value}")

        elif isinstance(data_node, list):
            for i, item in enumerate(data_node):
                if isinstance(item, (dict, list)):
                    branch = tree_node.add(f"[{i}]")
                    add_nodes(branch, item)
                else:
                    tree_node.add(f"[{i}] {item}")

    tree = Tree(title or "Data", guide_style="dim")
    add_nodes(tree, data)

    console.print(tree)


def paginate_results(
    items: List[Any],
    page_size: int = 10,
    formatter: Optional[callable] = None
) -> None:
    """Display results with pagination

    Args:
        items: List of items to display
        page_size: Items per page
        formatter: Optional function to format each item
    """
    if not items:
        console.print("[dim]No items to display[/dim]")
        return

    total_pages = (len(items) + page_size - 1) // page_size
    current_page = 0

    while True:
        # Clear and show current page
        console.clear()

        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(items))

        console.print(f"[bold]Page {current_page + 1} of {total_pages}[/bold]")
        console.print(f"Showing items {start_idx + 1}-{end_idx} of {len(items)}\n")

        # Display items
        for i in range(start_idx, end_idx):
            if formatter:
                console.print(formatter(items[i], i))
            else:
                console.print(f"{i + 1}. {items[i]}")

        # Navigation
        console.print(f"\n[dim]Commands: (n)ext, (p)revious, (g)oto, (q)uit[/dim]")

        cmd = Prompt.ask("Command", choices=['n', 'p', 'g', 'q'], default='n')

        if cmd == 'q':
            break
        elif cmd == 'n' and current_page < total_pages - 1:
            current_page += 1
        elif cmd == 'p' and current_page > 0:
            current_page -= 1
        elif cmd == 'g':
            page_num = Prompt.ask(
                f"Go to page (1-{total_pages})",
                default=str(current_page + 1)
            )
            if page_num.isdigit():
                new_page = int(page_num) - 1
                if 0 <= new_page < total_pages:
                    current_page = new_page
>>>>>>> Stashed changes
