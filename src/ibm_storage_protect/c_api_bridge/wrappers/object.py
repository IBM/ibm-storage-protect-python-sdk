"""
IBM Storage Protect Client API - Object Management Operations

This module provides Python wrappers for IBM Storage Protect object management
operations. These operations allow manipulation of backed-up objects without
transferring data content, including deletion, renaming, and attribute updates.

Object management operations are control path operations that modify metadata
and object properties on the server. They are distinct from data path operations
(backup/restore) which transfer actual file content.

Key Classes:
------------
1. **DeleteObjectOperation**: Delete backed-up objects
   - delete_by_name(): Delete using filespace/high-level/low-level name
   - delete_by_id(): Delete using object ID (hi/lo pair)

2. **RenameObjectOperation**: Rename backed-up objects
   - rename(): Change high-level and/or low-level names
   - Supports merge option to combine with existing objects

3. **UpdateObjectOperation**: Update object attributes
   - update(): Modify owner and/or management class
   - Selective updates using action flags

Transaction Management:
-----------------------
Delete and rename operations are wrapped in transactions to ensure atomicity:
- dsmBeginTxn(): Start a transaction
- Operation execution (dsmDeleteObj, dsmRenameObj)
- dsmEndTxnEx(): Commit (DSM_VOTE_COMMIT) or abort (DSM_VOTE_ABORT)

If an operation fails, the transaction is automatically aborted to maintain
data consistency. Update operations don't require explicit transactions.

Object Identification:
----------------------
Objects in IBM Storage Protect are identified by:
- **Filespace (fs)**: The logical container/namespace
- **High-level name (hl)**: Typically the directory path
- **Low-level name (ll)**: Typically the filename
- **Object type**: File, directory, or other types (DSM_OBJ_FILE, etc.)
- **Object ID**: Unique identifier (hi/lo pair) assigned by the server

The helper function key_to_hl_ll() splits a full path into hl and ll components.

C API Mapping:
--------------
- DeleteObjectOperation -> dsmDeleteObj()
- RenameObjectOperation -> dsmRenameObj()
- UpdateObjectOperation -> dsmUpdateObjEx()
- _begin_txn() -> dsmBeginTxn()
- _end_txn() -> dsmEndTxnEx()

Error Handling:
---------------
All operations may raise:
- ObjectMgmtError: Object management operation failures
- TSMTransactionError: Transaction commit/rollback failures

Transactions are automatically aborted on errors to prevent partial updates.
The check_rc() helper validates return codes and raises appropriate exceptions.

Thread Safety:
--------------
These operations are NOT thread-safe. Each requires exclusive access to the
session handle. Concurrent operations with the same handle will cause undefined
behavior and potential data corruption.

Resource Management:
--------------------
- Operations maintain transaction state (_txn_active flag)
- Automatic transaction cleanup on errors
- Proper structure initialization using init_struct()
- Handle unwrapping for C API compatibility

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Object Management", "Transaction Management"

Example Usage:
--------------
    # Delete an object by name
    deleter = DeleteObjectOperation(handle)
    deleter.delete_by_name("/backup/data", "/path/to/file.txt")

    # Delete by object ID
    deleter.delete_by_id(obj_id_hi=12345, obj_id_lo=67890)

    # Rename an object
    renamer = RenameObjectOperation(handle)
    renamer.rename("/backup/data", "/old/path.txt", "/new/path.txt")

    # Rename with merge (combine with existing object)
    renamer.rename("/backup/data", "/src.txt", "/dest.txt", merge=True)

    # Update object attributes
    updater = UpdateObjectOperation(handle)
    updater.update("/backup/data", "/path/file.txt",
                  owner="admin", management_class="STANDARD")
"""

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,broad-exception-caught

import ctypes
from ctypes import byref
from typing import Optional

