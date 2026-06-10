"""
test_filesystem_integration.py – integration tests for the filesystem backup and restore scripts.
"""

# pylint: disable=unused-argument,import-error,wrong-import-position

import os
import sys
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

import pytest

# Resolve the paths to target src directories (both for filesystem example and the SDK itself)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")))

from protect_filesystem import fs_backup, fs_restore
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.errors.error_codes import SDKErrorCode

def test_read_file_in_chunks():
    """Verify that read_file_in_chunks yields correct data blocks."""
    mock_data = b"Hello, World!"
    with patch("builtins.open", mock_open(read_data=mock_data)):
        chunks = list(fs_backup.read_file_in_chunks("dummy_path", chunk_size=5))
        assert chunks == [b"Hello", b", Wor", b"ld!"]

@patch("protect_filesystem.fs_backup.ClientSession")
@patch("protect_filesystem.fs_backup.DataClient")
@patch("protect_filesystem.fs_backup.collect_files")
def test_backup_success(mock_collect_files, mock_data_client_class, mock_session_class, tmp_path):
    """Verify a successful filesystem backup run."""
    # Create mock files
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    file1 = source_dir / "file1.txt"
    file1.write_text("content1")
    file2 = source_dir / "file2.txt"
    file2.write_text("content2")
    
    mock_collect_files.return_value = [file1, file2]

    mock_session = mock_session_class.return_value
    mock_client = mock_data_client_class.return_value

    # Mock group handle
    mock_group = MagicMock()
    mock_group.leader_id = {"hi": 0, "lo": 42}
    mock_client.create_group.return_value = mock_group

    with patch("builtins.open", mock_open(read_data=b"dummy content")):
        result = fs_backup.backup_directory(str(source_dir), group_name="test-group")

    # Assert session lifecycle and backup were called
    mock_session.login.assert_called_once()
    mock_client.create_group.assert_called_once()
    mock_group.add_leader.assert_called_once()
    mock_group.add_member.assert_called()
    mock_group.close.assert_called_once()
    mock_session.logout.assert_called_once()
    
    assert result["group_name"] == "test-group"
    assert result["total_files"] == 2
    assert result["successful"] == 2
    assert result["failed"] == 0

@patch("protect_filesystem.fs_backup.collect_files")
def test_backup_directory_not_found(mock_collect_files):
    """Verify backup fails cleanly if source directory does not exist."""
    mock_collect_files.side_effect = SystemExit(1)

    with pytest.raises(SystemExit) as exc_info:
        fs_backup.backup_directory("/nonexistent/path")
    assert exc_info.value.code == 1

@patch("protect_filesystem.fs_backup.ClientSession")
@patch("protect_filesystem.fs_backup.collect_files")
def test_backup_auth_failure(mock_collect_files, mock_session_class, tmp_path):
    """Verify backup handles authentication errors gracefully."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    file1 = source_dir / "file1.txt"
    file1.write_text("content1")
    
    mock_collect_files.return_value = [file1]

    mock_session = mock_session_class.return_value
    mock_session.login.side_effect = TSMError(
        error_code=SDKErrorCode.INVALID_CREDENTIALS,
        message="Invalid credentials"
    )

    with pytest.raises(SystemExit) as exc_info:
        fs_backup.backup_directory(str(source_dir))
    assert exc_info.value.code == 1
    mock_session.login.assert_called_once()

@patch("protect_filesystem.fs_backup.ClientSession")
@patch("protect_filesystem.fs_backup.DataClient")
@patch("protect_filesystem.fs_backup.collect_files")
def test_backup_tsm_error_retryable(mock_collect_files, mock_data_client_class, mock_session_class, tmp_path):
    """Verify backup handling of a retryable TSMError during backup."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    file1 = source_dir / "file1.txt"
    file1.write_text("content1")
    
    mock_collect_files.return_value = [file1]

    mock_session = mock_session_class.return_value
    mock_client = mock_data_client_class.return_value

    # Mock group to raise a retryable TSMError on leader upload
    mock_group = MagicMock()
    mock_group.add_leader.side_effect = TSMError(
        error_code=SDKErrorCode.BACKUP_FAILED,
        message="Retryable backup failure",
        retry_recommended=True,
        retry_after=10
    )
    mock_client.create_group.return_value = mock_group

    with patch("builtins.open", mock_open(read_data=b"dummy content")):
        with pytest.raises(SystemExit) as exc_info:
            fs_backup.backup_directory(str(source_dir))
        assert exc_info.value.code == 1

    mock_session.login.assert_called_once()
    mock_client.create_group.assert_called_once()
    mock_session.logout.assert_called_once()

