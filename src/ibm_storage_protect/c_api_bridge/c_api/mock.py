"""
IBM Storage Protect Client C API Mock Classes

This module provides mock implementations of ctypes CDLL and function classes
to facilitate testing of the Python SDK wrapper and bridge code without
requiring a native IBM Storage Protect library or dll.
"""

from unittest.mock import MagicMock

class MockFunction(MagicMock):
    """
    A mock ctypes function pointer that supports restype and argtypes attributes.
    Defaults to returning 0 (DSM_RC_OK).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.restype = None
        self.argtypes = None
        self.return_value = 0  # DSM_RC_OK by default


class MockCDLL:
    """
    A mock container that simulates a loaded ctypes.CDLL library instance.
    Dynamically generates and caches MockFunction instances upon attribute access.
    """
    def __init__(self, path: str = "mock_api", *args, **kwargs):
        self._path = path
        self._functions = {}

    def __getattr__(self, name: str) -> MockFunction:
        if name not in self._functions:
            self._functions[name] = MockFunction(name=name)
        return self._functions[name]
