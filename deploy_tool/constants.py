"""Global constants for deploy-tool"""

from enum import Enum, auto
import re

# Version related
MANIFEST_VERSION = "1.0"
CONFIG_VERSION = "1.0"

# Project identification
PROJECT_CONFIG_FILE = ".deploy-tool.yaml"
PROJECT_MARKERS = [
    PROJECT_CONFIG_FILE,
    "deployment",
    ".git"
]

# Directory structure
DEFAULT_DEPLOYMENT_DIR = "deployment"
DEFAULT_MANIFESTS_DIR = "deployment/manifests"
DEFAULT_RELEASES_DIR = "deployment/releases"
DEFAULT_CONFIGS_DIR = "deployment/package-configs"
DEFAULT_DIST_DIR = "dist"
DEFAULT_CACHE_DIR = ".deploy-tool-cache"

# File patterns
MANIFEST_FILE_PATTERN = "{component}/{version}.json"
PACKAGE_FILE_PATTERN = "{component}-{version}.tar.{ext}"
ARCHIVE_FILE_PATTERNS = {
    "gz": "{component}-{version}.tar.gz",
    "bz2": "{component}-{version}.tar.bz2",
    "xz": "{component}-{version}.tar.xz",
    "lz4": "{component}-{version}.tar.lz4",
    "": "{component}-{version}.tar"
}

# Default configuration values
DEFAULT_COMPRESSION_ALGORITHM = "gzip"
DEFAULT_COMPRESSION_LEVEL = 6
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 5  # seconds

# Common exclude patterns
DEFAULT_EXCLUDE_PATTERNS = [
    "*.log",
    "__pycache__/",
    ".DS_Store",
    ".git/",
    "*.tmp",
    "*.cache",
    "*.pyc",
    "*.pyo",
    ".pytest_cache/",
    ".mypy_cache/",
    ".tox/",
    "*.egg-info/",
    "build/",
    "dist/",
]

# Git related
GIT_IGNORE_TEMPLATE = """# Deploy Tool generated files
/dist/
*.tar.gz
*.tar.bz2
*.tar.xz
*.tar.lz4
*.zip

# Local cache
.deploy-tool-cache/

# Temporary files
*.tmp
*.temp

# But keep important files
!deployment/manifests/
!deployment/releases/
!deployment/package-configs/
"""

# Size limits
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
MIN_FILE_SIZE = 1  # 1 byte

# Progress display
PROGRESS_UPDATE_INTERVAL = 0.1  # seconds
PROGRESS_BAR_WIDTH = 50

# Storage related
DEFAULT_STORAGE_TYPE = "filesystem"
SUPPORTED_STORAGE_TYPES = ["filesystem", "bos", "s3"]

<<<<<<< Updated upstream
# Storage overhead thresholds
STORAGE_OVERHEAD_WARNING_SIZE = 100 * 1024 * 1024  # 100MB - Warn about copying overhead

# Symlink constants
SYMLINK_RELEASES_DIR = "releases"  # Directory for versioned releases
SYMLINK_CURRENT_VERSION_FILE = ".current-version"  # File tracking current version

# Post-publish instruction types
INSTRUCTION_TYPE_GIT = "git"
INSTRUCTION_TYPE_TRANSFER = "transfer"
INSTRUCTION_TYPE_DEPLOY = "deploy"

# Progress display for large files
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB - Show progress for large files
VERY_LARGE_FILE_THRESHOLD = 500 * 1024 * 1024  # 500MB - Extra warnings

# Deployment structure
DEPLOYMENT_METADATA_FILE = ".deploy-metadata.json"
DEPLOYMENT_STATE_FILE = ".deploy-state.json"
DEPLOYMENT_LOCK_FILE = ".deploy.lock"

# Version switching
VERSION_SWITCH_BACKUP_SUFFIX = ".backup"
VERSION_SWITCH_ROLLBACK_LIMIT = 3  # Keep last 3 versions for rollback
=======
# Deployment related
DEFAULT_DEPLOY_ROOT = "/opt/deployments"
COMPONENTS_DIR = "components"
LINKS_DIR = "links"
CURRENT_LINK_NAME = "current"
DEPLOYMENT_STATE_FILE = ".deployment-state.json"

# Storage type enums
class StorageType(Enum):
    FILESYSTEM = "filesystem"
    BOS = "bos"
    S3 = "s3"

# Operation modes
class OperationMode(Enum):
    INTERACTIVE = "interactive"
    COMMAND_LINE = "command_line"
    AUTO = "auto"

# Component status
class ComponentStatus(Enum):
    NOT_DEPLOYED = "not_deployed"
    DEPLOYED = "deployed"
    CURRENT = "current"
    DEPRECATED = "deprecated"

