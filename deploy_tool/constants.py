"""Global constants for deploy-tool"""

from enum import Enum, auto

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
MANIFEST_FILE_PATTERN = "{type}-{version}.manifest.json"
RELEASE_FILE_PATTERN = "{version}.release.json"
ARCHIVE_FILE_PATTERNS = {
    "gz": "{type}-{version}.tar.gz",
    "bz2": "{type}-{version}.tar.bz2",
    "xz": "{type}-{version}.tar.xz",
    "lz4": "{type}-{version}.tar.lz4",
    "": "{type}-{version}.tar"
}

# Default configuration values
DEFAULT_COMPRESSION_ALGORITHM = "gzip"
DEFAULT_COMPRESSION_LEVEL = 6
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB

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

# Environment variables
ENV_CONFIG_PATH = "DEPLOY_TOOL_CONFIG"
ENV_CACHE_DIR = "DEPLOY_TOOL_CACHE"
ENV_LOG_LEVEL = "DEPLOY_TOOL_LOG_LEVEL"
ENV_MANIFESTS_DIR = "DEPLOY_TOOL_MANIFESTS_DIR"
ENV_BOS_ACCESS_KEY = "BOS_ACCESS_KEY"
ENV_BOS_SECRET_KEY = "BOS_SECRET_KEY"
ENV_BOS_ENDPOINT = "BOS_ENDPOINT"

# Validation patterns
import re

VERSION_PATTERN = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

COMPONENT_TYPE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

MAX_COMPONENT_TYPE_LENGTH = 50

RELEASE_VERSION_DATE_PATTERN = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")

RELEASE_VERSION_SEMANTIC_PATTERN = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

# Time formats
ISO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DISPLAY_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Terminal colors (for Rich console)
COLORS = {
    "success": "green",
    "error": "red",
    "warning": "yellow",
    "info": "blue",
    "highlight": "cyan",
    "dim": "dim white"
}

# Plugin related
PLUGIN_ENTRY_POINT = "deploy_tool.plugins"
BUILTIN_PLUGINS = ["git_integration", "cache", "hooks"]

# Compression algorithms mapping
COMPRESSION_ALGORITHMS = {
    "gzip": "gz",
    "bzip2": "bz2",
    "xz": "xz",
    "lz4": "lz4",
    "none": ""
}

# File type categories
FILE_TYPE_CATEGORIES = {
    "code": [".py", ".js", ".java", ".cpp", ".c", ".h", ".go", ".rs"],
    "config": [".yaml", ".yml", ".json", ".xml", ".ini", ".conf", ".toml"],
    "data": [".csv", ".tsv", ".parquet", ".feather", ".h5", ".hdf5"],
    "model": [".pth", ".pt", ".pkl", ".joblib", ".onnx", ".pb"],
    "document": [".md", ".txt", ".rst", ".doc", ".docx", ".pdf"]
}

# PathType enum for path resolution
class PathType(Enum):
    """Path types for resolution"""
    AUTO = auto()  # Automatic detection
    SOURCE = auto()  # Source file path (relative to project root)
    CONFIG = auto()  # Configuration file path
    MANIFEST = auto()  # Manifest file path
    RELEASE = auto()  # Release file path
    DIST = auto()  # Distribution/output path
    CACHE = auto()  # Cache path
    ABSOLUTE = auto()  # Absolute path (no conversion)


# API endpoints (for future remote storage)
API_VERSION = "v1"
API_ENDPOINTS = {
    "upload": f"/api/{API_VERSION}/upload",
    "download": f"/api/{API_VERSION}/download",
    "list": f"/api/{API_VERSION}/list",
    "delete": f"/api/{API_VERSION}/delete",
    "info": f"/api/{API_VERSION}/info"
}

# Manifest schema version
MANIFEST_SCHEMA_VERSION = "1.0"

# Release metadata keys
RELEASE_METADATA_KEYS = [
    "created_by",
    "created_at",
    "description",
    "components",
    "tags",
    "notes"
]

# Component metadata keys
COMPONENT_METADATA_KEYS = [
    "description",
    "dependencies",
    "requirements",
    "checksum",
    "size",
    "files_count",
    "created_at",
    "created_by"
]

# Exit codes
class ExitCode:
    SUCCESS = 0
    GENERAL_ERROR = 1
    CONFIGURATION_ERROR = 2
    VALIDATION_ERROR = 3
    STORAGE_ERROR = 4
    PERMISSION_ERROR = 5
    NOT_FOUND_ERROR = 6
    ALREADY_EXISTS_ERROR = 7
    NETWORK_ERROR = 8
    TIMEOUT_ERROR = 9
    UNKNOWN_ERROR = 10