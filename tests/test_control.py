import pytest
from unittest.mock import MagicMock, patch
from ibm_storage_protect import ClientSession, ControlClient
from ibm_storage_protect.data_models.filespace import (
    FilespaceRegisterRequest,
    FilespaceUpdateRequest,
    FilespaceDeleteRequest,
)
from ibm_storage_protect.data_models.object import (
    ObjectDeleteRequest,
    ObjectDeleteByIdRequest,
    ObjectRenameRequest,
    ObjectUpdateRequest,
)
from ibm_storage_protect.errors import TSMError
from ibm_storage_protect.c_api_bridge.c_api.load import lib

def test_register_filespace_success():
    """Verify filespace registration C call invocation and return result mapping."""
    lib.dsmRegisterFS.return_value = 0  # DSM_RC_OK

    with ClientSession() as session:
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        control = ControlClient(session)

        result = control.register_filespace(FilespaceRegisterRequest(filespace="/myfs"))
        assert result.status == "success"
        assert result.filespace == "/myfs"
        assert lib.dsmRegisterFS.call_count == 1

def test_register_filespace_idempotent():
    """Verify filespace registration handles DSM_RC_FS_ALREADY_REGED (2062) as success."""
    lib.dsmRegisterFS.return_value = 2062  # DSM_RC_FS_ALREADY_REGED

    with ClientSession() as session:
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        control = ControlClient(session)

        # Should not raise an error even though server return code indicates "already exists"
        result = control.register_filespace(FilespaceRegisterRequest(filespace="/myfs"))
        assert result.status == "success"
        assert result.filespace == "/myfs"

def test_update_filespace():
    """Verify that update filespace triggers dsmUpdateFS with proper flags."""
    lib.dsmUpdateFS.return_value = 0

    with ClientSession() as session:
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        control = ControlClient(session)

        result = control.update_filespace(FilespaceUpdateRequest(
            filespace="/myfs",
            occupancy=2048,
            capacity=4096
        ))
        assert result.status == "success"
        assert lib.dsmUpdateFS.call_count == 1

def test_delete_filespace():
    """Verify that delete filespace calls dsmDeleteFS with repository parameter."""
    lib.dsmDeleteFS.return_value = 0

    with ClientSession() as session:
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        control = ControlClient(session)

        result = control.delete_filespace(FilespaceDeleteRequest(filespace="/myfs"))
        assert result.filespace == "/myfs"
        assert lib.dsmDeleteFS.call_count == 1

def test_delete_object_by_name():
    """Verify that delete by name maps correctly and executes C deletion transaction."""
    lib.dsmBeginTxn.return_value = 0
    lib.dsmDeleteObj.return_value = 0
    lib.dsmEndTxnEx.return_value = 0

    with ClientSession() as session:
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        control = ControlClient(session)

        result = control.delete_by_name(ObjectDeleteRequest(
            filespace="/myfs",
            key="/file.txt"
        ))
        assert result.key == "/file.txt"
        assert lib.dsmDeleteObj.call_count == 1
        assert lib.dsmEndTxnEx.call_count == 1

def test_rename_object_with_merge():
    """Verify rename object with merge option enabled."""
    lib.dsmBeginTxn.return_value = 0
    lib.dsmRenameObj.return_value = 0
    lib.dsmEndTxnEx.return_value = 0

    with ClientSession() as session:
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        control = ControlClient(session)

        result = control.rename(ObjectRenameRequest(
            filespace="/myfs",
            key="/file.txt",
            new_key="/archive.txt",
            merge=True
        ))
        assert result.old_key == "/file.txt"
        assert result.new_key == "/archive.txt"
        assert lib.dsmRenameObj.call_count == 1
