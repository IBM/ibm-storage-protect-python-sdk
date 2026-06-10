"""
IBM Storage Protect Client SDK - Data Management Client

This module provides the high-level data management interface for IBM Storage Protect
operations, including backup, restore, and group management functionality. It serves
as the primary user-facing API for data protection operations.

The DataClient class acts as a unified interface that delegates backup operations
to specialized backup clients and restore operations to specialized restore clients,
maintaining backward compatibility while providing better code organization.

Key Responsibilities:
---------------------
1. **Unified Interface**: Single entry point for all data management operations
2. **Delegation**: Routes operations to specialized client classes
3. **Backward Compatibility**: Maintains the same API surface for existing users
4. **Session Management**: Handles session lifecycle and resource cleanup
5. **Error Handling**: Comprehensive error handling with structured logging

Operation Types Supported:
--------------------------
- Single Backup: Back up individual objects with full control
- Batch Backup: Efficiently back up multiple objects in transactions
- Group Backup: Manage peer group backups with leader and members
- Single Restore: Restore individual backed-up objects
- Batch Restore: Restore multiple objects efficiently
- Group Restore: Restore all members of a group backup

Architecture:
-------------
DataClient (this file)
├── SingleBackupClient (single_backup.py) - Single object backups
├── BatchBackupClient (batch_backup.py) - Batch backups
├── GroupBackupClient (group_backup.py) - Group backups
├── SingleRestoreClient (single_restore.py) - Single object restores
├── BatchRestoreClient (batch_restore.py) - Batch restores
└── GroupRestoreClient (group_restore.py) - Group restores

Example Usage:
--------------
    # Initialize client (same as before)
    client = DataClient(session)

    # Single backup
    backup = BackupRequest(Key="/data/file.txt", Body=b"content")
    result = client.backup(backup)

    # Single restore
    restore = RestoreRequest(Key="/data/file.txt", Filespace="/myfs")
    result = client.restore(restore)

    # Group backup
    group = client.create_group("my-group", filespace="/myfs")
    group.add_leader(BackupRequest(Key="/leader.json", Body=b"{}"))
    group.add_member(BackupRequest(Key="/member1.dat", Body=b"data"))
    group.close()

See Also:
---------
- single_backup.SingleBackupClient: Single backup operations
- batch_backup.BatchBackupClient: Batch backup operations
- group_backup.GroupBackupClient: Group backup operations
- single_restore.SingleRestoreClient: Single restore operations
- batch_restore.BatchRestoreClient: Batch restore operations
- group_restore.GroupRestoreClient: Group restore operations
- base.BaseClient: Base class with session management
"""
# pylint: disable=line-too-long

from typing import Optional

from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_client.backup.single import SingleBackupClient
from ibm_storage_protect.data_client.backup.batch import BatchBackupClient
from ibm_storage_protect.data_client.backup.group import GroupBackupClient, GroupHandle
from ibm_storage_protect.data_client.restore.single import SingleRestoreClient
from ibm_storage_protect.data_client.restore.batch import BatchRestoreClient
from ibm_storage_protect.data_client.restore.group import GroupRestoreClient
from ibm_storage_protect.data_models.backup import (
    BackupRequest,
    BackupResult,
    BatchBackupRequest,
    BatchBackupResult,
)
from ibm_storage_protect.data_models.restore import (
    BatchRestoreRequest,
    BatchRestoreResult,
    GroupRestoreRequest,
    GroupRestoreResult,
    RestoreRequest,
    RestoreResult,
)
from ibm_storage_protect.logger import get_logger
from ibm_storage_protect.session import ClientSession

# Module-level logger for structured logging
_logger = get_logger(__name__)


