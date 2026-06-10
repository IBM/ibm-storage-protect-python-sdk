import pytest
from ibm_storage_protect.errors import (
    TSMError,
    TSMConnectionError,
    TSMAuthenticationError,
    TSMResourceError,
    TSMSystemError,
)
from ibm_storage_protect.errors.error_codes import SDKErrorCode
from ibm_storage_protect.errors.mapper import map_c_code_to_exception
from ibm_storage_protect.data_models.session import LoginCredentials

def test_exception_properties():
    """Verify that exception subclasses have correct default metadata properties."""
    conn_err = TSMConnectionError(
        error_code=SDKErrorCode.NETWORK_ERROR,
        message="Network timeout"
    )
    assert conn_err.category == "CONNECTION"
    assert conn_err.severity_level == "HIGH"
    assert conn_err.is_retryable is True
    assert conn_err.retry_after == 30

    auth_err = TSMAuthenticationError(
        error_code=SDKErrorCode.INVALID_CREDENTIALS,
        message="Login rejected"
    )
    assert auth_err.category == "AUTHENTICATION"
    assert auth_err.severity_level == "HIGH"
    assert auth_err.is_retryable is False

def test_c_code_mapping():
    """Verify that native C return codes are mapped to the correct Python exceptions."""
    # 2021: DSM_RC_COMM_ERROR -> TSMConnectionError
    exc = map_c_code_to_exception(2021, "Communication link failure")
    assert isinstance(exc, TSMConnectionError)
    assert exc.error_code == SDKErrorCode.NETWORK_ERROR
    assert exc.is_retryable is True

    # 52: DSM_RC_REJECT_VERIFIER_EXPIRED -> TSMAuthenticationError
    exc = map_c_code_to_exception(52, "Expired verifier")
    assert isinstance(exc, TSMAuthenticationError)
    assert exc.error_code == SDKErrorCode.PASSWORD_EXPIRED
    assert exc.is_retryable is False

    # 11: DSM_RC_NO_RESOURCES -> TSMResourceError
    exc = map_c_code_to_exception(11, "No space available")
    assert isinstance(exc, TSMResourceError)
    assert exc.error_code == SDKErrorCode.STORAGE_FULL
    assert exc.is_retryable is True
    assert exc.retry_after == 300

def test_unmapped_c_code_fallback():
    """Verify that unmapped C API codes fall back to TSMSystemError (TSM-9105)."""
    exc = map_c_code_to_exception(9999, "Mystery error")
    assert isinstance(exc, TSMSystemError)
    assert exc.error_code == SDKErrorCode.UNEXPECTED_ERROR
    assert exc.is_retryable is False

def test_exception_serialization():
    """Verify that exception properties serialize to a dictionary correctly."""
    err = TSMConnectionError(
        error_code=SDKErrorCode.NETWORK_ERROR,
        message="Timeout",
        details={"server": "sp-server"}
    )
    data = err.to_dict()
    assert data["error_code"] == "TSM-1101"
    assert data["category"] == "CONNECTION"
    assert data["severity"] == "HIGH"
    assert data["retry_recommended"] is True
    assert data["retry_after"] == 30
    assert data["details"] == {"server": "sp-server"}

def test_credential_sanitization():
    """Verify that node credentials (passwords) are sanitized/redacted when serialized."""
    creds = LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD")
    
    # 1. Pydantic string representation (model dump)
    dump_data = creds.model_dump()
    assert dump_data["password"] == "TEST-PASSWORD"  # Pydantic holds it
    
    # 2. String representation of the login model should not show the password
    rep = repr(creds)
    assert "TEST-PASSWORD" not in rep
    assert "password" in rep or "Password" in rep
