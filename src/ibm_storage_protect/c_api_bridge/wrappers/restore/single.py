"""
IBM Storage Protect Client API - Single Object Restore Operations

This module provides Python wrappers for IBM Storage Protect single object restore
operations, enabling retrieval of individual backed-up objects using the IBM Storage
Protect Client API.

Key Responsibilities:
---------------------
1. **Single Object Restore**: Restore individual backed-up objects by key
2. **Partial Restore**: Support for offset/length-based partial object retrieval
3. **Data Streaming**: Stream restored data as generators for memory efficiency
4. **Query Integration**: Automatically query for object metadata before restore
5. **Multi-Part Handling**: Handle objects split across multiple parts

Restore Workflow:
-----------------
1. **Query Phase**: Query backed-up objects to get object IDs and metadata
2. **Sort Parts**: Sort object parts by restore order (for multi-part objects)
3. **Begin Get Data**: Call dsmBeginGetData() with object list
4. **Stream Data**: Retrieve data via dsmGetObj() and dsmGetData()
5. **End Get Data**: Call dsmEndGetDataEx() to complete operation
6. **Error Handling**: Check return codes and map to SDK exceptions

Thread Safety:
--------------
Restore operations are NOT thread-safe when using the same session handle.
Each thread should maintain its own session handle for concurrent restores.

Performance Considerations:
---------------------------
- Chunk size affects memory usage and network efficiency (default: 1MB)
- Partial restores reduce data transfer for large objects
- Multi-part objects are automatically handled and reassembled

Client API Integration:
-----------------------
This module wraps the following Client API functions:
- dsmBeginGetData() - Initialize restore operation with object list
- dsmGetObj() - Retrieve first chunk of object data
- dsmGetData() - Retrieve subsequent chunks of object data
- dsmEndGetObj() - Complete single object retrieval
- dsmEndGetDataEx() - Complete entire restore operation

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Restore Operations", "Data Retrieval"

Example Usage:
--------------
    # Single object restore
    restore_op = RestoreOperation(
        handle=session_handle,
        filespace="/myfs",
        key="/data/file.txt"
    )
    result = restore_op.execute()
    for chunk in result["Body"]:
        process(chunk)

    # Partial restore
    restore_op = RestoreOperation(
        handle=session_handle,
        filespace="/myfs",
        key="/data/large_file.bin",
        offset=1024,
        length=4096
    )
    result = restore_op.execute()
"""

from __future__ import annotations

# pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments,too-many-instance-attributes,too-many-locals,broad-exception-caught


import ctypes
from ctypes import byref
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional
)

from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_ACTIVE,           # Object state: Active (current version)
    DSM_MAX_GET_OBJ,      # Maximum objects per restore operation (255)
    DSM_OBJ_FILE,         # Object type: File
    DataBlk,              # Structure for data transfer buffer
    DataBlkVersion,       # Version constant for DataBlk structure
    ObjID,                # Structure for object identifier (hi/lo pair)
    PartialObjData,       # Structure for partial object specifications
    PartialObjDataVersion,# Version constant for PartialObjData
    bFalse,               # Boolean false constant for C API
    bTrue,                # Boolean true constant for C API
    dsmEndGetDataExIn_t,  # Input structure for dsmEndGetDataEx()
    dsmEndGetDataExInVersion,  # Version constant for dsmEndGetDataExIn_t
    dsmEndGetDataExOut_t, # Output structure for dsmEndGetDataEx()
    dsmEndGetDataExOutVersion, # Version constant for dsmEndGetDataExOut_t
    dsmGetList,           # Structure for object list in restore operations
    dsmGetListPORVersion, # Version for partial object restore
    dsmGetListVersion,    # Version for full object restore
    gtBackup,             # Get type: Backup (vs. archive)
)
from ibm_storage_protect.c_api_bridge.c_api.return_codes import (
    DSM_RC_FINISHED,
    DSM_RC_MORE_DATA,
    DSM_RC_OK
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    init_struct,
    check_rc
)
from ibm_storage_protect.c_api_bridge.wrappers.query import execute_backup_query
from ibm_storage_protect.errors import (
    SDKErrorCode,
    TSMObjectError,
    TSMOperationError
)
from ibm_storage_protect.logger import get_logger

