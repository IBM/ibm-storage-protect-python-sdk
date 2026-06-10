import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from ibm_storage_protect import ClientSession, QueryClient
from ibm_storage_protect.data_models.query import (
    BackupQueryRequest,
    GroupQueryRequest,
    ListObjectsRequest,
    QueryFilespacesRequest,
    QueryObjectRequest,
    QueryMgmtClassesRequest,
)
from ibm_storage_protect.enums import ObjState, ObjType

@pytest.fixture
def query_client():
    session = ClientSession()
    from ibm_storage_protect.data_models.session import LoginCredentials; session.login(LoginCredentials(node="TEST-NODE", password="TEST-PASSWORD"))
    return QueryClient(session)

def test_query_object_success(query_client):
    """Verify that query_object returns a valid QueryObjectResult."""
    req = QueryObjectRequest(Filespace="/myfs", Key="/myfs/file.txt")
    
    mock_result = {
        "key": "myfs/file.txt",
        "filespace": "/myfs",
        "Size": 1024,
        "LastModified": datetime(2026, 5, 13, 16, 1, 1),
        "ObjectId": "1234-5678",
        "State": "active",
        "Owner": "root",
    }

    with patch("ibm_storage_protect.query.QueryOperation.query_object") as mock_op:
        mock_op.return_value = mock_result
        res = query_client.query_object(req)
        
        mock_op.assert_called_once()
        assert res.key == "myfs/file.txt"
        assert res.size == 1024
        assert res.owner == "root"

def test_execute_backup_query_success(query_client):
    """Verify that query_objects returns a valid BackupQueryResult."""
    req = BackupQueryRequest(Filespace="/myfs", Key="/myfs/*.txt")
    
    mock_results = [
        {
            "key": "myfs/file1.txt",
            "filespace": "/myfs",
            "Size": 512,
            "State": "active",
        },
        {
            "key": "myfs/file2.txt",
            "filespace": "/myfs",
            "Size": 1024,
            "State": "active",
        }
    ]

    with patch("ibm_storage_protect.query.execute_backup_query") as mock_op:
        mock_op.return_value = mock_results
        res = query_client.query_objects(req)
        
        mock_op.assert_called_once()
        assert res.total_objects == 2
        assert res.objects[0]["key"] == "myfs/file1.txt"
        assert res.objects[1]["Size"] == 1024

def test_execute_group_query_success(query_client):
    """Verify that query_group_members returns a valid GroupQueryResult."""
    req = GroupQueryRequest(
        Filespace="/myfs",
        GroupLeaderObjIdHi=1234,
        GroupLeaderObjIdLo=5678
    )
    
    mock_results = [
        {
            "key": "/myfs/manifest.json",
            "filespace": "/myfs",
            "Size": 1024,
            "ObjectId": "1234-5678",
            "State": "active",
            "is_group_leader": True,
        },
        {
            "key": "/myfs/data_page1.dat",
            "filespace": "/myfs",
            "Size": 2048,
            "ObjectId": "9999-8888",
            "State": "active",
            "is_group_leader": False,
        }
    ]

    with patch("ibm_storage_protect.query.execute_group_query") as mock_op:
        mock_op.return_value = mock_results
        res = query_client.query_group_members(req)
        
        mock_op.assert_called_once()
        assert res.total_objects == 2
        assert res.objects[0].is_group_leader is True
        assert res.objects[1].key == "/myfs/data_page1.dat"

def test_list_objects_success(query_client):
    """Verify that list_objects returns a valid ListObjectsResult."""
    req = ListObjectsRequest(filespace="/myfs", prefix="/backup", max_keys=10)
    
    mock_result = {
        "Name": "/myfs",
        "Prefix": "/backup",
        "Contents": [
            {"key": "/myfs/backup/file1.txt", "Size": 100},
            {"key": "/myfs/backup/file2.txt", "Size": 200}
        ],
        "KeyCount": 2,
        "MaxKeys": 10,
    }

    with patch("ibm_storage_protect.query.QueryOperation.list_objects") as mock_op:
        mock_op.return_value = mock_result
        res = query_client.list_objects(req)
        
        mock_op.assert_called_once()
        assert res.key_count == 2
        assert res.max_keys == 10
        assert res.contents[0]["key"] == "/myfs/backup/file1.txt"

def test_query_filespaces_success(query_client):
    """Verify that query_filespaces returns a valid QueryFilespacesResult."""
    req = QueryFilespacesRequest(fs_pattern="/myfs")
    
    mock_results = [
        {
            "filespace": "/myfs",
            "Occupancy": 5000,
            "Capacity": 10000,
        }
    ]

    with patch("ibm_storage_protect.query.QueryOperation.query_filespaces") as mock_op:
        mock_op.return_value = mock_results
        res = query_client.query_filespaces(req)
        
        mock_op.assert_called_once()
        assert res.total_filespaces == 1
        assert res.filespaces[0]["filespace"] == "/myfs"
        assert res.filespaces[0]["Occupancy"] == 5000

def test_query_mgmt_classes_success(query_client):
    """Verify that query_mgmt_classes returns a valid QueryMgmtClassesResult."""
    req = QueryMgmtClassesRequest(mc_name="*")
    
    mock_results = [
        {
            "Class": "STANDARD",
            "Description": "Default Management Class",
        }
    ]

    with patch("ibm_storage_protect.query.QueryOperation.query_mgmt_classes") as mock_op:
        mock_op.return_value = mock_results
        res = query_client.query_mgmt_classes(req)
        
        mock_op.assert_called_once()
        assert res.total_classes == 1
        assert res.management_classes[0]["Class"] == "STANDARD"
