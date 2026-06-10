"""
IBM Storage Protect Client API - Query Operations

This module provides Python wrappers for IBM Storage Protect query operations,
enabling retrieval of backed-up objects, filespaces, management classes, and
group backup information from the IBM Storage Protect server.

Key Responsibilities:
---------------------
1. **Backup Queries**: Query backed-up objects by filespace, key, and state
2. **Group Queries**: Retrieve group backup members and leader information
3. **Filespace Queries**: List available filespaces and their properties
4. **Management Class Queries**: Query management class configurations
5. **Object Listing**: List objects with prefix filtering and pagination

Query Types Supported:
----------------------
- qtBackup: Query backed-up objects (files, directories, etc.)
- qtFilespace: Query filespace information and statistics
- qtMC: Query management class definitions and policies
- qtBackupGroups: Query group backup relationships (via qtBackup)

Query Workflow:
---------------
1. **Begin Query**: Call dsmBeginQuery() with query type and parameters
2. **Fetch Results**: Repeatedly call dsmGetNextQObj() until finished
3. **End Query**: Call dsmEndQuery() to release resources
4. **Error Handling**: Check return codes and map to SDK exceptions

Thread Safety:
--------------
Query operations are NOT thread-safe when using the same session handle.
Each thread should maintain its own session handle for concurrent queries.

Performance Considerations:
---------------------------
- Use max_keys parameter to limit result set size
- Leverage prefix filtering to reduce server-side processing
- Point-in-time queries may be slower than active-only queries
- Group queries require full filespace scan for member identification

Client API Integration:
-----------------------
This module wraps the following Client API functions:
- dsmBeginQuery() - Initialize a query operation
- dsmGetNextQObj() - Retrieve next query result
- dsmEndQuery() - Terminate query and free resources

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Query Operations", "Object Management", "Group Backup"

Example Usage:
--------------
    # Query backed-up objects
    results = execute_backup_query(
        handle=session_handle,
        filespace="/myfs",
        key="/data/file.txt",
        obj_state=DSM_ACTIVE
    )

    # List objects with prefix
    listing = QueryOperation.list_objects(
        handle=session_handle,
        filespace="/myfs",
        prefix="/backup",
        max_keys=1000
    )

    # Query group members
    group_objects = execute_group_query(
        handle=session_handle,
        filespace="/myfs",
        leader_hi=12345,
        leader_lo=67890
    )
"""

from __future__ import annotations

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals


import ctypes
from ctypes import (
    byref,
    memset,
    sizeof
)
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_ACTIVE,
    DSM_OBJ_ANY_TYPE,
    DSM_OBJ_FILE,
    MEDIA_FIXED,
    MEDIA_LIBRARY,
    DataBlk,
    DataBlkVersion,
    ObjID,
    bFalse,
    bTrue,
    dsmObjName,
    qtBackup,
    qtFilespace,
    qtMC,
    qryBackupData,
    qryBackupDataVersion,
    qryFSData,
    qryFSDataVersion,
    qryMCData,
    qryMCDataVersion,
    qryRespBackupData,
    qryRespBackupDataVersion,
    qryRespFSData,
    qryRespFSDataVersion,
    qryRespMCData,
    qryRespMCDataVersion,
    qryRespMCDetailData,
    qryRespMCDetailDataVersion,
)
from ibm_storage_protect.c_api_bridge.c_api.return_codes import (
    DSM_RC_ABORT_NO_MATCH,
    DSM_RC_FINISHED,
    DSM_RC_MORE_DATA,
    DSM_RC_OK,
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    key_to_hl_ll,
    prefix_to_hl_ll,
    unwrap_handle as _unwrap,
    decode_field,
    size64,
    dsm_date_to_datetime,
    datetime_to_dsm_date,
    init_struct,
    check_rc
)
from ibm_storage_protect.logger import get_logger
# Module-level logger for structured logging
_logger = get_logger(__name__)

# Internal keys used for restore operations that should be filtered from user-facing results
_RESTORE_INTERNAL_KEYS = frozenset({"_objId", "_restoreOrder", "_mediaClassRaw"})







