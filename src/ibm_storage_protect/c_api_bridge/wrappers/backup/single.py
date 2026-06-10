"""
IBM Storage Protect Client API - Single Object Backup Operations

This module provides Python wrappers for IBM Storage Protect single object backup
operations, enabling data protection through individual object backups using the
IBM Storage Protect Client API.

Key Responsibilities:
---------------------
1. **Single Object Backup**: Back up individual objects with full control
2. **Transaction Management**: Handle backup transactions with commit/abort
3. **Management Class Binding**: Associate objects with storage policies
4. **Data Streaming**: Stream object data in chunks to the server
5. **Statistics Collection**: Collect and report backup statistics

Backup Workflow:
----------------
1. **Bind Management Class**: Associate object with storage policy via dsmBindMC()
2. **Begin Transaction**: Start backup transaction via dsmBeginTxn()
3. **Send Object Header**: Transmit metadata via dsmSendObj()
4. **Send Data**: Stream object data via dsmSendData()
5. **End Object**: Finalize object send via dsmEndSendObjEx()
6. **Commit Transaction**: Complete backup via dsmEndTxnEx()
7. **Error Handling**: Abort on failure and map errors to SDK exceptions

Thread Safety:
--------------
Backup operations are NOT thread-safe when using the same session handle.
Each thread should maintain its own session handle for concurrent backups.

Performance Considerations:
---------------------------
- Stream large files in chunks (4MB maximum per chunk)
- Enable compression for compressible data (set pre_compressed=False)
- Enable deduplication for redundant data (set disable_dedup=False)
- Use appropriate size estimates for optimal buffer allocation

Client API Integration:
-----------------------
This module wraps the following Client API functions:
- dsmBindMC() - Bind object to management class
- dsmBeginTxn() - Begin backup transaction
- dsmSendObj() - Send object metadata
- dsmSendData() - Send object data chunks
- dsmEndSendObjEx() - End object send and get statistics
- dsmEndTxnEx() - End transaction (commit or abort)

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Backup Operations", "Transaction Management"

Example Usage:
--------------
    # Single object backup
    backup_op = BackupOperation(
        session=session,
        filespace="/myfs",
        high_level="/data",
        low_level="/file.txt",
        data_source=file_data,
        size_estimate=1024000
    )
    result = backup_op.execute()
"""
# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals,attribute-defined-outside-init

import io
from ctypes import (
    byref,
    c_char_p,
    cast,
    create_string_buffer,
    memmove,
)
from typing import Generator, Optional, Union

from ibm_storage_protect.c_api_bridge.c_api.platform_types import dsBool_t
from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_MAX_EXT_OBJINFO_LENGTH,
    DSM_MAX_OBJINFO_LENGTH,
    DSM_OBJ_FILE,
    DSM_VOTE_ABORT,
    DSM_VOTE_COMMIT,
    DataBlk,
    DataBlkVersion,
    ObjAttr,
    ObjAttrVersion,
    bFalse,
    bTrue,
    dsmEndSendObjExIn_t,
    dsmEndSendObjExInVersion,
    dsmEndSendObjExOut_t,
    dsmEndSendObjExOutVersion,
    dsmEndTxnExIn_t,
    dsmEndTxnExInVersion,
    dsmEndTxnExOut_t,
    dsmEndTxnExOutVersion,
    dsmObjName,
    mcBindKey,
    mcBindKeyVersion,
    stBackup,
    stBackupMountWait,
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.errors import (
    SDKErrorCode,
    TSMDataError,
    TSMConfigurationError,
    TSMTransactionError,

)
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    unwrap_handle as _unwrap,
    init_struct,
    check_rc
)
from ibm_storage_protect.logger import get_logger

_logger = get_logger(__name__)