@patch("protect_filesystem.fs_backup.ClientSession")
@patch("protect_filesystem.fs_backup.DataClient")
@patch("protect_filesystem.fs_backup.collect_files")
def test_backup_tsm_error_non_retryable(mock_collect_files, mock_data_client_class, mock_session_class, tmp_path):
    """Verify backup handling of a non-retryable TSMError during backup."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    file1 = source_dir / "file1.txt"
    file1.write_text("content1")
    
    mock_collect_files.return_value = [file1]

    mock_session = mock_session_class.return_value
    mock_client = mock_data_client_class.return_value

    # Mock group to raise a non-retryable TSMError on leader upload
    mock_group = MagicMock()
    mock_group.add_leader.side_effect = TSMError(
        error_code=SDKErrorCode.BACKUP_FAILED,
        message="Critical backup failure",
        retry_recommended=False
    )
    mock_client.create_group.return_value = mock_group

    with patch("builtins.open", mock_open(read_data=b"dummy content")):
        with pytest.raises(SystemExit) as exc_info:
            fs_backup.backup_directory(str(source_dir))
        assert exc_info.value.code == 1

    mock_session.login.assert_called_once()
    mock_client.create_group.assert_called_once()
    mock_session.logout.assert_called_once()

@patch("protect_filesystem.fs_restore.ClientSession")
@patch("protect_filesystem.fs_restore.DataClient")
def test_restore_success(mock_data_client_class, mock_session_class, tmp_path):
    """Verify a successful filesystem restore run."""
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    mock_session = mock_session_class.return_value
    mock_client = mock_data_client_class.return_value

    # Mock restore result
    mock_member1 = MagicMock()
    mock_member1.key = "file1.txt"
    mock_member1.is_group_leader = True
    mock_member1.body = iter([b"chunk1", b"chunk2"])
    
    mock_member2 = MagicMock()
    mock_member2.key = "file2.txt"
    mock_member2.is_group_leader = False
    mock_member2.body = iter([b"chunk3", b"chunk4"])

    mock_result = MagicMock()
    mock_result.total_objects = 2
    mock_result.results = [mock_member1, mock_member2]
    mock_client.group_restore.return_value = mock_result

    result = fs_restore.restore_group(0, 42, str(dest_dir))

    # Assert restore client and session were used
    mock_session.login.assert_called_once()
    mock_client.group_restore.assert_called_once()
    mock_session.logout.assert_called_once()

    assert result["total_objects"] == 2
    assert result["successful"] == 2
    assert result["failed"] == 0
    assert result["leader_id"] == {"hi": 0, "lo": 42}

@patch("protect_filesystem.fs_restore.ClientSession")
def test_restore_auth_failure(mock_session_class, tmp_path):
    """Verify restore handles login failure gracefully."""
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    mock_session = mock_session_class.return_value
    mock_session.login.side_effect = TSMError(
        error_code=SDKErrorCode.INVALID_CREDENTIALS,
        message="Login failed"
    )

    with pytest.raises(SystemExit) as exc_info:
        fs_restore.restore_group(0, 42, str(dest_dir))
    assert exc_info.value.code == 1
    mock_session.login.assert_called_once()

@patch("protect_filesystem.fs_restore.ClientSession")
@patch("protect_filesystem.fs_restore.DataClient")
def test_restore_tsm_error_retryable(mock_data_client_class, mock_session_class, tmp_path):
    """Verify restore handling of a retryable TSMError during restore."""
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    mock_session = mock_session_class.return_value
    mock_client = mock_data_client_class.return_value

    # Mock restore to raise a retryable TSMError
    mock_client.group_restore.side_effect = TSMError(
        error_code=SDKErrorCode.RESTORE_FAILED,
        message="Retryable restore failure",
        retry_recommended=True,
        retry_after=5
    )

    with pytest.raises(SystemExit) as exc_info:
        fs_restore.restore_group(0, 42, str(dest_dir))
    assert exc_info.value.code == 1

    mock_session.login.assert_called_once()
    mock_client.group_restore.assert_called_once()
    mock_session.logout.assert_called_once()

@patch("protect_filesystem.fs_restore.ClientSession")
@patch("protect_filesystem.fs_restore.DataClient")
def test_restore_tsm_error_non_retryable(mock_data_client_class, mock_session_class, tmp_path):
    """Verify restore handling of a non-retryable TSMError during restore."""
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    mock_session = mock_session_class.return_value
    mock_client = mock_data_client_class.return_value

    # Mock restore to raise a non-retryable TSMError
    mock_client.group_restore.side_effect = TSMError(
        error_code=SDKErrorCode.RESTORE_FAILED,
        message="Critical restore failure",
        retry_recommended=False
    )

    with pytest.raises(SystemExit) as exc_info:
        fs_restore.restore_group(0, 42, str(dest_dir))
    assert exc_info.value.code == 1

    mock_session.login.assert_called_once()
    mock_client.group_restore.assert_called_once()
    mock_session.logout.assert_called_once()

# Made with Bob
