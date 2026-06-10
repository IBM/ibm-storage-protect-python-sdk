import sys
import pytest
from unittest.mock import MagicMock, patch
import ctypes
from typing import Any, cast

# During pytest, load.py automatically loads the MockCDLL from mock.py.
# We can safely import it directly without monkeypatching ctypes.CDLL.
from ibm_storage_protect.c_api_bridge.c_api.load import lib

@pytest.fixture(autouse=True)
def mock_lib_reset():
    """Reset all mock return values and call histories on the C library functions before each test."""
    # Reset all registered functions in our mock CDLL
    if hasattr(lib, "_functions"):
        for func in lib._functions.values():
            func.reset_mock()
            func.return_value = 0
            func.side_effect = None

        # Add default side effect for dsmInitEx to return a valid handle (1)
        def default_dsm_init_ex(handle_ref, *args, **kwargs):
            try:
                handle_ref._obj.value = 1
            except Exception:
                pass
            return 0  # Success

        lib.dsmInitEx.side_effect = default_dsm_init_ex

        # Add default side effect for dsmBindMC to populate mcBindKey with valid policy data.
        # Without this, backup_cg_exists remains 0 (falsy) and BackupOperation raises
        # TSMConfigurationError("No backup copy group in management class").
        def default_dsm_bind_mc(handle, obj_name_ptr, send_type, mc_bind_key_ptr, *args, **kwargs):
            try:
                mc = mc_bind_key_ptr._obj
                mc.backup_cg_exists = 1
                mc.backup_copy_dest = b"DISK"
            except Exception:
                pass
            return 0  # DSM_RC_OK

        lib.dsmBindMC.side_effect = default_dsm_bind_mc
    yield
