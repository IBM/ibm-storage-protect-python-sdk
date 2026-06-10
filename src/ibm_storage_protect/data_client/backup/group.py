"""
IBM Storage Protect Client SDK - Group Backup Operation

This module provides group backup functionality for IBM Storage Protect.
It handles peer group backups with leader/member relationships, allowing
multiple related objects to be backed up and managed as a cohesive unit.

Key Responsibilities:
---------------------
1. **Group Management**: Create, manage, and delete group backups
2. **Leader/Member Relationships**: Manage group leader and member objects
3. **Metadata Persistence**: Save and load group metadata to/from JSON files
4. **Group Operations**: Reopen, remove members, assign members, delete groups
5. **Error Handling**: Comprehensive error handling with structured logging

Classes:
--------
- GroupHandle: Handle for managing group backup operations
- GroupOperationWrapper: Wrapper for group operations with BackupRequest compatibility
- GroupBackupClient: Client for group backup operations

Example Usage:
--------------
    from ibm_storage_protect.data_client.group_backup import GroupBackupClient
    from ibm_storage_protect.data_models.backup import BackupRequest
    
    client = GroupBackupClient(session)
    
    # Create a new group
    group = client.create_group("my-group", filespace="/myfs")
    group.add_leader(BackupRequest(Key="/leader.json", Body=b"{}"))
    group.add_member(BackupRequest(Key="/member1.dat", Body=b"data"))
    group.close()
    
    # Load existing group
    group = client.load_group(".sp_groups.json", "my-group")
    group.reopen()
    group.add_member(BackupRequest(Key="/member2.dat", Body=b"more"))
    group.close()
"""
# pylint: disable=line-too-long,too-many-instance-attributes

import json
import os
from datetime import datetime
from typing import Optional

from ibm_storage_protect.c_api_bridge.wrappers.filespace import register_filespace as _register_filespace
from ibm_storage_protect.c_api_bridge.wrappers.backup import GroupBackupOperation
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    encode_obj_info,
    extract_enum_value,
    extract_mount_wait,
    validate_chunks,
)
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.backup import (
    BackupRequest,
    BeginGroupBackupRequest,
    GroupAssignToMembersRequest,
    GroupDeleteRequest,
    GroupOperationResult,
    GroupRemoveMembersRequest,
    ReopenGroupBackupRequest,
)
from ibm_storage_protect.enums import ObjType
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import get_logger, log_operation
from ibm_storage_protect.logger.context import set_log_context
from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.data_models.query import GroupQueryRequest

# Module-level logger for structured logging
_logger = get_logger(__name__)


class GroupOperationWrapper:
    """
    Wrapper for GroupBackupOperation that handles BackupRequest to dict conversion.
    
    This internal class bridges the gap between user-facing BackupRequest models and
    the dictionary format expected by the low-level GroupBackupOperation.
    
    Attributes
    ----------
    _operation : GroupBackupOperation
        Underlying group backup operation handler
    _client : GroupBackupClient
        Reference to client for data preparation
    
    Notes
    -----
    - Not intended for direct user instantiation
    - Automatically created by _begin_group_backup() and _reopen_group_backup()
    - Handles model transformation transparently
    """
    
    def __init__(self, operation: GroupBackupOperation, client: 'GroupBackupClient'):
        """
        Initialize wrapper with operation and client references.
        
        Parameters
        ----------
        operation : GroupBackupOperation
            Low-level group backup operation handler
        client : GroupBackupClient
            Client instance for data preparation
        """
        self._operation = operation
        self._client = client
    
    def open_with_leader(self, leader_backup_obj: BackupRequest):
        """
        Open group with leader, accepting BackupRequest object.
        
        Parameters
        ----------
        leader_backup_obj : BackupRequest
            Leader backup request model
        
        Returns
        -------
        dict
            Result with 'groupLeaderObjId' and 'leader' information
        """
        # Convert BackupRequest to dict format for C API
        leader_dict = self._client._prepare_backup_dict(leader_backup_obj)
        return self._operation.open_with_leader(leader_dict)
    
    def add_member(self, leader_obj_id: dict, member_backup_obj: BackupRequest):
        """
        Add member to group, accepting BackupRequest object.
        
        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' keys
        member_backup_obj : BackupRequest
            Member backup request model
        
        Returns
        -------
        dict
            Result with 'member' information
        """
        # Convert BackupRequest to dict format for C API
        member_dict = self._client._prepare_backup_dict(member_backup_obj)
        return self._operation.add_member(leader_obj_id, member_dict)
    
    def close_group(self, leader_obj_id: dict):
        """
        Close the group.
        
        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' keys
        
        Returns
        -------
        dict
            Result of close operation
        """
        return self._operation.close_group(leader_obj_id)


