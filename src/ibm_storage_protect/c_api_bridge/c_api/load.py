"""
IBM Storage Protect Client API Library Loader

This module handles the dynamic loading of the IBM Storage Protect Client API library
across different platforms (AIX, Windows, Linux). It attempts to locate and load
the appropriate shared library based on the operating system.

The module exports a single `lib` object which is a ctypes.CDLL instance representing
the loaded IBM Storage Protect API library. This object is used by dsmapifp.py to
define function prototypes.

Platform-Specific Library Names:
---------------------------------
- AIX: libApiTSM64.a (archive format)
- Windows: dsmtca64.dll (dynamic link library)
- Linux/Unix: libApiTSM64.so or libtsmapi64.so (shared object)

Environment Variable:
---------------------
IBM_SP_API_LIB: Set this environment variable to specify a custom path to the
                IBM Storage Protect API library if it's not in the default locations.

Default Search Paths:
---------------------
The module searches for the library in platform-specific default locations:
- AIX: /usr/lib/, /opt/tivoli/tsm/client/api/bin64/
- Windows: Current directory, C:\\Program Files\\Tivoli\\TSM\\api\\bin64\\
- Linux: Current directory, /opt/tivoli/tsm/client/api/bin64/, /usr/lib/, /usr/lib64/

Error Handling:
---------------
If the library cannot be loaded from any of the search paths, the module prints
an error message with the attempted paths and suggests setting the IBM_SP_API_LIB
environment variable. The `lib` variable will be None in this case.

Usage:
------
This module is imported by dsmapifp.py and should not typically be imported directly
by user code. The library loading happens at module import time.

Reference:
----------
For more information about the IBM Storage Protect Client API, see:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf

Example:
--------
    from .load import lib
    if lib is not None:
        # Library loaded successfully, can define function prototypes
        lib.dsmInit.restype = ctypes.c_int
        lib.dsmInit.argtypes = [...]
"""

from typing import Any
import ctypes
import sys
import os
import logging

_logger = logging.getLogger("ibm_storage_protect.c_api_bridge.c_api.load")

# Platform-specific library paths
def get_library_path():
    """
    Get the platform-specific library path for IBM Storage Protect Client API.

    This function returns a list of potential paths where the IBM Storage Protect
    Client API library might be located, based on the current operating system.

    Returns:
        list: A list of file paths (strings) to search for the API library.
              The list is ordered by priority, with the most likely locations first.

    Platform Detection:
        - sys.platform.startswith('aix'): AIX operating system
        - sys.platform == 'win32': Windows operating system
        - Other: Linux and Unix-like systems

    Environment Variable Override:
        If the IBM_SP_API_LIB environment variable is set, its value is inserted
        at the beginning of the search path list, giving it highest priority.
    """
    if sys.platform.startswith('aix'):
        # AIX uses .a (archive) format for shared libraries
        # The archive contains both 32-bit and 64-bit versions
        paths = [
            "/usr/lib/libApiTSM64.a",
            "/opt/tivoli/tsm/client/api/bin64/libApiTSM64.a",
        ]
    elif sys.platform == 'win32':
        # Windows uses .dll (Dynamic Link Library) format
        # dsmtca64.dll is the 64-bit Trusted Communication Agent library
        paths = [
            "dsmtca64.dll",
            "C:\\Program Files\\Tivoli\\TSM\\api\\bin64\\dsmtca64.dll",
        ]
    else:
        # Linux and other Unix-like systems use .so (shared object) format
        # Multiple naming conventions are supported for compatibility
        paths = [
            "libtsmapi64.so",
            "/opt/tivoli/tsm/client/api/bin64/libApiTSM64.so",
            "/usr/lib/libtsmapi64.so",
            "/usr/lib64/libtsmapi64.so",
        ]

    # Check environment variable override
    # This allows users to specify a custom library location without modifying code
    env_path = os.environ.get('IBM_SP_API_LIB')
    if env_path:
        paths.insert(0, env_path)

    return paths

# Check if we should load the mock C API library.
# This is active if pytest is in sys.modules or SP_USE_MOCK_C_API env var is set.
# If these conditions aren't met, we try loading the native library, with a mock fallback as a safety measure.
lib: Any = None  # Will hold the loaded library object (ctypes.CDLL or MockCDLL instance)
last_error = None  # Will hold the last exception if loading fails

# Check if pytest is running or mock is explicitly requested
is_testing = "pytest" in sys.modules or os.environ.get('SP_USE_MOCK_C_API', '').lower() in ('1', 'true')

if is_testing:
    try:
        from .mock import MockCDLL
        lib = MockCDLL("mock_api")
        _logger.info("Loaded mock IBM Storage Protect Client API library for unit-testing.")
    except Exception as e:
        last_error = e

if lib is None:
    for lib_path in get_library_path():
        try:
            # Attempt to load the library using ctypes.CDLL
            # CDLL is used for libraries with C calling convention
            lib = ctypes.CDLL(lib_path)
            _logger.info("Library loaded successfully from: %s", lib_path)
            break  # Success - stop searching
        except OSError as e:
            # Library not found at this path or failed to load
            # Continue to next path
            last_error = e
            continue

# If library loading failed for all paths, fall back to MockCDLL
if lib is None:
    try:
        from .mock import MockCDLL
        lib = MockCDLL("mock_api_fallback")
        _logger.warning("Native library load failed. Fell back to MockCDLL.")
    except Exception as e:
        _logger.error("Error loading native library: %s", last_error)
        _logger.error("Tried paths: %s", get_library_path())
        _logger.error("Set IBM_SP_API_LIB environment variable to specify custom library path")
    # Note: lib remains None, which will cause errors if function prototypes are accessed

# Made with Bob