# Import C API type definitions and constants
from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_BACKUPD_MC,          # Action flag: Update management class
    DSM_BACKUPD_OWNER,       # Action flag: Update owner
    DSM_BACKUP_REP,          # Repository selector: Backup repository
    DSM_OBJ_FILE,            # Object type: Regular file
    DSM_VOTE_ABORT,          # Transaction vote: Abort/rollback
    DSM_VOTE_COMMIT,         # Transaction vote: Commit
    ObjAttr,                 # Object attribute structure
    ObjAttrVersion,          # Version constant for ObjAttr

    delBackIDVersion,        # Version for delete-by-ID structure
    delBackVersion,          # Version for delete-by-name structure
    dsmDelInfo,              # Union structure for delete operations
    dsmEndTxnExIn_t,         # Transaction end input structure
    dsmEndTxnExInVersion,    # Version for dsmEndTxnExIn_t
    dsmEndTxnExOut_t,        # Transaction end output structure
    dsmEndTxnExOutVersion,   # Version for dsmEndTxnExOut_t
    dsmObjName,              # Object name structure (fs/hl/ll/type)
    dsmRenameIn_t,           # Rename operation input structure
    dsmRenameInVersion,      # Version for dsmRenameIn_t
    dsmRenameOut_t,          # Rename operation output structure
    dsmRenameOutVersion,     # Version for dsmRenameOut_t
    dsmUpdateObjExIn_t,      # Update operation input structure
    dsmUpdateObjExInVersion, # Version for dsmUpdateObjExIn_t
    dsmUpdateObjExOut_t,     # Update operation output structure
    dsmUpdateObjExOutVersion,# Version for dsmUpdateObjExOut_t
    stBackup,                # Send type: Backup operation
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.errors.exceptions import ObjectMgmtError
from ibm_storage_protect.errors import SDKErrorCode, TSMTransactionError
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    key_to_hl_ll,
    unwrap_handle as _unwrap,
    init_struct,
    check_rc
)
from ibm_storage_protect.logger import get_logger

# Module-level logger for structured logging
_logger = get_logger(__name__)


