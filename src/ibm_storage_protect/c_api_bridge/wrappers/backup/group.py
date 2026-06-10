# pylint: disable=too-many-lines,protected-access,too-many-arguments,too-many-positional-arguments
# This module implements comprehensive group backup operations for IBM Storage Protect.
# The length is justified by the complete implementation of all group backup workflows.
"""
IBM Storage Protect Client API - Group Backup Operations

This module provides Python wrappers for IBM Storage Protect group backup operations,
enabling data protection through peer group backups with leader/member relationships
using the IBM Storage Protect Client API.

Key Responsibilities:
---------------------
1. **Group Backup**: Manage peer group backups with leader and members
2. **Leader Management**: Create and manage group leader objects
3. **Member Management**: Add, remove, and assign member objects to groups
4. **Group Lifecycle**: Open, close, and delete group backups
5. **Relationship Tracking**: Maintain leader/member relationships

Group Backup Workflow:
----------------------
1. **Open Group**: Create group with leader via dsmGroupHandler(OPEN)
2. **Add Members**: Add member objects via dsmGroupHandler(ADD)
3. **Close Group**: Finalize group via dsmGroupHandler(CLOSE)
4. **Manage Members**: Remove/assign members via dsmGroupHandler(REMOVE/ASSIGNTO)
5. **Delete Group**: Delete leader to cascade delete all members

Thread Safety:
--------------
Group operations are NOT thread-safe when using the same session handle.
Each thread should maintain its own session handle for concurrent operations.

Performance Considerations:
---------------------------
- Group backups enable coordinated backup/restore of related objects
- Leader deletion cascades to all members (efficient group deletion)
- Use groups for logically related objects (e.g., database + logs)

Client API Integration:
-----------------------
This module wraps the following Client API functions:
- dsmGroupHandler() - Manage group backup operations (OPEN, ADD, CLOSE, REMOVE, ASSIGNTO)
- dsmDeleteObj() - Delete group leader (cascades to members)

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Group Backup", "Transaction Management"

Example Usage:
--------------
    # Group backup
    group_op = GroupBackupOperation(
        session=session,
        filespace="/myfs",
        group_tag="my-group-001"
    )
    leader_result = group_op.open_with_leader(leader_obj)
    member_result = group_op.add_member(leader_id, member_obj)
    group_op.close_group(leader_id)
"""

from ctypes import byref, c_uint32, cast, pointer, POINTER
from typing import Optional

from ibm_storage_protect.c_api_bridge.c_api.platform_types import dsStruct64_t
from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_GROUP_ACTION_ADD,
    DSM_GROUP_ACTION_ASSIGNTO,
    DSM_GROUP_ACTION_CLOSE,
    DSM_GROUP_ACTION_OPEN,
    DSM_GROUP_ACTION_REMOVE,
    DSM_GROUPTYPE_PEER,
    DSM_MEMBERTYPE_LEADER,
    DSM_MEMBERTYPE_MEMBER,
    DSM_OBJ_FILE,
    DSM_VOTE_ABORT,
    DSM_VOTE_COMMIT,
    ObjID,
    dsmGetList,
    dsmGetListVersion,
    dsmEndTxnExIn_t,
    dsmEndTxnExInVersion,
    dsmEndTxnExOut_t,
    dsmEndTxnExOutVersion,
    dsmGroupHandlerIn_t,
    dsmGroupHandlerInVersion,
    dsmGroupHandlerOut_t,
    dsmGroupHandlerOutVersion,
    dsmObjName,
)

from ibm_storage_protect.c_api_bridge.c_api.load import lib

from ibm_storage_protect.errors import (
    SDKErrorCode,
    TSMTransactionError,

)
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    init_struct,
    check_rc,
    parse_key,
    get_session_owner
)
from ibm_storage_protect.c_api_bridge.wrappers.object import (
    DeleteObjectOperation
)
from ibm_storage_protect.logger import get_logger
from ibm_storage_protect.c_api_bridge.wrappers.backup.single import (
    BackupOperation
)

_logger = get_logger(__name__)


