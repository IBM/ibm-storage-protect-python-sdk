import logging
import pytest
from unittest.mock import MagicMock, patch
from ibm_storage_protect.logger import (
    configure_logging,
    get_logger,
    set_sdk_log_level,
    set_log_context,
    clear_log_context,
    get_log_context,
    create_session_id,
    create_operation_id,
    log_operation,
    LogConfig
)
from ibm_storage_protect import initialize_environment, ClientSession
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.c_api_bridge.c_api.load import lib


def test_set_sdk_log_level():
    """Verify that dynamic log levels can be adjusted dynamically."""
    sdk_logger = logging.getLogger("ibm_storage_protect")
    
    # Configure logger first
    configure_logging(LogConfig(console_level="INFO"))
    
    # Root SDK logging level should be DEBUG (as configure_logging sets the root sdk logger to DEBUG and handler level to console_level)
    # Let's check dynamic levels adjustments
    set_sdk_log_level("DEBUG")
    assert sdk_logger.level == logging.DEBUG
    
    set_sdk_log_level("WARNING")
    assert sdk_logger.level == logging.WARNING


def test_log_context():
    """Verify set, get, and clear log context."""
    clear_log_context()
    ctx = get_log_context()
    assert all(v is None for v in ctx.values())
    
    set_log_context(session_handle="sess-123", object_key="obj-456")
    ctx = get_log_context()
    assert ctx["session_handle"] == "sess-123"
    assert ctx["object_key"] == "obj-456"
    assert ctx["correlation_id"] == "sess-123"
    
    clear_log_context()
    ctx = get_log_context()
    assert all(v is None for v in ctx.values())


def test_log_operation_context_manager():
    """Verify that log_operation records execution details."""
    logger = get_logger("test_op")
    mock_session = MagicMock()
    mock_session._session_id = "sess-789"
    
    with patch.object(logger, "info") as mock_info:
        with log_operation(logger, "test_operation", mock_session, object_key="obj-123"):
            pass
            
        # Should have log statements for started and completed
        assert mock_info.call_count >= 2
        
        # Check context
        calls = [call[1] for call in mock_info.call_args_list]
        event_types = [c.get("extra", {}).get("event_type") for c in calls if "extra" in c]
        assert any(et == "test_operation.started" for et in event_types)
        assert any(et == "test_operation.completed" for et in event_types)


def test_initialize_environment():
    """Verify initialize_environment calls dsmSetUp."""
    # Reset mock dsmSetUp
    lib.dsmSetUp.reset_mock()
    lib.dsmSetUp.return_value = 0
    
    rc = initialize_environment(
        dsmi_dir="C:\\tivoli",
        dsmi_config="C:\\tivoli\\dsm.opt",
        dsmi_log="C:\\tivoli\\dsmerror.log",
        log_name="TEST_APP",
        b_service=True
    )
    
    assert rc == 0
    assert lib.dsmSetUp.call_count == 1
    # Check that it passed some struct with correct values
    call_args = lib.dsmSetUp.call_args[0]
    b_service_val = call_args[0]
    env_setup_struct = call_args[1]._obj
    
    assert b_service_val is True
    assert env_setup_struct.dsmiDir == b"C:\\tivoli"
    assert env_setup_struct.dsmiConfig == b"C:\\tivoli\\dsm.opt"
    assert env_setup_struct.dsmiLog == b"C:\\tivoli\\dsmerror.log"
    assert env_setup_struct.logName == b"TEST_APP"


def test_log_server_event(mock_lib_reset):
    """Verify log_server_event calls dsmLogEventEx."""
    lib.dsmLogEventEx.reset_mock()
    lib.dsmLogEventEx.return_value = 0
    lib.dsmInitEx.return_value = 0
    
    session = ClientSession()
    session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    
    # We call log_server_event on ClientSession
    session.log_server_event(
        message="This is a test event log message",
        severity="warning",
        log_type="server",
        app_name="TESTAPP",
        app_msg_id="MSG0002"
    )
    
    assert lib.dsmLogEventEx.call_count == 1
    
    # Verify input struct arguments
    call_args = lib.dsmLogEventEx.call_args[0]
    log_ex_in = call_args[1]._obj
    
    assert log_ex_in.message == b"This is a test event log message"
    assert log_ex_in.appMsgID == b"MSG0002"
    assert log_ex_in.severity == 1  # logSeverity_t enum for Warning
    assert log_ex_in.appName == b"TESTAPP"