# Target status
class TargetStatus(Enum):
    AVAILABLE = "available"
    UNREACHABLE = "unreachable"
    AUTHENTICATED = "authenticated"
    PERMISSION_DENIED = "permission_denied"
>>>>>>> Stashed changes

# Error codes
class ErrorCode:
    CONFIG_FORMAT_ERROR = "DT001"
    SOURCE_NOT_FOUND = "DT002"
    VERSION_FORMAT_ERROR = "DT003"
    STORAGE_CONNECTION_FAILED = "DT004"
    PERMISSION_DENIED = "DT005"
    DISK_SPACE_INSUFFICIENT = "DT006"
    MANIFEST_VALIDATION_FAILED = "DT007"
    DEPLOY_TARGET_UNREACHABLE = "DT008"
    MISSING_REQUIRED_PARAMETER = "DT009"
    COMPONENT_NOT_FOUND = "DT010"
    RELEASE_NOT_FOUND = "DT011"
    FILE_ALREADY_EXISTS = "DT012"
    COMPONENT_TYPE_UNDEFINED = "DT013"
    RELEASE_COMPONENT_INCONSISTENT = "DT014"
    CHECKSUM_MISMATCH = "DT015"
    LINK_UPDATE_FAILED = "DT016"
    VERSION_ALREADY_DEPLOYED = "DT017"
    NO_AVAILABLE_SOURCE = "DT018"
    FAILOVER_EXHAUSTED = "DT019"
    PACK_FAILED = "DT020"
    VERSION_NOT_FOUND = "DT021"

# Environment variables
ENV_CONFIG_PATH = "DEPLOY_TOOL_CONFIG"
ENV_CACHE_DIR = "DEPLOY_TOOL_CACHE"
ENV_LOG_LEVEL = "DEPLOY_TOOL_LOG_LEVEL"
ENV_DEPLOY_ROOT = "DEPLOY_TOOL_DEPLOY_ROOT"
ENV_PROJECT_ROOT = "PROJECT_ROOT"
ENV_BOS_ACCESS_KEY = "BOS_AK"
ENV_BOS_SECRET_KEY = "BOS_SK"
ENV_BOS_ENDPOINT = "BOS_ENDPOINT"
ENV_S3_ACCESS_KEY = "AWS_ACCESS_KEY_ID"
ENV_S3_SECRET_KEY = "AWS_SECRET_ACCESS_KEY"
ENV_S3_REGION = "AWS_DEFAULT_REGION"

# Validation patterns
VERSION_PATTERN = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"$"
)
COMPONENT_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
TARGET_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

# Command aliases
COMMAND_ALIASES = {
    "ls": "list",
    "rm": "remove",
    "mv": "move",
    "cp": "copy",
    "stat": "status",
    "info": "show",
}

# Display constants
EMOJI_SUCCESS = "✓"
EMOJI_ERROR = "✗"
EMOJI_WARNING = "⚠"
EMOJI_INFO = "ℹ"
EMOJI_ARROW = "→"
EMOJI_PACKAGE = "📦"
EMOJI_ROCKET = "🚀"
EMOJI_FOLDER = "📁"
EMOJI_LINK = "🔗"
EMOJI_CLOUD = "☁️"
EMOJI_SERVER = "🖥️"

# Messages templates
MSG_PACK_SUCCESS = f"{EMOJI_SUCCESS} Package created: {{path}} ({{size}})"
MSG_PUBLISH_SUCCESS = f"{EMOJI_SUCCESS} Published to {{target}}: {{component}}:{{version}}"
MSG_DEPLOY_SUCCESS = f"{EMOJI_SUCCESS} Deployed: {{component}}:{{version}}"
MSG_LINK_UPDATED = f"{EMOJI_LINK} Link updated: {{link}} {EMOJI_ARROW} {{target}}"
MSG_VERSION_SWITCHED = f"{EMOJI_SUCCESS} Switched {{component}} from {{old_version}} to {{new_version}}"

# Failover messages
MSG_FAILOVER_RETRY = f"{EMOJI_WARNING} Failed to deploy from {{source}}, trying next source..."
MSG_FAILOVER_SUCCESS = f"{EMOJI_SUCCESS} Successfully deployed from {{source}} after {{attempts}} attempt(s)"
MSG_FAILOVER_EXHAUSTED = f"{EMOJI_ERROR} All deployment sources failed"

# Interactive prompts
PROMPT_SELECT_TARGET = "Select publish targets (space to select, enter to confirm):"
PROMPT_CONFIRM_DEPLOY = "Deploy {component}:{version} to {target}?"
PROMPT_SELECT_SOURCE = "Select deployment source:"
PROMPT_ENTER_VERSION = "Enter version number (e.g., 1.0.0):"
PROMPT_CONFIRM_OVERWRITE = "Version {version} already exists. Overwrite?"