def _begin_txn(handle, session_handle: Optional[str] = None, object_key: Optional[str] = None):
    """
    Begin a transaction for object management operations.

    This internal helper function starts a transaction using dsmBeginTxn(). Transactions
    ensure atomicity for operations like delete and rename - either the operation
    completes fully or is rolled back entirely.

    Transactions must be ended with _end_txn() using either DSM_VOTE_COMMIT (success)
    or DSM_VOTE_ABORT (failure/rollback).

    C API Mapping:
    --------------
    Calls dsmBeginTxn(handle)

    Args:
        handle: Raw session handle (already unwrapped)
        session_handle: Optional session identifier for logging
        object_key: Optional object key for logging

    Raises:
        Exception: If transaction cannot be started (via check_rc)

    Notes:
        - This is an internal function, not exposed in the public API
        - Must be paired with _end_txn() to complete the transaction
        - Nested transactions are not supported
        - Transaction state is tracked by the calling class (_txn_active flag)
    """
    _logger.debug(
        "Beginning transaction",
        extra={
            'event_type': 'c_api.transaction.begin',
            'operation': 'dsmBeginTxn',
            'handle': handle,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )
    # Call the C API function to begin a transaction
    rc = lib.dsmBeginTxn(handle)

    # Check return code and raise exception if transaction start failed
    check_rc(handle, rc, "dsmBeginTxn")

    _logger.debug(
        "Transaction begun successfully",
        extra={
            'event_type': 'c_api.transaction.begin.success',
            'handle': handle,
            'rc': rc,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )


def _end_txn(handle, vote, session_handle: Optional[str] = None, object_key: Optional[str] = None):
    """
    End a transaction with commit or abort vote.

    This internal helper function completes a transaction started with _begin_txn().
    The vote parameter determines whether to commit (make changes permanent) or
    abort (rollback changes).

    The function uses dsmEndTxnEx() which provides extended transaction control
    with input/output structures for additional information and error reporting.

    C API Mapping:
    --------------
    Calls dsmEndTxnEx() with:
    - dsmEndTxnExIn_t: Contains handle and vote
    - dsmEndTxnExOut_t: Returns reason code if transaction fails

    Args:
        handle: Raw session handle (already unwrapped)
        vote: Transaction vote - DSM_VOTE_COMMIT (1) to commit,
              DSM_VOTE_ABORT (2) to abort/rollback
        session_handle: Optional session identifier for logging
        object_key: Optional object key for logging

    Raises:
        TSMTransactionError: If transaction end fails (reason code != 0)
        Exception: If the C API call fails (via check_rc)

    Notes:
        - This is an internal function, not exposed in the public API
        - Must be called after _begin_txn() to complete the transaction
        - The reason field in output structure indicates transaction failure details
        - Automatic abort is attempted in exception handlers if transaction is active
        - Vote should be COMMIT on success, ABORT on any error during the operation
    """
    # Convert vote constant to readable string for logging
    vote_str = "COMMIT" if vote == DSM_VOTE_COMMIT else "ABORT"
    _logger.debug(
        "Ending transaction with vote: %s",
        vote_str,
        extra={
            'event_type': 'c_api.transaction.end',
            'operation': 'dsmEndTxnEx',
            'handle': handle,
            'vote': vote_str,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    # Initialize input structure for transaction end
    ein = init_struct(dsmEndTxnExIn_t, dsmEndTxnExInVersion)

    # Initialize output structure to receive transaction result
    eout = init_struct(dsmEndTxnExOut_t, dsmEndTxnExOutVersion)

    # Set the session handle
    ein.dsmHandle = handle

    # Set the vote (COMMIT or ABORT)
    ein.vote = vote

    # Call the C API function to end the transaction
    # Pass structures by reference (pointer) as required by C API
    rc = lib.dsmEndTxnEx(byref(ein), byref(eout))

    # Check return code and raise exception if the call failed
    check_rc(handle, rc, "dsmEndTxnEx")

    # Check the reason code in output structure
    # Non-zero reason indicates transaction failure even if rc was OK
    if eout.reason != 0:
        _logger.error(
            "Transaction end failed with reason code",
            extra={
                'event_type': 'c_api.transaction.end.failed',
                'handle': handle,
                'vote': vote_str,
                'reason_code': eout.reason,
                'rc': rc,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        raise TSMTransactionError(
            error_code=(
                SDKErrorCode.COMMIT_FAILED
                if vote == DSM_VOTE_COMMIT
                else SDKErrorCode.ROLLBACK_FAILED
            ),
            message=f"Transaction end failed with reason code: {eout.reason}"
        )

    _logger.debug(
        "Transaction ended successfully with %s",
        vote_str,
        extra={
            'event_type': 'c_api.transaction.end.success',
            'handle': handle,
            'vote': vote_str,
            'rc': rc,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )


class DeleteObjectOperation:
    """
    Delete backed-up objects from IBM Storage Protect server.

    This class provides methods to delete objects from the server using either
    object name (filespace/high-level/low-level) or object ID. Delete operations
    are wrapped in transactions to ensure atomicity.

    The class maintains transaction state and automatically handles transaction
    cleanup on errors. Each delete operation starts a new transaction, executes
    the deletion, and commits or aborts based on the result.

    C API Mapping:
    --------------
    Uses dsmDeleteObj() with dsmDelInfo union structure containing either:
    - backInfo: For delete-by-name (stVersion=delBackVersion)
    - backIDInfo: For delete-by-ID (stVersion=delBackIDVersion)

    Attributes:
        _handle: Raw session handle (unwrapped)
        _txn_active: Boolean flag tracking transaction state
        _session_handle: Optional session identifier for logging
        _object_key: Optional object key for logging
        _obj_name: dsmObjName structure (created in delete_by_name)

    Methods:
        delete_by_name(): Delete object using filespace and key (path)
        delete_by_id(): Delete object using object ID (hi/lo pair)

    Transaction Flow:
        1. Begin transaction (_begin_txn)
        2. Call dsmDeleteObj with appropriate delete info structure
        3. Commit transaction on success (_end_txn with DSM_VOTE_COMMIT)
        4. Abort transaction on error (_end_txn with DSM_VOTE_ABORT)

    Example:
        >>> deleter = DeleteObjectOperation(handle)
        >>> deleter.delete_by_name("/backup/data", "/path/to/file.txt")
        >>> deleter.delete_by_id(obj_id_hi=12345, obj_id_lo=67890)

    Notes:
        - Each method call is a separate transaction
        - Transactions are automatically aborted on errors
        - The class is not reusable across sessions
        - Not thread-safe - requires exclusive handle access

    See Also:
        - dsmDeleteObj() in dsmapifp.py: Underlying C API function
        - dsmDelInfo in dsmapitd.py: Union structure for delete operations
    """

    def __init__(
        self, handle,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None
    ):
        """
        Initialize a DeleteObjectOperation instance.

        Args:
            handle: Session handle from dsmInitEx(). Can be wrapped or unwrapped.
            session_handle: Optional session identifier for logging/tracking.
            object_key: Optional object key for logging/tracking.
        """
        # Unwrap the handle if needed (converts to raw C pointer)
        self._handle = _unwrap(handle)

        # Track transaction state to ensure proper cleanup
        self._txn_active = False

        # Store optional identifiers for logging
        self._session_handle = session_handle
        self._object_key = object_key

        # Initialize object name structure (will be populated in methods)
        self._obj_name = None

        _logger.debug(
            "DeleteObjectOperation initialized",
            extra={
                'event_type': 'c_api.delete_operation.init',
                'handle': self._handle,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )

    def delete_by_name(
        self, filespace: str, key: str,
        copy_group: int = 1, obj_type: int = DSM_OBJ_FILE
    ):
        """
        Delete an object by its name (filespace, high-level, low-level).

        This method deletes an object using its logical name components. The key
        is split into high-level (directory) and low-level (filename) parts using
        the key_to_hl_ll() helper function.

        The operation is wrapped in a transaction for atomicity. If the deletion
        fails, the transaction is automatically aborted.

        C API Mapping:
        --------------
        Calls dsmDeleteObj() with delete type 0x01 (by name) and dsmDelInfo
        containing backInfo structure with:
        - objNameP: Pointer to dsmObjName structure
        - copyGroup: Copy group number (default 1)

        Args:
            filespace: Name of the filespace containing the object
            key: Full path/key of the object (e.g., "/path/to/file.txt")
                Will be split into high-level and low-level names
            copy_group: Copy group number (default 1). Identifies which backup
                       copy to delete if multiple exist.
            obj_type: Object type constant (default DSM_OBJ_FILE for regular files)
                     Other types: DSM_OBJ_DIRECTORY, etc.

        Raises:
            ObjectMgmtError: If the delete operation fails
            TSMTransactionError: If transaction commit/abort fails

        Example:
            >>> deleter = DeleteObjectOperation(handle)
            >>> deleter.delete_by_name("/backup/data", "/home/user/file.txt")
            >>> deleter.delete_by_name("/backup/data", "/dir/file", copy_group=2)

        Notes:
            - The object must exist or an error will be raised
            - This deletes the object metadata and marks data for deletion
            - Actual data deletion may be deferred based on server policy
            - Each call is a separate transaction
        """
        _logger.info(
            "Deleting object by name",
            extra={
                'event_type': 'c_api.delete_by_name.started',
                'operation': 'delete_by_name',
                'filespace': filespace,
                'key': key,
                'copy_group': copy_group,
                'obj_type': obj_type,
                'session_handle': self._session_handle,
                'object_key': self._object_key
            }
        )

        # Split the key into high-level (directory) and low-level (filename) components
        hl, ll = key_to_hl_ll(key)

        # Initialize and populate the object name structure
        self._obj_name = init_struct(dsmObjName)
        self._obj_name.fs = filespace.encode("utf-8")  # Filespace name
        self._obj_name.hl = hl.encode()                # High-level name (directory)
        self._obj_name.ll = ll.encode()                # Low-level name (filename)
        self._obj_name.objType = obj_type             # Object type (file, directory, etc.)

        # Initialize the delete info union structure
        del_info = init_struct(dsmDelInfo)

        # Set up the backInfo variant for delete-by-name
        del_info.backInfo.stVersion = delBackVersion  # Structure version
        del_info.backInfo.objNameP  = ctypes.pointer(self._obj_name)  # Pointer to object name
        del_info.backInfo.copyGroup = copy_group      # Copy group number

        # Execute the delete operation with type 0x01 (by name)
        self._run(0x01, del_info, f"by_name: {filespace}/{key}")

    def delete_by_id(self, obj_id_hi: int, obj_id_lo: int):
        """
        Delete an object by its unique object ID.

        This method deletes an object using its server-assigned object ID, which
        is a 64-bit value split into high and low 32-bit components. Object IDs
        are typically obtained from query operations.

        The operation is wrapped in a transaction for atomicity. If the deletion
        fails, the transaction is automatically aborted.

        C API Mapping:
        --------------
        Calls dsmDeleteObj() with delete type 0x02 (by ID) and dsmDelInfo
        containing backIDInfo structure with objId (hi/lo pair).

        Args:
            obj_id_hi: High 32 bits of the object ID
            obj_id_lo: Low 32 bits of the object ID

        Raises:
            ObjectMgmtError: If the delete operation fails
            TSMTransactionError: If transaction commit/abort fails

        Example:
            >>> deleter = DeleteObjectOperation(handle)
            >>> # Object ID obtained from query
            >>> deleter.delete_by_id(obj_id_hi=12345, obj_id_lo=67890)

        Notes:
            - Object IDs are unique and persistent for each backed-up object
            - This method is faster than delete_by_name as it doesn't require name lookup
            - The object must exist or an error will be raised
            - Each call is a separate transaction
        """
        _logger.info(
            "Deleting object by ID",
            extra={
                'event_type': 'c_api.delete_by_id.started',
                'operation': 'delete_by_id',
                'obj_id_hi': obj_id_hi,
                'obj_id_lo': obj_id_lo,
                'session_handle': self._session_handle,
                'object_key': self._object_key
            }
        )

        # Initialize the delete info union structure
        del_info = init_struct(dsmDelInfo)

        # Set up the backIDInfo variant for delete-by-ID
        del_info.backIDInfo.stVersion = delBackIDVersion  # Structure version
        del_info.backIDInfo.objId.hi  = obj_id_hi         # High 32 bits of object ID
        del_info.backIDInfo.objId.lo  = obj_id_lo         # Low 32 bits of object ID

        # Execute the delete operation with type 0x02 (by ID)
        self._run(0x02, del_info, f"by_id: {obj_id_hi}/{obj_id_lo}")

    def _run(self, del_type, del_info, context_str):
        """
        Internal method to execute the delete operation within a transaction.

        This method handles the transaction lifecycle:
        1. Begin transaction
        2. Call dsmDeleteObj
        3. Commit on success or abort on failure

        Args:
            del_type: Delete type - 0x01 for by-name, 0x02 for by-ID
            del_info: dsmDelInfo union structure with appropriate variant populated
            context_str: Descriptive string for logging (e.g., "by_name: /fs/path")

        Raises:
            ObjectMgmtError: If the delete operation fails
            TSMTransactionError: If transaction commit/abort fails

        Notes:
            - Automatically manages transaction state via _txn_active flag
            - Attempts to abort transaction on any error
            - Logs all operations for debugging and audit purposes
        """
        _logger.debug(
            "Executing delete operation: %s",
            context_str,
            extra={
                'event_type': 'c_api.delete.execute',
                'handle': self._handle,
                'del_type': del_type,
                'context': context_str,
                'session_handle': self._session_handle,
                'object_key': self._object_key
            }
        )

        # Begin a new transaction for this delete operation
        _begin_txn(self._handle, self._session_handle, self._object_key)
        self._txn_active = True  # Mark transaction as active for cleanup tracking

        try:
            _logger.debug(
                "Calling dsmDeleteObj",
                extra={
                    'event_type': 'c_api.dsmDeleteObj.call',
                    'handle': self._handle,
                    'del_type': del_type,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )
            # Call the C API function to delete the object
            # Parameters: handle, delete type (0x01=by name, 0x02=by ID), delete info structure
            rc = lib.dsmDeleteObj(self._handle, del_type, del_info)

            # Check return code and raise exception if delete failed
            check_rc(self._handle, rc, "dsmDeleteObj")

            _logger.debug(
                "dsmDeleteObj completed successfully",
                extra={
                    'event_type': 'c_api.dsmDeleteObj.success',
                    'handle': self._handle,
                    'rc': rc,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )

            # Commit the transaction to make the deletion permanent
            _end_txn(self._handle, DSM_VOTE_COMMIT, self._session_handle, self._object_key)
            self._txn_active = False  # Transaction completed successfully

            _logger.info(
                "Delete operation completed: %s",
                context_str,
                extra={
                    'event_type': 'c_api.delete.completed',
                    'context': context_str,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )
        except ObjectMgmtError as e:
            # Log the error with full context
            _logger.error(
                "Delete operation failed: %s",
                context_str,
                extra={
                    'event_type': 'c_api.delete.failed',
                    'context': context_str,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                },
                exc_info=True
            )
            # Attempt to abort the transaction if it's still active
            if self._txn_active:
                try:
                    _logger.debug("Aborting transaction due to error")
                    _end_txn(self._handle, DSM_VOTE_ABORT, self._session_handle, self._object_key)
                except ObjectMgmtError:
                    # Log warning if abort fails, but don't mask the original error
                    _logger.warning("Failed to abort transaction", exc_info=True)
                self._txn_active = False
            # Re-raise the original exception
            raise


class RenameObjectOperation:
    """
    Rename backed-up objects on IBM Storage Protect server.

    This class provides functionality to rename objects by changing their high-level
    and/or low-level names. Rename operations are wrapped in transactions to ensure
    atomicity and support an optional merge mode to combine with existing objects.

    The class maintains transaction state and automatically handles transaction
    cleanup on errors. Each rename operation starts a new transaction, executes
    the rename, and commits or aborts based on the result.

    C API Mapping:
    --------------
    Uses dsmRenameObj() with dsmRenameIn_t input and dsmRenameOut_t output structures.

    Attributes:
        _handle: Raw session handle (unwrapped)
        _txn_active: Boolean flag tracking transaction state
        _session_handle: Optional session identifier for logging
        _object_key: Optional object key for logging
        _obj_name: dsmObjName structure (created in rename method)

    Methods:
        rename(): Rename object by changing high-level and/or low-level names

    Merge Mode:
        When merge=True, if an object with the new name already exists, the renamed
        object is merged with it. This is useful for consolidating backup versions.
        When merge=False (default), rename fails if the target name exists.

    Transaction Flow:
        1. Begin transaction (_begin_txn)
        2. Call dsmRenameObj with rename parameters
        3. Commit transaction on success (_end_txn with DSM_VOTE_COMMIT)
        4. Abort transaction on error (_end_txn with DSM_VOTE_ABORT)

    Example:
        >>> renamer = RenameObjectOperation(handle)
        >>> renamer.rename("/backup/data", "/old/path.txt", "/new/path.txt")
        >>> renamer.rename("/backup/data", "/src.txt", "/dest.txt", merge=True)

    Notes:
        - Each method call is a separate transaction
        - Transactions are automatically aborted on errors
        - The class is not reusable across sessions
        - Not thread-safe - requires exclusive handle access
        - Repository is always DSM_BACKUP_REP (backup repository)

    See Also:
        - dsmRenameObj() in dsmapifp.py: Underlying C API function
        - dsmRenameIn_t/dsmRenameOut_t in dsmapitd.py: Input/output structures
    """

    def __init__(
        self, handle,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None
    ):
        """
        Initialize a RenameObjectOperation instance.

        Args:
            handle: Session handle from dsmInitEx(). Can be wrapped or unwrapped.
            session_handle: Optional session identifier for logging/tracking.
            object_key: Optional object key for logging/tracking.
        """
        # Unwrap the handle if needed (converts to raw C pointer)
        self._handle = _unwrap(handle)

        # Track transaction state to ensure proper cleanup
        self._txn_active = False

        # Store optional identifiers for logging
        self._session_handle = session_handle
        self._object_key = object_key

        # Initialize object name structure (will be populated in methods)
        self._obj_name = None

        _logger.debug(
            "RenameObjectOperation initialized",
            extra={
                'event_type': 'c_api.rename_operation.init',
                'handle': self._handle,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )

    def rename(
        self, filespace: str, key: str, new_key: str,
        merge: bool = False, obj_type: int = DSM_OBJ_FILE
    ):
        """
        Rename an object by changing its high-level and/or low-level names.

        This method renames an object on the server by specifying new high-level
        and low-level names. The operation is wrapped in a transaction for atomicity.

        The merge parameter controls behavior when the target name already exists:
        - merge=False (default): Rename fails if target exists
        - merge=True: Renamed object is merged with existing target object

        C API Mapping:
        --------------
        Calls dsmRenameObj() with dsmRenameIn_t structure containing:
        - objNameP: Pointer to current object name
        - newHl: New high-level name
        - newLl: New low-level name
        - merge: Merge flag (0 or 1)
        - repository: DSM_BACKUP_REP (backup repository)

        Args:
            filespace: Name of the filespace containing the object
            key: Current full path/key of the object (e.g., "/old/path/file.txt")
                Will be split into current high-level and low-level names
            new_key: New full path/key for the object (e.g., "/new/path/file.txt")
                    Will be split into new high-level and low-level names
            merge: If True, merge with existing object at new_key if it exists.
                  If False (default), fail if new_key already exists.
            obj_type: Object type constant (default DSM_OBJ_FILE for regular files)

        Raises:
            Exception: If the rename operation fails
            TSMTransactionError: If transaction commit/abort fails

        Example:
            >>> renamer = RenameObjectOperation(handle)
            >>> # Simple rename
            >>> renamer.rename("/backup/data", "/old/file.txt", "/new/file.txt")

            >>> # Rename with merge
            >>> renamer.rename("/backup/data", "/src.txt", "/dest.txt", merge=True)

            >>> # Rename to different directory
            >>> renamer.rename("/backup/data", "/dir1/file.txt", "/dir2/file.txt")

         Notes:
            - The object must exist at the current key or an error will be raised
            - If merge=False and target exists, operation fails
            - If merge=True, backup versions are combined
            - Each call is a separate transaction
            - Only works with backup repository (not archive)
        """
        _logger.info(
            "Renaming object",
            extra={
                'event_type': 'c_api.rename.started',
                'operation': 'rename',
                'filespace': filespace,
                'old_key': key,
                'new_key': new_key,
                'merge': merge,
                'obj_type': obj_type,
                'session_handle': self._session_handle,
                'object_key': self._object_key
            }
        )

        # Split current key into high-level (directory) and low-level (filename)
        hl, ll         = key_to_hl_ll(key)

        # Split new key into new high-level and low-level names
        new_hl, new_ll = key_to_hl_ll(new_key)

        # Initialize and populate the current object name structure
        self._obj_name = init_struct(dsmObjName)
        self._obj_name.fs = filespace.encode()  # Filespace name
        self._obj_name.hl = hl.encode()         # Current high-level name
        self._obj_name.ll = ll.encode()         # Current low-level name
        self._obj_name.objType = obj_type      # Object type

        # Initialize the rename input structure
        rin = init_struct(dsmRenameIn_t, dsmRenameInVersion)
        rin.dsmHandle  = self._handle                      # Session handle
        rin.repository = DSM_BACKUP_REP                    # Backup repository
        rin.objNameP   = ctypes.pointer(self._obj_name)    # Pointer to current name
        rin.newHl      = new_hl.encode()                   # New high-level name
        rin.newLl      = new_ll.encode()                   # New low-level name
        rin.merge      = 1 if merge else 0                 # Merge flag (1=merge, 0=fail if exists)

        # Initialize the rename output structure to receive results
        rout = init_struct(dsmRenameOut_t, dsmRenameOutVersion)

        # Begin a new transaction for this rename operation
        _begin_txn(self._handle, self._session_handle, self._object_key)
        self._txn_active = True  # Mark transaction as active

        try:
            _logger.debug(
                "Calling dsmRenameObj",
                extra={
                    'event_type': 'c_api.dsmRenameObj.call',
                    'handle': self._handle,
                    'old_key': key,
                    'new_key': new_key,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )
            # Call the C API function to rename the object
            # Pass input and output structures by reference (pointer)
            rc = lib.dsmRenameObj(byref(rin), byref(rout))

            # Check return code and raise exception if rename failed
            check_rc(self._handle, rc, "dsmRenameObj")

            _logger.debug(
                "dsmRenameObj completed successfully",
                extra={
                    'event_type': 'c_api.dsmRenameObj.success',
                    'handle': self._handle,
                    'rc': rc,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )

            # Commit the transaction to make the rename permanent
            _end_txn(self._handle, DSM_VOTE_COMMIT, self._session_handle, self._object_key)
            self._txn_active = False  # Transaction completed successfully

            _logger.info(
                "Object rename completed",
                extra={
                    'event_type': 'c_api.rename.completed',
                    'filespace': filespace,
                    'old_key': key,
                    'new_key': new_key,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )
        except Exception as e:
            # Log the error with full context
            _logger.error(
                "Object rename failed",
                extra={
                    'event_type': 'c_api.rename.failed',
                    'filespace': filespace,
                    'old_key': key,
                    'new_key': new_key,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                },
                exc_info=True
            )
            # Attempt to abort the transaction if it's still active
            if self._txn_active:
                try:
                    _logger.debug("Aborting transaction due to error")
                    _end_txn(self._handle, DSM_VOTE_ABORT, self._session_handle, self._object_key)
                except Exception:
                    # Log warning if abort fails, but don't mask the original error
                    _logger.warning("Failed to abort transaction", exc_info=True)
                self._txn_active = False
            # Re-raise the original exception
            raise


class UpdateObjectOperation:
    """
    Update attributes of backed-up objects on IBM Storage Protect server.

    This class provides functionality to update object metadata such as owner
    and management class without modifying the actual data content. Update
    operations do NOT require explicit transactions (unlike delete/rename).

    The class allows selective updates using action flags - only specified
    attributes are modified, others remain unchanged.

    C API Mapping:
    --------------
    Uses dsmUpdateObjEx() with dsmUpdateObjExIn_t input and dsmUpdateObjExOut_t
    output structures.

    Attributes:
        _handle: Raw session handle (unwrapped)
        _session_handle: Optional session identifier for logging
        _object_key: Optional object key for logging

    Methods:
        update(): Update object owner and/or management class

    Action Flags:
        - DSM_BACKUPD_OWNER: Update the owner field
        - DSM_BACKUPD_MC: Update the management class field
        Flags are OR'd together to update multiple fields in one call.

    Management Class:
        Determines retention policy, backup frequency, and storage destination.
        Must match a management class defined in the server policy.

    Example:
        >>> updater = UpdateObjectOperation(handle)
        >>> updater.update("/backup/data", "/path/file.txt", owner="admin")
        >>> updater.update("/backup/data", "/path/file.txt",
        ...               management_class="STANDARD")
        >>> updater.update("/backup/data", "/path/file.txt",
        ...               owner="admin", management_class="STANDARD")

    Notes:
        - Does not require explicit transactions (unlike delete/rename)
        - Only specified attributes are updated
        - The object must exist or an error will be raised
        - Management class must be defined in server policy
        - Owner field is limited to 64 bytes
        - Not thread-safe - requires exclusive handle access

    See Also:
        - dsmUpdateObjEx() in dsmapifp.py: Underlying C API function
        - dsmUpdateObjExIn_t/dsmUpdateObjExOut_t in dsmapitd.py: I/O structures
    """

    def __init__(
        self, handle, session_handle: Optional[str] = None,
        object_key: Optional[str] = None
    ):
        """
        Initialize an UpdateObjectOperation instance.

        Args:
            handle: Session handle from dsmInitEx(). Can be wrapped or unwrapped.
            session_handle: Optional session identifier for logging/tracking.
            object_key: Optional object key for logging/tracking.
        """
        # Unwrap the handle if needed (converts to raw C pointer)
        self._handle = _unwrap(handle)

        # Store optional identifiers for logging
        self._session_handle = session_handle
        self._object_key = object_key

        _logger.debug(
            "UpdateObjectOperation initialized",
            extra={
                'event_type': 'c_api.update_operation.init',
                'handle': self._handle,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )

    def update(self, filespace: str, key: str,
               owner: str = "", management_class: str = "", obj_type: int = DSM_OBJ_FILE):
        """
        Update object attributes (owner and/or management class).

        This method updates metadata attributes of a backed-up object without
        modifying the actual data content. You can update owner, management class,
        or both in a single call.

        Unlike delete and rename operations, updates do NOT require explicit
        transactions. The operation is atomic at the C API level.

        C API Mapping:
        --------------
        Calls dsmUpdateObjEx() with dsmUpdateObjExIn_t structure containing:
        - objNameP: Pointer to object name structure
        - objAttrPtr: Pointer to object attributes with new values
        - objUpdAct: Action flags indicating which fields to update
        - sendType: stBackup (backup operation type)

        Args:
            filespace: Name of the filespace containing the object
            key: Full path/key of the object (e.g., "/path/to/file.txt")
                Will be split into high-level and low-level names
            owner: New owner name (up to 64 bytes). Empty string means no update.
            management_class: New management class name. Empty string means no update.
                             Must match a management class defined in server policy.
            obj_type: Object type constant (default DSM_OBJ_FILE for regular files)

        Raises:
            Exception: If the update operation fails

        Example:
            >>> updater = UpdateObjectOperation(handle)
            >>> # Update owner only
            >>> updater.update("/backup/data", "/path/file.txt", owner="admin")

            >>> # Update management class only
            >>> updater.update("/backup/data", "/path/file.txt",
            ...               management_class="STANDARD")

            >>> # Update both attributes
            >>> updater.update("/backup/data", "/path/file.txt",
            ...               owner="admin", management_class="STANDARD")

        Notes:
            - The object must exist or an error will be raised
            - Only non-empty parameters are updated
            - Management class must be defined in server policy
            - Owner field is limited to 64 bytes
            - Does not require explicit transaction management
            - Operation is atomic - either all updates succeed or none do
        """
        _logger.info(
            "Updating object",
            extra={
                'event_type': 'c_api.update.started',
                'operation': 'update',
                'filespace': filespace,
                'key': key,
                'owner': owner if owner else None,
                'management_class': management_class if management_class else None,
                'obj_type': obj_type,
                'session_handle': self._session_handle,
                'object_key': self._object_key
            }
        )

        # Split the key into high-level (directory) and low-level (filename) components
        hl, ll = key_to_hl_ll(key)

        # Initialize and populate the object name structure
        obj_name = init_struct(dsmObjName)
        obj_name.fs = filespace.encode()  # Filespace name
        obj_name.hl = hl.encode()         # High-level name (directory)
        obj_name.ll = ll.encode()         # Low-level name (filename)
        obj_name.objType = obj_type      # Object type

        # Initialize the object attributes structure
        obj_attr = init_struct(ObjAttr, ObjAttrVersion)

        # Set owner if provided (copy bytes into fixed-size array, max 64 bytes)
        if owner:
            owner_bytes = owner.encode()[:64]
            obj_attr.owner = owner_bytes

        # Set management class pointer if provided
        if management_class:
            obj_attr.mcNameP = management_class.encode()

        # Build action flags to indicate which fields should be updated
        # Start with no actions, then OR in flags for each provided parameter
        action = 0
        if owner:
            action |= DSM_BACKUPD_OWNER  # Update owner field
        if management_class:
            action |= DSM_BACKUPD_MC     # Update management class field

        _logger.debug(
            "Update action flags set",
            extra={
                'event_type': 'c_api.update.action_flags',
                'action': action,
                'has_owner': bool(owner),
                'has_mgmt_class': bool(management_class),
                'session_handle': self._session_handle,
                'object_key': self._object_key
            }
        )

        # Initialize the update input structure
        update_in = init_struct(dsmUpdateObjExIn_t, dsmUpdateObjExInVersion)
        update_in.dsmHandle = self._handle                    # Session handle
        update_in.sendType = stBackup                         # Operation type (backup)
        update_in.objNameP = ctypes.pointer(obj_name)         # Pointer to object name
        update_in.objAttrPtr = ctypes.pointer(obj_attr)       # Pointer to new attributes
        update_in.objUpdAct = action                          # Action flags

        # Initialize the update output structure to receive results
        update_out = init_struct(dsmUpdateObjExOut_t, dsmUpdateObjExOutVersion)

        try:
            _logger.debug(
                "Calling dsmUpdateObjEx",
                extra={
                    'event_type': 'c_api.dsmUpdateObjEx.call',
                    'handle': self._handle,
                    'filespace': filespace,
                    'key': key,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )
            # Call the C API function to update the object
            # Pass input and output structures by reference (pointer)
            rc = lib.dsmUpdateObjEx(byref(update_in), byref(update_out))

            # Check return code and raise exception if update failed
            check_rc(self._handle, rc, "dsmUpdateObjEx")

            _logger.info(
                "Object update completed",
                extra={
                    'event_type': 'c_api.update.completed',
                    'filespace': filespace,
                    'key': key,
                    'rc': rc,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                }
            )
        except Exception as e:
            _logger.error(
                "Object update failed",
                extra={
                    'event_type': 'c_api.update.failed',
                    'filespace': filespace,
                    'key': key,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'session_handle': self._session_handle,
                    'object_key': self._object_key
                },
                exc_info=True
            )
            raise
