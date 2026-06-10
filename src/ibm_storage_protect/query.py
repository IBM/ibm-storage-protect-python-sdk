"""
IBM Storage Protect SDK - Query Management Client

This module provides the high-level query client interface for the IBM Storage
Protect SDK. It wraps the low-level C API query operations with a clean,
Pythonic API using Pydantic models for request/response validation.

Key Responsibilities:
---------------------
1. **Request Validation**: Validate query parameters using Pydantic models
2. **API Translation**: Convert SDK models to C API parameters
3. **Response Transformation**: Convert C API results to SDK response models
4. **Error Handling**: Catch and transform exceptions with context
5. **Logging**: Provide structured logging for all query operations

Supported Query Operations:
----------------------------
- query_group_members(): Query group backup members by leader ID
- query_objects(): Query backed-up objects by key
- list_objects(): List objects with prefix filtering and pagination
- query_filespaces(): Query filespace information and statistics
- query_object(): Query a single object by exact key
- query_mgmt_classes(): Query management class definitions

Architecture:
-------------
This module sits between the user-facing API and the low-level C API layer:

User Code → QueryClient → C API Internal Layer → IBM SP Client API

The QueryClient class:
- Accepts Pydantic request models (GroupQueryRequest, BackupQueryRequest, etc.)
- Validates input parameters
- Converts to internal request models
- Calls C API functions via the c_api_bridge
- Transforms results to Pydantic response models
- Provides comprehensive error handling and logging

Thread Safety:
--------------
QueryClient instances are NOT thread-safe. Each thread should create its
own client instance with a separate session.

Performance Considerations:
---------------------------
- All queries include performance metrics (duration_ms) in logs
- Use max_keys parameter to limit result set size
- Leverage prefix filtering to reduce server-side processing
- Group queries require full filespace scans and may be slow

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf

Example Usage:
--------------
    from ibm_storage_protect import ClientSession, QueryClient
    from ibm_storage_protect.data_models.session import LoginCredentials
    from ibm_storage_protect.data_models.query import ListObjectsRequest

    session = ClientSession()
    credentials = LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD"))
    session.login(credentials)

    query_client = QueryClient(session)

    # List objects with prefix
    request = ListObjectsRequest(
        Filespace="/myfs",
        Prefix="/backup/2024",
        MaxKeys=100
    )
    result = query_client.list_objects(request)

    print(f"Found {result.key_count} objects")
    for obj in result.contents:
        print(f"  {obj['Key']}: {obj['Size']} bytes")

    # Query specific object
    from ibm_storage_protect.data_models.query import QueryObjectRequest
    obj_request = QueryObjectRequest(
        Filespace="/myfs",
        Key="/data/file.txt"
    )
    obj_result = query_client.query_object(obj_request)
    if obj_result:
        print(f"Object found: {obj_result.size} bytes")
"""
# pylint: disable=too-many-lines

import time
from typing import Optional

from ibm_storage_protect.c_api_bridge.wrappers.helper import extract_enum_value
from ibm_storage_protect.c_api_bridge.wrappers.query import (
    QueryOperation,
    execute_backup_query,
    execute_group_query,
)
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.query import (
    BackupQueryRequest,
    BackupQueryInternal,
    BackupQueryResult,
    GroupQueryRequest,
    GroupQueryInternal,
    GroupQueryResult,
    ListObjectsRequest,
    ListObjectsInternal,
    ListObjectsResult,
    ObjectMetadata,
    QueryFilespacesRequest,
    QueryFilespacesInternal,
    QueryFilespacesResult,
    QueryMgmtClassesRequest,
    QueryMgmtClassesInternal,
    QueryMgmtClassesResult,
    QueryObjectRequest,
    QueryObjectInternal,
    QueryObjectResult,
)
from ibm_storage_protect.enums import (
    ObjState,
    ObjType,
)
from ibm_storage_protect.errors.exceptions import (
    TSMError,
)
from ibm_storage_protect.logger import get_logger
from ibm_storage_protect.logger.context import (
    set_log_context,
)



