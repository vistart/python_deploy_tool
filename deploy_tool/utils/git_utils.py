"""Git operation utilities"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def is_git_repository(path: Path) -> bool:
    """
    Check if directory is a Git repository

    Args:
        path: Directory path

    Returns:
        True if it's a Git repository
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            cwd=path,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_current_branch(path: Path) -> Optional[str]:
    """
    Get current Git branch

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


def get_git_status(path: Path) -> Dict[str, bool]:
    """
    Get Git repository status

    Args:
        path: Repository path

    Returns:
        Dictionary with status information
    """
    status = {
        'is_git_repo': False,
        'has_uncommitted': False,
        'has_untracked': False,
        'is_clean': False
    }

    if not is_git_repository(path):
        return status

    status['is_git_repo'] = True

    try:
        # Check for uncommitted changes
        result = subprocess.run(
            ['git', 'diff', '--quiet', '--exit-code'],
            cwd=path
        )
        has_staged = result.returncode != 0

        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet', '--exit-code'],
            cwd=path
        )
        has_unstaged = result.returncode != 0

        status['has_uncommitted'] = has_staged or has_unstaged

        # Check for untracked files
        result = subprocess.run(
            ['git', 'ls-files', '--others', '--exclude-standard'],
            cwd=path,
            capture_output=True,
            text=True
        )
        status['has_untracked'] = bool(result.stdout.strip())

        status['is_clean'] = not (status['has_uncommitted'] or status['has_untracked'])

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return status


def is_file_tracked(path: Path, file_path: Path) -> bool:
    """
    Check if file is tracked by Git

    Args:
        path: Repository path
        file_path: File path to check

    Returns:
        True if file is tracked
    """
    try:
        relative_path = file_path.relative_to(path)
        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', str(relative_path)],
            cwd=path,
            capture_output=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return False


def get_remote_url(path: Path, remote: str = 'origin') -> Optional[str]:
    """
    Get Git remote URL

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


def get_git_info(path: Path) -> Dict[str, any]:
    """
    Get comprehensive Git repository information

    Args:
        path: Repository path

    Returns:
        Dictionary with Git information
    """
    info = {
        'is_git_repo': is_git_repository(path),
        'branch': None,
        'commit': None,
        'remote_url': None,
        'status': get_git_status(path)
    }

    if info['is_git_repo']:
        info['branch'] = get_current_branch(path)
        info['remote_url'] = get_remote_url(path)

        # Get current commit
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=path,
                capture_output=True,
                text=True,
                check=True
            )
            info['commit'] = result.stdout.strip()[:7]  # Short commit hash
        except:
            pass

    return info


def check_git_status(path: Path) -> Dict[str, any]:
    """
    Check detailed Git status (alias for get_git_status)

    Args:
        path: Repository path

    Returns:
        Dictionary with status information
    """
    return get_git_status(path)


def get_uncommitted_files(path: Path) -> List[str]:
    """
    Get list of uncommitted files

    Args:
        path: Repository path

    Returns:
        List of file paths with uncommitted changes
    """
    files = []

    if not is_git_repository(path):
        return files

    try:
        # Get modified files
        result = subprocess.run(
            ['git', 'diff', '--name-only'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            files.extend(result.stdout.strip().split('\n'))

        # Get staged files
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            files.extend(result.stdout.strip().split('\n'))

        # Get untracked files
        result = subprocess.run(
            ['git', 'ls-files', '--others', '--exclude-standard'],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            files.extend(result.stdout.strip().split('\n'))

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Remove duplicates and empty strings
    return list(filter(None, set(files)))


def suggest_git_commands(file_path: Path, operation: str) -> List[str]:
    """
    Suggest Git commands based on file and operation

    Args:
        file_path: File that was created/modified
        operation: Operation performed (e.g., 'pack', 'publish')

    Returns:
        List of suggested Git commands
    """
    suggestions = []
    file_name = file_path.name

    if operation == 'pack':
        suggestions.extend([
            f"git add {file_path}",
            f"git commit -m 'Add {file_name}'",
            "git push"
        ])
    elif operation == 'publish':
        suggestions.extend([
            f"git add {file_path}",
            f"git commit -m 'Publish {file_name}'",
            f"git tag -a v{file_name.split('-')[1].split('.')[0]} -m 'Release version'",
            "git push --tags"
        ])

    return suggestions


def get_last_commit_date(path: Path, file_path: Optional[Path] = None) -> Optional[str]:
    """
    Get last commit date for repository or specific file

    Args:
        path: Repository path
        file_path: Optional specific file

    Returns:
        ISO format date string or None
    """
    try:
        cmd = ['git', 'log', '-1', '--format=%ai']
        if file_path:
            cmd.append(str(file_path))

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_file_history(path: Path, file_path: Path, limit: int = 10) -> List[Dict[str, str]]:
    """
    Get commit history for a file

    Args:
        path: Repository path
        file_path: File path
        limit: Maximum number of commits

    Returns:
        List of commit information
    """
    history = []

    try:
        result = subprocess.run(
            ['git', 'log', f'--max-count={limit}', '--pretty=format:%H|%ai|%an|%s', str(file_path)],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|', 3)
                if len(parts) == 4:
                    history.append({
                        'commit': parts[0][:7],
                        'date': parts[1],
                        'author': parts[2],
                        'message': parts[3]
                    })

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return history


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