def _make_data_blk(buf_ptr: ctypes.c_char_p,
                   buf_len: int,
                   session_handle: Optional[str] = None,
                   object_key: Optional[str] = None,
                   ) -> DataBlk:
    """
    Create and initialize a DataBlk structure for query operations.

    The DataBlk structure is used by the IBM Storage Protect Client API to
    receive query results. This function properly initializes the structure
    with the provided buffer pointer and length.

    Parameters
    ----------
    buf_ptr : ctypes.c_char_p
        Pointer to the buffer that will receive query result data.
        Typically points to a query response structure (e.g., qryRespBackupData).
    buf_len : int
        Size of the buffer in bytes. Must match the size of the response structure.
    session_handle : str, optional
        Correlation ID for logging and tracking purposes.
    object_key : str, optional
        Object identifier for logging context.

    Returns
    -------
    DataBlk
        An initialized DataBlk structure ready for use with dsmGetNextQObj().

    Notes
    -----
    - The structure version is set to DataBlkVersion
    - numBytes is initialized to 0 and will be set by the Client API
    - The buffer must remain valid for the lifetime of the query operation

    Client API Reference
    --------------------
    DataBlk structure in structs.py
    Used with dsmGetNextQObj() to receive query results

    Example
    -------
    >>> resp = qryRespBackupData()
    >>> buf_ptr = ctypes.cast(byref(resp), ctypes.c_char_p)
    >>> data_blk = _make_data_blk(buf_ptr, sizeof(qryRespBackupData))
    >>> rc = lib.dsmGetNextQObj(handle, byref(data_blk))
    """
    _logger.debug(
        "Creating query data block",
        extra={
            'event_type': 'c_api.query.data_blk.init',
            'buffer_length': buf_len,
            'session_handle': session_handle,
            'object_key': object_key

        }
    )
    blk = init_struct(DataBlk, DataBlkVersion)
    blk.bufferLen  = buf_len
    blk.numBytes   = 0
    blk.bufferPtr  = buf_ptr
    return blk


def _media_str(media: int) -> str:
    """
    Convert a media class code to a human-readable string.

    IBM Storage Protect uses integer codes to represent storage media types.
    This function converts these codes to descriptive strings for user display.

    Parameters
    ----------
    media : int
        The media class code from the Client API (e.g., MEDIA_FIXED, MEDIA_LIBRARY).

    Returns
    -------
    str
        A human-readable media type string:
        - "DISK" for fixed disk storage (MEDIA_FIXED)
        - "TAPE" for tape library storage (MEDIA_LIBRARY)
        - Hexadecimal representation for unknown codes (e.g., "0x03")

    Notes
    -----
    - MEDIA_FIXED typically indicates disk-based storage pools
    - MEDIA_LIBRARY typically indicates tape-based storage pools
    - Unknown codes are formatted as hexadecimal for debugging

    Example
    -------
    >>> _media_str(MEDIA_FIXED)
    'DISK'

    >>> _media_str(MEDIA_LIBRARY)
    'TAPE'

    >>> _media_str(0x99)
    '0x99'
    """
    if media == MEDIA_FIXED:
        return "DISK"
    if media == MEDIA_LIBRARY:
        return "TAPE"
    return f"0x{media:02X}"