class DataClient(BaseClient):
    """
    High-level data management client for IBM Storage Protect operations.

    This is the primary user-facing interface for backup and restore operations.
    It provides type-safe, validated methods for all data protection operations
    by delegating to specialized backup and restore clients internally.

    The client handles:
    - Unified interface for backup and restore operations
    - Delegation to specialized clients
    - Session management and lifecycle
    - Error handling and logging
    - Resource cleanup

    Attributes
    ----------
    _session : ClientSession
        Active session with IBM Storage Protect server
    _single_backup_client : SingleBackupClient
        Internal client for single backup operations
    _batch_backup_client : BatchBackupClient
        Internal client for batch backup operations
    _group_backup_client : GroupBackupClient
        Internal client for group backup operations
    _single_restore_client : SingleRestoreClient
        Internal client for single restore operations
    _batch_restore_client : BatchRestoreClient
        Internal client for batch restore operations
    _group_restore_client : GroupRestoreClient
        Internal client for group restore operations

    Methods
    -------
    backup(backup_request)
        Back up a single object
    batch_backup(batch_request)
        Back up multiple objects in batch
    restore(restore_request)
        Restore a single object
    batch_restore(batch_request)
        Restore multiple objects in batch
    group_restore(group_request)
        Restore all members of a group
    create_group(name, filespace, members, metadata_file)
        Create a new group backup handle
    load_group(filepath, name, filespace)
        Load existing group from metadata file
    get_group(name, leader_id, filespace, metadata_file)
        Get group handle with known leader_id

    Notes
    -----
    - Inherits from BaseClient for session management
    - All operations use structured logging
    - Errors are mapped to SDK exceptions
    - Supports context manager protocol
    - Maintains backward compatibility with previous API

    See Also
    --------
    BaseClient : Base class with session management
    SingleBackupClient : Single backup operations
    BatchBackupClient : Batch backup operations
    GroupBackupClient : Group backup operations
    SingleRestoreClient : Single restore operations
    BatchRestoreClient : Batch restore operations
    GroupRestoreClient : Group restore operations
    GroupHandle : Handle for group operations
    """

    def __init__(self, session: ClientSession):
        """
        Initialize the data management client with a session.

        Parameters
        ----------
        session : ClientSession
            Active IBM Storage Protect session
        """
        super().__init__(session)

        # Initialize specialized clients for delegation
        self._single_backup_client = SingleBackupClient(session)
        self._batch_backup_client = BatchBackupClient(session)
        self._group_backup_client = GroupBackupClient(session)
        self._single_restore_client = SingleRestoreClient(session)
        self._batch_restore_client = BatchRestoreClient(session)
        self._group_restore_client = GroupRestoreClient(session)

        _logger.debug(
            "DataClient initialized with specialized operation clients",
            extra={
                'event_type': 'client.initialized',
                'session_handle': getattr(session, '_session_id', None)
            }
        )

    # ==================== Backup Operations (Delegated to Backup Clients) ====================

    def backup(self, backup_request: BackupRequest) -> BackupResult:
        """
        Back up a single object to IBM Storage Protect.

        This method delegates to SingleBackupClient.backup() to handle the complete
        backup workflow: validation, filespace registration, data transformation,
        C API execution, and result mapping.

        Parameters
        ----------
        backup_request : BackupRequest
            Backup request model with Key, Body, Filespace, etc.

        Returns
        -------
        BackupResult
            Result with status, filespace, high_level, low_level, and stats

        Raises
        ------
        ValueError
            If Key is empty or invalid
        TSMError
            If backup operation fails

        See Also
        --------
        SingleBackupClient.backup : Actual implementation
        batch_backup : Back up multiple objects efficiently
        """
        return self._single_backup_client.backup(backup_request)

    def batch_backup(self, batch_request: BatchBackupRequest) -> BatchBackupResult:
        """
        Back up multiple objects in batch for improved efficiency.

        This method delegates to BatchBackupClient.batch_backup() to handle batch
        backup operations with optimized transactions.

        Parameters
        ----------
        batch_request : BatchBackupRequest
            Batch backup request with Objects list, Filespace, and MaxPerTxn

        Returns
        -------
        BatchBackupResult
            Result with status, results list, total_objects, successful, and failed counts

        Raises
        ------
        TSMError
            If batch operation fails completely

        See Also
        --------
        BatchBackupClient.batch_backup : Actual implementation
        backup : Back up a single object
        """
        return self._batch_backup_client.batch_backup(batch_request)

    def create_group(self, name, filespace="/", members=None, metadata_file=".sp_groups.json") -> GroupHandle:
        """
        Create a new group backup with optional initial members.

        This method delegates to GroupBackupClient.create_group() to create a
        GroupHandle instance that manages a group backup operation.

        Parameters
        ----------
        name : str
            Unique name for the group (used as group tag)
        filespace : str, optional
            Target filespace. Defaults to "/".
        members : list, optional
            List of BackupRequest objects to add as members.
            If provided, the group is automatically closed after adding all members.
        metadata_file : str, optional
            Path to JSON file for persisting group metadata.
            Defaults to ".sp_groups.json" in the current directory.

        Returns
        -------
        GroupHandle
            Handle for managing the group backup

        Raises
        ------
        TSMError
            If group creation or member addition fails

        See Also
        --------
        GroupBackupClient.create_group : Actual implementation
        load_group : Load an existing group from metadata
        get_group : Get a group handle with known leader_id
        """
        return self._group_backup_client.create_group(name, filespace, members, metadata_file)

    def load_group(self, filepath, name, filespace="/") -> GroupHandle:
        """
        Load an existing group backup from a metadata file.

        This method delegates to GroupBackupClient.load_group() to reconstruct a
        GroupHandle from previously saved metadata.

        Parameters
        ----------
        filepath : str
            Path to the JSON metadata file containing group information
        name : str
            Name of the group to load from the metadata
        filespace : str, optional
            Filespace override. Defaults to "/" or uses the filespace stored in metadata.

        Returns
        -------
        GroupHandle
            Handle for the loaded group

        Raises
        ------
        FileNotFoundError
            If the metadata file doesn't exist
        ValueError
            If the specified group name is not found in the metadata
        json.JSONDecodeError
            If the metadata file is not valid JSON

        See Also
        --------
        GroupBackupClient.load_group : Actual implementation
        create_group : Create a new group
        get_group : Get a group handle with known leader_id
        """
        return self._group_backup_client.load_group(filepath, name, filespace)

    def get_group(self, name, leader_id, filespace="/", metadata_file=".sp_groups.json") -> GroupHandle:
        """
        Get a group handle using a known leader ID.

        This method delegates to GroupBackupClient.get_group() to create a GroupHandle
        for an existing group when you already know the leader_id.

        Parameters
        ----------
        name : str
            Name for the group (used for logging and identification)
        leader_id : dict
            The leader object's ID with 'hi' and 'lo' keys
        filespace : str, optional
            Target filespace. Defaults to "/".
        metadata_file : str, optional
            Path for metadata persistence if needed. Defaults to ".sp_groups.json".

        Returns
        -------
        GroupHandle
            Handle for the group

        See Also
        --------
        GroupBackupClient.get_group : Actual implementation
        create_group : Create a new group
        load_group : Load a group from metadata file
        """
        return self._group_backup_client.get_group(name, leader_id, filespace, metadata_file)

    # ==================== Restore Operations (Delegated to Restore Clients) ====================

    def restore(self, restore_request: RestoreRequest) -> RestoreResult:
        """
        Restore a single object from IBM Storage Protect.

        This method delegates to SingleRestoreClient.restore() to handle the complete
        restore workflow: validation, data retrieval, and result mapping.

        Parameters
        ----------
        restore_request : RestoreRequest
            Restore request model with Key, Filespace, ObjState, PitDate, etc.

        Returns
        -------
        RestoreResult
            Result with key, body (generator), last_modified, object_id, etc.

        Raises
        ------
        TSMError
            If restore operation fails

        Notes
        -----
        - Body is returned as a generator for memory efficiency
        - Supports point-in-time restore via PitDate parameter
        - Supports partial restore via Offset and Length parameters

        See Also
        --------
        SingleRestoreClient.restore : Actual implementation
        batch_restore : Restore multiple objects efficiently
        """
        return self._single_restore_client.restore(restore_request)

    def batch_restore(self, batch_request: BatchRestoreRequest) -> BatchRestoreResult:
        """
        Restore multiple objects in batch for improved efficiency.

        This method delegates to BatchRestoreClient.batch_restore() to handle batch
        restore operations with optimized performance.

        Parameters
        ----------
        batch_request : BatchRestoreRequest
            Batch restore request with objects list and Filespace

        Returns
        -------
        BatchRestoreResult
            Result with Results list and TotalObjects count

        Raises
        ------
        TSMError
            If batch operation fails

        See Also
        --------
        BatchRestoreClient.batch_restore : Actual implementation
        restore : Restore a single object
        """
        return self._batch_restore_client.batch_restore(batch_request)

    def group_restore(self, group_request: GroupRestoreRequest) -> GroupRestoreResult:
        """
        Restore all members of a group backup.

        This method delegates to GroupRestoreClient.group_restore() to restore an
        entire group backup, including the leader and all member objects.

        Parameters
        ----------
        group_request : GroupRestoreRequest
            Group restore request with GroupLeaderObjIdHi, GroupLeaderObjIdLo, Filespace, etc.

        Returns
        -------
        GroupRestoreResult
            Result with Results list (including leader and members) and TotalObjects count

        Raises
        ------
        TSMError
            If group restore operation fails

        Notes
        -----
        - Restores leader and all members atomically
        - Each result includes is_group_leader flag
        - Body for each object is returned as a generator

        See Also
        --------
        GroupRestoreClient.group_restore : Actual implementation
        """
        return self._group_restore_client.group_restore(group_request)

    # ==================== Shared Properties and Methods ====================

    @property
    def owner(self) -> Optional[str]:
        """
        Get the owner name for operations.

        Returns the owner name from the session, or None if not set.
        This is used as the default owner for backup and restore operations.

        Returns
        -------
        Optional[str]
            Owner name or None if not set

        Example
        -------
        >>> client = DataClient(session)
        >>> print(client.owner)
        'myuser'
        """
        return self._single_backup_client._get_owner() or None

    @property
    def _session(self) -> ClientSession:
        """
        Get the active session instance.

        Returns
        -------
        ClientSession
            Active IBM Storage Protect session
        """
        return self.__session

    @_session.setter
    def _session(self, value: ClientSession):
        """
        Set the active session instance.

        Also updates the session for all internal specialized clients.

        Parameters
        ----------
        value : ClientSession
            Session instance to set
        """
        self.__session = value
        # Update session for all internal clients
        if hasattr(self, '_single_backup_client'):
            self._single_backup_client._session = value
        if hasattr(self, '_batch_backup_client'):
            self._batch_backup_client._session = value
        if hasattr(self, '_group_backup_client'):
            self._group_backup_client._session = value
        if hasattr(self, '_single_restore_client'):
            self._single_restore_client._session = value
        if hasattr(self, '_batch_restore_client'):
            self._batch_restore_client._session = value
        if hasattr(self, '_group_restore_client'):
            self._group_restore_client._session = value

    def __enter__(self):
        """
        Context manager entry: return self for with statement.

        Enables using DataClient with Python's context manager protocol:

        Example
        -------
        >>> with DataClient(session) as client:
        ...     result = client.backup(backup_request)

        Returns
        -------
        DataClient
            Self reference for context manager
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: cleanup resources if needed.

        Called automatically when exiting a with statement. Currently performs
        no cleanup as session management is handled separately.

        Parameters
        ----------
        exc_type : type
            Exception type if an exception occurred
        exc_val : Exception
            Exception instance if an exception occurred
        exc_tb : traceback
            Traceback object if an exception occurred

        Returns
        -------
        None
            Does not suppress exceptions (returns None/False)
        """
        return False

    def __repr__(self) -> str:
        """
        String representation of DataClient.

        Returns
        -------
        str
            String representation showing session information

        Example
        -------
        >>> client = DataClient(session)
        >>> print(repr(client))
        'DataClient(session=<ClientSession object>)'
        """
        return f"DataClient(session={self._session})"

# Made with Bob
