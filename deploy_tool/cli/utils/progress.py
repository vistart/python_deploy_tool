# deploy_tool/cli/utils/progress.py
"""Progress display utilities"""

from contextlib import contextmanager
from typing import Generator, Callable

from rich.console import Console
from rich.live import Live
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TimeRemainingColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TaskID,
)
from rich.table import Table


class ProgressManager:
    """Centralized progress management"""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self._progress = None
        self._live = None

    @contextmanager
    def basic_progress(self, description: str = "Processing...") -> Generator[Progress, None, None]:
        """Simple spinner progress"""
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
        ) as progress:
            progress.add_task(description)
            yield progress

    @contextmanager
    def file_progress(self) -> Generator[Progress, None, None]:
        """Progress bar for file operations"""
        with Progress(
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TransferSpeedColumn(),
                "•",
                TimeRemainingColumn(),
                console=self.console,
        ) as progress:
            yield progress

    @contextmanager
    def multi_progress(self) -> Generator[Progress, None, None]:
        """Progress for multiple concurrent tasks"""
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=self.console,
        ) as progress:
            yield progress

    def create_pack_progress(self) -> Progress:
        """Create progress display for packing operations"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "({task.completed}/{task.total})",
            TimeRemainingColumn(),
            console=self.console,
        )

    def create_publish_progress(self) -> Progress:
        """Create progress display for publishing operations"""
        return Progress(
            TextColumn("[bold blue]{task.fields[component]}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            console=self.console,
        )


class AsyncProgressReporter:
    """Async-friendly progress reporter"""

    def __init__(self, progress: Progress, task_id: TaskID):
        self.progress = progress
        self.task_id = task_id
        self._total = 0
        self._completed = 0

    async def set_total(self, total: int) -> None:
        """Set total amount of work"""
        self._total = total
        self.progress.update(self.task_id, total=total)

    async def advance(self, amount: int = 1) -> None:
        """Advance progress by amount"""
        self._completed += amount
        self.progress.advance(self.task_id, amount)

    async def update(self, completed: int) -> None:
        """Update to specific completion amount"""
        advance = completed - self._completed
        if advance > 0:
            self._completed = completed
            self.progress.advance(self.task_id, advance)

    async def finish(self) -> None:
        """Mark task as complete"""
        if self._total > 0:
            remaining = self._total - self._completed
            if remaining > 0:
                self.progress.advance(self.task_id, remaining)


def create_status_table(title: str, data: dict) -> Table:
    """Create a status table for live display"""
    table = Table(title=title, show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in data.items():
        table.add_row(key, str(value))

    return table


class LiveStatusDisplay:
    """Live updating status display"""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self._live = None
        self._status_data = {}

    def __enter__(self):
        self._live = Live(
            self._create_display(),
            console=self.console,
            refresh_per_second=4
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.__exit__(*args)

    def update(self, **kwargs) -> None:
        """Update status values"""
        self._status_data.update(kwargs)
        if self._live:
            self._live.update(self._create_display())

    def _create_display(self) -> Table:
        """Create the display table"""
        return create_status_table("Status", self._status_data)


# Utility functions for common progress patterns

def progress_callback(progress: Progress, task_id: TaskID) -> Callable[[int, int], None]:
    """Create a progress callback function

    Returns a function that can be used as a progress callback
    with signature (completed, total).
    """

    def callback(completed: int, total: int) -> None:
        if progress and task_id is not None:
            progress.update(task_id, completed=completed, total=total)

    return callback


async def run_with_progress(coro, description: str = "Processing...",
                            console: Console = None) -> any:
    """Run an async coroutine with a simple progress spinner"""
    console = console or Console()

    with console.status(description) as status:
        result = await coro

    return result