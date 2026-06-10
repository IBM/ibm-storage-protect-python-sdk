"""
IBM Storage Protect Client API - Group Restore Operations

This module provides Python wrappers for IBM Storage Protect group restore operations,
enabling retrieval of all members of a group backup using the IBM Storage Protect
Client API.

Key Responsibilities:
---------------------
1. **Group Restore**: Restore all members of a group backup by leader ID
2. **Query Integration**: Automatically query for all group members
3. **Member Ordering**: Sort members by restore order for correct retrieval
4. **Data Streaming**: Stream data for all members efficiently
5. **Leader Identification**: Identify and mark the group leader in results

Group Restore Workflow:
-----------------------
1. **Query Phase**: Query for all group members using leader object ID
2. **Validation**: Verify group exists and check member count limits
3. **Sort Members**: Sort members by restore order
4. **Begin Get Data**: Call dsmBeginGetData() with all member object IDs
5. **Stream Data**: Retrieve data for each member
6. **End Get Data**: Call dsmEndGetDataEx() to complete operation

Thread Safety:
--------------
Group operations are NOT thread-safe when using the same session handle.
Each thread should maintain its own session handle for concurrent operations.

Performance Considerations:
---------------------------
- All group members are restored in a single API call
- Maximum 255 members per group (Client API limit)
- Members are automatically sorted by restore order
- Efficient for logically related objects (e.g., database + logs)

Client API Integration:
-----------------------
This module wraps the following Client API functions:
- dsmBeginGetData() - Initialize restore operation with all member IDs
- dsmGetObj() - Retrieve first chunk of member data
- dsmGetData() - Retrieve subsequent chunks of member data
- dsmEndGetObj() - Complete single member retrieval
- dsmEndGetDataEx() - Complete entire group restore operation

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Group Backup", "Restore Operations"

Example Usage:
--------------
    # Restore entire group by leader ID
    group_restore = GroupRestoreOperation(
        handle=session_handle,
        filespace="/myfs",
        leader_hi=12345,
        leader_lo=67890
    )
    members = group_restore.execute()
    for member in members:
        if member['IsGroupLeader']:
            print(f"Leader: {member['Key']}")
        data = b"".join(member['Body'])
        save_file(member['Key'], data)
"""

from __future__ import annotations

# pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments,too-many-instance-attributes,broad-exception-caught


import ctypes
from ctypes import byref
from typing import (
    Any,
    Dict,
    List,
    Optional
)

from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_MAX_GET_OBJ,      # Maximum objects per restore operation (255)
    DSM_OBJ_FILE,         # Object type: File
    ObjID,                # Structure for object identifier (hi/lo pair)
    bFalse,               # Boolean false constant for C API
    bTrue,                # Boolean true constant for C API
    gtBackup,             # Get type: Backup (vs. archive)
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.errors.exceptions import ObjectNotFoundError
from ibm_storage_protect.errors import (
    SDKErrorCode,
    TSMOperationError
)
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    check_rc,
    iter_chunks
)
from ibm_storage_protect.c_api_bridge.wrappers.query import execute_group_query
from ibm_storage_protect.logger import get_logger
from ibm_storage_protect.c_api_bridge.wrappers.restore.single import (
    _build_get_list,
    _stream_one_obj,
    _end_get_data_ex,
    DEFAULT_CHUNK_SIZE
)

# Module-level logger for structured logging
_logger = get_logger(__name__)