class GroupHandle:
    """
    Handle for managing group backup operations.
    
    This class provides a high-level interface for creating and managing group backups,
    including adding leaders and members, closing groups, and persisting metadata.
    
    Attributes
    ----------
    _name : str
        Unique name for the group
    _client : GroupBackupClient
        The group backup operation client
    _filespace : str
        Target filespace
    _leader_id : dict, optional
        Leader object ID with 'hi' and 'lo' keys
    _metadata_file : str
        Path to metadata file
    _operation : GroupOperationWrapper, optional
        Current group operation wrapper
    _is_open : bool
        Whether group is currently open
    _is_closed : bool
        Whether group has been closed
    _first_member_is_leader : bool
        Whether first member became the leader
    
    Methods
    -------
    add_leader(backup_item)
        Add an explicit leader object to the group
    add_member(backup_item)
        Add a member object to the group
    close()
        Close the group to finalize it
    reopen()
        Reopen a closed group to add more members
    remove_members(member_keys)
        Remove specific members from the group
    delete()
        Delete the entire group
    save(filepath)
        Save group metadata to file
    """
    
    def __init__(self, name: str, client: 'GroupBackupClient', filespace: str = "/", 
                 leader_id: Optional[dict] = None, metadata_file: str = ".sp_groups.json"):
        """
        Initialize a group handle.
        
        Parameters
        ----------
        name : str
            Unique name for the group
        client : GroupBackupClient
            The group backup operation client
        filespace : str, optional
            Target filespace (default: "/")
        leader_id : dict, optional
            Existing leader ID with 'hi' and 'lo' keys
        metadata_file : str, optional
            Path to metadata file (default: ".sp_groups.json")
        """
        self._name = name
        self._client = client
        self._filespace = filespace
        self._leader_id = leader_id
        self._metadata_file = metadata_file
        self._operation: Optional[GroupOperationWrapper] = None
        self._is_open = False
        self._is_closed = False
        self._first_member_is_leader = False
        
        _logger.debug("GroupHandle created: %s", name, extra={'event_type': 'group_handle.created', 'group_name': name, 'has_leader_id': leader_id is not None})
    
    def add_leader(self, backup_item: BackupRequest):
        """
        Add an explicit leader object to the group.
        
        Parameters
        ----------
        backup_item : BackupRequest
            Leader backup request model
        
        Returns
        -------
        dict
            Result with leader information
        
        Raises
        ------
        ValueError
            If group is closed or already has a leader
        """
        if self._is_closed:
            raise ValueError(f"Group '{self._name}' is already closed")
        if self._leader_id is not None:
            raise ValueError(f"Group '{self._name}' already has a leader")
        
        if not self._is_open:
            self._open_group()
        
        _logger.info("Adding explicit leader to group '%s'", self._name, extra={'event_type': 'group_handle.add_leader', 'group_name': self._name, 'leader_key': backup_item.key})
        
        result = self._operation.open_with_leader(backup_item)
        self._leader_id = result['groupLeaderObjId']
        
        self._persist_metadata()
        
        _logger.info("Leader added: %s-%s", self._leader_id['hi'], self._leader_id['lo'], extra={'event_type': 'group_handle.leader_added', 'group_name': self._name})
        return result
    
    def add_member(self, backup_item: BackupRequest):
        """
        Add a member object to the group.
        
        If no leader exists, the first member becomes the leader automatically.
        
        Parameters
        ----------
        backup_item : BackupRequest
            Member backup request model
        
        Returns
        -------
        dict
            Result with member information
        
        Raises
        ------
        ValueError
            If group is closed
        """
        if self._is_closed:
            raise ValueError(f"Group '{self._name}' is closed. Use reopen() first.")
        
        if not self._is_open:
            self._open_group()
        
        if self._leader_id is None:
            _logger.info("First member becomes leader for group '%s'", self._name, extra={'event_type': 'group_handle.auto_leader', 'group_name': self._name})
            result = self._operation.open_with_leader(backup_item)
            self._leader_id = result['groupLeaderObjId']
            self._first_member_is_leader = True
            self._persist_metadata()
            return result
        else:
            _logger.debug("Adding member to group '%s'", self._name, extra={'event_type': 'group_handle.add_member', 'group_name': self._name})
            return self._operation.add_member(self._leader_id, backup_item)
    
    def close(self):
        """
        Close the group to finalize it.
        
        Returns
        -------
        dict
            Result of close operation
        
        Raises
        ------
        ValueError
            If group is not open or has no members
        """
        if self._is_closed:
            _logger.warning("Group '%s' is already closed", self._name)
            return
        if not self._is_open:
            raise ValueError(f"Group '{self._name}' is not open")
        if self._leader_id is None:
            raise ValueError(f"Cannot close group '{self._name}': no members added")
        
        _logger.info("Closing group '%s'", self._name, extra={'event_type': 'group_handle.close', 'group_name': self._name})
        
        result = self._operation.close_group(self._leader_id)
        self._is_closed = True
        self._is_open = False
        return result
    
    def reopen(self):
        """
        Reopen a closed group to add more members.
        
        Returns
        -------
        GroupHandle
            Self reference for chaining
        
        Raises
        ------
        ValueError
            If group is not closed or has no leader_id
        """
        if not self._is_closed:
            raise ValueError(f"Group '{self._name}' is not closed")
        if self._leader_id is None:
            raise ValueError(f"Cannot reopen group '{self._name}': no leader_id available")
        
        _logger.info("Reopening group '%s'", self._name, extra={'event_type': 'group_handle.reopen', 'group_name': self._name})
        
        reopen_request = ReopenGroupBackupRequest(
            group_tag=self._name,
            group_leader_obj_id_hi=self._leader_id['hi'],
            group_leader_obj_id_lo=self._leader_id['lo'],
            filespace=self._filespace
        )
        
        self._operation = self._client._reopen_group_backup(reopen_request)
        self._is_open = True
        self._is_closed = False
        return self
    
    def remove_members(self, member_keys):
        """
        Remove specific members from the group by their keys.
        
        Parameters
        ----------
        member_keys : list
            List of member object keys to remove
        
        Returns
        -------
        GroupOperationResult
            Result of remove operation
        
        Raises
        ------
        ValueError
            If group has no leader_id
        """
        if self._leader_id is None:
            raise ValueError(f"Cannot remove members: group '{self._name}' has no leader_id")
        
        query_client = QueryClient(self._client._session)
        group_query = GroupQueryRequest(
            filespace=self._filespace,
            group_leader_obj_id_hi=self._leader_id['hi'],
            group_leader_obj_id_lo=self._leader_id['lo']
        )
        
        result = query_client.query_group_members(group_query)
        
        normalized_keys = set()
        for key in member_keys:
            normalized_keys.add(key)
            normalized_keys.add(key if key.startswith('/') else '/' + key)
            normalized_keys.add(key[1:] if key.startswith('/') else key)
        
        member_obj_ids = []
        for obj in result.objects:
            if not obj.is_group_leader and obj.key in normalized_keys:
                obj_id_parts = obj.object_id.split('-')
                member_obj_ids.append({"hi": int(obj_id_parts[0]), "lo": int(obj_id_parts[1])})
        
        if not member_obj_ids:
            _logger.warning("No members found to remove from group '%s'", self._name)
            return GroupOperationResult(status="success", message="No members found to remove")
        
        remove_request = GroupRemoveMembersRequest(
            group_tag=self._name,
            group_leader_obj_id_hi=self._leader_id['hi'],
            group_leader_obj_id_lo=self._leader_id['lo'],
            member_obj_ids=member_obj_ids,
            filespace=self._filespace
        )
        
        return self._client._group_remove_members(remove_request)
    
    def delete(self):
        """
        Delete the entire group including leader and all members.
        
        Returns
        -------
        GroupOperationResult
            Result of delete operation
        
        Raises
        ------
        ValueError
            If group has no leader_id
        """
        if self._leader_id is None:
            raise ValueError(f"Cannot delete group '{self._name}': no leader_id available")
        
        _logger.info("Deleting group '%s'", self._name, extra={'event_type': 'group_handle.delete', 'group_name': self._name})
        
        delete_request = GroupDeleteRequest(
            group_tag=self._name,
            group_leader_obj_id_hi=self._leader_id['hi'],
            group_leader_obj_id_lo=self._leader_id['lo'],
            filespace=self._filespace
        )
        
        result = self._client._group_delete(delete_request)
        self._remove_from_metadata()
        return result
    
    def save(self, filepath=None):
        """
        Save group metadata to file for persistence.
        
        Parameters
        ----------
        filepath : str, optional
            Path to save metadata file. If not provided, uses current metadata_file.
        """
        if filepath:
            self._metadata_file = filepath
        self._persist_metadata()
        _logger.info("Group metadata saved to %s", self._metadata_file, extra={'event_type': 'group_handle.saved', 'group_name': self._name})
    
    @property
    def name(self):
        """Get the group name/tag."""
        return self._name
    
    @property
    def leader_id(self):
        """Get the leader object ID (dict with 'hi' and 'lo' keys)."""
        return self._leader_id
    
    @property
    def is_open(self):
        """Check if group is currently open for modifications."""
        return self._is_open
    
    @property
    def is_closed(self):
        """Check if group has been closed."""
        return self._is_closed
    
    def _open_group(self):
        """Internal: Open a new group backup operation."""
        request = BeginGroupBackupRequest(group_tag=self._name, filespace=self._filespace)
        self._operation = self._client._begin_group_backup(request)
        self._is_open = True
    
    def _persist_metadata(self):
        """Internal: Persist group metadata to JSON file."""
        if self._leader_id is None:
            return
        
        metadata = {}
        if os.path.exists(self._metadata_file):
            try:
                with open(self._metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except (json.JSONDecodeError, IOError):
                metadata = {}
        
        metadata[self._name] = {
            "leader_id": self._leader_id,
            "filespace": self._filespace,
            "created_at": datetime.now().isoformat(),
            "first_member_is_leader": self._first_member_is_leader
        }
        
        with open(self._metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def _remove_from_metadata(self):
        """Internal: Remove group from metadata file after deletion."""
        if not os.path.exists(self._metadata_file):
            return
        
        try:
            with open(self._metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if self._name in metadata:
                del metadata[self._name]
                with open(self._metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
        except (json.JSONDecodeError, IOError) as e:
            _logger.warning("Failed to remove group from metadata: %s", e)
    
    def __enter__(self):
        """Context manager entry: return self for with statement."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: automatically close group if open."""
        if self._is_open and not self._is_closed and self._leader_id is not None:
            try:
                self.close()
            except Exception as e:
                _logger.error("Error closing group in context manager: %s", e)
        return False
    
    def __repr__(self):
        """String representation of GroupHandle."""
        return f"GroupHandle(name='{self._name}', leader_id={self._leader_id}, is_open={self._is_open})"


class GroupBackupClient(BaseClient):
    """
    Client for group backup operations.
    
    This class provides methods for creating, managing, and executing group backups,
    including group creation, member management, and group operations.
    
    Attributes
    ----------
    _session : ClientSession
        Active session with IBM Storage Protect server
    
    Methods
    -------
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
    """
    
    def create_group(self, name: str, filespace: str = "/", members=None, metadata_file: str = ".sp_groups.json") -> GroupHandle:
        """
        Create a new group backup with optional initial members.
        
        Parameters
        ----------
        name : str
            Unique name for the group
        filespace : str, optional
            Target filespace (default: "/")
        members : list, optional
            List of BackupRequest objects to add as members
        metadata_file : str, optional
            Path to metadata file (default: ".sp_groups.json")
        
        Returns
        -------
        GroupHandle
            Handle for managing the group backup
        
        Example
        -------
        >>> group = client.create_group("my-group", filespace="/myfs")
        >>> group.add_member(BackupRequest(Key="/file.txt", Body=b"data"))
        >>> group.close()
        """
        _logger.info("Creating group '%s'", name, extra={'event_type': 'client.create_group', 'group_name': name})
        
        group = GroupHandle(name, self, filespace=filespace, metadata_file=metadata_file)
        
        if members:
            for member in members:
                group.add_member(member)
            group.close()
        
        return group
    
    def load_group(self, filepath: str, name: str, filespace: str = "/") -> GroupHandle:
        """
        Load an existing group backup from a metadata file.
        
        Parameters
        ----------
        filepath : str
            Path to the JSON metadata file
        name : str
            Name of the group to load
        filespace : str, optional
            Filespace override (default: "/")
        
        Returns
        -------
        GroupHandle
            Handle for the loaded group
        
        Raises
        ------
        FileNotFoundError
            If metadata file doesn't exist
        ValueError
            If group name not found in metadata
        
        Example
        -------
        >>> group = client.load_group(".sp_groups.json", "my-group")
        >>> group.reopen()
        >>> group.add_member(BackupRequest(Key="/new.txt", Body=b"data"))
        >>> group.close()
        """
        _logger.info("Loading group '%s' from %s", name, filepath, extra={'event_type': 'client.load_group', 'group_name': name, 'filepath': filepath})
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Metadata file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        if name not in metadata:
            raise ValueError(f"Group '{name}' not found in {filepath}")
        
        group_data = metadata[name]
        group = GroupHandle(
            name,
            self,
            filespace=group_data.get('filespace', filespace),
            leader_id=group_data['leader_id'],
            metadata_file=filepath
        )
        group._is_closed = True
        return group
    
    def get_group(self, name: str, leader_id: dict, filespace: str = "/", metadata_file: str = ".sp_groups.json") -> GroupHandle:
        """
        Get a group handle using a known leader ID.
        
        Parameters
        ----------
        name : str
            Name for the group
        leader_id : dict
            Leader object ID with 'hi' and 'lo' keys
        filespace : str, optional
            Target filespace (default: "/")
        metadata_file : str, optional
            Path to metadata file (default: ".sp_groups.json")
        
        Returns
        -------
        GroupHandle
            Handle for the group
        
        Example
        -------
        >>> leader_id = {"hi": 0, "lo": 8251150}
        >>> group = client.get_group("my-group", leader_id)
        >>> group.reopen()
        """
        _logger.info("Getting group '%s' with provided leader_id", name, extra={'event_type': 'client.get_group', 'group_name': name})
        
        group = GroupHandle(name, self, filespace=filespace, leader_id=leader_id, metadata_file=metadata_file)
        group._is_closed = True
        return group
    
    def _prepare_backup_dict(self, backup_obj: BackupRequest) -> dict:
        """
        Internal method to prepare a backup dictionary from a BackupRequest model.
        
        Parameters
        ----------
        backup_obj : BackupRequest
            Backup request model
        
        Returns
        -------
        dict
            Dictionary suitable for C API operations
        """
        data_source = validate_chunks(backup_obj.body)
        obj_type_value = extract_enum_value(backup_obj.obj_type, ObjType, default=ObjType.FILE.value)
        mount_wait_value = extract_mount_wait(backup_obj.mount_wait)
        obj_info_bytes = encode_obj_info(backup_obj.obj_info)
        
        return {
            "Key": backup_obj.key,
            "Body": data_source,
            "ObjType": obj_type_value,
            "Owner": backup_obj.owner or self._get_owner(),
            "ManagementClass": backup_obj.management_class,
            "SizeEstimate": backup_obj.size_estimate,
            "PreCompressed": backup_obj.pre_compressed,
            "MountWait": mount_wait_value,
            "ObjInfo": obj_info_bytes,
            "DisableDedup": backup_obj.disable_dedup,
        }
    
    def _begin_group_backup(self, request: BeginGroupBackupRequest) -> GroupOperationWrapper:
        """Internal method to begin a group backup operation."""
        session_handle = getattr(self._session, '_session_id', None)
        object_key = request.group_tag
        filespace = request.filespace or "/"
        
        _register_filespace(
            handle=self._require_handle(),
            filespace=filespace
        )
        
        operation = GroupBackupOperation(
            session=self,
            filespace=filespace,
            group_tag=request.group_tag,
            session_handle=session_handle,
            object_key=object_key,
        )
        
        return GroupOperationWrapper(operation, self)
    
    def _reopen_group_backup(self, request: ReopenGroupBackupRequest) -> GroupOperationWrapper:
        """Internal method to reopen a group backup operation."""
        session_handle = getattr(self._session, '_session_id', None)
        object_key = request.group_tag
        filespace = request.filespace or "/"
        
        _register_filespace(
            handle=self._require_handle(),
            filespace=filespace
        )
        
        operation = GroupBackupOperation(
            session=self,
            filespace=filespace,
            group_tag=request.group_tag,
            session_handle=session_handle,
            object_key=object_key,
        )
        
        return GroupOperationWrapper(operation, self)
    
    def _group_remove_members(self, request: GroupRemoveMembersRequest) -> GroupOperationResult:
        """Internal method to remove members from a group."""
        object_key = request.group_tag
        filespace = request.filespace or "/"
        
        context_details = {
            'group_tag': request.group_tag,
            'leader_obj_id_hi': request.group_leader_obj_id_hi,
            'leader_obj_id_lo': request.group_leader_obj_id_lo,
            'member_count': len(request.member_obj_ids)
        }
        
        with log_operation(
            _logger,
            'group_remove_members',
            self,
            filespace=filespace,
            object_key=object_key,
            context_details=context_details
        ) as log_data:
            operation = GroupBackupOperation(
                session=self,
                filespace=filespace,
                group_tag=request.group_tag,
                session_handle=getattr(self._session, '_session_id', None),
                object_key=object_key,
            )
            
            leader_obj_id = {
                "hi": request.group_leader_obj_id_hi,
                "lo": request.group_leader_obj_id_lo
            }
            
            result = operation.remove_members(leader_obj_id, request.member_obj_ids)
            
            log_data["metrics"]["members_removed"] = len(request.member_obj_ids)
            
            return GroupOperationResult(
                status="success",
                message=f"Removed {len(request.member_obj_ids)} members from group"
            )
    
    def _group_delete(self, request: GroupDeleteRequest) -> GroupOperationResult:
        """Internal method to delete a group."""
        object_key = request.group_tag
        filespace = request.filespace or "/"
        
        context_details = {
            'group_tag': request.group_tag,
            'leader_obj_id_hi': request.group_leader_obj_id_hi,
            'leader_obj_id_lo': request.group_leader_obj_id_lo
        }
        
        with log_operation(
            _logger,
            'group_delete',
            self,
            filespace=filespace,
            object_key=object_key,
            context_details=context_details
        ) as log_data:
            operation = GroupBackupOperation(
                session=self,
                filespace=filespace,
                group_tag=request.group_tag,
                session_handle=getattr(self._session, '_session_id', None),
                object_key=object_key,
            )
            
            leader_obj_id = {
                "hi": request.group_leader_obj_id_hi,
                "lo": request.group_leader_obj_id_lo
            }
            
            result = operation.delete_group(leader_obj_id)
            
            log_data["context"]["deleted_group"] = request.group_tag
            
            return GroupOperationResult(
                status="success",
                message=f"Deleted group '{request.group_tag}'"
            )
    
    def _get_owner(self) -> str:
        """
        Internal: Get the owner name from the session manager.

        Returns
        -------
        str
            Owner name from session manager, or empty string if not available
        """
        if hasattr(self._session, '_session_manager') and self._session._session_manager:
            return self._session._session_manager.owner or ""
        return ""

# Made with Bob
