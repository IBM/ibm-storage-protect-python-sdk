"""
IBM Storage Protect Client API - Control Management Operations

This module provides high-level Python interfaces for IBM Storage Protect control
management operations. Control operations manage metadata and object properties
without transferring actual data content, including filespace management and
object manipulation.

Control operations are distinct from data operations (backup/restore) which handle
actual file content transfer. This module acts as a bridge between user-facing
data models and the low-level C API control path operations.

Key Classes:
------------
**ControlClient**: Main control client for filespace and object management
    - Filespace Operations: Register, update, and delete filespaces
    - Object Operations: Delete, rename, and update backed-up objects

Filespace Management:
---------------------
Filespaces are logical containers that organize backed-up objects, typically
representing filesystems, application namespaces, or data sources.

1. **register_filespace()**: Create a new filespace on the server
   - Required before backing up objects to the filespace
   - Idempotent operation (safe to call multiple times)

2. **update_filespace()**: Modify filespace attributes
   - Update capacity, occupancy, type, and descriptive information
   - Selective updates using optional parameters

3. **delete_filespace()**: Remove filespace and all its objects
   - Irreversible operation affecting all repositories
   - Deletes all objects within the filespace

Object Management:
------------------
Object operations manipulate backed-up objects without data transfer:

1. **delete_by_name()**: Delete object using filespace and key path
   - Wrapped in transaction for atomicity
   - Supports copy group specification

2. **delete_by_id()**: Delete object using unique object ID
   - More efficient for known object IDs
   - Wrapped in transaction for atomicity

3. **rename()**: Change object's high-level and/or low-level names
   - Supports merge option to combine with existing objects
   - Wrapped in transaction for atomicity

4. **update()**: Modify object attributes (owner, management class)
   - Selective updates using optional parameters
   - No explicit transaction required

Architecture:
-------------
This module follows a layered architecture:

1. **User Layer**: Pydantic data models (SPFilespace*, SPObject*)
   - Type validation and serialization
   - User-friendly field names and aliases

2. **Control Layer** (this module): ControlClient
   - Session management and handle validation
   - Logging and metrics collection
   - Error handling and exception translation

3. **C API Layer**: Low-level C API wrappers
   - Direct C API function calls
   - Structure initialization and memory management
   - Transaction management for atomic operations

Error Handling:
---------------
All operations may raise:
- **TSMError**: Base exception for TSM-specific errors
  - Contains error code, message, and context
  - Provides to_dict() for structured error information
- **FsRegisterError**: Filespace registration failures
- **ObjectMgmtError**: Object management operation failures
- **TSMTransactionError**: Transaction commit/rollback failures

Exceptions include detailed context for debugging and are logged with
structured information including session handles and object keys.

Logging:
--------
All operations use structured logging with consistent event types:
- Event lifecycle: started -> c_api_call -> completed/failed/error
- Metrics: duration_ms for performance tracking
- Context: session_handle, object_key, operation parameters
- Error details: error codes, messages, and stack traces

Thread Safety:
--------------
ControlClient is NOT thread-safe. Each instance requires exclusive access
to its session handle. Concurrent operations with the same handle will cause
undefined behavior and potential data corruption.

For multi-threaded applications, create separate client instances with
separate sessions for each thread.

Performance Considerations:
---------------------------
- Filespace operations are lightweight metadata operations
- Object operations involve server communication but no data transfer
- Transaction overhead is minimal for single operations
- Batch operations should use appropriate grouping strategies

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Filespace Management", "Object Management", "Transaction Management"

Example Usage:
--------------
    # Initialize client with session
    client = ControlClient(session)

    # Register a filespace
    result = client.register_filespace(
        FilespaceRegisterRequest(Filespace="/backup/data")
    )

    # Update filespace metrics
    result = client.update_filespace(
        FilespaceUpdateRequest(
            Filespace="/backup/data",
            Occupancy=5000000000,  # 5GB
            Capacity=10000000000   # 10GB
        )
    )

    # Delete an object
    result = client.delete_by_name(
        ObjectDeleteRequest(
            Filespace="/backup/data",
            Key="/path/to/file.txt"
        )
    )

    # Rename an object
    result = client.rename(
        ObjectRenameRequest(
            Filespace="/backup/data",
            Key="/old/path.txt",
            NewKey="/new/path.txt"
        )
    )

    # Update object attributes
    result = client.update(
        ObjectUpdateRequest(
            Filespace="/backup/data",
            Key="/path/file.txt",
            Owner="admin",
            ManagementClass="STANDARD"
        )
    )

    # Delete filespace and all objects
    result = client.delete_filespace(
        SPFilespaceDelete(Filespace="/backup/data")
    )

See Also:
---------
- c_api_bridge.wrappers.filespace: Low-level filespace operations
- c_api_bridge.wrappers.object: Low-level object operations
- data_models.filespace: Filespace data model definitions
- data_models.object: Object management data model definitions
- session: Session lifecycle management
"""
# pylint: disable=too-many-lines