class GroupBackupOperation:
    """
    Group backup operation handler for peer group backups.

    Manages IBM Storage Protect peer group backups, where multiple objects
    are logically grouped with a leader and members. Provides operations
    to create, modify, and delete group relationships.

    Group backups enable:
    - Logical grouping of related objects
    - Coordinated backup/restore operations
    - Relationship tracking between objects

    Attributes
    ----------
    session : Session
        The active IBM Storage Protect session.
    filespace : str
        The filespace name for group objects.
    group_tag : bytes
        Unique identifier for the group.

    Notes
    -----
    - Leader object must be backed up first (open_with_leader)
    - Members are added after leader creation (add_member)
    - Group must be closed after all members added (close_group)
    - Deleting leader cascades to all members

    Example
    -------
    >>> group_op = GroupBackupOperation(
    ...     session=session,
    ...     filespace="/myfs",
    ...     group_tag="my-group-001"
    ... )
    >>> leader_result = group_op.open_with_leader(leader_obj)
    >>> member_result = group_op.add_member(leader_id, member_obj)
    >>> group_op.close_group(leader_id)
    """

    def __init__ (
        self,
        session,
        filespace,
        group_tag,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None
        ) :
        """
        Initialize the group backup operation.

        Parameters
        ----------
        session : Session
            The active IBM Storage Protect session wrapper.
        filespace : str
            The destination filespace name for group objects.
        group_tag : str or bytes
            Unique tag to identify this group backup.
        session_handle : str, optional
            Correlation ID for session logging.
        object_key : str, optional
            Correlation ID for object logging.
        """

        self.session = session
        self.filespace = filespace
        self.group_tag = group_tag.encode('utf-8') if isinstance(group_tag, str) else group_tag
        self.session_handle = session_handle
        self.object_key = object_key
        self._handle = self._get_handle()
        self._leader_obj_name = None

    def _get_handle(self) -> int:
        """Extract integer handle from session."""
        raw = self.session._session.handle
        return raw.value if isinstance(raw, c_uint32) else int(raw)

    def open_with_leader(self, leader_backup_obj):
        """
        Open a new group backup with a leader object.

        Creates a new peer group by backing up the leader object and
        establishing it as the group leader. This must be the first
        operation when creating a group.

        Parameters
        ----------
        leader_backup_obj : dict
            Leader object dictionary with Key, Body, and attributes.

        Returns
        -------
        dict
            Result containing group leader object ID and statistics.

        Raises
        ------
        BackupError
            If group creation or leader backup fails.

        Notes
        -----
        - Leader object is backed up first
        - Group is created via dsmGroupHandler(OPEN)
        - Leader object ID is returned for subsequent operations

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_OPEN
        """
        _logger.info(
            "Opening group backup with leader object",
            extra={
                'event_type': 'c_api.backup.group.open.started',
                'filespace': self.filespace,
                'key': leader_backup_obj["Key"],
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        leader_op = self._make_op(leader_backup_obj)
        leader_op._bind_management_class()
        leader_op._begin_transaction()

        try:
            self._call_group_handler_open(leader_op._obj_name)
            self._leader_obj_name = leader_op._obj_name
            leader_op._send_object_header()
            leader_op._send_data()
            leader_op._end_object()
            leader_op._commit_transaction()

            leader_obj_id = leader_op._txn_endout.groupLeaderObjId

            result = {
                "status": "success",
                "groupLeaderObjId": {
                    "hi": int(leader_obj_id.hi),
                    "lo": int(leader_obj_id.lo)
                },
                "leader": {
                    "Key": leader_backup_obj["Key"],
                    "stats": leader_op.get_stats()
                }
            }
            _logger.info(
                "Group backup opened successfully",
                extra={
                    'event_type': 'c_api.backup.group.open.completed',
                    'group_leader_obj_id': f"{int(leader_obj_id.hi)}-{int(leader_obj_id.lo)}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            return result

        except Exception:
            _logger.error(
                "Failed to open group backup",
                extra={
                    'event_type': 'c_api.backup.group.open.failed',
                    'filespace': self.filespace,
                    'key': leader_backup_obj["Key"],
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                },
                exc_info=True
            )
            leader_op._abort_transaction()
            raise

    def add_member(self, leader_obj_id: dict, member_backup_obj):
        """
        Add a member object to an existing group.

        Backs up a member object and associates it with the group leader.
        Can be called multiple times to add multiple members.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.
        member_backup_obj : dict
            Member object dictionary with Key, Body, and attributes.

        Returns
        -------
        dict
            Result containing member backup statistics.

        Raises
        ------
        BackupError
            If member backup or group association fails.

        Notes
        -----
        - Group must be opened first via open_with_leader()
        - Member is backed up and linked to leader
        - Multiple members can be added sequentially

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_ADD
        """
        _logger.info(
            "Adding member to group backup",
            extra={
                'event_type': 'c_api.backup.group.add_member.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'key': member_backup_obj["Key"],
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        member_op = self._make_op(member_backup_obj)
        member_op._bind_management_class()
        member_op._begin_transaction()

        try:
            self._call_group_handler_add(leader_obj_id)
            member_op._send_object_header()
            member_op._send_data()
            member_op._end_object()
            member_op._commit_transaction()

            result = {
                "status": "success",
                "member": {
                    "Key": member_backup_obj["Key"],
                    "stats": member_op.get_stats()
                }
            }
            _logger.info(
                "Group member added successfully",
                extra={
                    'event_type': 'c_api.backup.group.add_member.completed',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'key': member_backup_obj["Key"],
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            return result

        except Exception:
            _logger.error(
                "Failed to add member to group backup",
                extra={
                    'event_type': 'c_api.backup.group.add_member.failed',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'key': member_backup_obj["Key"],
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                },
                exc_info=True
            )
            member_op._abort_transaction()
            raise

    def close_group(self, leader_obj_id: dict):
        """
        Close a group backup after all members are added.

        Finalizes the group backup operation, committing all group
        relationships to the server.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.

        Returns
        -------
        dict
            Result confirming group closure.

        Raises
        ------
        TSMTransactionError
            If group closure transaction fails.

        Notes
        -----
        - Must be called after all members are added
        - Commits group relationships to server
        - Group cannot be modified after closure

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_CLOSE
        """
        _logger.info(
            "Closing group backup",
            extra={
                'event_type': 'c_api.backup.group.close.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        _logger.debug(
            "Calling dsmBeginTxn",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginTxn',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        rc = lib.dsmBeginTxn(self._handle)
        check_rc(self._handle, rc, "dsmBeginTxn")

        try:
            #self._call_group_handler_close(leader_obj_id)
            end_in = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)
            end_out = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)
            end_in.dsmHandle = self._handle
            end_in.vote = DSM_VOTE_COMMIT

            _logger.debug(
                "Calling dsmEndTxnEx",
                extra={
                    'event_type': 'c_api.function.call',
                    'function': 'dsmEndTxnEx',
                    'vote': 'commit',
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )

            rc = lib.dsmEndTxnEx(byref(end_in), byref(end_out))

            check_rc(self._handle, rc, "dsmEndTxnEx (commit)")

            if end_out.reason != 0:
                _logger.error(
                    "Group close transaction failed",
                    extra={
                        'event_type': 'c_api.backup.group.close.failed',
                        'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                        'reason_code': end_out.reason,
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )

                raise TSMTransactionError(
                    error_code=SDKErrorCode.COMMIT_FAILED,
                    message=f"Transaction failed with reason: {end_out.reason}"
                )

            result = {
                "status": "success",
                "groupLeaderObjId": leader_obj_id
            }
            _logger.info(
                "Group backup closed",
                extra={
                    'event_type': 'c_api.backup.group.close.completed',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            return result

        except Exception:
            _logger.warning(
                "Aborting group close transaction",
                extra={
                    'event_type': 'c_api.backup.group.close.abort',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            end_in_abort = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)
            end_out_abort = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)
            end_in_abort.dsmHandle = self._handle
            end_in_abort.vote = DSM_VOTE_ABORT
            lib.dsmEndTxnEx(byref(end_in_abort), byref(end_out_abort))

            _logger.warning(
                "Group close transaction aborted",
                extra={
                    'event_type': 'c_api.backup.group.close.abort.completed',
                    'reason_code': end_out_abort.reason,
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            raise

    def remove_members(self, leader_obj_id: dict, member_obj_ids: list):
        """
        Remove members from an existing group.

        Removes specified member objects from the group while keeping
        the leader and other members intact.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.
        member_obj_ids : list
            List of member object IDs to remove.

        Returns
        -------
        dict
            Result with count of removed members.

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_REMOVE
        """
        _logger.info(
            "Removing members from group backup",
            extra={
                'event_type': 'c_api.backup.group.remove_members.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'member_count': len(member_obj_ids),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        _logger.debug(
            "Calling dsmBeginTxn",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginTxn'
            }
        )
        rc = lib.dsmBeginTxn(self._handle)
        check_rc(self._handle, rc, "dsmBeginTxn")

        try:
            self._call_group_handler_remove(leader_obj_id, member_obj_ids)

            end_in = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)
            end_out = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)
            end_in.dsmHandle = self._handle
            end_in.vote = DSM_VOTE_COMMIT

            _logger.debug(
                "Calling dsmEndTxnEx",
                extra={
                    'event_type': 'c_api.function.call',
                    'function': 'dsmEndTxnEx',
                    'vote': 'commit',
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            rc = lib.dsmEndTxnEx(byref(end_in), byref(end_out))
            check_rc(self._handle, rc, "dsmEndTxnEx (commit)")

            if end_out.reason != 0:
                _logger.error(
                    "Group member removal transaction failed",
                    extra={
                        'event_type': 'c_api.backup.group.remove_members.failed',
                        'reason_code': end_out.reason,
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )

                raise TSMTransactionError(
                    error_code=SDKErrorCode.COMMIT_FAILED,
                    message=f"Transaction failed with reason: {end_out.reason}"
                )

            result = {
                "status": "success",
                "removedCount": len(member_obj_ids)
            }
            _logger.info(
                "Members removed from group backup",
                extra={
                    'event_type': 'c_api.backup.group.remove_members.completed',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'removed_count': len(member_obj_ids),
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            return result

        except Exception:
            _logger.warning(
                "Aborting group member removal transaction",
                extra={
                    'event_type': 'c_api.backup.group.remove_members.abort',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            end_in_abort = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)
            end_out_abort = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)
            end_in_abort.dsmHandle = self._handle
            end_in_abort.vote = DSM_VOTE_ABORT
            lib.dsmEndTxnEx(byref(end_in_abort), byref(end_out_abort))

            _logger.warning(
                "Group member removal transaction aborted",
                extra={
                    'event_type': 'c_api.backup.group.remove_members.abort.completed',
                    'reason_code': end_out_abort.reason,
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            raise


    def assignto_members(self, leader_obj_id: dict, member_obj_ids: list):
        """
        Assign existing objects as members to a group.

        Associates already-backed-up objects with a group leader,
        making them group members without re-backing them up.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.
        member_obj_ids : list
            List of existing object IDs to assign as members.

        Returns
        -------
        dict
            Result with count of assigned members.

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_ASSIGNTO
        """
        _logger.info(
            "Assigning members to group backup",
            extra={
                'event_type': 'c_api.backup.group.assignto_members.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'member_count': len(member_obj_ids),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        _logger.debug(
            "Calling dsmBeginTxn",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginTxn',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        rc = lib.dsmBeginTxn(self._handle)
        check_rc(self._handle, rc, "dsmBeginTxn")

        try:
            self._call_group_handler_assignto(leader_obj_id, member_obj_ids)

            end_in = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)
            end_out = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)
            end_in.dsmHandle = self._handle
            end_in.vote = DSM_VOTE_COMMIT

            _logger.debug(
                "Calling dsmEndTxnEx",
                extra={
                    'event_type': 'c_api.function.call',
                    'function': 'dsmEndTxnEx',
                    'vote': 'commit',
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            rc = lib.dsmEndTxnEx(byref(end_in), byref(end_out))
            check_rc(self._handle, rc, "dsmEndTxnEx (commit)")

            if end_out.reason != 0:
                _logger.error(
                    "Group member assignment transaction failed",
                    extra={
                        'event_type': 'c_api.backup.group.assignto_members.failed',
                        'reason_code': end_out.reason,
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )

                raise TSMTransactionError(
                    error_code=SDKErrorCode.COMMIT_FAILED,
                    message=f"Transaction failed with reason: {end_out.reason}"
                )

            result = {
                "status": "success",
                "assignedCount": len(member_obj_ids)
            }
            _logger.info(
                "Members assigned to group backup",
                extra={
                    'event_type': 'c_api.backup.group.assignto_members.completed',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'assigned_count': len(member_obj_ids),
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            return result

        except Exception:
            _logger.warning(
                "Aborting group member assignment transaction",
                extra={
                    'event_type': 'c_api.backup.group.assignto_members.abort',
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            end_in_abort = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)
            end_out_abort = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)
            end_in_abort.dsmHandle = self._handle
            end_in_abort.vote = DSM_VOTE_ABORT
            lib.dsmEndTxnEx(byref(end_in_abort), byref(end_out_abort))

            _logger.warning(
                "Group member assignment transaction aborted",
                extra={
                    'event_type': 'c_api.backup.group.assignto_members.abort.completed',
                    'reason_code': end_out_abort.reason,
                    'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            raise

    def delete_group(self, leader_obj_id: dict):
        """
        Delete a group by deleting the leader object.

        Deletes the group leader, which automatically cascades to delete
        all group members. This is the standard way to delete an entire group.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.

        Returns
        -------
        dict
            Result confirming deletion.

        Notes
        -----
        - Deleting leader cascades to all members
        - All group objects are removed from server
        - Cannot be undone

        Client API Reference
        --------------------
        dsmDeleteObj() - Delete object by ID
        """
        _logger.info(
            "Deleting group backup",
            extra={
                'event_type': 'c_api.backup.group.delete.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        delete_op = DeleteObjectOperation(self._handle)
        delete_op.delete_by_id(
            obj_id_hi=leader_obj_id['hi'],
            obj_id_lo=leader_obj_id['lo']
        )

        _logger.info(
            "Group backup deleted",
            extra={
                'event_type': 'c_api.backup.group.delete.completed',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        return {
            "status": "success"
        }

    def _make_op(self, obj):
        """
        Create a BackupOperation for a group object.

        Parameters
        ----------
        obj : dict
            Object dictionary with Key, Body, and attributes.

        Returns
        -------
        BackupOperation
            Configured backup operation for the object.
        """
        hl, ll = parse_key(obj["Key"])
        return BackupOperation(
            session=self.session,
            filespace=self.filespace,
            high_level=hl,
            low_level=ll,
            data_source=obj["Body"],          # already validate_chunks'd in client.py
            obj_type=obj.get("ObjType", DSM_OBJ_FILE),
            owner=obj.get("Owner", get_session_owner(self.session)),
            management_class=obj.get("ManagementClass"),
            size_estimate=obj.get("SizeEstimate", 1024),
            pre_compressed=obj.get("PreCompressed", False),
            mount_wait=obj.get("MountWait", True),
            obj_info=obj.get("ObjInfo"),           # ← ADDED
            disable_dedup=obj.get("DisableDedup", False),  # ← ADDED
        )

    def _call_group_handler_open(self, obj_name: dsmObjName):
        """
        Call dsmGroupHandler to open a new group.

        Parameters
        ----------
        obj_name : dsmObjName
            Object name structure for the leader.

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_OPEN
        """
        _logger.debug(
            "Opening C API group handler",
            extra={'event_type': 'c_api.backup.group.handler_open.started',
                'session_handle': self.session_handle,
                'object_key': self.object_key},

        )
        gi = init_struct(dsmGroupHandlerIn_t, dsmGroupHandlerInVersion)
        go = init_struct(dsmGroupHandlerOut_t, dsmGroupHandlerOutVersion)

        gi.dsmHandle = self._handle
        gi.groupType = DSM_GROUPTYPE_PEER
        gi.actionType = DSM_GROUP_ACTION_OPEN
        gi.memberType = DSM_MEMBERTYPE_LEADER
        gi.uniqueGroupTagP = self.group_tag
        gi.objNameP = pointer(obj_name)

        _logger.debug(
            "Calling dsmGroupHandler",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmGroupHandler',
                'action': 'OPEN',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        rc = lib.dsmGroupHandler(byref(gi), byref(go))
        check_rc(self._handle, rc, "dsmGroupHandler(OPEN)")

    def _call_group_handler_add(self, leader_obj_id: dict):
        """
        Call dsmGroupHandler to add a member to the group.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_ADD
        """
        _logger.debug(
            "Adding member via C API group handler",
            extra={
                'event_type': 'c_api.backup.group.handler_add.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        gi = init_struct(dsmGroupHandlerIn_t, dsmGroupHandlerInVersion)
        go = init_struct(dsmGroupHandlerOut_t, dsmGroupHandlerOutVersion)

        gi.dsmHandle = self._handle
        gi.groupType = DSM_GROUPTYPE_PEER
        gi.actionType = DSM_GROUP_ACTION_ADD
        gi.memberType = DSM_MEMBERTYPE_MEMBER
        gi.uniqueGroupTagP = (
            self.group_tag.encode('utf-8')
            if isinstance(self.group_tag, str)
            else self.group_tag
        )
        gi.leaderObjId.hi = leader_obj_id['hi']
        gi.leaderObjId.lo = leader_obj_id['lo']

        _logger.debug(
            "Calling dsmGroupHandler",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmGroupHandler',
                'action': 'ADD',
                'session_handle': self.session_handle,
                'object_key': self.object_key

            }
        )
        rc = lib.dsmGroupHandler(byref(gi), byref(go))
        check_rc(self._handle, rc, "dsmGroupHandler(ADD)")

    def _call_group_handler_close(self, leader_obj_id: dict):
        """
        Call dsmGroupHandler to close the group.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_CLOSE
        """
        _logger.debug(
            "Closing C API group handler",
            extra={
                'event_type': 'c_api.backup.group.handler_close.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        gi = init_struct(dsmGroupHandlerIn_t, dsmGroupHandlerInVersion)
        go = init_struct(dsmGroupHandlerOut_t, dsmGroupHandlerOutVersion)

        gi.dsmHandle = self._handle
        gi.groupType = DSM_GROUPTYPE_PEER
        gi.actionType = DSM_GROUP_ACTION_CLOSE
        gi.memberType = 0  # Must be 0 for CLOSE action, not DSM_MEMBERTYPE_LEADER
        gi.uniqueGroupTagP = (
            self.group_tag.encode('utf-8')
            if isinstance(self.group_tag, str)
            else self.group_tag
        )
        leader_id = dsStruct64_t()
        leader_id.hi = leader_obj_id["hi"]
        leader_id.lo = leader_obj_id["lo"]
        gi.leaderObjId = leader_id

        # Use the stored leader object name from when the group was opened
        # Match C API behavior: reuse the leader's objName but modify ll to "\"
        # See sampleapi.c line 649: strcpy(objName.ll,dsTEXT("/"));
        if self._leader_obj_name is not None:
            # Modify the ll field to match C API behavior
            self._leader_obj_name.ll = b"/"
            gi.objNameP = pointer(self._leader_obj_name)
        else:
            # Fallback: create a minimal object name if leader name wasn't stored
            close_obj_name = init_struct(dsmObjName)
            close_obj_name.fs = self.filespace.encode('utf-8')
            close_obj_name.hl = b"/"
            close_obj_name.ll = b"/"
            close_obj_name.objType = DSM_OBJ_FILE
            gi.objNameP = pointer(close_obj_name)








        _logger.debug(
            "Calling dsmGroupHandler",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmGroupHandler',
                'action': 'CLOSE',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        rc = lib.dsmGroupHandler(byref(gi), byref(go))

        check_rc(self._handle, rc, "dsmGroupHandler(CLOSE)")

    def _call_group_handler_remove(self, leader_obj_id: dict, member_obj_ids: list):
        """
        Call dsmGroupHandler to remove members from the group.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.
        member_obj_ids : list
            List of member object IDs to remove.

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_REMOVE
        """
        _logger.debug(
            "Removing members via C API group handler",
            extra={
                'event_type': 'c_api.backup.group.handler_remove.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'member_count': len(member_obj_ids),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        num_objs = len(member_obj_ids)
        obj_id_array = (ObjID * num_objs)()

        for i, obj_id in enumerate(member_obj_ids):
            obj_id_array[i].hi = obj_id['hi']
            obj_id_array[i].lo = obj_id['lo']

        get_list = dsmGetList()
        get_list.stVersion = dsmGetListVersion
        get_list.numObjId = num_objs
        get_list.objId = cast(obj_id_array, POINTER(ObjID))

        gi = init_struct(dsmGroupHandlerIn_t, dsmGroupHandlerInVersion)
        go = init_struct(dsmGroupHandlerOut_t, dsmGroupHandlerOutVersion)

        gi.dsmHandle = self._handle
        gi.groupType = DSM_GROUPTYPE_PEER
        gi.actionType = DSM_GROUP_ACTION_REMOVE
        gi.memberType = 0
        gi.uniqueGroupTagP = self.group_tag.encode('utf-8') if isinstance(self.group_tag, str) else self.group_tag
        gi.leaderObjId.hi = leader_obj_id['hi']
        gi.leaderObjId.lo = leader_obj_id['lo']
        gi.memberObjList = get_list

        _logger.debug(
            "Calling dsmGroupHandler",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmGroupHandler',
                'action': 'REMOVE',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        rc = lib.dsmGroupHandler(byref(gi), byref(go))
        check_rc(self._handle, rc, "dsmGroupHandler(REMOVE)")

    def _call_group_handler_assignto(self, leader_obj_id: dict, member_obj_ids: list):
        """
        Call dsmGroupHandler to assign existing objects as members.

        Parameters
        ----------
        leader_obj_id : dict
            Leader object ID with 'hi' and 'lo' components.
        member_obj_ids : list
            List of existing object IDs to assign as members.

        Client API Reference
        --------------------
        dsmGroupHandler() with DSM_GROUP_ACTION_ASSIGNTO
        """
        _logger.debug(
            "Assigning members via C API group handler",
            extra={
                'event_type': 'c_api.backup.group.handler_assignto.started',
                'leader_obj_id': f"{leader_obj_id['hi']}-{leader_obj_id['lo']}",
                'member_count': len(member_obj_ids),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        num_objs = len(member_obj_ids)
        obj_id_array = (ObjID * num_objs)()

        for i, obj_id in enumerate(member_obj_ids):
            obj_id_array[i].hi = obj_id['hi']
            obj_id_array[i].lo = obj_id['lo']

        get_list = dsmGetList()
        get_list.stVersion = dsmGetListVersion
        get_list.numObjId = num_objs
        get_list.objId = cast(obj_id_array, POINTER(ObjID))

        gi = init_struct(dsmGroupHandlerIn_t, dsmGroupHandlerInVersion)
        go = init_struct(dsmGroupHandlerOut_t, dsmGroupHandlerOutVersion)

        gi.dsmHandle = self._handle
        gi.groupType = DSM_GROUPTYPE_PEER
        gi.actionType = DSM_GROUP_ACTION_ASSIGNTO
        gi.memberType = DSM_MEMBERTYPE_MEMBER
        gi.uniqueGroupTagP = self.group_tag.encode('utf-8') if isinstance(self.group_tag, str) else self.group_tag
        gi.leaderObjId.hi = leader_obj_id['hi']
        gi.leaderObjId.lo = leader_obj_id['lo']
        gi.memberObjList = get_list

        _logger.debug(
            "Calling dsmGroupHandler",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmGroupHandler',
                'action': 'ASSIGNTO',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        rc = lib.dsmGroupHandler(byref(gi), byref(go))
        check_rc(self._handle, rc, "dsmGroupHandler(ASSIGNTO)")