class BackupOperation:
    """
    Single object backup operation handler.

    Manages the complete lifecycle of backing up a single object to IBM Storage
    Protect, including management class binding, transaction management, metadata
    transmission, data streaming, and statistics collection.

    This class encapsulates the IBM Storage Protect Client API backup workflow:
    1. Bind to management class (dsmBindMC)
    2. Begin transaction (dsmBeginTxn)
    3. Send object header (dsmSendObj)
    4. Send data chunks (dsmSendData)
    5. End object send (dsmEndSendObjEx)
    6. Commit transaction (dsmEndTxnEx)

    Attributes
    ----------
    MAX_CHUNK_SIZE : int
        Maximum size for data chunks (4MB). Enforced by Client API buffer limits.

    Notes
    -----
    - Data chunks must not exceed 4MB (MAX_CHUNK_SIZE)
    - Transactions are automatically aborted on errors
    - Statistics are collected during object finalization
    - Management class binding validates storage policy configuration

    Example
    -------
    >>> backup_op = BackupOperation(
    ...     session=session,
    ...     filespace="/myfs",
    ...     high_level="/backup",
    ...     low_level="/data.db",
    ...     data_source=file_generator(),
    ...     size_estimate=10485760,
    ...     management_class="STANDARD"
    ... )
    >>> result = backup_op.execute()
    >>> print(result['stats'])
    """

    # Maximum chunk size enforced by IBM Storage Protect Client API (4MB)
    MAX_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB

    def __init__(
        self,
        session,
        filespace: str,
        high_level: str,
        low_level: str,
        data_source: Union[bytes, io.BufferedIOBase, Generator[bytes, None, None]],
        obj_type: int = DSM_OBJ_FILE,
        owner: str = "",
        management_class: Optional[str] = None,
        size_estimate: int = 0,
        pre_compressed: bool = False,
        mount_wait: bool = True,
        obj_info: Optional[bytes] = None,
        disable_dedup: bool = False,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None,
    ):
        """
        Initialize a backup operation for a single object.

        Parameters
        ----------
        session : Session
            Active IBM Storage Protect session with valid handle.
        filespace : str
            Filespace name (must be registered with server).
        high_level : str
            High-level name component (directory path, e.g., "/data/logs").
        low_level : str
            Low-level name component (filename, e.g., "/app.log").
        data_source : Union[bytes, io.BufferedIOBase, Generator[bytes, None, None]]
            Data to back up. Can be:
            - bytes/bytearray: Direct data (must be ≤ 4MB)
            - Generator: Yields bytes chunks (each ≤ 4MB)
        obj_type : int, optional
            Object type constant (default: DSM_OBJ_FILE).
        owner : str, optional
            Object owner name (default: session owner or empty string).
        management_class : Optional[str], optional
            Management class name for storage policy (default: None uses default MC).
        size_estimate : int, optional
            Estimated object size in bytes (default: 0, uses 1024).
        pre_compressed : bool, optional
            Whether data is already compressed (default: False).
        mount_wait : bool, optional
            Whether to wait for tape mount if needed (default: True).
        obj_info : Optional[bytes], optional
            Application-specific metadata (default: None).
        disable_dedup : bool, optional
            Whether to disable server-side deduplication (default: False).
        session_handle : Optional[str], optional
            Session handle for logging/tracking (default: None).
        object_key : Optional[str], optional
            Object key for logging/tracking (default: None).
        """
        self.session = session
        self.filespace = filespace
        self.high_level = high_level
        self.low_level = low_level
        self.data_source = data_source
        self.obj_type = obj_type
        self.owner = owner
        self.management_class = management_class
        self.size_estimate = size_estimate
        self.pre_compressed = pre_compressed
        self.obj_info = obj_info
        self.disable_dedup = disable_dedup
        self.session_handle = session_handle
        self.object_key = object_key
        self._send_type = stBackupMountWait if mount_wait else stBackup
        handle = session._session.handle
        self._handle = _unwrap(handle)

        self._txn_active = False

        _logger.debug(
            "BackupOperation initialized",
            extra={
                'event_type': 'c_api.backup.init',
                'handle':self._handle,
                'filespace': filespace,
                'key':high_level+low_level,
                'obj_type': obj_type,
                'size_estimate': size_estimate,
                'pre_compressed': pre_compressed,
                'disable_dedup': disable_dedup,
                'mount_wait': mount_wait,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )

    def execute(self):
        ''' Execution function '''
        _logger.info(
            "Executing backup operation",
            extra={
                'event_type': 'c_api.backup.execute.started',
                'filespace': self.filespace,
                'high_level': self.high_level,
                'low_level': self.low_level,
                'obj_type': self.obj_type,
                'size_estimate': self.size_estimate,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        try:
            self._bind_management_class()
            self._begin_transaction()
            self._send_object_header()
            self._send_data()
            self._end_object()
            self._commit_transaction()

            stats = self.get_stats()
            _logger.info(
                "Backup operation completed",
                extra={
                    'event_type': 'c_api.backup.execute.completed',
                    'filespace': self.filespace,
                    'high_level': self.high_level,
                    'low_level': self.low_level,
                    'obj_type': self.obj_type,
                    'stats': stats,
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )

            return {
                "status": "success",
                "filespace": self.filespace,
                "high_level": self.high_level,
                "low_level": self.low_level,
                "stats": stats
            }
        except Exception as e:
            _logger.error(
                "Backup operation failed",
                extra={
                    'event_type': 'c_api.backup.execute.failed',
                    'filespace': self.filespace,
                    'high_level': self.high_level,
                    'low_level': self.low_level,
                    'obj_type': self.obj_type,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                },
                exc_info=True
            )
            # Abort transaction if active to maintain consistency
            if self._txn_active:
                self._abort_transaction()
            raise

    def _bind_management_class(self):
        """
        Bind the object to a management class and validate storage policy.

        Calls dsmBindMC() to associate the object with a management class, which
        determines the storage policy (retention, copy groups, destinations).
        Validates that the management class has a valid backup copy group and
        destination.

        Raises
        ------
        TSMConfigurationError
            If management class has no backup copy group or no backup destination.

        Notes
        -----
        - Uses default management class if none specified
        - Validates backup copy group existence
        - Validates backup copy destination configuration
        - Stores bound object name and MC key for later use

        Client API Reference
        --------------------
        dsmBindMC() - Bind object to management class
        mcBindKey structure - Contains binding results and validation info
        """
        _logger.debug(
            "Binding management class",
            extra={
                'event_type': 'c_api.backup.bind_mc.started',
                'filespace': self.filespace,
                'high_level': self.high_level,
                'low_level': self.low_level,
                'management_class': self.management_class or 'default',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Initialize object name structure with filespace and path components
        obj_name = init_struct(dsmObjName)
        obj_name.fs = self.filespace.encode('utf-8')
        obj_name.hl = self.high_level.encode('utf-8')
        obj_name.ll = self.low_level.encode('utf-8')
        obj_name.objType = self.obj_type

        _logger.debug(
            "Calling dsmBindMC",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmBindMC',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Call Client API to bind management class
        mc_bind_key = init_struct(mcBindKey, mcBindKeyVersion)
        rc = lib.dsmBindMC(self._handle, byref(obj_name), self._send_type, byref(mc_bind_key))

        check_rc(self._handle, rc, "dsmBindMC")

        # Validate that management class has a backup copy group
        if not mc_bind_key.backup_cg_exists:
            _logger.error(
                "No backup copy group in management class",
                extra={
                    'event_type': 'c_api.backup.bind_mc.failed',
                    'reason': 'backup_copy_group_missing',
                    'management_class': self.management_class or 'default',
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )

            raise TSMConfigurationError(
                error_code=SDKErrorCode.MANAGEMENT_CLASS_ERROR,
                message="No backup copy group in management class"
            )

        # Validate that backup copy group has a destination configured
        dest = bytes(mc_bind_key.backup_copy_dest).rstrip(b'\x00').decode('utf-8', errors='replace')
        if not dest.strip():
            _logger.error(
                "Management class has no backup copy destination",
                extra={
                    'event_type': 'c_api.backup.bind_mc.failed',
                    'reason': 'backup_copy_destination_missing',
                    'management_class': self.management_class or 'default',
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )

            raise TSMConfigurationError(
                error_code=SDKErrorCode.MANAGEMENT_CLASS_ERROR,
                message=f"Management class '{self.management_class or 'default'}' has no backup "
                        "copy destination. Contact your IBM SP administrator."
            )

        # Store bound object name and MC key for use in subsequent operations
        self._obj_name = obj_name
        self._mc_bind_key = mc_bind_key

        _logger.debug(
            "Management class bound successfully",
            extra={
                'event_type': 'c_api.backup.bind_mc.completed',
                'management_class': self.management_class or 'default',
                'destination': dest,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

    def _begin_transaction(self):
        """
        Begin a backup transaction to ensure atomic operation.

        Calls dsmBeginTxn() to start a transaction that groups all backup
        operations for this object. The transaction ensures that either all
        operations succeed (commit) or all are rolled back (abort).

        Transactions provide:
        - Atomicity: All-or-nothing backup
        - Consistency: Server state remains valid
        - Isolation: No interference from other operations

        Raises
        ------
        BackupError
            If transaction cannot be started.

        Notes
        -----
        - Sets _txn_active flag for cleanup tracking
        - Transaction must be committed or aborted before session end
        - Multiple objects can be sent within a single transaction (batch mode)

        Client API Reference
        --------------------
        dsmBeginTxn() - Begin transaction
        """
        _logger.debug(
            "Beginning backup transaction",
            extra={
                'event_type': 'c_api.backup.begin_txn',
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

        # Call Client API to begin transaction
        rc = lib.dsmBeginTxn(self._handle)
        check_rc(self._handle, rc, "dsmBeginTxn")

        # Mark transaction as active for cleanup tracking
        self._txn_active = True

        _logger.debug(
            "Backup transaction begun",
            extra={
                'event_type': 'c_api.backup.begin_txn.completed',
                'rc': rc,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

    def _send_object_header(self):
        """
        Send object metadata and attributes to the server.

        Calls dsmSendObj() to transmit object attributes including size estimate,
        compression status, deduplication settings, owner, management class, and
        optional application-specific metadata (objInfo).

        The header must be sent before any data chunks. It establishes the object's
        identity and storage characteristics on the server.

        Raises
        ------
        TSMConfigurationError
            If management class name is invalid (empty or too long).
        TSMDataError
            If objInfo exceeds maximum length (1024 bytes extended, 255 standard).
        BackupError
            If header transmission fails.

        Notes
        -----
        - Size estimate is used for buffer allocation (not enforced)
        - Extended objInfo (>255 bytes) requires useExtObjInfo flag
        - Owner field is limited to 64 bytes
        - Management class name is limited to 30 characters
        - Pre-compressed flag prevents server-side compression
        - Disable dedup flag forces full data transmission

        Client API Reference
        --------------------
        dsmSendObj() - Send object attributes
        ObjAttr structure - Contains object metadata
        """
        _logger.debug(
            "Sending object header",
            extra={
                'event_type': 'c_api.backup.send_header.started',
                'filespace': self.filespace,
                'high_level': self.high_level,
                'low_level': self.low_level,
                'size_estimate': self.size_estimate,
                'pre_compressed': self.pre_compressed,
                'disable_dedup': self.disable_dedup,
                'has_obj_info': self.obj_info is not None,
                'management_class': self.management_class,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Initialize object attributes structure
        obj_attr = init_struct(ObjAttr, ObjAttrVersion)

        # Set size estimate (use 1024 if not provided)
        size = self.size_estimate if self.size_estimate > 0 else 1024
        # Split 64-bit size into high and low 32-bit components
        obj_attr.sizeEstimate.hi = (size >> 32) & 0xFFFFFFFF
        obj_attr.sizeEstimate.lo = size & 0xFFFFFFFF

        # Set compression flag (skip server compression if already compressed)
        obj_attr.objCompressed = dsBool_t(bTrue if self.pre_compressed else bFalse)

        # Set deduplication flag (disable server dedup if requested)
        obj_attr.disableDeduplication = dsBool_t(bTrue if self.disable_dedup else bFalse)

        # Handle optional object information (application metadata)
        if self.obj_info is not None:
            # Ensure objInfo is bytes
            info_bytes = (
                self.obj_info if isinstance(self.obj_info, bytes)
                else self.obj_info.encode('utf-8')
            )

            # Validate objInfo length against maximum
            if len(info_bytes) > DSM_MAX_EXT_OBJINFO_LENGTH:
                _logger.error(
                    "Object info exceeds maximum supported length",
                    extra={
                        'event_type': 'c_api.backup.send_header.failed',
                        'reason': 'obj_info_too_long',
                        'obj_info_length': len(info_bytes),
                        'max_obj_info_length': DSM_MAX_EXT_OBJINFO_LENGTH,
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )

                raise TSMDataError(
                    error_code=SDKErrorCode.INVALID_DATA_FORMAT,
                    message=f"ObjInfo too long: max {DSM_MAX_EXT_OBJINFO_LENGTH} bytes"
                )

            # Use extended objInfo if exceeds standard limit
            if len(info_bytes) > DSM_MAX_OBJINFO_LENGTH:
                obj_attr.useExtObjInfo = dsBool_t(bTrue)
                _logger.debug(
                    "Using extended object info",
                    extra={
                        'event_type': 'c_api.backup.send_header.ext_obj_info_enabled',
                        'obj_info_length': len(info_bytes),
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )
            obj_attr.objInfo = info_bytes
            obj_attr.objInfoLength = len(info_bytes)

        # Handle optional management class override
        if self.management_class is not None:
            mc = self.management_class.strip()

            # Validate management class name is not empty
            if not mc:
                _logger.error(
                    "Management class cannot be empty",
                    extra={
                        'event_type': 'c_api.backup.send_header.failed',
                        'reason': 'management_class_empty',
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )

                raise TSMConfigurationError(
                    error_code=SDKErrorCode.INVALID_PARAMETER,
                    message="ManagementClass cannot be empty string"
                )

            # Validate management class name length
            if len(mc) > 30:
                _logger.error(
                    "Management class name too long",
                    extra={
                        'event_type': 'c_api.backup.send_header.failed',
                        'reason': 'management_class_too_long',
                        'management_class_length': len(mc),
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )

                raise TSMConfigurationError(
                    error_code=SDKErrorCode.INVALID_PARAMETER,
                    message="ManagementClass name too long: max 30 chars"
                )

            obj_attr.mcNameP = self.management_class.encode('utf-8')

        # Set owner field (limited to 64 bytes)
        owner_bytes = self.owner.encode('utf-8')[:64]
        if owner_bytes:
            memmove(obj_attr.owner, owner_bytes, len(owner_bytes))

        _logger.debug(
            "Calling dsmSendObj",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmSendObj',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

        # Call Client API to send object header
        rc = lib.dsmSendObj(
            self._handle,
            self._send_type,
            None,  # sendDataInfo (reserved, must be NULL)
            byref(self._obj_name),
            byref(obj_attr),
            None  # dataBlkPtr (NULL for header-only call)
        )

        check_rc(self._handle, rc, "dsmSendObj")
        _logger.debug(
            "Object header sent",
            extra={
                'event_type': 'c_api.backup.send_header.completed',
                'effective_size_estimate': size,
                'owner_present': bool(owner_bytes),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

    def _send_data(self):
        _logger.debug(
            "Sending backup data stream",
            extra={
                'event_type': 'c_api.backup.send_data.started',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        data_blk = DataBlk()
        data_blk.stVersion = DataBlkVersion
        chunk_count = 0
        total_bytes = 0

        for chunk in self.data_source:
            if not chunk:
                _logger.debug(
                    "Encountered empty chunk; ending data stream",
                    extra={
                        'event_type': 'c_api.backup.send_data.empty_chunk',
                        'chunks_sent': chunk_count,
                        'bytes_sent': total_bytes,
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )
                break

            if not isinstance(chunk, (bytes, bytearray)):
                _logger.warning(
                    "Skipping non-bytes chunk in backup data source",
                    extra={
                        'event_type': 'c_api.backup.send_data.invalid_chunk',
                        'chunk_type': type(chunk).__name__,
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )
                continue

            chunk_len = len(chunk)

            if chunk_len > self.MAX_CHUNK_SIZE:
                _logger.error(
                    "Chunk size exceeds maximum allowed size",
                    extra={
                        'event_type': 'c_api.backup.send_data.failed',
                        'reason': 'chunk_size_exceeded',
                        'chunk_size': chunk_len,
                        'max_chunk_size': self.MAX_CHUNK_SIZE,
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )

                raise TSMDataError(
                    error_code=SDKErrorCode.SIZE_LIMIT_EXCEEDED,
                    message=f"Chunk size {chunk_len} exceeds maximum {self.MAX_CHUNK_SIZE} (4MB)"
                )

            data_blk.bufferLen = chunk_len
            pinned = create_string_buffer(chunk, chunk_len)
            data_blk.bufferPtr = cast(pinned, c_char_p)
            data_blk.numBytes = 0

            _logger.debug(
                "Calling dsmSendData",
                extra={
                    'event_type': 'c_api.function.call',
                    'function': 'dsmSendData',
                    'chunk_index': chunk_count + 1,
                    'chunk_size': chunk_len,
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            rc = lib.dsmSendData(self._handle, byref(data_blk))

            check_rc(self._handle, rc, "dsmSendData")
            chunk_count += 1
            total_bytes += chunk_len

        _logger.debug(
            "Backup data stream sent",
            extra={
                'event_type': 'c_api.backup.send_data.completed',
                'chunks_sent': chunk_count,
                'bytes_sent': total_bytes,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

    def _end_object(self):
        _logger.debug(
            "Ending backup object send",
            extra={
                'event_type': 'c_api.backup.end_object.started',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        end_in = init_struct(dsmEndSendObjExIn_t, dsmEndSendObjExInVersion)
        end_out = init_struct(dsmEndSendObjExOut_t, dsmEndSendObjExOutVersion)
        end_in.dsmHandle = self._handle
        _logger.debug(
            "Calling dsmEndSendObjEx",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmEndSendObjEx',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        rc = lib.dsmEndSendObjEx(byref(end_in), byref(end_out))

        check_rc(self._handle, rc, "dsmEndSendObjEx")

        self._backup_stats = {
            "total_bytes_sent": end_out.totalBytesSent.lo + (end_out.totalBytesSent.hi << 32),
            "compressed": bool(end_out.objCompressed),
            "compressed_size": end_out.totalCompressSize.lo + (end_out.totalCompressSize.hi << 32),
            "deduplicated": bool(end_out.objDeduplicated),
            "dedup_size": end_out.totalDedupSize.lo + (end_out.totalDedupSize.hi << 32)
        }
        _logger.debug(
            "Backup object send ended",
            extra={
                'event_type': 'c_api.backup.end_object.completed',
                'stats': self._backup_stats,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

    def _commit_transaction(self):
        _logger.debug(
            "Committing backup transaction",
            extra={
                'event_type': 'c_api.backup.commit_txn.started',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
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

        self._txn_active = False
        self._txn_endout = end_out

        check_rc(self._handle, rc, "dsmEndTxnEx (commit)")
        if end_out.reason != 0:
            _logger.error(
                "Transaction commit failed",
                extra={
                    'event_type': 'c_api.backup.commit_txn.failed',
                    'reason_code': end_out.reason,
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )

            raise TSMTransactionError(
                error_code=SDKErrorCode.COMMIT_FAILED,
                message=f"Transaction commit failed with reason code: {end_out.reason}"
            )

        self._group_leader_obj_id = (
            f"{int(end_out.groupLeaderObjId.hi)}-{int(end_out.groupLeaderObjId.lo)}"
            if end_out.groupLeaderObjId.hi or end_out.groupLeaderObjId.lo
            else None
        )

        _logger.debug(
            "Transaction committed",
            extra={
                'event_type': 'c_api.backup.commit_txn.completed',
                'group_leader_obj_id': self._group_leader_obj_id,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

    def send_within_txn(self):
        """
        Send object within an existing transaction (batch mode).

        Performs the core backup steps (bind MC, send header, send data, end object)
        without beginning or committing a transaction. Used by BatchBackupOperation
        to send multiple objects within a single transaction.

        Notes
        -----
        - Transaction must be started by caller before calling this method
        - Transaction must be committed or aborted by caller after all objects sent
        - Used for batch backup operations to improve efficiency
        """
        self._bind_management_class()
        self._send_object_header()
        self._send_data()
        self._end_object()

    def _abort_transaction(self):
        """
        Abort the backup transaction and roll back changes.

        Calls dsmEndTxnEx() with DSM_VOTE_ABORT to cancel the transaction and
        discard all changes made during the transaction. Used for error recovery
        to maintain server consistency.

        Notes
        -----
        - Clears _txn_active flag after abort
        - Does nothing if no transaction is active
        - All objects sent in the transaction are discarded

        Client API Reference
        --------------------
        dsmEndTxnEx() - End transaction with abort vote
        """
        if not self._txn_active:
            _logger.debug(
                "No active transaction to abort",
                extra={
                    'event_type': 'c_api.backup.abort_txn.skipped',
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            return
        _logger.warning(
            "Aborting backup transaction",
            extra={
                'event_type': 'c_api.backup.abort_txn.started',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        _logger.debug(
            "Calling dsmEndTxnEx",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmEndTxnEx',
                'vote': 'abort',
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        end_in = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)
        end_out = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)
        end_in.dsmHandle = self._handle
        end_in.vote = DSM_VOTE_ABORT
        lib.dsmEndTxnEx(byref(end_in), byref(end_out))
        self._txn_active = False
        _logger.warning(
            "Backup transaction aborted",
            extra={
                'event_type': 'c_api.backup.abort_txn.completed',
                'reason_code': end_out.reason,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )

    def get_stats(self):
        """
        Retrieve backup statistics collected during operation.

        Returns the statistics gathered from dsmEndSendObjEx(), including
        bytes sent, compression results, and deduplication results.

        Returns
        -------
        dict or None
            Backup statistics dictionary or None if not yet available.
        """
        if not hasattr(self, "_backup_stats"):
            return None
        stats = dict(self._backup_stats)
        stats["GroupLeaderObjId"] = getattr(self, "_group_leader_obj_id", None)
        return stats
