#!/usr/bin/env python3
"""
Setup script for deploy-tool.

This file is primarily for backward compatibility.
The project is configured via pyproject.toml using hatchling.
"""

import codecs
import os
import re
from setuptools import setup, find_packages


def read(rel_path):
    """Read file content."""
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r', 'utf-8') as fp:
        return fp.read()


def find_version(rel_path):
    """Extract version from __init__.py file."""
    init_content = read(rel_path)
    version_match = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        init_content,
        re.MULTILINE
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


if __name__ == "__main__":
    setup(
        name="deploy-tool",
        version=find_version("deploy_tool/__init__.py"),
        packages=find_packages(exclude=["tests*", "docs*", "examples*", "scripts*"]),
        python_requires=">=3.8",
    )