import time

from ibm_storage_protect.c_api_bridge.wrappers.filespace import (
    delete_filespace as _delete_filespace,
    register_filespace as _register_filespace,
    update_filespace as _update_filespace,
)
from ibm_storage_protect.c_api_bridge.wrappers.object import (
    DeleteObjectOperation,
    RenameObjectOperation,
    UpdateObjectOperation,
)
from ibm_storage_protect.c_api_bridge.wrappers.helper import extract_enum_value
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.filespace import (
    FilespaceDeleteRequest,
    FilespaceDeleteInternal,
    FilespaceDeleteResult,
    FilespaceRegisterRequest,
    FilespaceRegisterInternal,
    FilespaceRegisterResult,
    FilespaceUpdateRequest,
    FilespaceUpdateInternal,
    FilespaceUpdateResult,
)
from ibm_storage_protect.data_models.object import (
    ObjectDeleteRequest,
    ObjectDeleteByIdRequest,
    ObjectDeleteByIdInternal,
    ObjectDeleteByIdResult,
    ObjectDeleteInternal,
    ObjectDeleteResult,
    ObjectRenameRequest,
    ObjectRenameInternal,
    ObjectRenameResult,
    ObjectUpdateRequest,
    ObjectUpdateInternal,
    ObjectUpdateResult,
)
from ibm_storage_protect.enums import ObjType
from ibm_storage_protect.errors.exceptions import (
    TSMError,
)
from ibm_storage_protect.logger import get_logger, set_log_context


_logger = get_logger(__name__)


