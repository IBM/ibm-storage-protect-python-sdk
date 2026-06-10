import pytest
from unittest.mock import patch
import ctypes
from ibm_storage_protect import ClientSession
from ibm_storage_protect.data_models.session import LoginCredentials, PasswordChange
from ibm_storage_protect.errors import TSMAuthenticationError
from ibm_storage_protect.c_api_bridge.c_api.load import lib

def test_session_login_success():
    """Verify that a successful login establishes an active handle and logs in."""
    # lib.dsmInitEx is mocked by conftest to return 0 (success)
    lib.dsmInitEx.return_value = 0

    session = ClientSession()
    creds = LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD")
    
    result = session.login(creds)
    assert session.is_active is True
    assert session.handle > 0
    assert result.handle == session.handle
    assert lib.dsmInitEx.call_count == 1

def test_session_login_failure():
    """Verify that a login failure raises TSMAuthenticationError when the C API returns an authentication error code."""
    # Code 52: DSM_RC_REJECT_VERIFIER_EXPIRED (password expired)
    # Must clear side_effect first — it takes priority over return_value when set
    lib.dsmInitEx.side_effect = None
    lib.dsmInitEx.return_value = 52

    session = ClientSession()
    creds = LoginCredentials(node="TEST-NODE", password="EXPIRED-TEST-PASSWORD")

    with pytest.raises(TSMAuthenticationError):
        session.login(creds)
    
    assert session.is_active is False

def test_session_logout():
    """Verify that logout terminates the session and calls dsmTerminate."""
    lib.dsmInitEx.return_value = 0
    lib.dsmTerminate.return_value = 0

    session = ClientSession()
    session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    assert session.is_active is True

    session.logout()
    assert session.is_active is False
    assert lib.dsmTerminate.call_count == 1

def test_session_context_manager():
    """Verify that the context manager automatically initiates login and terminates on exit."""
    lib.dsmInitEx.return_value = 0
    lib.dsmTerminate.return_value = 0

    with ClientSession() as session:
        session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        assert session.is_active is True
    
    # Exited block - should have automatically called logout
    assert session.is_active is False
    assert lib.dsmTerminate.call_count == 1

def test_session_context_manager_exception():
    """Verify that the context manager triggers logout even if an exception occurs inside the block."""
    lib.dsmInitEx.return_value = 0
    lib.dsmTerminate.return_value = 0

    session_ref = None
    with pytest.raises(ValueError):
        with ClientSession() as session:
            session_ref = session
            session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
            raise ValueError("Test dynamic crash")

    assert session_ref is not None
    assert session_ref.is_active is False
    assert lib.dsmTerminate.call_count == 1

def test_change_password_success():
    """Verify that password changes execute successfully via C API."""
    lib.dsmInitEx.return_value = 0
    lib.dsmChangePW.return_value = 0

    with ClientSession() as session:
        session.login(LoginCredentials(node="TEST-NODE", password="OLD-TEST-PASSWORD"))
        
        change_req = PasswordChange(
            current_password="OLD-TEST-PASSWORD",
            new_password="NEW-TEST-PASSWORD"
        )
        # Should not raise any errors
        session.change_password(change_req)
        assert lib.dsmChangePW.call_count == 1
