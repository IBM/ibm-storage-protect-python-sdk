"""
IBM Storage Protect Client API - Batch Restore Operations

This module provides Python wrappers for IBM Storage Protect batch restore operations,
enabling efficient retrieval of multiple backed-up objects using the IBM Storage Protect
Client API.

Key Responsibilities:
---------------------
1. **Batch Restore**: Efficiently restore multiple objects with different specifications
2. **Query Integration**: Automatically query for all objects before restore
3. **Batch Optimization**: Group object parts for optimal retrieval
4. **Data Collection**: Collect and organize data for all objects
5. **Result Ordering**: Return results in original specification order

Batch Restore Workflow:
-----------------------
1. **Query Phase**: Query for all specified objects to get object IDs
2. **Validation**: Verify all objects exist and check part count limits
3. **Sort Parts**: Sort all parts globally by restore order for efficiency
4. **Batch Processing**: Process parts in batches of MAX_BATCH (255)
5. **Data Collection**: Collect data for all parts
6. **Result Assembly**: Assemble results in original specification order

Thread Safety:
--------------
Batch operations are NOT thread-safe when using the same session handle.
Each thread should maintain its own session handle for concurrent operations.

Performance Considerations:
---------------------------
- Use batch restore for multiple objects to reduce API overhead
- Objects are queried and restored in optimized order
- Chunk size affects memory usage and network efficiency
- Partial restores supported per object specification

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
    # Batch restore
    batch_op = BatchRestoreOperation(
        handle=session_handle,
        specs=[
            {"Key": "/file1.txt"},
            {"Key": "/file2.txt", "Offset": 1024, "Length": 4096}
        ],
        default_filespace="/myfs"
    )
    results = batch_op.execute()
    for result in results:
        data = b"".join(result["Body"])
"""

from __future__ import annotations

# pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments,too-many-instance-attributes,too-many-locals,broad-exception-caught,line-too-long


import ctypes
from ctypes import byref
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional
)

from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_ACTIVE,           # Object state: Active (current version)
    DSM_MAX_GET_OBJ,      # Maximum objects per restore operation (255)
    DSM_OBJ_FILE,         # Object type: File
    ObjID,                # Structure for object identifier (hi/lo pair)
    bFalse,               # Boolean false constant for C API
    bTrue,                # Boolean true constant for C API
    gtBackup,             # Get type: Backup (vs. archive)
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.errors import (
    SDKErrorCode,
    TSMObjectError,
    TSMOperationError
    )
from ibm_storage_protect.c_api_bridge.wrappers.helper import check_rc
from ibm_storage_protect.c_api_bridge.wrappers.query import execute_backup_query
from ibm_storage_protect.logger import get_logger
from .single import _build_get_list, _stream_one_obj, _end_get_data_ex, DEFAULT_CHUNK_SIZE

# Module-level logger for structured logging
_logger = get_logger(__name__)


