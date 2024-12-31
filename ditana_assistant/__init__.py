"""
ditana-assistant package.

An AI-powered assistant application that combines GUI and terminal functionality
with optional introspective contextual augmentation.

This package provides the core functionality for the Ditana Assistant,
including AI model integration, system interaction, and contextual enhancement.

The version is imported from the package metadata if the package is installed,
otherwise it defaults to "unknown".

Attributes:
    __version__ (str): The version of the ditana-assistant package.

For detailed information about features and usage, please refer to the project's
README.md file or official documentation.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ditana-assistant")
except PackageNotFoundError:
    # Package is not installed
    __version__ = "unknown"
