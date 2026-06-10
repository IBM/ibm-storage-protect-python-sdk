"""
conftest.py – shared pytest fixtures for the filesystem example tests.

Mocks the ctypes.CDLL layer so tests run without a real IBM Storage Protect installation.
"""

# pylint: disable=protected-access,wrong-import-position,wrong-import-order

import os
import sys
import pytest

# Resolve the path to target src directories (both for filesystem example and the SDK itself)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")))


# During pytest, load.py automatically loads the MockCDLL from mock.py.
# We can safely import it directly without monkeypatching ctypes.CDLL.
from ibm_storage_protect.c_api_bridge.c_api.load import lib

@pytest.fixture(autouse=True)
def mock_lib_reset():
    """Reset all mock return values and call histories on the C library functions before each test."""
    if hasattr(lib, "_functions"):
        for func in lib._functions.values():
            func.reset_mock()
            func.return_value = 0
            func.side_effect = None
    yield

# Made with Bob