# Module-level logger for structured logging
_logger = get_logger(__name__)


class QueryClient(BaseClient):
    """
    High-level query client for IBM Storage Protect operations.

    This class provides a clean, Pythonic interface for querying backed-up objects,
    filespaces, and management classes. It handles request validation, API translation,
    response transformation, and comprehensive error handling.

    The client uses Pydantic models for all requests and responses, ensuring type
    safety and automatic validation. All operations include structured logging with
    performance metrics.

    Attributes
    ----------
    _session : ClientSession
        The active session instance providing the connection handle.

    Methods
    -------
    query_group_members(query_request)
        Query all members of a group backup by leader ID.
    query_objects(query_request)
        Query backed-up objects by filespace and key.
    list_objects(list_request)
        List objects with prefix filtering and pagination.
    query_filespaces(query_request)
        Query filespace information and statistics.
    query_object(query_request)
        Query a single object by exact key.
    query_mgmt_classes(query_request)
        Query management class definitions and policies.

    Notes
    -----
    - All methods require an active session (must call login() first)
    - Methods raise TSMError subclasses on failure
    - All operations are logged with structured context
    - Performance metrics are included in log output

    Example
    -------
    >>> from ibm_storage_protect import ClientSession, QueryClient
    >>> from ibm_storage_protect.data_models.session import LoginCredentials
    >>> from ibm_storage_protect.data_models.query import ListObjectsRequest
    >>>
    >>> session = ClientSession()
    >>> credentials = LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD"))
    >>> session.login(credentials)
    >>>
    >>> # Use the query client
    >>> query_client = QueryClient(session)
    >>> request = ListObjectsRequest(Filespace="/myfs", Prefix="/backup")
    >>> result = query_client.list_objects(request)
    >>> print(f"Found {result.key_count} objects")
    """

    def query_group_members(self, query_request: GroupQueryRequest) -> GroupQueryResult:
        """
        Query all members of a group backup by group leader object ID.

        Retrieves all objects that belong to a specific group backup, identified
        by the group leader's object ID. Group backups allow multiple related
        objects to be backed up together as a logical unit.

        Parameters
        ----------
        query_request : GroupQueryRequest
            The group query request containing:
            - Filespace: Filespace name containing the group
            - GroupLeaderObjIdHi: High 32 bits of leader object ID
            - GroupLeaderObjIdLo: Low 32 bits of leader object ID
            - Owner: Optional owner name filter
            - ObjType: Optional object type filter

        Returns
        -------
        GroupQueryResult
            The query result containing:
            - objects: List of ObjectMetadata for all group members
            - total_objects: Total number of objects in the group

            The leader object is always first in the list, followed by members.

        Raises
        ------
        TSMError
            If the query operation fails (connection, authentication, etc.)
        QueryError
            If the query parameters are invalid or the group is not found

        Notes
        -----
        - This operation performs a full filespace scan to find group members
        - Performance scales with the number of objects in the filespace
        - Invalid group IDs (0-0) return an empty result
        - The operation includes performance metrics in logs

        Example
        -------
        >>> from ibm_storage_protect.data_models.query import GroupQueryRequest
        >>>
        >>> request = GroupQueryRequest(
        ...     Filespace="/myfs",
        ...     GroupLeaderObjIdHi=12345,
        ...     GroupLeaderObjIdLo=67890
        ... )
        >>> result = query_client.query_group_members(request)
        >>>
        >>> print(f"Group has {result.total_objects} objects")
        >>> leader = result.objects[0]
        >>> print(f"Leader: {leader.key}")
        >>> for member in result.objects[1:]:
        ...     print(f"  Member: {member.key}")
        """
        # Extract session context for logging and tracking
        session_handle = getattr(self._session, '_session_id', None)
        object_key = query_request.filespace
        start_time = time.perf_counter()

        # Set logging context for this operation
        set_log_context(session_handle=session_handle, object_key=object_key)

        # Log operation start with full context
        _logger.info(
            "Executing group query for filespace: %s", query_request.filespace,
            extra={
                'event_type': 'query.group.started',
                'operation': 'query.group',
                'filespace': query_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'owner': query_request.owner,
                    'obj_type': str(query_request.obj_type)
                },
                'status': 'started'
            }
        )

        try:
            # Extract enum value for object type, defaulting to FILE if not specified
            obj_type_value = extract_enum_value(query_request.obj_type, ObjType, ObjType.FILE)

            # Create internal request model for C API layer
            internal_request = GroupQueryInternal(
                handle=self._require_handle(),
                filespace=query_request.filespace,
                leader_hi=query_request.group_leader_obj_id_hi,
                leader_lo=query_request.group_leader_obj_id_lo,
                owner=query_request.owner or "",  # Empty string for no owner filter
                obj_type=obj_type_value,
            )

            # Execute the group query via C API layer
            results = execute_group_query(
                handle=internal_request.handle,
                filespace=internal_request.filespace,
                leader_hi=internal_request.leader_hi,
                leader_lo=internal_request.leader_lo,
                owner=internal_request.owner,
                obj_type=internal_request.obj_type,
                session_handle=session_handle,
                object_key=object_key,
            )

            # Calculate operation duration for performance tracking
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            # Log successful completion with metrics
            _logger.info(
                "Group query completed: %s objects found", len(results),
                extra={
                    'event_type': 'query.group.completed',
                    'operation': 'query.group',
                    'filespace': query_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'total_objects': len(results),
                        'duration_ms': duration_ms
                    }
                }
            )

            # Transform results to response model with full metadata
            return GroupQueryResult(
                Objects=[ObjectMetadata(**obj) for obj in results],
                TotalObjects=len(results),
            )

        except TSMError as e:
            # Handle TSM-specific errors with detailed logging
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Group query failed for filespace: %s", query_request.filespace,
                extra={
                    'event_type': 'query.group.failed',
                    'operation': 'query.group',
                    'filespace': query_request.filespace,
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
            # Handle unexpected errors with full context
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during group query: %s", query_request.filespace,
                extra={
                    'event_type': 'query.group.error',
                    'operation': 'query.group',
                    'filespace': query_request.filespace,
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

    def query_objects(self, query_request: BackupQueryRequest) -> BackupQueryResult:
        """
        Query backed-up objects by filespace and key pattern.

        Retrieves backed-up objects matching the specified filespace and key pattern.
        Supports filtering by object state (active/inactive), object type, point-in-time
        date, and owner.

        Parameters
        ----------
        query_request : BackupQueryRequest
            The backup query request containing:
            - Filespace: Filespace name to query
            - Key: Object key path or pattern
            - ObjState: Object state filter (default: ACTIVE)
            - ObjType: Object type filter (default: FILE)
            - PitDate: Point-in-time date for historical queries
            - Owner: Optional owner name filter

        Returns
        -------
        BackupQueryResult
            The query result containing:
            - objects: List of object dictionaries with metadata
            - total_objects: Total number of objects found

        Raises
        ------
        TSMError
            If the query operation fails
        QueryError
            If the query parameters are invalid

        Notes
        -----
        - Wildcards (*) are supported in the Key parameter
        - Point-in-time queries may be slower than active-only queries
        - Results are ordered by object path
        - Empty results return a list with zero objects

        Example
        -------
        >>> from ibm_storage_protect.data_models.query import BackupQueryRequest
        >>> from ibm_storage_protect.enums import ObjState
        >>>
        >>> request = BackupQueryRequest(
        ...     Filespace="/myfs",
        ...     Key="/data/*.txt",
        ...     ObjState=ObjState.ACTIVE
        ... )
        >>> result = query_client.query_objects(request)
        >>> print(f"Found {result.total_objects} objects")
        """
        # Extract session context for logging and tracking
        session_handle = getattr(self._session, '_session_id', None)
        object_key = query_request.filespace
        start_time = time.perf_counter()

        # Set logging context for this operation
        set_log_context(session_handle=session_handle, object_key=object_key)

        # Log operation start with full context
        _logger.info(
            "Executing backup query: %s", query_request.key,
            extra={
                'event_type': 'query.backup.started',
                'operation': 'query.backup',
                'filespace': query_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'owner': query_request.owner,
                    'pit_date': (
                        query_request.pit_date.isoformat()
                        if query_request.pit_date
                        else None
                    ),
                    'obj_state': str(query_request.obj_state),
                    'obj_type': str(query_request.obj_type)
                },
                'status': 'started'
            }
        )

        try:
            # Extract enum values with defaults
            obj_state_value = extract_enum_value(query_request.obj_state, ObjState, ObjState.ACTIVE)
            obj_type_value = extract_enum_value(query_request.obj_type, ObjType, ObjType.FILE)

            # Create internal request model for C API layer
            internal_request = BackupQueryInternal(
                handle=self._require_handle(),
                filespace=query_request.filespace,
                key=query_request.key,
                obj_state=obj_state_value,
                obj_type=obj_type_value,
                pit_date=query_request.pit_date,
                owner=query_request.owner or "",  # Empty string for no owner filter
            )

            # Execute the backup query via C API layer
            results = execute_backup_query(
                handle=internal_request.handle,
                filespace=internal_request.filespace,
                key=internal_request.key,
                obj_state=internal_request.obj_state,
                obj_type=internal_request.obj_type,
                pit_date=internal_request.pit_date,
                owner=internal_request.owner,
                session_handle=session_handle,
                object_key=object_key,
            )

            # Calculate operation duration for performance tracking
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            # Log successful completion with metrics
            _logger.info(
                "Backup query completed: %s objects found", len(results),
                extra={
                    'event_type': 'query.backup.completed',
                    'operation': 'query.backup',
                    'filespace': query_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'total_objects': len(results),
                        'duration_ms': duration_ms
                    }
                }
            )

            # Transform results to response model
            return BackupQueryResult(
                Objects=results,
                TotalObjects=len(results),
            )

        except TSMError as e:
            # Handle TSM-specific errors with detailed logging
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Backup query failed for filespace: %s", query_request.filespace,
                extra={
                    'event_type': 'query.backup.failed',
                    'operation': 'query.backup',
                    'filespace': query_request.filespace,
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
            # Handle unexpected errors with full context
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during backup query for filespace: %s", query_request.filespace,
                extra={
                    'event_type': 'query.backup.error',
                    'operation': 'query.backup',
                    'filespace': query_request.filespace,
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

    def list_objects(self, list_request: ListObjectsRequest) -> ListObjectsResult:
        """
        List backed-up objects with prefix filtering and pagination.

        Retrieves a paginated list of backed-up objects matching the specified prefix.
        This operation is optimized for browsing large object collections and supports
        filtering by object state, type, and point-in-time date.

        Parameters
        ----------
        list_request : ListObjectsRequest
            The list request containing:
            - Filespace: Filespace name to query (default: "/")
            - Prefix: Object key prefix filter (default: "")
            - MaxKeys: Maximum number of objects to return (default: 1000, max: 10000)
            - ObjState: Object state filter (default: ACTIVE)
            - ObjType: Object type filter (default: FILE)
            - PitDate: Point-in-time date for historical queries

        Returns
        -------
        ListObjectsResult
            The list result containing:
            - Name: Filespace name
            - Prefix: Prefix used for filtering
            - Contents: List of object dictionaries with metadata
            - KeyCount: Number of objects returned
            - MaxKeys: Maximum keys requested

        Raises
        ------
        TSMError
            If the list operation fails
        QueryError
            If the list parameters are invalid

        Notes
        -----
        - Use prefix filtering to reduce server-side processing
        - Results are limited by MaxKeys parameter
        - For large result sets, implement pagination using prefix
        - Empty prefix returns all objects (up to MaxKeys limit)

        Example
        -------
        >>> from ibm_storage_protect.data_models.query import ListObjectsRequest
        >>>
        >>> request = ListObjectsRequest(
        ...     Filespace="/myfs",
        ...     Prefix="/backup/2024",
        ...     MaxKeys=100
        ... )
        >>> result = query_client.list_objects(request)
        >>> print(f"Found {result.key_count} objects")
        >>> for obj in result.contents:
        ...     print(f"  {obj['Key']}: {obj['Size']} bytes")
        """
        # Extract session context for logging and tracking
        session_handle = getattr(self._session, '_session_id', None)
        object_key = list_request.filespace
        start_time = time.perf_counter()

        # Set logging context for this operation
        set_log_context(session_handle=session_handle, object_key=object_key)

        # Log operation start with full context
        _logger.info(
            "Listing objects",
            extra={
                'event_type': 'query.list_objects.started',
                'operation': 'query.list_objects',
                'filespace': list_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'prefix': list_request.prefix,
                    'max_keys': list_request.max_keys,
                    'pit_date': list_request.pit_date.isoformat() if list_request.pit_date else None
                },
                'status': 'started'
            }
        )
        try:
            # Extract enum values with defaults
            obj_state_value = extract_enum_value(list_request.obj_state, ObjState, ObjState.ACTIVE)
            obj_type_value = extract_enum_value(list_request.obj_type, ObjType, ObjType.FILE)

            # Create internal request model for C API layer
            internal_request = ListObjectsInternal(
                handle=self._require_handle(),
                filespace=list_request.filespace or "/",  # Default to root filespace
                prefix=list_request.prefix,
                max_keys=list_request.max_keys or 1000,  # Default to 1000 objects
                obj_state=obj_state_value,
                obj_type=obj_type_value,
                pit_date=list_request.pit_date,
            )

            # Execute the list operation via C API layer
            result = QueryOperation.list_objects(
                handle=internal_request.handle,
                filespace=internal_request.filespace,
                prefix=internal_request.prefix,
                max_keys=internal_request.max_keys,
                obj_state=internal_request.obj_state,
                obj_type=internal_request.obj_type,
                pit_date=internal_request.pit_date,
                session_handle=session_handle,
                object_key=object_key,
            )

            # Calculate operation duration for performance tracking
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            # Log successful completion with metrics
            _logger.info(
                "List objects completed",
                extra={
                    'event_type': 'query.list_objects.completed',
                    'operation': 'query.list_objects',
                    'filespace': list_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'key_count': result["KeyCount"],
                        'duration_ms': duration_ms
                    }
                }
            )

            # Transform results to response model
            return ListObjectsResult(
                Name=result["Name"],
                Prefix=result["Prefix"],
                Contents=result["Contents"],
                KeyCount=result["KeyCount"],
                MaxKeys=result["MaxKeys"],
            )
        except TSMError as e:
            # Handle TSM-specific errors with detailed logging
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "List objects failed",
                extra={
                    'event_type': 'query.list_objects.failed',
                    'operation': 'query.list_objects',
                    'filespace': list_request.filespace,
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
            # Handle unexpected errors with full context
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error while listing objects",
                extra={
                    'event_type': 'query.list_objects.error',
                    'operation': 'query.list_objects',
                    'filespace': list_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    }
                },
                exc_info=True
            )
            raise

    def query_filespaces(self, query_request: QueryFilespacesRequest) -> QueryFilespacesResult:
        """
        Query filespaces by name pattern.

        Retrieves filespace metadata and statistics from the IBM Storage Protect
        server using the specified pattern.

        Parameters
        ----------
        query_request : QueryFilespacesRequest
            The filespace query request containing:
            - fs_pattern: Glob pattern for matching filespaces (default: "*")

        Returns
        -------
        QueryFilespacesResult
            The query result containing:
            - filespaces: List of filespace metadata dictionaries with occupancy, capacity, etc.
            - total_filespaces: Total count of matched filespaces

        Raises
        ------
        TSMError
            If the query operation fails

        Example
        -------
        >>> from ibm_storage_protect.data_models.query import QueryFilespacesRequest
        >>>
        >>> request = QueryFilespacesRequest(fs_pattern="/myfs*")
        >>> result = query_client.query_filespaces(request)
        >>> print(f"Found {result.total_filespaces} filespaces")
        >>> for fs in result.filespaces:
        ...     print(f"  {fs['Name']}: {fs['Occupancy']} bytes used")
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = query_request.fs_pattern or "*"
        start_time = time.perf_counter()

        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Querying filespaces",
            extra={
                'event_type': 'query.filespaces.started',
                'operation': 'query.filespaces',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'fs_pattern': query_request.fs_pattern
                },
                'status': 'started'
            }
        )
        try:
            internal_request = QueryFilespacesInternal(
                handle=self._require_handle(),
                fs_pattern=query_request.fs_pattern,
            )

            results = QueryOperation.query_filespaces(
                handle=internal_request.handle,
                fs_pattern=internal_request.fs_pattern,
                session_handle=session_handle,
                object_key=object_key,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Filespace query completed",
                extra={
                    'event_type': 'query.filespaces.completed',
                    'operation': 'query.filespaces',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'total_filespaces': len(results),
                        'duration_ms': duration_ms
                    }
                }
            )

            return QueryFilespacesResult(
                Filespaces=results,
                TotalFilespaces=len(results),
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Filespace query failed",
                extra={
                    'event_type': 'query.filespaces.failed',
                    'operation': 'query.filespaces',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict()
                },
                exc_info=True
            )
            raise
        except Exception as e:
            # Handle unexpected errors with full context
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during filespace query",
                extra={
                    'event_type': 'query.filespaces.error',
                    'operation': 'query.filespaces',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    }
                },
                exc_info=True
            )
            raise

    def query_object(self, query_request: QueryObjectRequest) -> Optional[QueryObjectResult]:
        """
        Query a single object by exact key.

        Returns metadata for the specified object key in the given filespace.
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = query_request.key
        start_time = time.perf_counter()

        # Set log context for this operation
        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Querying object",
            extra={
                'event_type': 'query.object.started',
                'operation': 'query.object',
                'filespace': query_request.filespace,
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'obj_state': str(query_request.obj_state),
                    'obj_type': str(query_request.obj_type)
                },
                'status': 'started'
            }
        )
        try:
            obj_state_value = extract_enum_value(query_request.obj_state, ObjState, ObjState.ACTIVE)
            obj_type_value = extract_enum_value(query_request.obj_type, ObjType, ObjType.FILE)

            internal_request = QueryObjectInternal(
                handle=self._require_handle(),
                filespace=query_request.filespace or "/",
                key=query_request.key,
                obj_state=obj_state_value,
                obj_type=obj_type_value,
            )

            result = QueryOperation.query_object(
                handle=internal_request.handle,
                filespace=internal_request.filespace,
                key=internal_request.key,
                obj_state=internal_request.obj_state,
                obj_type=internal_request.obj_type,
                session_handle=session_handle,
                object_key=object_key,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            if result is None:
                _logger.info(
                    "Object query completed with no result",
                    extra={
                        'event_type': 'query.object.completed',
                        'operation': 'query.object',
                        'filespace': query_request.filespace,
                        'session_handle': session_handle,
                        'object_key': object_key,
                        'duration_ms': duration_ms,
                        'status': 'not_found'
                    }
                )
                return None

            _logger.info(
                "Object query completed",
                extra={
                    'event_type': 'query.object.completed',
                    'operation': 'query.object',
                    'filespace': query_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success'
                }
            )
            return QueryObjectResult(**result)
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Object query failed",
                extra={
                    'event_type': 'query.object.failed',
                    'operation': 'query.object',
                    'filespace': query_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict()
                },
                exc_info=True
            )
            raise
        except Exception as e:
            # Handle unexpected errors with full context
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during object query",
                extra={
                    'event_type': 'query.object.error',
                    'operation': 'query.object',
                    'filespace': query_request.filespace,
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    }
                },
                exc_info=True
            )
            raise

    def query_mgmt_classes(self, query_request: QueryMgmtClassesRequest) -> QueryMgmtClassesResult:
        """
        Query management class definitions and policies.

        Retrieves management class information from the IBM Storage Protect server,
        including backup and archive copy group settings.

        Parameters
        ----------
        query_request : QueryMgmtClassesRequest
            The management class query request containing:
            - McName: Management class name pattern (default: "" = all classes)
            - Detail: Include detailed copy group information (default: True)

        Returns
        -------
        QueryMgmtClassesResult
            The query result containing:
            - management_classes: List of management class dictionaries
            - total_classes: Total number of classes found

            When Detail=True, each class includes:
            - Name, Description
            - BackupCG: Backup copy group settings
            - ArchiveCG: Archive copy group settings

        Raises
        ------
        TSMError
            If the query operation fails

        Example
        -------
        >>> from ibm_storage_protect.data_models.query import QueryMgmtClassesRequest
        >>>
        >>> request = QueryMgmtClassesRequest(Detail=True)
        >>> result = query_client.query_mgmt_classes(request)
        >>> for mc in result.management_classes:
        ...     print(f"{mc['Name']}: {mc['Description']}")
        ...     if 'BackupCG' in mc:
        ...         print(f"  Backup: {mc['BackupCG']['Name']}")
        """
        session_handle = getattr(self._session, '_session_id', None)
        object_key = "mgmt_classes"
        start_time = time.perf_counter()

        set_log_context(session_handle=session_handle, object_key=object_key)

        _logger.info(
            "Querying management classes",
            extra={
                'event_type': 'query.mgmt_classes.started',
                'operation': 'query.mgmt_classes',
                'session_handle': session_handle,
                'object_key': object_key,
                'context': {
                    'mc_name': query_request.mc_name,
                    'detail': query_request.detail
                },
                'status': 'started'
            }
        )
        try:
            internal_request = QueryMgmtClassesInternal(
                handle=self._require_handle(),
                mc_name=query_request.mc_name or "",
                detail=query_request.detail,
            )

            results = QueryOperation.query_mgmt_classes(
                handle=internal_request.handle,
                mc_name=internal_request.mc_name,
                detail=internal_request.detail,
                session_handle=session_handle,
                object_key=object_key,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Management class query completed",
                extra={
                    'event_type': 'query.mgmt_classes.completed',
                    'operation': 'query.mgmt_classes',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'total_classes': len(results),
                        'duration_ms': duration_ms
                    }
                }
            )

            return QueryMgmtClassesResult(
                ManagementClasses=results,
                TotalClasses=len(results),
            )
        except TSMError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Management class query failed",
                extra={
                    'event_type': 'query.mgmt_classes.failed',
                    'operation': 'query.mgmt_classes',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict()
                },
                exc_info=True
            )
            raise
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during management class query",
                extra={
                    'event_type': 'query.mgmt_classes.error',
                    'operation': 'query.mgmt_classes',
                    'session_handle': session_handle,
                    'object_key': object_key,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    }
                },
                exc_info=True
            )
            raise

    def __enter__(self):
        """
        Enter the context manager block.

        Returns
        -------
        QueryClient
            Self reference.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager block. Performs any necessary cleanup.
        """

    def __repr__(self) -> str:
        """
        Return a string representation of the QueryClient.

        Returns
        -------
        str
            A string containing client and session information.
        """
        return f"QueryClient(session={self._session})"
