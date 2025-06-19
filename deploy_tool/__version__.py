"""Version information for deploy-tool package"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
__author__ = "vistart"
__email__ = "i@vistart.me"
__license__ = "MIT"
__copyright__ = "Copyright 2025 vistart"

# Version details
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION_SUFFIX = ""  # For pre-release versions like "alpha", "beta", "rc1"

# Full version string
if VERSION_SUFFIX:
    VERSION_STRING = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}-{VERSION_SUFFIX}"
else:
    VERSION_STRING = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

# Ensure version consistency
assert __version__ == VERSION_STRING, "Version mismatch between __version__ and VERSION_STRING"


def get_version():
    """Get the version string"""
    return __version__


def get_version_info():
    """Get the version tuple"""
    return __version_info__