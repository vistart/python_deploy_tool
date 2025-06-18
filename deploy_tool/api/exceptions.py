"""Exception definitions for deploy-tool API"""


class DeployToolError(Exception):
    """Base exception for deploy-tool"""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code


class PackError(DeployToolError):
    """Packing operation error"""
    pass


class MissingTypeError(PackError):
    """Missing package type error"""

    def __init__(self, message: str = "Package type is required"):
        super().__init__(message, "DT013")


class MissingVersionError(PackError):
    """Missing version error"""

    def __init__(self, message: str = "Version is required"):
        super().__init__(message, "DT009")


class PublishError(DeployToolError):
    """Publishing operation error"""
    pass


class ComponentNotFoundError(PublishError):
    """Component not found error"""

    def __init__(self, component_type: str, version: str):
        message = f"Component not found: {component_type}:{version}"
        super().__init__(message, "DT010")
        self.component_type = component_type
        self.version = version


class DeployError(DeployToolError):
    """Deployment operation error"""
    pass


class ReleaseNotFoundError(DeployError):
    """Release version not found error"""

    def __init__(self, release_version: str):
        message = f"Release not found: {release_version}"
        super().__init__(message, "DT011")
        self.release_version = release_version


class ValidationError(DeployToolError):
    """Validation error"""

    def __init__(self, message: str):
        super().__init__(message, "DT007")


class ConfigError(DeployToolError):
    """Configuration error"""

    def __init__(self, message: str):
        super().__init__(message, "DT001")


class PathError(DeployToolError):
    """Path related error"""
    pass


class ProjectNotFoundError(PathError):
    """Project root not found error"""

    def __init__(self, message: str = None):
        if message is None:
            message = (
                "No project root found. Please ensure:\n"
                "1. You are in a project directory\n"
                "2. The project root contains .deploy-tool.yaml\n"
                "3. Or use --project-root parameter to specify project location\n"
                "\n"
                "Initialize a new project: deploy-tool init"
            )
        super().__init__(message, "DT002")


class StorageError(DeployToolError):
    """Storage operation error"""

    def __init__(self, message: str):
        super().__init__(message, "DT004")


class PermissionError(DeployToolError):
    """Permission denied error"""

    def __init__(self, message: str):
        super().__init__(message, "DT005")


class DiskSpaceError(DeployToolError):
    """Insufficient disk space error"""

    def __init__(self, message: str):
        super().__init__(message, "DT006")


class FileExistsError(DeployToolError):
    """File already exists error"""

    def __init__(self, file_path: str):
        message = f"File already exists: {file_path}. Use --force to overwrite."
        super().__init__(message, "DT012")
        self.file_path = file_path


class ComponentInconsistentError(DeployToolError):
    """Release component inconsistent error"""

    def __init__(self, message: str):
        super().__init__(message, "DT014")


class UserCancelledError(DeployToolError):
    """User cancelled the operation"""

    def __init__(self):
        super().__init__("Operation cancelled by user")