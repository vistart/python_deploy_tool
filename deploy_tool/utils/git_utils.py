"""Git operation utilities"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple


def is_git_repository(path: Path) -> bool:
    """
    Check if path is inside a git repository

    Args:
        path: Path to check

    Returns:
        True if inside a git repository
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_current_branch(path: Path) -> Optional[str]:
    """
    Get current git branch

    Args:
        path: Repository path

    Returns:
        Branch name or None
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_git_status(path: Path) -> Dict[str, List[str]]:
    """
    Get git status information

    Args:
        path: Repository path

    Returns:
        Dictionary with status information
    """
    status = {
        'modified': [],
        'added': [],
        'deleted': [],
        'renamed': [],
        'untracked': [],
    }

    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.splitlines():
            if not line:
                continue

            status_code = line[:2]
            file_path = line[3:]

            if status_code == '??':
                status['untracked'].append(file_path)
            elif status_code[1] == 'M' or status_code[0] == 'M':
                status['modified'].append(file_path)
            elif status_code[1] == 'A' or status_code[0] == 'A':
                status['added'].append(file_path)
            elif status_code[1] == 'D' or status_code[0] == 'D':
                status['deleted'].append(file_path)
            elif status_code[0] == 'R':
                status['renamed'].append(file_path)

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return status


def is_file_tracked(path: Path, file_path: Path) -> bool:
    """
    Check if file is tracked by git

    Args:
        path: Repository path
        file_path: File to check

    Returns:
        True if file is tracked
    """
    try:
        # Make path relative to repository
        if file_path.is_absolute():
            rel_path = file_path.relative_to(path)
        else:
            rel_path = file_path

        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', str(rel_path)],
            cwd=path,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return False


def get_remote_url(path: Path, remote: str = "origin") -> Optional[str]:
    """
    Get git remote URL

    Args:
        path: Repository path
        remote: Remote name

    Returns:
        Remote URL or None
    """
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', remote],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_last_commit_hash(path: Path, short: bool = False) -> Optional[str]:
    """
    Get last commit hash

    Args:
        path: Repository path
        short: Whether to return short hash

    Returns:
        Commit hash or None
    """
    try:
        args = ['git', 'rev-parse']
        if short:
            args.append('--short')
        args.append('HEAD')

        result = subprocess.run(
            args,
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_commit_count(path: Path) -> int:
    """
    Get total commit count

    Args:
        path: Repository path

    Returns:
        Number of commits
    """
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return int(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return 0


def get_tags(path: Path) -> List[str]:
    """
    Get list of git tags

    Args:
        path: Repository path

    Returns:
        List of tag names
    """
    try:
        result = subprocess.run(
            ['git', 'tag', '-l'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return [tag.strip() for tag in result.stdout.splitlines() if tag.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def is_dirty(path: Path) -> bool:
    """
    Check if repository has uncommitted changes

    Args:
        path: Repository path

    Returns:
        True if there are uncommitted changes
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_ahead_behind(path: Path) -> Tuple[int, int]:
    """
    Get ahead/behind count relative to upstream

    Args:
        path: Repository path

    Returns:
        Tuple of (ahead_count, behind_count)
    """
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}'],
            cwd=path,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))

    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        pass

    return (0, 0)


def add_files(path: Path, files: List[str]) -> bool:
    """
    Add files to git staging

    Args:
        path: Repository path
        files: List of file paths to add

    Returns:
        True if successful
    """
    try:
        result = subprocess.run(
            ['git', 'add'] + files,
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False