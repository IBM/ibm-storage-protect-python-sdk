"""
IBM Storage Protect Client API - Filespace Management Operations

This module provides Python wrappers for IBM Storage Protect filespace management
operations. Filespaces are logical containers that organize backed-up objects,
typically representing filesystems, application namespaces, or data sources.

Filespace Lifecycle:
--------------------
1. **Registration** (register_filespace): Create a new filespace on the server
   - Must be done before backing up objects to the filespace
   - Idempotent: Returns success if filespace already exists
   - Sets initial attributes: type, capacity, occupancy, and info string

2. **Update** (update_filespace): Modify filespace attributes
   - Update capacity and occupancy to reflect storage usage
   - Change filespace type or descriptive information
   - Selective updates using action flags

3. **Deletion** (delete_filespace): Remove filespace and all its objects
   - Deletes from all repositories (backup and archive)
   - Irreversible operation - all objects in the filespace are removed
   - Requires appropriate permissions

Key Concepts:
-------------
- **Filespace Name**: Unique identifier for the filespace (e.g., "/backup/data")
- **Filespace Type**: Descriptive string indicating the data source (e.g., "Python-SDK")
- **Capacity**: Total storage capacity of the source (in bytes, stored as dsStruct64_t)
- **Occupancy**: Current storage usage of the source (in bytes, stored as dsStruct64_t)
- **fsInfo**: Descriptive text about the filespace (Unix-specific attribute)

C API Mapping:
--------------
- register_filespace() -> dsmRegisterFS()
- update_filespace() -> dsmUpdateFS()
- delete_filespace() -> dsmDeleteFS()

Return Codes:
-------------
- DSM_RC_OK (0): Operation successful
- DSM_RC_FS_ALREADY_REGED (2025): Filespace already registered (treated as success)
- Other codes indicate errors and raise exceptions

Thread Safety:
--------------
These functions are NOT thread-safe. Each requires exclusive access to the session
handle. Concurrent calls with the same handle will cause undefined behavior.

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapter: "Filespace Management"

Example Usage:
--------------
    # Register a new filespace
    register_filespace(handle, "/backup/database")

    # Update filespace with current usage
    update_filespace(handle, "/backup/database",
                     occupancy=5000000000,  # 5GB used
                   capacity=10000000000,  # 10GB total
                   fs_info="Production database backup")

    # Delete filespace and all its objects
    delete_filespace(handle, "/backup/database")
"""
# pylint: disable=too-many-arguments,too-many-positional-arguments

from ctypes import byref
from typing import Optional

# Import C API type definitions and constants
from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_FSUPD_CAPACITY,      # Action flag: Update capacity field
    DSM_FSUPD_FSINFO,        # Action flag: Update fsInfo field
    DSM_FSUPD_FSTYPE,        # Action flag: Update fsType field
    DSM_FSUPD_OCCUPANCY,     # Action flag: Update occupancy field
    DSM_REPOS_ALL,           # Repository selector: All repositories (backup + archive)
    dsmFSUpd,                # Structure for filespace update data
    dsmFSUpdVersion,         # Version constant for dsmFSUpd structure
    regFSData,               # Structure for filespace registration data
    regFSDataVersion,        # Version constant for regFSData structure
)
from ibm_storage_protect.c_api_bridge.c_api.return_codes import (
    DSM_RC_FS_ALREADY_REGED,
    DSM_RC_OK
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
     unwrap_handle as _unwrap,
      init_struct,
       check_rc
    )
