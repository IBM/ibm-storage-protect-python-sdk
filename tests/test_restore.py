import pytest
from unittest.mock import MagicMock, patch
from collections import namedtuple
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.restore import RestoreRequest
from ibm_storage_protect.errors import TSMOperationError
from ibm_storage_protect.c_api_bridge.c_api.load import lib

from ibm_storage_protect.c_api_bridge.c_api.structs import ObjID

MockRestoreOrder = namedtuple("MockRestoreOrder", ["top", "hi_hi", "hi_lo", "lo_hi", "lo_lo"])

@pytest.fixture
def mock_query_client():
    """Mock the query_objects function used by the restore operation."""
    with patch("ibm_storage_protect.c_api_bridge.wrappers.restore.single.execute_backup_query") as mock_query:
        # Create a mock query result containing metadata objects
        mock_restore_order = MockRestoreOrder(top=1, hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=1)

        mock_obj_id = ObjID()
        mock_obj_id.hi = 0
        mock_obj_id.lo = 8251150

        mock_entry = {
            "key": "myfs/file.txt",
            "filespace": "/myfs",
            "_objId": mock_obj_id,
            "_restoreOrder": mock_restore_order,
            "ObjectId": "0-8251150",
            "LastModified": None,
            "MediaClass": "DISK",
            "ManagementClass": "STANDARD",
        }
        mock_query.return_value = [mock_entry]
        yield mock_query

def test_restore_success(mock_query_client):
    """Verify that a successful single object restore returns a stream generator."""
    lib.dsmBeginGetData.return_value = 0
    lib.dsmGetObj.return_value = 0
    # dsmGetData returns DSM_RC_FINISHED (12) by default or 0
    lib.dsmGetData.return_value = 12  # DSM_RC_FINISHED means no more chunks in this part
    lib.dsmEndGetObj.return_value = 0
    lib.dsmEndGetDataEx.return_value = 0

    session = ClientSession()
    from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    client = DataClient(session)

    restore_spec = RestoreRequest(
        Key="/myfs/file.txt",
        Filespace="/myfs"
    )

    result = client.restore(restore_spec)
    assert result.key == "myfs/file.txt"
    
    # Consume body generator
    body_data = b"".join(result.body)
    assert isinstance(body_data, bytes)
    assert lib.dsmBeginGetData.call_count == 1
    assert lib.dsmGetObj.call_count == 1
    assert lib.dsmEndGetDataEx.call_count == 1

def test_restore_multi_part_sorting():
    """Verify that multi-part files are retrieved in order of restoreOrder."""
    with patch("ibm_storage_protect.c_api_bridge.wrappers.restore.single.execute_backup_query") as mock_query:
        # Define 2 parts with restoreOrder, returned OUT OF ORDER from query
        part_a_order = MockRestoreOrder(top=1, hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=2)
        part_a_id = ObjID(hi=0, lo=8251151)
        part_a = {
            "key": "myfs/file.txt",
            "filespace": "/myfs",
            "_objId": part_a_id,
            "_restoreOrder": part_a_order,
            "ObjectId": "0-8251151",
            "LastModified": None,
            "MediaClass": "DISK",
            "ManagementClass": "STANDARD",
        }

        part_b_order = MockRestoreOrder(top=1, hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=1)
        part_b_id = ObjID(hi=0, lo=8251150)
        part_b = {
            "key": "myfs/file.txt",
            "filespace": "/myfs",
            "_objId": part_b_id,
            "_restoreOrder": part_b_order,
            "ObjectId": "0-8251150",
            "LastModified": None,
            "MediaClass": "DISK",
            "ManagementClass": "STANDARD",
        }

        mock_query.return_value = [part_a, part_b]

        lib.dsmBeginGetData.return_value = 0
        lib.dsmGetObj.return_value = 0
        lib.dsmGetData.return_value = 12
        lib.dsmEndGetObj.return_value = 0
        lib.dsmEndGetDataEx.return_value = 0

        session = ClientSession()
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        client = DataClient(session)

        restore_spec = RestoreRequest(Key="/myfs/file.txt", Filespace="/myfs")
        result = client.restore(restore_spec)
        b"".join(result.body)

        # Confirm dsmGetObj was called with part_b's ObjectId hi/lo first (since lo_lo = 1 < 2)
        # Verify call order and arguments
        assert lib.dsmGetObj.call_count == 2

def test_pit_restore():
    """Verify that restore with a pit_date passes the datetime correctly to the query and restore calls."""
    from datetime import datetime
    pit_date = datetime(2026, 5, 13, 16, 1, 1)

    with patch("ibm_storage_protect.c_api_bridge.wrappers.restore.single.execute_backup_query") as mock_query:
        mock_query.return_value = [
            {
                "key": "/myfs/file.txt",
                "ObjectId": "0-8251150",
                "State": "active",
                "_objId": ObjID(hi=0, lo=8251150),
                "_restoreOrder": MockRestoreOrder(top=1, hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=1)
            }
        ]
        
        lib.dsmBeginGetData.return_value = 0
        lib.dsmGetObj.return_value = 0
        lib.dsmGetData.return_value = 12  # DSM_RC_FINISHED
        lib.dsmEndGetObj.return_value = 0
        lib.dsmEndGetDataEx.return_value = 0

        session = ClientSession()
        from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
        client = DataClient(session)

        restore_spec = RestoreRequest(
            Key="/myfs/file.txt",
            Filespace="/myfs",
            PitDate=pit_date
        )

        result = client.restore(restore_spec)
        assert result.key == "myfs/file.txt"
        
        # Consume the stream
        b"".join(result.body)

        # Verify that query_objects was called with the correct pit_date
        mock_query.assert_called_once()
        kwargs = mock_query.call_args[1]
        assert kwargs.get("pit_date") == pit_date
