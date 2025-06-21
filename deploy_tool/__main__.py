# deploy_tool/__main__.py
"""Support for python -m deploy_tool"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())