from ibm_storage_protect.logger import get_logger
# Module-level logger for structured logging
_logger = get_logger(__name__)
def register_filespace (
    handle,
    filespace: str,
    session_handle: Optional[str] = None,
    object_key: Optional[str] = None
    ) -> None:
    """
    Register a new filespace with the IBM Storage Protect server.

    This function creates a new filespace on the server, which is required before
    backing up any objects. A filespace is a logical container that organizes objects,
    typically representing a filesystem, application namespace, or data source.

    The function is idempotent - if the filespace already exists (DSM_RC_FS_ALREADY_REGED),
    it returns successfully without error. This allows safe repeated calls.

    C API Mapping:
    --------------
    Calls dsmRegisterFS() with a regFSData structure containing:
    - fsName: The filespace name
    - fsType: Set to "Python-SDK" to identify the source
    - fsInfo: Descriptive text "Python SDK Filespace"
    - occupancy: Initial value of 100 bytes (lo=100, hi=0)
    - capacity: Initial value of 1000 bytes (lo=1000, hi=0)

    Args:
        handle: Session handle from dsmInitEx(). Can be wrapped or unwrapped.
        filespace: Name of the filespace to register. Should be a unique identifier
                  like "/backup/data" or "AppName". Maximum length depends on
                  server configuration (typically 1024 bytes).
        session_handle: Optional session identifier for logging/tracking purposes.
        object_key: Optional object key for logging/tracking purposes.

    Returns:
        None: Function returns nothing on success.

    Raises:
        FsRegisterError: If registration fails (except for already-registered case).
        Exception: For other unexpected errors during the operation.

    Notes:
        - The filespace must be registered before any backup operations to it
        - Initial capacity/occupancy values are placeholders; update them with
          update_filespace() to reflect actual storage metrics
        - Filespace names are case-sensitive on most platforms
        - The fsType "Python-SDK" helps identify objects backed up by this SDK

    Example:
        >>> register_filespace(handle, "/backup/database")
        >>> # Filespace is now ready for backup operations

        >>> # Safe to call multiple times
        >>> register_filespace(handle, "/backup/database")  # No error

    See Also:
        - update_filespace(): Update filespace attributes after registration
        - delete_filespace(): Remove a filespace and all its objects
        - dsmRegisterFS() in dsmapifp.py: Underlying C API function
    """
    _logger.info(
        "Registering filespace",
        extra={
            'event_type': 'c_api.filespace.register.started',
            'operation': 'register_filespace',
            'filespace': filespace,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )
    # Initialize the filespace registration structure with proper version
    fs_data = init_struct(regFSData, regFSDataVersion)
    # Set the filespace name (UTF-8 encoded for C API compatibility)
    fs_data.fsName = filespace.encode("utf-8")
    # Set filespace type to identify this as a Python SDK backup
    fs_data.fsType = b"Python-SDK"
    # Set descriptive information about the filespace (Unix-specific attribute)
    fs_info = b"Python SDK Filespace"
    fs_data.fsAttr.unixFSAttr.fsInfo = fs_info
    fs_data.fsAttr.unixFSAttr.fsInfoLength = len(fs_info) + 1  # Include null terminator
    # Set initial occupancy (current usage) - placeholder value of 100 bytes
    # Use dsStruct64_t format: hi (high 32 bits) and lo (low 32 bits)
    fs_data.occupancy.hi = 0
    fs_data.occupancy.lo = 100
    # Set initial capacity (total size) - placeholder value of 1000 bytes
    fs_data.capacity.hi = 0
    fs_data.capacity.lo = 1000

    # Unwrap the handle if it's wrapped (converts to raw C pointer)
    handle = _unwrap(handle)

    _logger.debug(
        "Calling dsmRegisterFS",
        extra={
            'event_type': 'c_api.dsmRegisterFS.call',
            'handle': handle,
            'filespace': filespace,
            'fs_type': 'Python-SDK',
            'occupancy': 100,
            'capacity': 1000,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    # Call the C API function to register the filespace
    # byref() passes the structure by reference (pointer) as required by C API
    rc = lib.dsmRegisterFS(handle, byref(fs_data))

    # Check return code: accept both success and already-registered as valid outcomes
    if rc not in (DSM_RC_OK, DSM_RC_FS_ALREADY_REGED):
        _logger.error(
            "Filespace registration failed",
            extra={
                'event_type': 'c_api.filespace.register.failed',
                'filespace': filespace,
                'rc': rc,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
        # Raise exception for actual errors (helper function checks error message)
        check_rc(handle, rc, "dsmRegisterFS")
    elif rc == DSM_RC_FS_ALREADY_REGED:
        # Filespace already exists - this is acceptable, log and continue
        _logger.info(
            "Filespace already registered",
            extra={
                'event_type': 'c_api.filespace.register.already_exists',
                'filespace': filespace,
                'rc': rc,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
    else:
        _logger.info(
            "Filespace registration completed",
            extra={
                'event_type': 'c_api.filespace.register.completed',
                'filespace': filespace,
                'rc': rc,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )


def update_filespace(
    handle,
    filespace: str,
    fs_info: Optional[str] = None,
    occupancy: Optional[int] = None,
    capacity: Optional[int] = None,
    fs_type: Optional[str] = None,
    session_handle: Optional[str] = None,
    object_key: Optional[str] = None,
) -> None:
    """
    Update attributes of an existing filespace on the IBM Storage Protect server.

    This function allows selective updates to filespace metadata without affecting
    the backed-up objects. You can update capacity, occupancy, type, and descriptive
    information independently or in combination.

    The function uses action flags (DSM_FSUPD_*) to indicate which fields should be
    updated, allowing efficient partial updates without resending unchanged data.

    C API Mapping:
    --------------
    Calls dsmUpdateFS() with a dsmFSUpd structure and action flags:
    - DSM_FSUPD_FSTYPE: Update the fsType field
    - DSM_FSUPD_FSINFO: Update the fsInfo field
    - DSM_FSUPD_OCCUPANCY: Update the occupancy field
    - DSM_FSUPD_CAPACITY: Update the capacity field

    Args:
        handle: Session handle from dsmInitEx(). Can be wrapped or unwrapped.
        filespace: Name of the filespace to update. Must already be registered.
        fs_info: Optional descriptive text about the filespace (Unix-specific).
                Updates the fsInfo field if provided.
        occupancy: Optional current storage usage in bytes. Updates the occupancy
                  field if provided. Stored as dsStruct64_t (hi=0, lo=value).
        capacity: Optional total storage capacity in bytes. Updates the capacity
                 field if provided. Stored as dsStruct64_t (hi=0, lo=value).
        fs_type: Optional filespace type string. Updates the fsType field if provided.
        session_handle: Optional session identifier for logging/tracking purposes.
        object_key: Optional object key for logging/tracking purposes.

    Returns:
        None: Function returns nothing on success.

    Raises:
        Exception: If the update operation fails. The exception includes the
                  return code and error message from the C API.

    Notes:
        - The filespace must already be registered before calling this function
        - Only provided parameters are updated; others remain unchanged
        - Capacity and occupancy are limited to 32-bit values (lo field only)
          For values > 4GB, you would need to use the hi field as well
        - Updates are atomic - either all specified fields update or none do
        - This operation does not affect backed-up objects in the filespace

    Example:
        >>> # Update storage metrics
        >>> update_filespace(handle, "/backup/data",
        ...                occupancy=5000000000,  # 5GB used
        ...                capacity=10000000000)  # 10GB total

        >>> # Update descriptive information
        >>> update_filespace(handle, "/backup/data",
        ...                fs_info="Production database - daily backup",
        ...                fs_type="PostgreSQL")

        >>> # Update single field
        >>> update_filespace(handle, "/backup/data", occupancy=6000000000)

    See Also:
        - register_filespace(): Register a new filespace
        - delete_filespace(): Remove a filespace
        - dsmUpdateFS() in dsmapifp.py: Underlying C API function
    """
    _logger.info(
        "Updating filespace",
        extra={
            'event_type': 'c_api.filespace.update.started',
            'operation': 'update_filespace',
            'filespace': filespace,
            'has_fs_info': fs_info is not None,
            'has_occupancy': occupancy is not None,
            'has_capacity': capacity is not None,
            'has_fs_type': fs_type is not None,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    # Unwrap the handle if it's wrapped (converts to raw C pointer)
    handle = _unwrap(handle)

    # Initialize the filespace update structure with proper version
    upd = init_struct(dsmFSUpd, dsmFSUpdVersion)

    # Build action flags to indicate which fields should be updated
    # Start with no actions, then OR in flags for each provided parameter
    upd_action = 0

    # Update filespace type if provided
    if fs_type is not None:
        upd.fsType = fs_type.encode("utf-8")
        upd_action |= DSM_FSUPD_FSTYPE  # Set the fsType update flag
        _logger.debug("Setting fs_type: %s", fs_type)

    # Update filespace info string if provided (Unix-specific attribute)
    if fs_info is not None:
        fs_info_bytes = fs_info.encode("utf-8")
        upd.fsAttr.unixFSAttr.fsInfo = fs_info_bytes
        upd.fsAttr.unixFSAttr.fsInfoLength = len(fs_info_bytes)
        upd_action |= DSM_FSUPD_FSINFO  # Set the fsInfo update flag
        _logger.debug("Setting fs_info: %s", fs_info)

    # Update occupancy (current usage) if provided
    if occupancy is not None:
        upd.occupancy.hi = 0  # High 32 bits (for values > 4GB)
        upd.occupancy.lo = occupancy  # Low 32 bits
        upd_action |= DSM_FSUPD_OCCUPANCY  # Set the occupancy update flag
        _logger.debug("Setting occupancy: %s", occupancy)

    # Update capacity (total size) if provided
    if capacity is not None:
        upd.capacity.hi = 0  # High 32 bits (for values > 4GB)
        upd.capacity.lo = capacity  # Low 32 bits
        upd_action |= DSM_FSUPD_CAPACITY  # Set the capacity update flag
        _logger.debug("Setting capacity: %s", capacity)

    _logger.debug(
        "Calling dsmUpdateFS",
        extra={
            'event_type': 'c_api.dsmUpdateFS.call',
            'handle': handle,
            'filespace': filespace,
            'upd_action': upd_action,
            'occupancy': occupancy,
            'capacity': capacity,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    try:
        # Call the C API function to update the filespace
        # Parameters: handle, filespace name (UTF-8), update structure pointer, action flags
        rc = lib.dsmUpdateFS(handle, filespace.encode("utf-8"), byref(upd), upd_action)

        # Check return code and raise exception if operation failed
        check_rc(handle, rc, "dsmUpdateFS")

        _logger.info(
            "Filespace update completed",
            extra={
                'event_type': 'c_api.filespace.update.completed',
                'filespace': filespace,
                'rc': rc,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
    except Exception as e:
        _logger.error(
            "Filespace update failed",
            extra={
                'event_type': 'c_api.filespace.update.failed',
                'filespace': filespace,
                'error': str(e),
                'error_type': type(e).__name__,
                'session_handle': session_handle,
                'object_key': object_key
            },
            exc_info=True
        )
        raise


def delete_filespace(
    handle,
    fs_name: str,
    session_handle: Optional[str] = None,
    object_key: Optional[str] = None
) -> None:
    """
    Delete a filespace and all its objects from the IBM Storage Protect server.

    This function permanently removes a filespace and ALL objects it contains from
    both backup and archive repositories. This is an irreversible operation that
    should be used with caution.

    The deletion affects all repositories (DSM_REPOS_ALL), meaning both backup
    and archive copies are removed. There is no way to recover the data after
    this operation completes successfully.

    C API Mapping:
    --------------
    Calls dsmDeleteFS() with:
    - handle: Session handle
    - fsName: Filespace name (UTF-8 encoded)
    - repository: DSM_REPOS_ALL (delete from all repositories)

    Args:
        handle: Session handle from dsmInitEx(). Can be wrapped or unwrapped.
        fs_name: Name of the filespace to delete. Must match an existing filespace.
        session_handle: Optional session identifier for logging/tracking purposes.
        object_key: Optional object key for logging/tracking purposes.

    Returns:
        None: Function returns nothing on success.

    Raises:
        Exception: If the deletion operation fails. Common reasons include:
                  - Filespace does not exist
                  - Insufficient permissions
                  - Server communication error
                  - Active operations on the filespace

    Notes:
        - This operation is IRREVERSIBLE - all data in the filespace is permanently deleted
        - Deletes from ALL repositories (backup and archive)
        - The filespace must exist or an error will be raised
        - Any active backup/restore operations on the filespace should be completed first
        - After deletion, the filespace name can be reused by calling register_filespace()
        - Consider using object-level deletion if you only need to remove specific objects

    Warning:
        This is a destructive operation. Ensure you have proper authorization and
        backups before deleting a filespace. There is no undo or recovery mechanism.

    Example:
        >>> # Delete a filespace and all its objects
        >>> delete_filespace(handle, "/backup/old_data")
        >>> # All objects in /backup/old_data are now permanently deleted

        >>> # The filespace name can be reused
        >>> register_filespace(handle, "/backup/old_data")

    See Also:
        - register_filespace(): Register a new filespace
        - update_filespace(): Update filespace attributes
        - DeleteObjectOperation: Delete individual objects without removing the filespace
        - dsmDeleteFS() in dsmapifp.py: Underlying C API function
    """
    _logger.info(
        "Deleting filespace",
        extra={
            'event_type': 'c_api.filespace.delete.started',
            'operation': 'delete_filespace',
            'filespace': fs_name,
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    # Unwrap the handle if it's wrapped (converts to raw C pointer)
    handle = _unwrap(handle)

    _logger.debug(
        "Calling dsmDeleteFS",
        extra={
            'event_type': 'c_api.dsmDeleteFS.call',
            'handle': handle,
            'filespace': fs_name,
            'repository': 'DSM_REPOS_ALL',
            'session_handle': session_handle,
            'object_key': object_key
        }
    )

    try:
        # Call the C API function to delete the filespace
        # Parameters: handle, filespace name (UTF-8), repository selector
        # DSM_REPOS_ALL means delete from both backup and archive repositories
        rc = lib.dsmDeleteFS(handle, fs_name.encode("utf-8"), DSM_REPOS_ALL)

        # Check return code and raise exception if operation failed
        check_rc(handle, rc, "dsmDeleteFS")

        _logger.info(
            "Filespace deletion completed",
            extra={
                'event_type': 'c_api.filespace.delete.completed',
                'filespace': fs_name,
                'rc': rc,
                'session_handle': session_handle,
                'object_key': object_key
            }
        )
    except Exception as e:
        _logger.error(
            "Filespace deletion failed",
            extra={
                'event_type': 'c_api.filespace.delete.failed',
                'filespace': fs_name,
                'error': str(e),
                'error_type': type(e).__name__,
                'session_handle': session_handle,
                'object_key': object_key
            },
            exc_info=True
        )
        raise