# Module-level logger for structured logging
_logger = get_logger(__name__)

# Default chunk size for streaming data (1MB)
# Balances memory usage and network efficiency
DEFAULT_CHUNK_SIZE = 1 * 1024 * 1024


def _build_get_list(
    obj_arr:     ctypes.Array,
    n:           int,
    has_partial: bool,
    offsets:     List[int],
    lengths:     List[int],
) -> tuple:
    """
    Build dsmGetList structure for restore operation.

    Parameters
    ----------
    obj_arr : ctypes.Array
        Array of ObjID structures
    n : int
        Number of objects
    has_partial : bool
        Whether partial restore is requested
    offsets : List[int]
        List of byte offsets for partial restore
    lengths : List[int]
        List of byte lengths for partial restore

    Returns
    -------
    tuple
        (get_list, anchor) where anchor keeps partial_arr alive
    """
    get_list = init_struct(dsmGetList)
    anchor = None

    if has_partial:
        PartArray   = PartialObjData * n
        partial_arr = PartArray()
        for i in range(n):
            partial_arr[i].stVersion = PartialObjDataVersion
            partial_arr[i].partialObjOffset.hi = (offsets[i] >> 32) & 0xFFFFFFFF
            partial_arr[i].partialObjOffset.lo =  offsets[i]        & 0xFFFFFFFF
            partial_arr[i].partialObjLength.hi = (lengths[i] >> 32) & 0xFFFFFFFF
            partial_arr[i].partialObjLength.lo =  lengths[i]        & 0xFFFFFFFF
        get_list.stVersion      = dsmGetListPORVersion
        get_list.partialObjData = ctypes.cast(partial_arr, ctypes.POINTER(PartialObjData))
        anchor = partial_arr
    else:
        get_list.stVersion      = dsmGetListVersion
        get_list.partialObjData = None

    get_list.numObjId = n
    get_list.objId    = ctypes.cast(obj_arr, ctypes.POINTER(ObjID))
    return get_list, anchor


