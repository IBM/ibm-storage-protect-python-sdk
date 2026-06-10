import pytest
from unittest.mock import MagicMock, patch
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.backup import BackupRequest, BatchBackupRequest
from ibm_storage_protect.errors import TSMDataError, TSMOperationError, TSMResourceError
from ibm_storage_protect.c_api_bridge.c_api.load import lib

def test_backup_success():
    """Verify that a successful backup returns a valid result model."""
    lib.dsmInitEx.return_value = 0
    lib.dsmBindMC.return_value = 0
    lib.dsmBeginTxn.return_value = 0
    lib.dsmSendObj.return_value = 0
    lib.dsmSendData.return_value = 0
    lib.dsmEndSendObjEx.return_value = 0
    lib.dsmEndTxnEx.return_value = 0

    session = ClientSession()
    from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    client = DataClient(session)

    backup_spec = BackupRequest(
        Key="/myfs/file.txt",
        Body=b"file contents",
        Filespace="/myfs"
    )

    result = client.backup(backup_spec)
    assert result.status == "success"
    assert result.filespace == "/myfs"
    assert lib.dsmSendObj.call_count == 1
    assert lib.dsmSendData.call_count == 1
    assert lib.dsmEndTxnEx.call_count == 1

def test_backup_chunk_size_guard():
    """Verify that the backup helper raises ValueError if the body bytes exceed 4MB."""
    session = ClientSession()
    from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    client = DataClient(session)

    # Pass direct bytes (5MB) — validate_chunks raises eagerly before any C API calls
    backup_spec = BackupRequest(
        Key="/myfs/file.txt",
        Body=b"x" * (5 * 1024 * 1024),
        Filespace="/myfs"
    )

    with pytest.raises(ValueError) as exc_info:
        client.backup(backup_spec)
    
    assert "exceeds" in str(exc_info.value)
    # Native C calls should not be touched — validation happens before C API layer
    assert lib.dsmSendObj.call_count == 0

def test_backup_transaction_abort_on_failure():
    """Verify that any exception raised during the backup block causes a transaction rollback (DSM_VOTE_ABORT)."""
    lib.dsmBindMC.return_value = 0
    lib.dsmBeginTxn.return_value = 0
    lib.dsmSendObj.return_value = 0
    # Mock dsmSendData to return a C error (e.g. 11, storage full)
    lib.dsmSendData.return_value = 11 

    session = ClientSession()
    from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    client = DataClient(session)

    backup_spec = BackupRequest(
        Key="/myfs/file.txt",
        Body=b"file contents",
        Filespace="/myfs"
    )

    with pytest.raises(TSMResourceError):
        client.backup(backup_spec)

    # End transaction must be called to abort (vote = 2 / DSM_VOTE_ABORT)
    assert lib.dsmEndTxnEx.call_count == 1
    # Check that the mock dsmEndTxnEx was called with abort vote argument
    # (The signature is handle, vote, reason, etc.)
    args, kwargs = lib.dsmEndTxnEx.call_args
    # First argument is byref(end_in). We retrieve the struct using _obj.
    end_in = args[0]._obj
    assert end_in.vote == 2  # 2 corresponds to DSM_VOTE_ABORT

def test_group_reopen_and_modify(tmp_path):
    """Verify loading, reopening, adding member, query-based removal, and deleting a group."""
    from ibm_storage_protect import ClientSession, DataClient
    from ibm_storage_protect.data_models.backup import BackupRequest
    from unittest.mock import MagicMock, patch
    import json
    import os

    metadata_path = tmp_path / ".sp_groups.json"
    
    # 1. Setup mock dsmEndTxnEx to return group leader ID
    def mock_dsm_end_txn_ex(end_in_ptr, end_out_ptr):
        end_out = end_out_ptr.contents if hasattr(end_out_ptr, 'contents') else end_out_ptr._obj
        end_out.reason = 0
        end_out.groupLeaderObjId.hi = 1234
        end_out.groupLeaderObjId.lo = 5678
        return 0
    lib.dsmEndTxnEx.side_effect = mock_dsm_end_txn_ex
    lib.dsmGroupHandler.return_value = 0
    lib.dsmBeginTxn.return_value = 0
    lib.dsmDeleteObj.return_value = 0

    session = ClientSession()
    from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    client = DataClient(session)

    # 2. Create the group and save leader
    group = client.create_group("postgresql-db-backup", metadata_file=str(metadata_path))
    leader_backup = BackupRequest(Key="/db/manifest.json", Body=b"manifest")
    group.add_leader(leader_backup)
    group.close()

    assert group.leader_id == {"hi": 1234, "lo": 5678}
    assert os.path.exists(metadata_path)

    # 3. Load group from metadata
    loaded_group = client.load_group(str(metadata_path), "postgresql-db-backup")
    assert loaded_group.leader_id == {"hi": 1234, "lo": 5678}
    assert loaded_group.is_closed is True

    # 4. Reopen and add member
    loaded_group.reopen()
    assert loaded_group.is_open is True
    member_backup = BackupRequest(Key="/db/data_page1.dat", Body=b"data")
    loaded_group.add_member(member_backup)
    loaded_group.close()

    # 5. Remove member by key
    with patch("ibm_storage_protect.data_client.backup.QueryClient") as mock_query_class:
        mock_query_client = mock_query_class.return_value
        
        mock_result = MagicMock()
        mock_leader_meta = MagicMock()
        mock_leader_meta.is_group_leader = True
        mock_leader_meta.key = "/db/manifest.json"
        mock_leader_meta.ObjectId = "1234-5678"
        
        mock_member_meta = MagicMock()
        mock_member_meta.is_group_leader = False
        mock_member_meta.key = "/db/data_page1.dat"
        mock_member_meta.ObjectId = "9999-8888"
        
        mock_result.objects = [mock_leader_meta, mock_member_meta]
        mock_query_client.query_group_members.return_value = mock_result

        remove_res = loaded_group.remove_members(["/db/data_page1.dat"])
        assert remove_res.status == "success"

    # 6. Delete group
    delete_res = loaded_group.delete()
    assert delete_res.status == "success"

    # Verify that metadata is cleaned up
    with open(metadata_path, 'r') as f:
        meta_content = json.load(f)
    assert "postgresql-db-backup" not in meta_content