class ControlClient(BaseClient):
    """
    IBM Storage Protect Control Client for filespace and object management.

    This class provides high-level interfaces for control path operations that
    manage metadata and object properties without transferring data content.
    It bridges user-facing Pydantic models and low-level C API operations.

    The client handles:
    - Session management and handle validation
    - Request/response model transformation
    - Structured logging with metrics collection
    - Error handling and exception translation
    - Performance tracking (duration_ms)

    Attributes:
        _session: ClientSession instance providing the session handle

    Methods:
        Filespace Operations:
            - register_filespace(): Create a new filespace
            - update_filespace(): Modify filespace attributes
            - delete_filespace(): Remove filespace and all objects

        Object Operations:
            - delete_by_name(): Delete object using filespace and key
            - delete_by_id(): Delete object using object ID
            - rename(): Change object names
            - update(): Modify object attributes

    Thread Safety:
        NOT thread-safe. Each instance requires exclusive session access.
        Create separate instances for concurrent operations.

    Example:
        >>> client = ControlClient()
        >>> client._session = session
        >>>
        >>> # Register filespace
        >>> result = client.register_filespace(
        ...     FilespaceRegisterRequest(Filespace="/backup/data")
        ... )
        >>>
        >>> # Delete object
        >>> result = client.delete_by_name(
        ...     ObjectDeleteRequest(Filespace="/backup/data", Key="/file.txt")
        ... )

    See Also:
        - c_api_bridge.c_api_controlpath: Low-level C API wrappers
        - data_models.filespace: Filespace data models
        - data_models.object: Object management data
          models
    """

    def register_filespace(
        self, register_request: FilespaceRegisterRequest
    ) -> FilespaceRegisterResult:
        """
        Register a new filespace with the IBM Storage Protect server.

        Creates a new filespace on the server, which is required before backing up
        any objects. A filespace is a logical container that organizes objects,
        typically representing a filesystem, application namespace, or data source.

        This operation is idempotent - if the filespace already exists, it returns
        successfully without error. This allows safe repeated calls.

        C API Flow:
        -----------
        1. Validate request and extract session handle
        2. Create internal request with handle
        3. Call _register_filespace() from c_api_controlpath
        4. Track metrics and log structured events
        5. Return result model or raise exception

        Args:
            register_request: FilespaceRegisterRequest model containing:
                - Filespace: Name of the filespace to register

        Returns:
            FilespaceRegisterRequestResult containing:
                - Status: "success" on successful registration
                - Filespace: Name of the registered filespace

        Raises:
            TSMError: If registration fails (except already-registered case)
            Exception: For unexpected errors during the operation

        Logging:
            - Event: control.filespace.register.started/completed/failed/error
            - Metrics: duration_ms
            - Context: session_handle, object_key (filespace name)

        Notes:
            - Filespace must be registered before backup operations
            - Initial capacity/occupancy are placeholders; update with update_filespace()
            - Filespace names are case-sensitive on most platforms
            - Safe to call multiple times (idempotent)

        Example:
            >>> req = FilespaceRegisterRequest(Filespace="/backup/database")
            >>> result = client.register_filespace(req)
            >>> print(f"status: {result.status}, filespace: {result.filespace}")

        See Also:
            - update_filespace(): Update filespace attributes
            - delete_filespace(): Remove a filespace
            - c_api_bridge.wrappers.filespace.register_filespace()
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = register_request.filespace
        start_time = time.perf_counter()
        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Filespace registration started",
            extra={
                'event_type': 'control.filespace.register.started',
                'operation': 'register_filespace',
                'filespace': register_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'status': 'started'
            }
        )

        internal_request = FilespaceRegisterInternal(
            handle=self._require_handle(),
            filespace=register_request.filespace,
        )

        _logger.debug(
            "Calling C API register_filespace",
            extra={
                'event_type': 'control.filespace.register.c_api_call',
                'operation': 'register_filespace',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'handle': internal_request.handle,
                    'filespace': internal_request.filespace
                }
            }
        )

        try:
            _register_filespace(
                handle=internal_request.handle,
                filespace=internal_request.filespace,
                session_handle=session_handle,
                object_key=object_key
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Filespace registration completed",
                extra={
                    'event_type': 'control.filespace.register.completed',
                    'operation': 'register_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return FilespaceRegisterResult(
                Status="success",
                Filespace=internal_request.filespace,
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Filespace registration failed",
                extra={
                    'event_type': 'control.filespace.register.failed',
                    'operation': 'register_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during filespace registration",
                extra={
                    'event_type': 'control.filespace.register.error',
                    'operation': 'register_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def update_filespace(self, update_request: FilespaceUpdateRequest) -> FilespaceUpdateResult:
        """
        Update attributes of an existing filespace on the IBM Storage Protect server.

        Allows selective updates to filespace metadata without affecting backed-up
        objects. You can update capacity, occupancy, type, and descriptive information
        independently or in combination. Only provided fields are updated.

        C API Flow:
        -----------
        1. Validate request and extract session handle
        2. Create internal request with optional fields
        3. Call _update_filespace() from c_api_controlpath
        4. Track metrics and log structured events
        5. Return result model or raise exception

        Args:
            update_request: FilespaceUpdateRequest model containing:
                - filespace: Name of the filespace to update (required)
                - fs_type: Optional filespace type string
                - fs_info: Optional descriptive information
                - occupancy: Optional current usage in bytes
                - capacity: Optional total capacity in bytes

        Returns:
            FilespaceUpdateResult containing:
                - status: "success" on successful update
                - filespace: Name of the updated filespace

        Raises:
            TSMError: If update operation fails
            Exception: For unexpected errors during the operation

        Logging:
            - Event: control.filespace.update.started/completed/failed/error
            - Metrics: duration_ms
            - Context: session_handle, object_key, occupancy, capacity, fs_type

        Notes:
            - Filespace must already be registered
            - Only provided parameters are updated; others remain unchanged
            - Updates are atomic - all specified fields update or none do
            - Does not affect backed-up objects in the filespace

        Example:
            >>> req = FilespaceUpdateRequest(
            ...     filespace="/backup/data",
            ...     occupancy=5000000000,  # 5GB used
            ...     capacity=10000000000,  # 10GB total
            ...     fs_info="Production database backup"
            ... )
            >>> result = client.update_filespace(req)

        See Also:
            - register_filespace(): Register a new filespace
            - delete_filespace(): Remove a filespace
            - c_api_bridge.wrappers.filespace.update_filespace()
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = update_request.filespace
        start_time = time.perf_counter()
        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Filespace update started",
            extra={
                'event_type': 'control.filespace.update.started',
                'operation': 'update_filespace',
                'filespace': update_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'occupancy': update_request.occupancy,
                    'capacity': update_request.capacity,
                    'fs_type': update_request.fs_type
                },
                'status': 'started'
            }
        )

        internal_request = FilespaceUpdateInternal(
            handle=self._require_handle(),
            filespace=update_request.filespace,
            fs_type=update_request.fs_type,
            fs_info=update_request.fs_info,
            occupancy=update_request.occupancy,
            capacity=update_request.capacity,
        )

        _logger.debug(
            "Calling C API update_filespace",
            extra={
                'event_type': 'control.filespace.update.c_api_call',
                'operation': 'update_filespace',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'handle': internal_request.handle,
                    'filespace': internal_request.filespace,
                    'occupancy': internal_request.occupancy,
                    'capacity': internal_request.capacity
                }
            }
        )

        try:
            _update_filespace(
                handle=internal_request.handle,
                filespace=internal_request.filespace,
                fs_info=internal_request.fs_info,
                occupancy=internal_request.occupancy,
                capacity=internal_request.capacity,
                fs_type=internal_request.fs_type,
                session_handle=session_handle,
                object_key=object_key
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Filespace update completed",
                extra={
                    'event_type': 'control.filespace.update.completed',
                    'operation': 'update_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return FilespaceUpdateResult(
                Status="success",
                Filespace=internal_request.filespace,
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Filespace update failed",
                extra={
                    'event_type': 'control.filespace.update.failed',
                    'operation': 'update_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during filespace update",
                extra={
                    'event_type': 'control.filespace.update.error',
                    'operation': 'update_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def delete_filespace(self, delete_request: FilespaceDeleteRequest) -> FilespaceDeleteResult:
        """
        Delete a filespace and ALL its objects from the IBM Storage Protect server.

        WARNING: This operation is IRREVERSIBLE and permanently removes the filespace
        and ALL objects it contains from both backup and archive repositories. There
        is no way to recover the data after this operation completes successfully.

        C API Flow:
        -----------
        1. Validate request and extract session handle
        2. Create internal request with handle
        3. Call _delete_filespace() from c_api_controlpath
        4. Track metrics and log structured events
        5. Return result model or raise exception

        Args:
            delete_request: FilespaceDeleteRequest model containing:
                - filespace: Name of the filespace to delete

        Returns:
            FilespaceDeleteResult containing:
                - status: "success" on successful deletion
                - filespace: Name of the deleted filespace

        Raises:
            TSMError: If deletion fails (filespace doesn't exist, insufficient permissions, etc.)
            Exception: For unexpected errors during the operation

        Logging:
            - Event: control.filespace.delete.started/completed/failed/error
            - Metrics: duration_ms
            - Context: session_handle, object_key (filespace name)

        Notes:
            - IRREVERSIBLE operation - all data permanently deleted
            - Deletes from ALL repositories (backup and archive)
            - Filespace must exist or an error will be raised
            - Complete any active operations before deletion
            - Filespace name can be reused after deletion

        Warning:
            This is a destructive operation. Ensure proper authorization and
            backups before deleting a filespace. No undo or recovery mechanism exists.

        Example:
            >>> req = FilespaceDeleteRequest(filespace="/backup/old_data")
            >>> result = client.delete_filespace(req)
            >>> # All objects in /backup/old_data are now permanently deleted

        See Also:
            - register_filespace(): Register a new filespace
            - delete_by_name(): Delete individual objects
            - c_api_bridge.wrappers.filespace.delete_filespace()
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = delete_request.filespace
        start_time = time.perf_counter()
        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Filespace deletion started",
            extra={
                'event_type': 'control.filespace.delete.started',
                'operation': 'delete_filespace',
                'filespace': delete_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'status': 'started'
            }
        )

        internal_request = FilespaceDeleteInternal(
            handle=self._require_handle(),
            filespace=delete_request.filespace,
        )

        _logger.debug(
            "Calling C API delete_filespace",
            extra={
                'event_type': 'control.filespace.delete.c_api_call',
                'operation': 'delete_filespace',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'handle': internal_request.handle,
                    'filespace': internal_request.filespace
                }
            }
        )

        try:
            _delete_filespace(
                handle=internal_request.handle,
                fs_name=internal_request.filespace,
                session_handle=session_handle,
                object_key=object_key
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Filespace deletion completed",
                extra={
                    'event_type': 'control.filespace.delete.completed',
                    'operation': 'delete_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return FilespaceDeleteResult(
                Status="success",
                Filespace=internal_request.filespace,
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Filespace deletion failed",
                extra={
                    'event_type': 'control.filespace.delete.failed',
                    'operation': 'delete_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during filespace deletion",
                extra={
                    'event_type': 'control.filespace.delete.error',
                    'operation': 'delete_filespace',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def delete_by_name(self, delete_request: ObjectDeleteRequest) -> ObjectDeleteResult:
        """
        Delete a backed-up object using its filespace and key (path).

        Deletes an object from the server using its logical name components.
        The operation is wrapped in a transaction for atomicity - either the
        deletion completes fully or is rolled back entirely.

        C API Flow:
        -----------
        1. Validate request and extract session/object identifiers
        2. Convert ObjType enum to integer value
        3. Create DeleteObjectOperation instance
        4. Begin transaction, delete object, commit/abort
        5. Track metrics and log structured events
        6. Return result model or raise exception

        Args:
            delete_request: ObjectDeleteRequest model containing:
                - filespace: Name of the filespace containing the object
                - key: Full path to the object (e.g., "/path/to/file.txt")
                - copy_group: Copy group number (default: 1)
                - obj_type: Object type (default: FILE)

        Returns:
            ObjectDeleteResult containing:
                - status: "success" on successful deletion
                - filespace: Name of the filespace
                - key: Path of the deleted object

        Raises:
            TSMError: If deletion fails
            ObjectMgmtError: For object management specific errors
            TSMTransactionError: If transaction commit/rollback fails
            Exception: For unexpected errors during the operation

        Logging:
            - Event: control.object.delete_by_name.started/completed/failed/error
            - Metrics: duration_ms
            - Context: session_handle, object_key, filespace, key, copy_group, obj_type

        Notes:
            - Operation is wrapped in a transaction for atomicity
            - Transaction automatically aborted on errors
            - Object must exist or an error will be raised
            - Deletion is permanent and cannot be undone

        Example:
            >>> req = ObjectDeleteRequest(
            ...     filespace="/backup/data",
            ...     key="/documents/report.pdf",
            ...     copy_group=1
            ... )
            >>> result = client.delete_by_name(req)

        See Also:
            - delete_by_id(): Delete using object ID
            - delete_filespace(): Delete entire filespace
            - c_api_bridge.wrappers.object.DeleteObjectOperation
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = delete_request.key
        start_time = time.perf_counter()

        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Object deletion by name started",
            extra={
                'event_type': 'control.object.delete_by_name.started',
                'operation': 'delete_by_name',
                'filespace': delete_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'key': delete_request.key,
                    'copy_group': delete_request.copy_group,
                    'obj_type': str(delete_request.obj_type) if delete_request.obj_type else None
                },
                'status': 'started'
            }
        )

        obj_type_value = extract_enum_value(delete_request.obj_type, ObjType, ObjType.FILE)

        internal_request = ObjectDeleteInternal(
            handle=self._require_handle(),
            filespace=delete_request.filespace,
            key=delete_request.key,
            copy_group=delete_request.copy_group,
            obj_type=obj_type_value,
        )

        _logger.debug(
            "Calling C API delete_by_name",
            extra={
                'event_type': 'control.object.delete_by_name.c_api_call',
                'operation': 'delete_by_name',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'handle': internal_request.handle,
                    'filespace': internal_request.filespace,
                    'key': internal_request.key,
                    'obj_type': internal_request.obj_type
                }
            }
        )

        try:
            operation = DeleteObjectOperation(
                handle=internal_request.handle,
                session_handle=session_handle,
                object_key=object_key
            )
            operation.delete_by_name(
                filespace=internal_request.filespace,
                key=internal_request.key,
                copy_group=internal_request.copy_group,
                obj_type=internal_request.obj_type,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Object deletion by name completed",
                extra={
                    'event_type': 'control.object.delete_by_name.completed',
                    'operation': 'delete_by_name',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'context': {
                        'key': internal_request.key
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return ObjectDeleteResult(
                Status="success",
                Filespace=internal_request.filespace,
                Key=internal_request.key,
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Object deletion by name failed",
                extra={
                    'event_type': 'control.object.delete_by_name.failed',
                    'operation': 'delete_by_name',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'context': {
                        'key': internal_request.key
                    },
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during object deletion by name",
                extra={
                    'event_type': 'control.object.delete_by_name.error',
                    'operation': 'delete_by_name',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'context': {
                        'key': internal_request.key
                    },
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def delete_by_id(self, delete_request: ObjectDeleteByIdRequest) -> ObjectDeleteByIdResult:
        """
        Delete a backed-up object using its unique object ID.

        More efficient than delete_by_name when the object ID is known. The operation
        is wrapped in a transaction for atomicity - either the deletion completes
        fully or is rolled back entirely.

        C API Flow:
        -----------
        1. Validate request and create object key for logging
        2. Create DeleteObjectOperation instance
        3. Begin transaction, delete by ID, commit/abort
        4. Track metrics and log structured events
        5. Return result model or raise exception

        Args:
            delete_request: ObjectDeleteByIdRequest model containing:
                - obj_id_hi: High 32 bits of the object ID
                - obj_id_lo: Low 32 bits of the object ID

        Returns:
            ObjectDeleteByIdResult containing:
                - status: "success" on successful deletion
                - obj_id_hi: High 32 bits of deleted object's ID
                - obj_id_lo: Low 32 bits of deleted object's ID

        Raises:
            TSMError: If deletion fails
            ObjectMgmtError: For object management specific errors
            TSMTransactionError: If transaction commit/rollback fails
            Exception: For unexpected errors during the operation

        Logging:
            - Event: control.object.delete_by_id.started/completed/failed/error
            - Metrics: duration_ms
            - Context: session_handle, object_key, obj_id_hi, obj_id_lo

        Notes:
            - More efficient than delete_by_name for known IDs
            - Operation is wrapped in a transaction for atomicity
            - Transaction automatically aborted on errors
            - Object ID must be valid or an error will be raised
            - Deletion is permanent and cannot be undone

        Example:
            >>> req = ObjectDeleteByIdRequest(
            ...     obj_id_hi=12345,
            ...     obj_id_lo=67890
            ... )
            >>> result = client.delete_by_id(req)

        See Also:
            - delete_by_name(): Delete using filespace and key
            - c_api_bridge.wrappers.object.DeleteObjectOperation
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = f"obj_{delete_request.obj_id_hi}_{delete_request.obj_id_lo}"
        start_time = time.perf_counter()

        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Object deletion by ID started",
            extra={
                'event_type': 'control.object.delete_by_id.started',
                'operation': 'delete_by_id',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'obj_id_hi': delete_request.obj_id_hi,
                    'obj_id_lo': delete_request.obj_id_lo
                },
                'status': 'started'
            }
        )

        internal_request = ObjectDeleteByIdInternal(
            handle=self._require_handle(),
            obj_id_hi=delete_request.obj_id_hi,
            obj_id_lo=delete_request.obj_id_lo,
        )

        _logger.debug(
            "Calling C API delete_by_id",
            extra={
                'event_type': 'control.object.delete_by_id.c_api_call',
                'operation': 'delete_by_id',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'handle': internal_request.handle,
                    'obj_id_hi': internal_request.obj_id_hi,
                    'obj_id_lo': internal_request.obj_id_lo
                }
            }
        )

        try:
            operation = DeleteObjectOperation(
                handle=internal_request.handle,
                session_handle=session_handle,
                object_key=object_key
            )
            operation.delete_by_id(
                obj_id_hi=internal_request.obj_id_hi,
                obj_id_lo=internal_request.obj_id_lo,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Object deletion by ID completed",
                extra={
                    'event_type': 'control.object.delete_by_id.completed',
                    'operation': 'delete_by_id',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'context': {
                        'obj_id_hi': internal_request.obj_id_hi,
                        'obj_id_lo': internal_request.obj_id_lo
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return ObjectDeleteByIdResult(
                Status="success",
                ObjIdHi=internal_request.obj_id_hi,
                ObjIdLo=internal_request.obj_id_lo,
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Object deletion by ID failed",
                extra={
                    'event_type': 'control.object.delete_by_id.failed',
                    'operation': 'delete_by_id',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'context': {
                        'obj_id_hi': internal_request.obj_id_hi,
                        'obj_id_lo': internal_request.obj_id_lo
                    },
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during object deletion by ID",
                extra={
                    'event_type': 'control.object.delete_by_id.error',
                    'operation': 'delete_by_id',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'context': {
                        'obj_id_hi': internal_request.obj_id_hi,
                        'obj_id_lo': internal_request.obj_id_lo
                    },
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def rename(self, rename_request: ObjectRenameRequest) -> ObjectRenameResult:
        """
        Rename a backed-up object by changing its high-level and/or low-level names.

        Changes an object's path without transferring data. The operation is wrapped
        in a transaction for atomicity - either the rename completes fully or is
        rolled back entirely. Supports merge option to combine with existing objects.

        C API Flow:
        -----------
        1. Validate request and extract session/object identifiers
        2. Convert ObjType enum to integer value
        3. Create RenameObjectOperation instance
        4. Begin transaction, rename object, commit/abort
        5. Track metrics and log structured events
        6. Return result model or raise exception

        Args:
            rename_request: ObjectRenameRequest model containing:
                - filespace: Name of the filespace containing the object
                - key: Current full path to the object
                - new_key: New full path for the object
                - merge: If True, merge with existing object at new_key (default: False)
                - obj_type: Object type (default: FILE)

        Returns:
            ObjectRenameResult containing:
                - status: "success" on successful rename
                - filespace: Name of the filespace
                - old_key: Original path of the object
                - new_key: New path of the object

        Raises:
            TSMError: If rename fails
            ObjectMgmtError: For object management specific errors
            TSMTransactionError: If transaction commit/rollback fails
            Exception: For unexpected errors during the operation

        Logging:
            - Event: control.object.rename.started/completed/failed/error
            - Metrics: duration_ms
            - Context: session_handle, object_key, filespace, old_key, new_key, merge

        Notes:
            - Operation is wrapped in a transaction for atomicity
            - Transaction automatically aborted on errors
            - Merge option combines with existing object at destination
            - Original object must exist or an error will be raised
            - Rename is atomic - either completes fully or rolls back

        Example:
            >>> req = ObjectRenameRequest(
            ...     filespace="/backup/data",
            ...     key="/old/path.txt",
            ...     new_key="/new/path.txt",
            ...     merge=False
            ... )
            >>> result = client.rename(req)

        See Also:
            - update(): Modify object attributes
            - c_api_bridge.wrappers.object.RenameObjectOperation
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = rename_request.key
        start_time = time.perf_counter()

        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Object rename started",
            extra={
                'event_type': 'control.object.rename.started',
                'operation': 'rename',
                'filespace': rename_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'old_key': rename_request.key,
                    'new_key': rename_request.new_key,
                    'merge': rename_request.merge,
                    'obj_type': str(rename_request.obj_type) if rename_request.obj_type else None
                },
                'status': 'started'
            }
        )

        obj_type_value = extract_enum_value(rename_request.obj_type, ObjType, ObjType.FILE)

        internal_request = ObjectRenameInternal(
            handle=self._require_handle(),
            filespace=rename_request.filespace,
            key=rename_request.key,
            new_key=rename_request.new_key,
            merge=rename_request.merge,
            obj_type=obj_type_value,
        )

        _logger.debug(
            "Calling C API rename",
            extra={
                'event_type': 'control.object.rename.c_api_call',
                'operation': 'rename',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'handle': internal_request.handle,
                    'filespace': internal_request.filespace,
                    'old_key': internal_request.key,
                    'new_key': internal_request.new_key,
                    'merge': internal_request.merge
                }
            }
        )

        try:
            operation = RenameObjectOperation(
                handle=internal_request.handle,
                session_handle=session_handle,
                object_key=object_key
            )
            operation.rename(
                filespace=internal_request.filespace,
                key=internal_request.key,
                new_key=internal_request.new_key,
                merge=internal_request.merge,
                obj_type=internal_request.obj_type,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Object rename completed",
                extra={
                    'event_type': 'control.object.rename.completed',
                    'operation': 'rename',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'context': {
                        'old_key': internal_request.key,
                        'new_key': internal_request.new_key
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return ObjectRenameResult(
                Status="success",
                Filespace=internal_request.filespace,
                OldKey=internal_request.key,
                NewKey=internal_request.new_key,
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Object rename failed",
                extra={
                    'event_type': 'control.object.rename.failed',
                    'operation': 'rename',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'context': {
                        'old_key': internal_request.key,
                        'new_key': internal_request.new_key
                    },
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during object rename",
                extra={
                    'event_type': 'control.object.rename.error',
                    'operation': 'rename',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'context': {
                        'old_key': internal_request.key,
                        'new_key': internal_request.new_key
                    },
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def update(self, update_request: ObjectUpdateRequest) -> ObjectUpdateResult:
        """
        Update attributes of a backed-up object (owner and/or management class).

        Modifies an object's metadata without transferring data. Allows selective
        updates - only provided fields are changed. Does not require explicit
        transaction management (handled internally by C API).

        C API Flow:
        -----------
        1. Validate request and extract session/object identifiers
        2. Convert ObjType enum to integer value
        3. Create UpdateObjectOperation instance
        4. Call update with optional owner/management_class
        5. Track metrics and log structured events
        6. Return result model or raise exception

        Args:
            update_request: ObjectUpdateRequest model containing:
                - filespace: Name of the filespace containing the object
                - key: Full path to the object
                - owner: Optional new owner name
                - management_class: Optional new management class name
                - obj_type: Object type (default: FILE)

        Returns:
            ObjectUpdateResult containing:
                - status: "success" on successful update
                - filespace: Name of the filespace
                - key: Path of the updated object

        Raises:
            TSMError: If update fails
            ObjectMgmtError: For object management specific errors
            Exception: For unexpected errors during the operation

        Logging:
            - Event: control.object.update.started/completed/failed/error
            - Metrics: duration_ms
            - Context: session_handle, object_key, filespace, key, owner, management_class

        Notes:
            - Only provided parameters are updated; others remain unchanged
            - Does not require explicit transaction (handled by C API)
            - Object must exist or an error will be raised
            - Updates are atomic - all specified fields update or none do

        Example:
            >>> req = ObjectUpdateRequest(
            ...     filespace="/backup/data",
            ...     key="/path/file.txt",
            ...     owner="admin",
            ...     management_class="STANDARD"
            ... )
            >>> result = client.update(req)

        See Also:
            - rename(): Change object names
            - c_api_bridge.wrappers.object.UpdateObjectOperation
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = update_request.key
        start_time = time.perf_counter()
        set_log_context(session_handle=session_handle, object_key=object_key)
        _logger.info(
            "Object update started",
            extra={
                'event_type': 'control.object.update.started',
                'operation': 'update',
                'filespace': update_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'key': update_request.key,
                    'owner': update_request.owner,
                    'management_class': update_request.management_class,
                    'obj_type': str(update_request.obj_type) if update_request.obj_type else None
                },
                'status': 'started'
            }
        )

        obj_type_value = extract_enum_value(update_request.obj_type, ObjType, ObjType.FILE)

        internal_request = ObjectUpdateInternal(
            handle=self._require_handle(),
            filespace=update_request.filespace,
            key=update_request.key,
            owner=update_request.owner,
            management_class=update_request.management_class,
            obj_type=obj_type_value,
        )

        _logger.debug(
            "Calling C API update",
            extra={
                'event_type': 'control.object.update.c_api_call',
                'operation': 'update',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'handle': internal_request.handle,
                    'filespace': internal_request.filespace,
                    'key': internal_request.key,
                    'owner': internal_request.owner,
                    'management_class': internal_request.management_class
                }
            }
        )

        try:
            operation = UpdateObjectOperation(
                handle=internal_request.handle,
                session_handle=session_handle,
                object_key=object_key
            )
            operation.update(
                filespace=internal_request.filespace,
                key=internal_request.key,
                owner=internal_request.owner or "",
                management_class=internal_request.management_class or "",
                obj_type=internal_request.obj_type,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Object update completed",
                extra={
                    'event_type': 'control.object.update.completed',
                    'operation': 'update',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'context': {
                        'key': internal_request.key
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return ObjectUpdateResult(
                Status="success",
                Filespace=internal_request.filespace,
                Key=internal_request.key,
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Object update failed",
                extra={
                    'event_type': 'control.object.update.failed',
                    'operation': 'update',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'context': {
                        'key': internal_request.key
                    },
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during object update",
                extra={
                    'event_type': 'control.object.update.error',
                    'operation': 'update',
                    'filespace': internal_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'context': {
                        'key': internal_request.key
                    },
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def __enter__(self):
        """
        Context manager entry.

        Returns:
            self: The client instance for use in with statements
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """


    def __repr__(self) -> str:
        """
        String representation of the client.

        Returns:
            str: String representation including session information
        """
        return f"ControlClient(session={self._session})"