def _stream_one_obj(
    handle:    int,
    obj_id:    ObjID,
    chunk_buf: ctypes.Array,
    chunk_size: int,
    session_handle: Optional[str]  = None,
    object_key: Optional[str]      = None,
) -> Generator[bytes, None, None]:
    """
    Stream data for a single object from IBM Storage Protect.

    Parameters
    ----------
    handle : int
        Session handle
    obj_id : ObjID
        Object identifier
    chunk_buf : ctypes.Array
        Buffer for data chunks
    chunk_size : int
        Size of chunk buffer
    session_handle : Optional[str]
        Session handle for logging
    object_key : Optional[str]
        Object key for logging

    Yields
    ------
    bytes
        Data chunks from the object
    """
    _logger.debug(
        "Streaming object data",
        extra={
            'event_type': 'c_api.restore.stream_obj.started',
            'obj_id_hi': obj_id.hi,
            'obj_id_lo': obj_id.lo,
            'chunk_size': chunk_size,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    data_blk = init_struct(DataBlk, DataBlkVersion)
    data_blk.bufferLen = chunk_size
    data_blk.numBytes  = 0
    data_blk.bufferPtr = ctypes.cast(chunk_buf, ctypes.c_char_p)

    _logger.debug(
        "Calling dsmGetObj",
        extra={
            'event_type': 'c_api.function.call',
            'function': 'dsmGetObj',
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    rc = lib.dsmGetObj(handle, byref(obj_id), byref(data_blk))
    if rc not in (DSM_RC_OK, DSM_RC_MORE_DATA, DSM_RC_FINISHED):
        check_rc(handle, rc, "dsmGetObj")
    if data_blk.numBytes > 0:
        yield bytes(chunk_buf[: data_blk.numBytes])

    bytes_received = data_blk.numBytes

    while rc == DSM_RC_MORE_DATA:
        data_blk.numBytes  = 0
        data_blk.bufferPtr = ctypes.cast(chunk_buf, ctypes.c_char_p)

        _logger.debug(
            "Calling dsmGetData",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmGetData',
                'session_handle': session_handle,
                'object_key': object_key
            }
        )

        rc = lib.dsmGetData(handle, byref(data_blk))
        if rc not in (DSM_RC_OK, DSM_RC_MORE_DATA, DSM_RC_FINISHED):
            check_rc(handle, rc, "dsmGetData")
        if data_blk.numBytes > 0:
            bytes_received += data_blk.numBytes
            yield bytes(chunk_buf[: data_blk.numBytes])

    _logger.debug(
        "Calling dsmEndGetObj",
        extra={
            'event_type': 'c_api.function.call',
            'function': 'dsmEndGetObj',
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    end_rc = lib.dsmEndGetObj(handle)
    if end_rc != DSM_RC_OK:
        check_rc(handle, end_rc, "dsmEndGetObj")

    _logger.debug(
        "Object streaming completed",
        extra={
            'event_type': 'c_api.restore.stream_obj.completed',
            'bytes_received': bytes_received,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )


def _end_get_data_ex(
    handle: int,
    session_handle: Optional[str]  = None,
    object_key: Optional[str]      = None,
) -> None:
    """
    End the restore operation and clean up resources.

    Parameters
    ----------
    handle : int
        Session handle
    session_handle : Optional[str]
        Session handle for logging
    object_key : Optional[str]
        Object key for logging
    """
    _logger.debug(
        "Ending get data operation",
        extra={
            'event_type': 'c_api.restore.end_get_data.started',
            'session_handle': session_handle,
            'object_key': object_key
        },
    )

    end_in  = init_struct(dsmEndGetDataExIn_t, dsmEndGetDataExInVersion)
    end_out = init_struct(dsmEndGetDataExOut_t, dsmEndGetDataExOutVersion)
    end_in.dsmHandle  = handle
    end_out.stVersion = dsmEndGetDataExOutVersion

    _logger.debug(
        "Calling dsmEndGetDataEx",
        extra={
            'event_type': 'c_api.function.call',
            'function': 'dsmEndGetDataEx',
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    rc = lib.dsmEndGetDataEx(byref(end_in), byref(end_out))
    check_rc(handle, rc, "dsmEndGetDataEx")

    _logger.debug(
        "Get data operation ended",
        extra={
            'event_type': 'c_api.restore.end_get_data.completed',
            'session_handle': session_handle,
            'object_key': object_key
        },
    )


class RestoreOperation:
    """
    Restore a single backed-up object from IBM Storage Protect.

    This class handles the complete workflow for restoring a single object:
    querying for the object, initiating the restore operation, streaming the
    data, and cleaning up resources. Supports both full and partial object
    restore.

    Restore Process:
    ----------------
    1. Query for object by filespace and key to get object ID(s)
    2. Sort object parts by restore order (for multi-part objects)
    3. Call dsmBeginGetData() to initiate restore
    4. Stream data chunks via dsmGetObj() and dsmGetData()
    5. Call dsmEndGetDataEx() to complete operation

    Attributes
    ----------
    handle : int
        Session handle from dsmInitEx().
    filespace : str
        Filespace name where the object is stored.
    key : str
        Object key (path) to restore.
    obj_state : int, default=DSM_ACTIVE
        Object state filter (DSM_ACTIVE, DSM_INACTIVE, DSM_ANY_MATCH).
    obj_type : int, default=DSM_OBJ_FILE
        Object type filter (DSM_OBJ_FILE, DSM_OBJ_DIRECTORY, etc.).
    pit_date : datetime, optional
        Point-in-time date for historical restore. None for latest version.
    mount_wait : bool, default=True
        Whether to wait for tape mount if object is on tape.
    offset : int, default=0
        Starting byte offset for partial restore (0 for full restore).
    length : int, default=0
        Number of bytes to restore (0 for full restore from offset to end).
    owner : str, default=""
        Owner name for multi-owner configurations.
    session_handle : str, optional
        Correlation ID for logging.
    object_key : str, optional
        Object identifier for logging.
    chunk_size : int
        Size of data chunks for streaming (default: DEFAULT_CHUNK_SIZE).

    Notes
    -----
    - Objects may consist of multiple parts (e.g., large files)
    - Parts are automatically sorted by restore order
    - Maximum 255 parts per object (DSM_MAX_GET_OBJ limit)
    - Partial restore reduces data transfer for large objects

    Example
    -------
    >>> restore_op = RestoreOperation(
    ...     handle=session_handle,
    ...     filespace="/myfs",
    ...     key="/data/file.txt"
    ... )
    >>> result = restore_op.execute()
    >>> data = b"".join(result["Body"])
    """

    def __init__(
        self,
        handle:         int,
        filespace:      str,
        key:            str,
        obj_state:      int                = DSM_ACTIVE,
        obj_type:       int                = DSM_OBJ_FILE,
        pit_date:       Optional[datetime] = None,
        mount_wait:     bool               = True,
        offset:         int                = 0,
        length:         int                = 0,
        owner:          str                = "",
        session_handle: Optional[str]      = None,
        object_key:     Optional[str]      = None,
    ):
        """
        Initialize a RestoreOperation instance.

        Parameters
        ----------
        handle : int
            Session handle from dsmInitEx()
        filespace : str
            Filespace name where the object is stored
        key : str
            Object key (path) to restore
        obj_state : int, optional
            Object state filter (default: DSM_ACTIVE)
        obj_type : int, optional
            Object type filter (default: DSM_OBJ_FILE)
        pit_date : datetime, optional
            Point-in-time date for historical restore
        mount_wait : bool, optional
            Whether to wait for tape mount (default: True)
        offset : int, optional
            Starting byte offset for partial restore (default: 0)
        length : int, optional
            Number of bytes to restore (default: 0, full restore)
        owner : str, optional
            Owner name for multi-owner configurations
        session_handle : str, optional
            Correlation ID for logging
        object_key : str, optional
            Object identifier for logging
        """
        self.handle         = handle
        self.filespace      = filespace
        self.key            = key
        self.obj_state      = obj_state
        self.obj_type       = obj_type
        self.pit_date       = pit_date
        self.mount_wait     = mount_wait
        self.offset         = offset
        self.length         = length
        self.owner          = owner
        self.session_handle = session_handle
        self.object_key     = object_key
        self.chunk_size     = DEFAULT_CHUNK_SIZE

    def execute(self) -> Dict[str, Any]:
        """
        Execute single object restore operation.

        Queries for the object, initiates restore, streams data, and returns
        the result with metadata and a data generator.

        Returns
        -------
        Dict[str, Any]
            Result dictionary containing:
            - Key: Object key without leading slash
            - Filespace: Filespace name
            - Body: Generator[bytes] yielding data chunks
            - LastModified: Last modification datetime
            - ObjectId: Object identifier string
            - MediaClass: Storage media class
            - ManagementClass: Management class name

        Raises
        ------
        TSMObjectError
            If the object is not found.
        TSMOperationError
            If the object has too many parts (> DSM_MAX_GET_OBJ).
        RestoreError
            If any Client API operation fails.

        Example
        -------
        >>> result = restore_op.execute()
        >>> print(f"Restoring: {result['Key']}")
        >>> data = b"".join(result["Body"])
        >>> print(f"Size: {len(data)} bytes")
        """
        _logger.info(
            "Executing single restore operation",
            extra={
                'event_type': 'c_api.restore.single.execute.started',
                'filespace': self.filespace,
                'key': self.key,
                'obj_state': self.obj_state,
                'obj_type': self.obj_type,
                'offset': self.offset,
                'length': self.length,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Query for the object
        entries = execute_backup_query(
            handle    = self.handle,
            filespace = self.filespace,
            key       = self.key,
            obj_state = self.obj_state,
            obj_type  = self.obj_type,
            pit_date  = self.pit_date,
            owner     = self.owner,
            session_handle = self.session_handle,
            object_key = self.object_key,
        )

        # Verify object exists
        if not entries:
            raise TSMObjectError(
                error_code=SDKErrorCode.OBJECT_NOT_FOUND,
                message=f"Object not found: filespace={self.filespace!r} key={self.key!r}"
            )

        # Check part count limit
        if len(entries) > DSM_MAX_GET_OBJ:
            raise TSMOperationError(
                error_code=SDKErrorCode.OPERATION_FAILED,
                message=f"Object '{self.key}' has {len(entries)} parts, exceeds C API limit of {DSM_MAX_GET_OBJ}"
            )

        # Sort parts by restore order
        entries.sort(key=lambda e: (
            e["_restoreOrder"].top,
            e["_restoreOrder"].hi_hi,
            e["_restoreOrder"].hi_lo,
            e["_restoreOrder"].lo_hi,
            e["_restoreOrder"].lo_lo,
        ))

        # Stream the data
        meta = entries[0]  # Metadata from first part
        body_generator = self._stream_data(entries)

        _logger.info(
            "Single restore operation completed",
            extra={
                'event_type': 'c_api.restore.single.execute.completed',
                'filespace': self.filespace,
                'key': self.key,
                'part_count': len(entries),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        return {
            "Key":             self.key.lstrip("/"),
            "Filespace":       self.filespace,
            "Body":            body_generator,
            "LastModified":    meta.get("LastModified"),
            "ObjectId":        meta.get("ObjectId", ""),
            "MediaClass":      meta.get("MediaClass", ""),
            "ManagementClass": meta.get("ManagementClass", ""),
        }

    def _stream_data(self, entries: List[Dict[str, Any]]) -> Generator[bytes, None, None]:
        """
        Stream data for all object parts.

        Parameters
        ----------
        entries : List[Dict[str, Any]]
            List of object parts with metadata

        Yields
        ------
        bytes
            Data chunks from all parts in order
        """
        n = len(entries)
        ObjArray = ObjID * n
        obj_arr  = ObjArray()

        for i, e in enumerate(entries):
            obj_arr[i].hi = e["_objId"].hi
            obj_arr[i].lo = e["_objId"].lo

        # Determine if partial restore
        is_partial = (self.offset > 0 or self.length > 0)
        offsets = [self.offset] * n if is_partial else []
        lengths = [self.length] * n if is_partial else []

        get_list, _anchor = _build_get_list(obj_arr, n, is_partial, offsets, lengths)

        _logger.debug(
            "Calling dsmBeginGetData",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginGetData',
                'mount_wait': self.mount_wait,
                'part_count': n,
                'is_partial': is_partial,
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

        # Stream data from all parts
        chunk_buf = ctypes.create_string_buffer(self.chunk_size)
        pending_error = None

        try:
            for entry in entries:
                obj_id = entry["_objId"]
                try:
                    yield from _stream_one_obj(
                        self.handle, obj_id, chunk_buf, self.chunk_size,
                        self.session_handle, self.object_key
                    )
                except Exception as exc:
                    pending_error = exc
                    break
        finally:
            _end_get_data_ex(self.handle, self.session_handle, self.object_key)
            if pending_error:
                raise pending_error
