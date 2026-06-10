"""
IBM Storage Protect Python SDK package.

This package exposes the top-level client classes used by IBM Storage Protect
SDK consumers.
"""

from .session import ClientSession, initialize_environment
from .data_client import DataClient
from .control import ControlClient
from .query import QueryClient

__version__ = "0.1.0"

__all__ = [
    "ClientSession",
    "initialize_environment",
    "DataClient",
    "ControlClient",
    "QueryClient",
]