class BatchRestoreOperation:
    """
    Batch restore operation handler for multiple objects.

    Efficiently restores multiple objects by querying for all objects,
    optimizing retrieval order, and batching API calls. Returns results
    in the original specification order.

    This class handles the complete workflow for restoring multiple objects:
    querying for all objects, validating existence, sorting parts for optimal
    retrieval, batching API calls, collecting data, and assembling results.

    Attributes
    ----------
    MAX_BATCH : int
        Maximum objects per batch (255, enforced by Client API).
    handle : int
        Session handle from dsmInitEx().
    specs : List[Dict[str, Any]]
        List of object specifications to restore.
    default_filespace : str
        Default filespace for specs without explicit filespace.
    default_obj_state : int
        Default object state filter (default: DSM_ACTIVE).
    default_obj_type : int
        Default object type filter (default: DSM_OBJ_FILE).
    default_pit_date : datetime, optional
        Default point-in-time date.
    default_mount_wait : bool
        Default tape mount wait behavior (default: True).
    session_handle : str, optional
        Correlation ID for logging.
    object_key : str, optional
        Object identifier for logging.
    chunk_size : int
        Size of data chunks for streaming.

    Notes
    -----
    - Results are returned in the same order as specs
    - Each result's Body is a generator that yields data chunks
    - All object parts are collected before returning
    - Empty specs list returns empty results list
    - Maximum 255 parts per object (DSM_MAX_GET_OBJ limit)

    Example
    -------
    >>> batch_op = BatchRestoreOperation(
    ...     handle=session_handle,
    ...     specs=[
    ...         {"Key": "/file1.txt"},
    ...         {"Key": "/file2.txt", "Offset": 1024, "Length": 4096}
    ...     ],
    ...     default_filespace="/myfs"
    ... )
    >>> results = batch_op.execute()
    >>> for i, result in enumerate(results):
    ...     print(f"Object {i}: {result['Key']}")
    ...     data = b"".join(result["Body"])
    """

    # Maximum objects per batch (enforced by IBM Storage Protect Client API)
    MAX_BATCH = DSM_MAX_GET_OBJ  # 255

    def __init__(
        self,
        handle:             int,
        specs:              List[Dict[str, Any]],
        default_filespace:  str,
        default_obj_state:  int                = DSM_ACTIVE,
        default_obj_type:   int                = DSM_OBJ_FILE,
        default_pit_date:   Optional[datetime] = None,
        default_mount_wait: bool               = True,
        session_handle:     Optional[str]      = None,
        object_key:         Optional[str]      = None,
    ):
        """
        Initialize a BatchRestoreOperation instance.

        Parameters
        ----------
        handle : int
            Session handle from dsmInitEx()
        specs : List[Dict[str, Any]]
            List of object specifications to restore
        default_filespace : str
            Default filespace for specs without explicit filespace
        default_obj_state : int, optional
            Default object state filter (default: DSM_ACTIVE)
        default_obj_type : int, optional
            Default object type filter (default: DSM_OBJ_FILE)
        default_pit_date : datetime, optional
            Default point-in-time date
        default_mount_wait : bool, optional
            Default tape mount wait behavior (default: True)
        session_handle : str, optional
            Correlation ID for logging
        object_key : str, optional
            Object identifier for logging
        """
        self.handle             = handle
        self.specs              = specs
        self.default_filespace  = default_filespace
        self.default_obj_state  = default_obj_state
        self.default_obj_type   = default_obj_type
        self.default_pit_date   = default_pit_date
        self.default_mount_wait = default_mount_wait
        self.session_handle     = session_handle
        self.object_key         = object_key
        self.chunk_size         = DEFAULT_CHUNK_SIZE

    def execute(self) -> List[Dict[str, Any]]:
        """
        Execute batch restore operation and return all object data.

        Queries for all specified objects, batches them efficiently, restores
        the data, and returns results in the original specification order.

        Returns
        -------
        List[Dict[str, Any]]
            List of result dictionaries, one per specification, each containing:
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
            If any specified object is not found.
        TSMOperationError
            If any object has too many parts (> MAX_BATCH).
        RestoreError
            If any Client API operation fails.

        Notes
        -----
        - Results are returned in the same order as specs
        - Each result's Body is a generator that must be consumed
        - All object parts are collected before returning
        - Empty specs list returns empty results list

        Example
        -------
        >>> results = batch_op.execute()
        >>> for i, result in enumerate(results):
        ...     print(f"Object {i}: {result['Key']}")
        ...     data = b"".join(result["Body"])
        ...     print(f"Size: {len(data)} bytes")
        """
        # Handle empty specs
        if not self.specs:
            return []

        _logger.info(
            "Executing batch restore operation",
            extra={
                'event_type': 'c_api.restore.batch.execute.started',
                'spec_count': len(self.specs),
                'default_filespace': self.default_filespace,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Lists to track object parts and metadata
        flat_entries: List[tuple]          = []  # (spec_idx, part_idx, entry)
        spec_metas:   List[Dict[str, Any]] = []  # Metadata per spec

        # Query for each object specification
        for spec_idx, spec in enumerate(self.specs):
            # Extract parameters with defaults
            fs        = spec.get("Filespace") or self.default_filespace
            key       = spec["Key"]
            obj_state = spec.get("ObjState", self.default_obj_state)
            obj_type  = spec.get("ObjType",  self.default_obj_type)
            pit_date  = spec.get("PitDate",  self.default_pit_date)
            owner     = spec.get("Owner",    "")

            # Query for this object
            entries = execute_backup_query(
                handle    = self.handle,
                filespace = fs,
                key       = key,
                obj_state = obj_state,
                obj_type  = obj_type,
                pit_date  = pit_date,
                owner     = owner,
                session_handle = self.session_handle,
                object_key = self.object_key,
            )

            # Verify object exists
            if not entries:
                raise TSMObjectError(
                    error_code=SDKErrorCode.OBJECT_NOT_FOUND,
                    message=f"Object not found: filespace={fs!r} key={key!r}"
                )

            # Check part count limit
            if len(entries) > self.MAX_BATCH:
                raise TSMOperationError(
                    error_code=SDKErrorCode.OPERATION_FAILED,
                    message=f"Object '{key}' has {len(entries)} parts, exceeds C API limit of {self.MAX_BATCH}. Split into smaller batches."
                )

            # Sort parts by restore order
            entries.sort(key=lambda e: (
                e["_restoreOrder"].top,
                e["_restoreOrder"].hi_hi,
                e["_restoreOrder"].hi_lo,
                e["_restoreOrder"].lo_hi,
                e["_restoreOrder"].lo_lo,
            ))

            # Store metadata for this specification
            spec_metas.append({
                "key":        key.lstrip("/"),
                "fs":         fs,
                "meta":       entries[0],  # Metadata from first part
                "mount_wait": spec.get("MountWait", self.default_mount_wait),
                "offset":     spec.get("Offset",    0),
                "length":     spec.get("Length",    0),
            })

            # Add all parts to flat list with tracking indices
            for part_idx, entry in enumerate(entries):
                flat_entries.append((spec_idx, part_idx, entry))

        # Sort all parts globally by restore order for optimal retrieval
        flat_entries.sort(key=lambda x: (
            x[2]["_restoreOrder"].top,
            x[2]["_restoreOrder"].hi_hi,
            x[2]["_restoreOrder"].hi_lo,
            x[2]["_restoreOrder"].lo_hi,
            x[2]["_restoreOrder"].lo_lo,
        ))

        # Initialize storage for collected data
        # Structure: collected_data[spec_idx][part_idx] = List[bytes]
        collected_data: Dict[int, Dict[int, List[bytes]]] = {
            i: {} for i in range(len(self.specs))
        }

        # Process entries in batches of MAX_BATCH
        for i in range(0, len(flat_entries), self.MAX_BATCH):
            self._retrieve_batch(
                flat_entries[i : i + self.MAX_BATCH],
                collected_data,
                spec_metas,
            )

        # Assemble final results in original specification order
        results: List[Dict[str, Any]] = []
        for spec_idx, sm in enumerate(spec_metas):
            parts = collected_data[spec_idx]
            meta  = sm["meta"]

            # Create result with generator that yields chunks in part order
            results.append({
                "Key":             sm["key"],
                "Filespace":       sm["fs"],
                # Generator that yields chunks from all parts in order
                "Body": (
                    chunk
                    for part_chunks in [parts[i] for i in sorted(parts)]
                    for chunk in part_chunks
                ),
                "LastModified":    meta.get("LastModified"),
                "ObjectId":        meta.get("ObjectId", ""),
                "MediaClass":      meta.get("MediaClass", ""),
                "ManagementClass": meta.get("ManagementClass", ""),
            })

        _logger.info(
            "Batch restore operation completed",
            extra={
                'event_type': 'c_api.restore.batch.execute.completed',
                'spec_count': len(self.specs),
                'total_parts': len(flat_entries),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        return results

    def _retrieve_batch(
        self,
        batch:          List[tuple],
        collected_data: Dict[int, Dict[int, List[bytes]]],
        spec_metas:     List[Dict[str, Any]],
    ) -> None:
        """
        Retrieve a batch of object parts from the server.

        Internal method that handles restoration of a single batch (up to
        MAX_BATCH object parts). Calls dsmBeginGetData(), streams all parts,
        and stores the data in collected_data.

        Parameters
        ----------
        batch : List[tuple]
            List of (spec_idx, part_idx, entry) tuples to restore.
        collected_data : Dict[int, Dict[int, List[bytes]]]
            Storage for collected data, indexed by spec and part.
        spec_metas : List[Dict[str, Any]]
            Metadata for each specification (mount_wait, offset, length).

        Notes
        -----
        - Builds object array from batch entries
        - Determines if any object needs partial restore
        - Collects all chunks into lists (not generators)
        - Ensures dsmEndGetDataEx() is called even on error
        """
        # Build array of object IDs for this batch
        n        = len(batch)
        ObjArray = ObjID * n
        obj_arr  = ObjArray()
        for i, (_, _, entry) in enumerate(batch):
            obj_arr[i].hi = entry["_objId"].hi
            obj_arr[i].lo = entry["_objId"].lo

        # Check if any object in batch needs partial restore
        has_partial = any(
            spec_metas[si].get("offset", 0) > 0 or spec_metas[si].get("length", 0) > 0
            for si, _, _ in batch
        )

        # Check if any object needs tape mount wait
        mount_wait = any(spec_metas[si].get("mount_wait", True) for si, _, _ in batch)

        # Build get list with partial restore info if needed
        get_list, _anchor = _build_get_list(
            obj_arr,
            n,
            has_partial,
            offsets = [spec_metas[si].get("offset", 0) for si, _, _ in batch],
            lengths = [spec_metas[si].get("length", 0) for si, _, _ in batch],
        )

        _logger.debug(
            "Calling dsmBeginGetData for batch",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBeginGetData',
                'batch_size': n,
                'mount_wait': mount_wait,
                'has_partial': has_partial,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        rc = lib.dsmBeginGetData(
            self.handle,
            bTrue if mount_wait else bFalse,
            gtBackup,
            byref(get_list),
        )
        check_rc(self.handle, rc, "dsmBeginGetData")

        # Allocate buffer for streaming data chunks
        chunk_buf     = ctypes.create_string_buffer(self.chunk_size)
        pending_error = None

        try:
            # Stream and collect data for each object part in batch
            for si, pi, entry in batch:
                # Collect all chunks for this part (must materialize while buffer is valid)
                collected_data[si][pi] = list(
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