class GroupRestoreOperation:
    """
    Restore all members of a group backup from IBM Storage Protect.

    This class handles restoration of group backups, which are collections of
    related objects backed up together. All group members are restored in a
    single operation using their group leader object ID.

    Group Restore Process:
    ----------------------
    1. Query for group members using leader object ID
    2. Sort members by restore order
    3. Call dsmBeginGetData() with all member object IDs
    4. Stream data for each member
    5. Call dsmEndGetDataEx() to complete operation

    Attributes
    ----------
    handle : int
        Session handle from dsmInitEx().
    filespace : str
        Filespace name where the group is stored.
    leader_hi : int
        High 32 bits of the group leader object ID.
    leader_lo : int
        Low 32 bits of the group leader object ID.
    owner : str, default=""
        Owner name for multi-owner configurations.
    obj_type : int, default=DSM_OBJ_FILE
        Object type filter for group members.
    mount_wait : bool, default=True
        Whether to wait for tape mount if objects are on tape.
    session_handle : str, optional
        Correlation ID for logging.
    object_key : str, optional
        Object identifier for logging.
    chunk_size : int
        Size of data chunks for streaming.
    MAX_BATCH : int
        Maximum group members per operation (DSM_MAX_GET_OBJ = 255).

    Notes
    -----
    - Group backups enable atomic backup/restore of related objects
    - All members are restored together in a single API call
    - Maximum 255 members per group (Client API limit)
    - Members are automatically sorted by restore order

    Example
    -------
    >>> # Restore entire group by leader ID
    >>> group_restore = GroupRestoreOperation(
    ...     handle=session_handle,
    ...     filespace="/myfs",
    ...     leader_hi=12345,
    ...     leader_lo=67890
    ... )
    >>> members = group_restore.execute()
    >>> for member in members:
    ...     print(f"Member: {member['Key']}")
    ...     with open(member['Key'], 'wb') as f:
    ...         for chunk in member['Body']:
    ...             f.write(chunk)

    See Also
    --------
    RestoreOperation : Restore single object
    BatchRestoreOperation : Restore multiple objects efficiently
    """
    # Maximum group members per operation (Client API limit)
    MAX_BATCH = DSM_MAX_GET_OBJ

    def __init__(
        self,
        handle:     int,
        filespace:  str,
        leader_hi:  int,
        leader_lo:  int,
        owner:      str  = "",
        obj_type:   int  = DSM_OBJ_FILE,
        mount_wait: bool = True,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None,
    ):
        """
        Initialize a GroupRestoreOperation instance.

        Parameters
        ----------
        handle : int
            Session handle from dsmInitEx()
        filespace : str
            Filespace name where group is stored
        leader_hi : int
            High 32 bits of group leader object ID
        leader_lo : int
            Low 32 bits of group leader object ID
        owner : str, optional
            Owner name for multi-owner configurations
        obj_type : int, optional
            Object type filter (default: DSM_OBJ_FILE)
        mount_wait : bool, optional
            Wait for tape mount if needed (default: True)
        session_handle : str, optional
            Correlation ID for logging
        object_key : str, optional
            Object identifier for logging
        """
        self.handle     = handle
        self.filespace  = filespace
        self.leader_hi  = leader_hi
        self.leader_lo  = leader_lo
        self.owner      = owner
        self.obj_type   = obj_type
        self.mount_wait = mount_wait
        self.session_handle = session_handle
        self.object_key = object_key
        self.chunk_size = DEFAULT_CHUNK_SIZE

    def execute(self) -> List[Dict[str, Any]]:
        """
        Execute group restore operation and return all member data.

        Queries for all group members, restores their data, and returns
        results with metadata for each member.

        Returns
        -------
        List[Dict[str, Any]]
            List of member dictionaries, each containing:
            - Key: Object key without leading slash
            - Filespace: Filespace name
            - Body: Generator[bytes] yielding data chunks
            - IsGroupLeader: True if this is the group leader
            - LastModified: Last modification datetime
            - ObjectId: Object identifier string
            - MediaClass: Storage media class
            - ManagementClass: Management class name

        Raises
        ------
        ObjectNotFoundError
            If no group is found with the specified leader ID.
        TSMOperationError
            If group has too many members (> MAX_BATCH).
        RestoreError
            If any Client API operation fails.

        Notes
        -----
        - All members are restored in a single operation
        - Members are returned in restore order
        - Each member's Body is a generator that must be consumed
        - The group leader is identified by IsGroupLeader=True

        Example
        -------
        >>> members = group_op.execute()
        >>> for member in members:
        ...     if member['IsGroupLeader']:
        ...         print(f"Leader: {member['Key']}")
        ...     data = b"".join(member["Body"])
        ...     save_file(member['Key'], data)
        """
        _logger.info(
            "Executing group restore operation",
            extra={
                'event_type': 'c_api.restore.group.execute.started',
                'filespace': self.filespace,
                'leader_hi': self.leader_hi,
                'leader_lo': self.leader_lo,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Query for all group members using leader object ID
        entries = execute_group_query(
            handle    = self.handle,
            filespace = self.filespace,
            leader_hi = self.leader_hi,
            leader_lo = self.leader_lo,
            owner     = self.owner,
            obj_type  = self.obj_type,
        )

        # Verify group exists
        if not entries:
            raise ObjectNotFoundError(
                error_code=SDKErrorCode.OBJECT_NOT_FOUND,
                message=f"No group found for GroupLeaderObjId="
                        f"{self.leader_hi}-{self.leader_lo} "
                        f"in filespace={self.filespace!r}"
            )

        # Check if group exceeds Client API limit
        if len(entries) > self.MAX_BATCH:
            raise TSMOperationError(
                error_code=SDKErrorCode.SIZE_LIMIT_EXCEEDED,
                message=f"Group has {len(entries)} members, exceeds C API "
                        f"limit of {self.MAX_BATCH}."
            )

        # Sort members by restore order for correct retrieval sequence
        entries.sort(key=lambda e: (
            e["_restoreOrder"].top,
            e["_restoreOrder"].hi_hi,
            e["_restoreOrder"].hi_lo,
            e["_restoreOrder"].lo_hi,
            e["_restoreOrder"].lo_lo,
        ))

        # Build array of object IDs for all group members
        n        = len(entries)
        ObjArray = ObjID * n
        obj_arr  = ObjArray()
        for i, e in enumerate(entries):
            obj_arr[i].hi = e["_objId"].hi
            obj_arr[i].lo = e["_objId"].lo

        # Build get list for full restore (no partial restore for groups)
        get_list, _anchor = _build_get_list(obj_arr, n, False, [0] * n, [0] * n)

        _logger.debug(
            "Calling dsmBeginGetData for group",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginGetData',
                'num_members': n,
                'mount_wait': self.mount_wait,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        rc = lib.dsmBeginGetData(
            self.handle,
            bTrue if self.mount_wait else bFalse,
            gtBackup,
            byref(get_list),
        )
        check_rc(self.handle, rc, "dsmBeginGetData")

        # Allocate buffer for streaming data chunks
        chunk_buf     = ctypes.create_string_buffer(self.chunk_size)
        # Storage for collected data: collected[member_idx] = List[bytes]
        collected:    Dict[int, List[bytes]] = {}
        pending_error = None

        try:
            # Stream and collect data for each group member
            for i, entry in enumerate(entries):
                # Collect all chunks for this member (must materialize while buffer is valid)
                collected[i] = list(
                    _stream_one_obj(
                        self.handle, entry["_objId"], chunk_buf, self.chunk_size,
                        self.session_handle, self.object_key
                    )
                )
        except Exception as exc:
            # Capture exception but don't raise yet (cleanup first)
            pending_error = exc
        finally:
            # Always end the restore operation to free resources
            _end_get_data_ex(self.handle, self.session_handle, self.object_key)

        # Re-raise exception after cleanup if one occurred
        if pending_error:
            raise pending_error

        _logger.info(
            "Group restore operation completed",
            extra={
                'event_type': 'c_api.restore.group.execute.completed',
                'num_members': len(entries),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Return list of member results with metadata
        return [
            {
                "Key":             entry.get("Key", ""),
                "Filespace":       entry.get("Filespace", ""),
                "Body":            iter_chunks(collected[i]),  # Lazy generator from collected chunks
                "IsGroupLeader":   entry.get("IsGroupLeader", False),
                "LastModified":    entry.get("LastModified"),
                "ObjectId":        entry.get("ObjectId", ""),
                "MediaClass":      entry.get("MediaClass", ""),
                "ManagementClass": entry.get("ManagementClass", ""),
            }
            for i, entry in enumerate(entries)
        ]