def _run_backup_query(
    handle:    int,
    filespace: str,
    hl:        str,
    ll:        str,
    obj_state: int,
    obj_type:  int = DSM_OBJ_FILE,
    max_keys:  int = 0,
    pit_date: Optional[datetime] = None,
    owner : str = "",
    session_handle: Optional[str] = None,
    object_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _logger.debug(
        "Running backup query",
        extra={
            'event_type': 'c_api.query.backup.started',
            'filespace': filespace,
            'hl': hl,
            'll': ll,
            'obj_state': obj_state,
            'obj_type': obj_type,
            'max_keys': max_keys,
            'owner': owner or None,
            'pit_date': pit_date.isoformat() if pit_date else None,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    obj_name = init_struct(dsmObjName)
    obj_name.fs = filespace.encode("utf-8")
    obj_name.hl      = hl.encode("utf-8")
    obj_name.ll      = ll.encode("utf-8")
    obj_name.objType = obj_type


    qry = init_struct(qryBackupData, qryBackupDataVersion)
    qry.objName   = ctypes.pointer(obj_name)
    qry.objState  = obj_state
    qry.owner     = owner.encode("utf-8") if owner else None
    qry.pitDate   = datetime_to_dsm_date(pit_date)

    _logger.debug(
        "Calling dsmBeginQuery",
        extra={
            'event_type': 'c_api.function.call',
            'function': 'dsmBeginQuery',
            'query_type': 'qtBackup',
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    rc = lib.dsmBeginQuery(handle, qtBackup, byref(qry))
    check_rc(handle, rc, f"dsmBeginQuery(qtBackup) for fs={filespace!r}, hl={hl!r}, ll={ll!r}")

    results:  List[Dict[str, Any]] = []
    resp      = qryRespBackupData()
    resp_size = sizeof(qryRespBackupData)
    data_blk  = _make_data_blk(
        ctypes.cast(byref(resp), ctypes.c_char_p),
        resp_size,
        session_handle,
        object_key
    )

    try:
        while True:
            if max_keys and len(results) >= max_keys:
                _logger.debug(
                    "Backup query reached max_keys limit",
                    extra={
                        'event_type': 'c_api.query.backup.limit_reached',
                        'max_keys': max_keys,
                        'results_count': len(results),
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
                break

            memset(byref(resp), 0, resp_size)
            resp.stVersion     = qryRespBackupDataVersion
            data_blk.numBytes  = 0
            data_blk.bufferPtr = ctypes.cast(byref(resp), ctypes.c_char_p)

            _logger.debug(
                "Calling dsmGetNextQObj",
                extra={
                    'event_type': 'c_api.function.call',
                    'function': 'dsmGetNextQObj',
                    'query_type': 'qtBackup',
                    'results_count': len(results),
                    'session_handle': session_handle,
                    'object_key': object_key
                }
            )

            rc = lib.dsmGetNextQObj(handle, byref(data_blk))

            if rc in (DSM_RC_FINISHED, DSM_RC_ABORT_NO_MATCH):
                _logger.debug(
                    "Backup query finished",
                    extra={
                        'event_type': 'c_api.query.backup.finished',
                        'rc': rc,
                        'results_count': len(results),
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
                break
            if rc not in (DSM_RC_OK, DSM_RC_MORE_DATA):
                _logger.error(
                    "Backup query returned unexpected response code",
                    extra={
                        'event_type': 'c_api.query.backup.failed',
                        'rc': rc,
                        'results_count': len(results),
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
                check_rc(handle, rc, "dsmGetNextQObj")

            obj_id    = ObjID()
            obj_id.hi = resp.objId.hi
            obj_id.lo = resp.objId.lo

            hl_str    = decode_field(resp.objName.hl)
            ll_str    = decode_field(resp.objName.ll)
            full_path = hl_str.rstrip("/") + ll_str
            result = {
                "_objId":          obj_id,
                "_restoreOrder":   resp.restoreOrderExt,
                "_mediaClassRaw":  int(resp.mediaClass),
                "Key":             full_path.lstrip("/"),
                "Filespace":       decode_field(resp.objName.fs),
                "HighLevel":       hl_str,
                "LowLevel":        ll_str,
                "Size":            size64(resp.sizeEstimate),
                "LastModified":    dsm_date_to_datetime(resp.insDate),
                "ExpiryDate":      dsm_date_to_datetime(resp.expDate),
                "ObjectId":        f"{resp.objId.hi}-{resp.objId.lo}",
                "ObjectIdRaw":     {"hi": int(resp.objId.hi), "lo": int(resp.objId.lo)},
                "State":           "active" if resp.objState == DSM_ACTIVE else "inactive",
                "MediaClass":      _media_str(resp.mediaClass),
                "ManagementClass": decode_field(resp.mcName),
                "Owner":           decode_field(resp.owner),
                "Compressed":      bool(resp.compressType),
                "Deduplicated":    bool(resp.clientDeduplicated),
                "CopyGroup":       int(resp.copyGroup),
                "GroupLeaderObjId":    f"{int(resp.baseObjId.hi)}-{int(resp.baseObjId.lo)}",
                "GroupLeaderObjIdRaw": {
                    "hi": int(resp.baseObjId.hi),
                    "lo": int(resp.baseObjId.lo),
                },
                "IsGroupLeader":       bool(resp.isGroupLeader),
                "IsOpenGroup":         bool(resp.isOpenGroup),

            }
            results.append(result)
            _logger.debug(
                "Backup query entry received",
                extra={
                    'event_type': 'c_api.query.backup.entry',
                    'key': result["Key"],
                    'object_id': result["ObjectId"],
                    'state': result["State"],
                    'results_count': len(results),
                    'session_handle': session_handle,
                    'object_key': object_key
                }
            )
    finally:
        _logger.debug(
            "Calling dsmEndQuery",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmEndQuery',
                'query_type': 'qtBackup',
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        lib.dsmEndQuery(handle)
        _logger.debug(
            "Backup query cleanup completed",
            extra={
                'event_type': 'c_api.query.backup.cleanup_completed',
                'results_count': len(results),
                'session_handle': session_handle,
                'object_key': object_key
            }
        )

    return results

def execute_group_query(
    handle,
    filespace: str,
    leader_hi: int,
    leader_lo: int,
    owner:     str = "",
    obj_type:  int = DSM_OBJ_ANY_TYPE,
    session_handle: Optional[str] = None,
    object_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """ executing group query """
    _logger.debug(
        "Executing group query",
        extra={
            'event_type': 'c_api.query.group.started',
            'filespace': filespace,
            'leader_hi': leader_hi,
            'leader_lo': leader_lo,
            'owner': owner or None,
            'obj_type': obj_type,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    if leader_hi == 0 and leader_lo == 0:
        _logger.warning(
            "Group query received invalid leader ID",
            extra={
                'event_type': 'c_api.query.group.invalid_leader',
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        return []

    h = _unwrap(handle)

    all_objs = _run_backup_query(
        handle    = h,
        filespace = filespace,
        hl        = "/*",
        ll        = "/*",
        obj_state = DSM_ACTIVE,
        obj_type  = obj_type,
        owner     = owner,
        session_handle = session_handle,
        object_key = object_key,
    )


    leader = next(
        (o for o in all_objs
         if o["ObjectIdRaw"]["hi"] == leader_hi
         and o["ObjectIdRaw"]["lo"] == leader_lo),
        None,
    )


    if leader is None:
        _logger.info(
            "Group query found no leader object",
            extra={
                'event_type': 'c_api.query.group.no_leader',
                'leader_hi': leader_hi,
                'leader_lo': leader_lo,
                'results_count': 0,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        return []


    members = [
        o for o in all_objs
        if o["GroupLeaderObjIdRaw"]["hi"] == leader_hi
        and o["GroupLeaderObjIdRaw"]["lo"] == leader_lo
        and not (o["ObjectIdRaw"]["hi"] == leader_hi
                 and o["ObjectIdRaw"]["lo"] == leader_lo)
    ]

    result = [leader] + members
    _logger.debug(
        "Group query completed",
        extra={
            'event_type': 'c_api.query.group.completed',
            'leader_object_id': leader["ObjectId"],
            'member_count': len(members),
            'results_count': len(result),
            'session_handle': session_handle,
            'object_key': object_key
        }
    )
    return result





def execute_backup_query(
    handle,
    filespace: str,
    key:       str,
    obj_state: int = DSM_ACTIVE,
    obj_type: int = DSM_OBJ_FILE,
    pit_date:  Optional[datetime] = None,
    owner: str = "",
    session_handle: Optional[str] = None,
    object_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query backed-up objects by filespace and key.

    This is a convenience wrapper around _run_backup_query() that automatically
    parses the object key into high-level and low-level components.

    Parameters
    ----------
    handle : int or c_uint32
        The session handle from dsmInitEx().
    filespace : str
        The filespace name to query.
    key : str
        The object key to query. Supports wildcards (*).
    obj_state : int, optional
        Object state filter (default: DSM_ACTIVE).
    obj_type : int, optional
        Object type filter (default: DSM_OBJ_FILE).
    pit_date : datetime, optional
        Point-in-time date for historical queries.
    owner : str, optional
        Owner name filter (default: "").
    session_handle : str, optional
        Correlation ID for logging.
    object_key : str, optional
        Object identifier for logging context.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries representing matching objects.

    Notes
    -----
    - The key is automatically parsed into HL/LL components
    - Wildcards (*) are supported in both directory and filename portions

    Example
    -------
    >>> results = execute_backup_query(
    ...     handle=session_handle,
    ...     filespace="/myfs",
    ...     key="/backup/data/file.txt"
    ... )
    """
    _logger.debug(
        "Executing backup query for key",
        extra={
            'event_type': 'c_api.query.backup_key.started',
            'filespace': filespace,
            'key': key,
            'obj_state': obj_state,
            'obj_type': obj_type,
            'owner': owner or None,
            'pit_date': pit_date.isoformat() if pit_date else None,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    hl, ll = key_to_hl_ll(key)
    results = _run_backup_query(
        handle    = _unwrap(handle),
        filespace = filespace,
        hl        = hl,
        ll        = ll,
        obj_type = obj_type,
        obj_state = obj_state,
        pit_date  = pit_date,
        owner = owner,
        session_handle = session_handle,
        object_key = object_key,
    )
    _logger.debug(
        "Backup query for key completed",
        extra={
            'event_type': 'c_api.query.backup_key.completed',
            'filespace': filespace,
            'key': key,
            'results_count': len(results),
            'session_handle': session_handle,
            'object_key': object_key
        }
    )
    return results


class QueryOperation:
    """
    Static utility class for IBM Storage Protect query operations.

    This class provides high-level query methods that wrap the Client API
    query functions. All methods are static and do not require instantiation.

    Supported Operations:
    ---------------------
    - list_objects(): List objects with prefix filtering and pagination
    - query_filespaces(): Query filespace information and statistics
    - query_object(): Query a single object by exact key
    - query_mgmt_classes(): Query management class definitions

    Example Usage:
    --------------
    >>> result = QueryOperation.list_objects(
    ...     handle=session_handle,
    ...     filespace="/myfs",
    ...     prefix="/backup",
    ...     max_keys=100
    ... )
    """

    @staticmethod
    def list_objects(
        handle,
        filespace: str,
        prefix:    str = "",
        max_keys:  int = 1000,
        obj_state: int = DSM_ACTIVE,
        obj_type: int = DSM_OBJ_FILE,
        pit_date:  Optional[datetime] = None,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List objects in a filespace with optional prefix filtering.

        This method provides S3-like list_objects functionality for IBM Storage
        Protect, allowing efficient browsing of backed-up objects with prefix
        filtering and pagination support.

        Parameters
        ----------
        handle : int or c_uint32
            The session handle from dsmInitEx().
        filespace : str
            The filespace name to list objects from.
        prefix : str, optional
            Object key prefix filter (default: "" = all objects).
        max_keys : int, optional
            Maximum number of objects to return (default: 1000).
        obj_state : int, optional
            Object state filter (default: DSM_ACTIVE).
        obj_type : int, optional
            Object type filter (default: DSM_OBJ_FILE).
        pit_date : datetime, optional
            Point-in-time date for historical listing.
        session_handle : str, optional
            Correlation ID for logging.
        object_key : str, optional
            Object identifier for logging context.

        Returns
        -------
        Dict[str, Any]
            A dictionary with keys: Name, Prefix, Contents, KeyCount, MaxKeys.

        Example
        -------
        >>> result = QueryOperation.list_objects(
        ...     handle=session_handle,
        ...     filespace="/myfs",
        ...     prefix="/backup/2024",
        ...     max_keys=100
        ... )
        """
        _logger.info(
            "Listing objects from filespace",
            extra={
                'event_type': 'c_api.query.list_objects.started',
                'filespace': filespace,
                'prefix': prefix,
                'max_keys': max_keys,
                'obj_state': obj_state,
                'obj_type': obj_type,
                'pit_date': pit_date.isoformat() if pit_date else None,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        hl, ll = prefix_to_hl_ll(prefix)

        raw = _run_backup_query(
            handle    = _unwrap(handle),
            filespace = filespace,
            hl        = hl,
            ll        = ll,
            obj_state = obj_state,
            obj_type= obj_type,
            max_keys  = max_keys,
            pit_date  = pit_date,
            session_handle = session_handle,
            object_key = object_key,
        )

        normalized_prefix = prefix.lstrip("/")
        contents: List[Dict[str, Any]] = []

        for entry in raw:
            if normalized_prefix and not entry["Key"].startswith(normalized_prefix):
                continue
            contents.append(
                {k: v for k, v in entry.items() if k not in _RESTORE_INTERNAL_KEYS}
            )

        result = {
            "Name":     filespace,
            "Prefix":   prefix,
            "Contents": contents,
            "KeyCount": len(contents),
            "MaxKeys":  max_keys,
        }
        _logger.info(
            "Object listing completed",
            extra={
                'event_type': 'c_api.query.list_objects.completed',
                'filespace': filespace,
                'prefix': prefix,
                'key_count': len(contents),
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        return result

    @staticmethod
    def query_filespaces(
        handle,
        fs_pattern: str = "*",
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query filespace information and statistics.

        Retrieves a list of filespaces accessible to the current session,
        including capacity, occupancy, and backup history information.

        Parameters
        ----------
        handle : int or c_uint32
            The session handle from dsmInitEx().
        fs_pattern : str, optional
            Filespace name pattern with wildcard support (default: "*").
        session_handle : str, optional
            Correlation ID for logging.
        object_key : str, optional
            Object identifier for logging context.

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries, each representing a filespace with metadata.

        Example
        -------
        >>> filespaces = QueryOperation.query_filespaces(
        ...     handle=session_handle
        ... )
        """
        _logger.info(
            "Querying filespaces",
            extra={
                'event_type': 'c_api.query.filespaces.started',
                'fs_pattern': fs_pattern,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        h = _unwrap(handle)

        qry = init_struct(qryFSData, qryFSDataVersion)
        qry.fsName    = fs_pattern.encode("utf-8")

        _logger.debug(
            "Calling dsmBeginQuery",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginQuery',
                'query_type': 'qtFilespace',
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        rc = lib.dsmBeginQuery(h, qtFilespace, byref(qry))
        check_rc(h, rc, "dsmBeginQuery(qtFilespace)")

        results:  List[Dict[str, Any]] = []
        resp      = qryRespFSData()
        resp_size = sizeof(qryRespFSData)
        data_blk  = _make_data_blk(
            ctypes.cast(byref(resp), ctypes.c_char_p),
            resp_size,
        )

        try:
            while True:
                memset(byref(resp), 0, resp_size)
                resp.stVersion     = qryRespFSDataVersion
                data_blk.numBytes  = 0
                data_blk.bufferPtr = ctypes.cast(byref(resp), ctypes.c_char_p)

                _logger.debug(
                    "Calling dsmGetNextQObj",
                    extra={
                        'event_type': 'c_api.function.call',
                        'function': 'dsmGetNextQObj',
                        'query_type': 'qtFilespace',
                        'results_count': len(results),
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
                rc = lib.dsmGetNextQObj(h, byref(data_blk))

                if rc in (DSM_RC_FINISHED, DSM_RC_ABORT_NO_MATCH):
                    _logger.debug(
                        "Filespace query finished",
                        extra={
                            'event_type': 'c_api.query.filespaces.finished',
                            'rc': rc,
                            'results_count': len(results),
                            'session_handle': session_handle,
                            'object_key': object_key
                        }
                    )
                    break
                if rc not in (DSM_RC_OK, DSM_RC_MORE_DATA):
                    _logger.error(
                        "Filespace query returned unexpected response code",
                        extra={
                            'event_type': 'c_api.query.filespaces.failed',
                            'rc': rc,
                            'results_count': len(results),
                            'session_handle': session_handle,
                            'object_key': object_key
                        }
                    )
                    check_rc(h, rc, "dsmGetNextQObj(qtFilespace)")

                entry = {
                    "Name":                 decode_field(resp.fsName),
                    "Type":                 decode_field(resp.fsType),
                    "Occupancy":            size64(resp.occupancy),
                    "Capacity":             size64(resp.capacity),
                    "BackupStartDate":      dsm_date_to_datetime(resp.backStartDate),
                    "BackupCompleteDate":   dsm_date_to_datetime(resp.backCompleteDate),
                    "LastBackupFromServer": dsm_date_to_datetime(resp.lastBackOpDateFromServer),
                    "LastBackupFromLocal":  dsm_date_to_datetime(resp.lastBackOpDateFromLocal),
                }
                results.append(entry)
                _logger.debug(
                    "Filespace query entry received",
                    extra={
                        'event_type': 'c_api.query.filespaces.entry',
                        'filespace': entry["Name"],
                        'results_count': len(results),
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
        finally:
            _logger.debug(
                "Calling dsmEndQuery",
                extra={
                    'event_type': 'c_api.function.call',
                    'function': 'dsmEndQuery',
                    'query_type': 'qtFilespace',
                    'session_handle': session_handle,
                    'object_key': object_key
                }
            )
            lib.dsmEndQuery(h)

        _logger.info(
            "Filespace query completed",
            extra={
                'event_type': 'c_api.query.filespaces.completed',
                'fs_pattern': fs_pattern,
                'results_count': len(results),
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        return results

    @staticmethod
    def query_object(
        handle,
        filespace: str,
        key:       str,
        obj_state: int = DSM_ACTIVE,
        obj_type: int = DSM_OBJ_FILE,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Query a single object by exact key.

        Retrieves metadata for a specific backed-up object identified by its
        exact key path. Returns None if the object is not found.

        Parameters
        ----------
        handle : int or c_uint32
            The session handle from dsmInitEx().
        filespace : str
            The filespace name containing the object.
        key : str
            The exact object key path.
        obj_state : int, optional
            Object state filter (default: DSM_ACTIVE).
        obj_type : int, optional
            Object type filter (default: DSM_OBJ_FILE).
        session_handle : str, optional
            Correlation ID for logging.
        object_key : str, optional
            Object identifier for logging context.

        Returns
        -------
        Optional[Dict[str, Any]]
            A dictionary with object metadata, or None if not found.

        Example
        -------
        >>> obj = QueryOperation.query_object(
        ...     handle=session_handle,
        ...     filespace="/myfs",
        ...     key="/data/file.txt"
        ... )
        >>> if obj:
        ...     print(f"Size: {obj['Size']} bytes")
        """
        _logger.info(
            "Querying single object",
            extra={
                'event_type': 'c_api.query.object.started',
                'filespace': filespace,
                'key': key,
                'obj_state': obj_state,
                'obj_type': obj_type,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        raw        = execute_backup_query(
            handle    = handle,
            filespace = filespace,
            key       = key,
            obj_state = obj_state,
            obj_type=obj_type,
            session_handle = session_handle,
            object_key = object_key,
        )
        normalized = key.lstrip("/")
        for entry in raw:
            if entry["Key"].lstrip("/") == normalized:
                result = {k: v for k, v in entry.items() if k not in _RESTORE_INTERNAL_KEYS}
                _logger.info(
                    "Single object query completed",
                    extra={
                        'event_type': 'c_api.query.object.completed',
                        'filespace': filespace,
                        'key': key,
                        'found': True,
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
                return result
        _logger.info(
            "Single object query completed",
            extra={
                'event_type': 'c_api.query.object.completed',
                'filespace': filespace,
                'key': key,
                'found': False,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        return None

    @staticmethod
    def query_mgmt_classes(
        handle,
        mc_name: str = "",
        detail: bool = True,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None,
    ):
        """
        Query management class definitions and policies.

        Retrieves management class information from the IBM Storage Protect server,
        including backup and archive copy group settings.

        Parameters
        ----------
        handle : int or c_uint32
            The session handle from dsmInitEx().
        mc_name : str, optional
            Management class name pattern (default: "" = all classes).
        detail : bool, optional
            Include detailed copy group information (default: True).
        session_handle : str, optional
            Correlation ID for logging.
        object_key : str, optional
            Object identifier for logging context.

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries, each representing a management class.

        Notes
        -----
        - When detail=True, includes BackupCG and ArchiveCG dictionaries
        - When detail=False, only includes Name and Description

        Example
        -------
        >>> classes = QueryOperation.query_mgmt_classes(
        ...     handle=session_handle,
        ...     detail=True
        ... )
        >>> for mc in classes:
        ...     print(f"{mc['Name']}: {mc['Description']}")
        ...     if 'BackupCG' in mc:
        ...         print(f"  Backup: {mc['BackupCG']['Name']}")
        """
        _logger.info(
            "Querying management classes",
            extra={
                'event_type': 'c_api.query.mgmt_classes.started',
                'management_class': mc_name or None,
                'detail': detail,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        h = _unwrap(handle)

        qry = init_struct(qryMCData, qryMCDataVersion)
        qry.mcName    = mc_name.encode("utf-8") if mc_name else None
        qry.mcDetail  = bTrue if detail else bFalse

        _logger.debug(
            "Calling dsmBeginQuery",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginQuery',
                'query_type': 'qtMC',
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        rc = lib.dsmBeginQuery(h, qtMC, byref(qry))
        check_rc(h, rc, "dsmBeginQuery(qtMC)")

        results = []
        if detail:
            resp      = qryRespMCDetailData()
            resp_size = sizeof(qryRespMCDetailData)
            resp_ver  = qryRespMCDetailDataVersion
        else:
            resp      = qryRespMCData()
            resp_size = sizeof(qryRespMCData)
            resp_ver  = qryRespMCDataVersion

        data_blk = _make_data_blk(ctypes.cast(byref(resp), ctypes.c_char_p), resp_size)

        try:
            while True:
                memset(byref(resp), 0, resp_size)
                resp.stVersion       = resp_ver
                data_blk.numBytes    = 0
                data_blk.bufferPtr   = ctypes.cast(byref(resp), ctypes.c_char_p)

                _logger.debug(
                    "Calling dsmGetNextQObj",
                    extra={
                        'event_type': 'c_api.function.call',
                        'function': 'dsmGetNextQObj',
                        'query_type': 'qtMC',
                        'results_count': len(results),
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
                rc = lib.dsmGetNextQObj(h, byref(data_blk))
                if rc in (DSM_RC_FINISHED, DSM_RC_ABORT_NO_MATCH):
                    _logger.debug(
                        "Management class query finished",
                        extra={
                            'event_type': 'c_api.query.mgmt_classes.finished',
                            'rc': rc,
                            'results_count': len(results),
                            'session_handle': session_handle,
                            'object_key': object_key
                        }
                    )
                    break
                if rc not in (DSM_RC_OK, DSM_RC_MORE_DATA):
                    _logger.error(
                        "Management class query returned unexpected response code",
                        extra={
                            'event_type': 'c_api.query.mgmt_classes.failed',
                            'rc': rc,
                            'results_count': len(results),
                            'session_handle': session_handle,
                            'object_key': object_key
                        }
                    )
                    check_rc(h, rc, "dsmGetNextQObj(qtMC)")

                entry: Dict[str, Any] = {
                    "Name":        decode_field(resp.mcName),
                    "Description": decode_field(resp.mcDesc),
                }
                if detail:
                    b = resp.backupDet
                    a = resp.archDet
                    backup_cg: Dict[str, Any] = {
                        "Name":        decode_field(b.cgName),
                        "Frequency":   int(b.frequency),
                        "VerExist":    int(b.verDataExst),
                        "VerDeleted":  int(b.verDataDltd),
                        "RetExtra":    int(b.retXtraVers),
                        "RetOnly":     int(b.retOnlyVers),
                        "Destination": decode_field(b.destName),
                        "LanFree":     bool(b.bLanFreeDest),
                        "Dedup":       bool(b.bDeduplicate),
                    }
                    archive_cg: Dict[str, Any] = {
                        "Name":        decode_field(a.cgName),
                        "Destination": decode_field(a.destName),
                        "RetainVers":  int(a.retainVers),
                        "LanFree":     bool(a.bLanFreeDest),
                    }
                    entry["BackupCG"] = backup_cg
                    entry["ArchiveCG"] = archive_cg
                results.append(entry)
                _logger.debug(
                    "Management class query entry received",
                    extra={
                        'event_type': 'c_api.query.mgmt_classes.entry',
                        'management_class': entry["Name"],
                        'results_count': len(results),
                        'session_handle': session_handle,
                        'object_key': object_key
                    }
                )
        finally:
            _logger.debug(
                "Calling dsmEndQuery",
                extra={
                    'event_type': 'c_api.function.call',
                    'function': 'dsmEndQuery',
                    'query_type': 'qtMC',
                    'session_handle': session_handle,
                    'object_key': object_key
                }
            )
            lib.dsmEndQuery(h)

        _logger.info(
            "Management class query completed",
            extra={
                'event_type': 'c_api.query.mgmt_classes.completed',
                'management_class': mc_name or None,
                'detail': detail,
                'results_count': len(results),
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        return results
