"""
IBM Storage Protect Client SDK - Group Restore Operation

This module provides group restore functionality for IBM Storage Protect.
It handles restoring all members of a group backup atomically, including
the leader and all member objects.

Key Responsibilities:
---------------------
1. **Group Restore**: Restore all members of a group backup
2. **Leader/Member Handling**: Properly identify and restore leader and members
3. **Data Streaming**: Memory-efficient data retrieval via generators
4. **Error Handling**: Comprehensive error handling with structured logging
5. **Atomic Operations**: Restore entire group as a cohesive unit

Classes:
--------
- GroupRestoreClient: Client for group restore operations

Example Usage:
--------------
    from ibm_storage_protect.data_client.group_restore import GroupRestoreClient
    from ibm_storage_protect.data_models.restore import GroupRestoreRequest
    
    client = GroupRestoreClient(session)
    group = GroupRestoreRequest(
        Filespace="/myfs",
        GroupLeaderObjIdHi=0,
        GroupLeaderObjIdLo=8251150
    )
    result = client.group_restore(group)
    
    for member in result.results:
        if member.is_group_leader:
            print(f"Leader: {member.key}")
        else:
            print(f"Member: {member.key}")
        
        for chunk in member.body:
            process(chunk)
"""
# pylint: disable=line-too-long

from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    extract_enum_value,
    extract_mount_wait,
)
from ibm_storage_protect.c_api_bridge.wrappers.restore import GroupRestoreOperation
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.restore import (
    GroupRestoreRequest,
    GroupRestoreMemberResult,
    GroupRestoreResult,
)
from ibm_storage_protect.enums import ObjType
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import get_logger, log_operation
from ibm_storage_protect.logger.context import set_log_context
from ibm_storage_protect.session import ClientSession

# Module-level logger for structured logging
_logger = get_logger(__name__)


class GroupRestoreClient(BaseClient):
    """
    Client for group restore operations.
    
    This class provides type-safe, validated methods for restoring entire
    group backups including the leader and all member objects.
    
    Attributes
    ----------
    _session : ClientSession
        Active session with IBM Storage Protect server
    
    Methods
    -------
    group_restore(group_request)
        Restore all members of a group
    
    Notes
    -----
    - Inherits from BaseClient for session management
    - All operations use structured logging
    - Errors are mapped to SDK exceptions
    - Body for each object is returned as a generator
    - Supports context manager protocol
    """

    def group_restore(self, group_request: GroupRestoreRequest) -> GroupRestoreResult:
        """
        Restore all members of a group backup.

        This method restores an entire group backup, including the leader and all
        member objects. The group is identified by the leader's object ID.

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
        - Leader object ID must be known (from backup or query)
        
        Example
        -------
        >>> group = GroupRestoreRequest(
        ...     Filespace="/myfs",
        ...     GroupLeaderObjIdHi=0,
        ...     GroupLeaderObjIdLo=8251150
        ... )
        >>> result = client.group_restore(group)
        >>> print(f"{result.total_objects} objects restored")
        """
        filespace = group_request.filespace or "/"
        object_key = f"group_{group_request.group_leader_obj_id_hi}_{group_request.group_leader_obj_id_lo}"

        context_details = {
            'leader_obj_id_hi': group_request.group_leader_obj_id_hi,
            'leader_obj_id_lo': group_request.group_leader_obj_id_lo,
            'obj_type': str(group_request.obj_type) if group_request.obj_type else None
        }

        with log_operation(
            _logger,
            'group_restore',
            self,
            filespace=filespace,
            object_key=object_key,
            context_details=context_details
        ) as log_data:
            obj_type_value = extract_enum_value(group_request.obj_type, ObjType, ObjType.FILE)
            mount_wait_value = extract_mount_wait(group_request.mount_wait)

            operation = GroupRestoreOperation(
                handle=self._require_handle(),
                filespace=filespace,
                leader_hi=group_request.group_leader_obj_id_hi,
                leader_lo=group_request.group_leader_obj_id_lo,
                owner=group_request.owner or self._get_owner(),
                obj_type=obj_type_value,
                mount_wait=mount_wait_value,
                session_handle=getattr(self._session, '_session_id', None),
                object_key=object_key,
            )

            results = operation.execute()

            # Update logging context/metrics on success
            log_data["context"]["leader_obj_id"] = f"{group_request.group_leader_obj_id_hi}-{group_request.group_leader_obj_id_lo}"
            log_data["metrics"]["total_objects"] = len(results)

            return GroupRestoreResult(
                Results=[
                    GroupRestoreMemberResult(
                        Key=result["Key"],
                        Filespace=result["Filespace"],
                        Body=result["Body"],
                        IsGroupLeader=result.get("IsGroupLeader", False),
                        LastModified=result.get("LastModified"),
                        ObjectId=result.get("ObjectId", ""),
                        MediaClass=result.get("MediaClass", ""),
                        ManagementClass=result.get("ManagementClass", ""),
                    )
                    for result in results
                ],
                TotalObjects=len(results),
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
