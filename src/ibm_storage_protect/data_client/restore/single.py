"""
IBM Storage Protect Client SDK - Single Restore Operation

This module provides single object restore functionality for IBM Storage Protect.
It handles the complete restore workflow for individual objects including validation,
data retrieval, and result mapping with support for point-in-time and partial restores.

Key Responsibilities:
---------------------
1. **Single Object Restore**: Restore individual backed-up objects
2. **Point-in-Time Restore**: Retrieve historical versions by date
3. **Partial Restore**: Retrieve specific byte ranges from objects
4. **Data Streaming**: Memory-efficient data retrieval via generators
5. **Error Handling**: Comprehensive error handling with structured logging

Classes:
--------
- SingleRestoreClient: Client for single object restore operations

Example Usage:
--------------
    from ibm_storage_protect.data_client.single_restore import SingleRestoreClient
    from ibm_storage_protect.data_models.restore import RestoreRequest
    
    client = SingleRestoreClient(session)
    restore = RestoreRequest(
        Key="/data/file.txt",
        Filespace="/myfs"
    )
    result = client.restore(restore)
    
    # Stream data chunks
    with open("restored_file.txt", "wb") as f:
        for chunk in result.body:
            f.write(chunk)
"""
# pylint: disable=line-too-long

import time

from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    extract_enum_value,
    extract_mount_wait,
)
from ibm_storage_protect.c_api_bridge.wrappers.restore import RestoreOperation
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.restore import (
    RestoreRequest,
    RestoreResult,
)
from ibm_storage_protect.enums import (
    ObjState,
    ObjType,
)
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import get_logger, log_operation
from ibm_storage_protect.logger.context import set_log_context
from ibm_storage_protect.session import ClientSession

# Module-level logger for structured logging
_logger = get_logger(__name__)


class SingleRestoreClient(BaseClient):
    """
    Client for single object restore operations.
    
    This class provides type-safe, validated methods for restoring individual
    objects from IBM Storage Protect. It handles the complete restore workflow
    including validation, data retrieval, and result mapping.
    
    Attributes
    ----------
    _session : ClientSession
        Active session with IBM Storage Protect server
    
    Methods
    -------
    restore(restore_request)
        Restore a single object
    
    Notes
    -----
    - Inherits from BaseClient for session management
    - All operations use structured logging
    - Errors are mapped to SDK exceptions
    - Body is returned as a generator for memory efficiency
    - Supports context manager protocol
    """

    def restore(self, restore_request: RestoreRequest) -> RestoreResult:
        """
        Restore a single object from IBM Storage Protect.

        This method handles the complete restore workflow: validation, data
        retrieval, and result mapping. Supports point-in-time restore and
        partial restore (specific byte ranges).

        Parameters
        ----------
        restore_request : RestoreRequest
            Restore request model with Key, Filespace, ObjState, PitDate, etc.

        Returns
        -------
        RestoreResult
            Result with key, body (generator), last_modified, object_id, etc.

        Raises
        ------
        TSMError
            If restore operation fails

        Notes
        -----
        - Body is returned as a generator for memory efficiency
        - Supports point-in-time restore via PitDate parameter
        - Supports partial restore via Offset and Length parameters
        - ObjState defaults to ACTIVE if not specified
        
        Example
        -------
        >>> restore = RestoreRequest(Key="/data/file.txt", Filespace="/myfs")
        >>> result = client.restore(restore)
        >>> for chunk in result.body:
        ...     process(chunk)
        """
        filespace = restore_request.filespace or "/"
        context_details = {
            'key': restore_request.key,
            'obj_state': str(restore_request.obj_state) if restore_request.obj_state else None,
            'obj_type': str(restore_request.obj_type) if restore_request.obj_type else None,
            'pit_date': restore_request.pit_date.isoformat() if restore_request.pit_date else None,
            'offset': restore_request.offset,
            'length': restore_request.length
        }

        with log_operation(
            _logger,
            'restore',
            self,
            filespace=filespace,
            object_key=restore_request.key,
            context_details=context_details
        ) as log_data:
            obj_state_value = extract_enum_value(restore_request.obj_state, ObjState, ObjState.ACTIVE)
            obj_type_value = extract_enum_value(restore_request.obj_type, ObjType, ObjType.FILE)
            mount_wait_value = extract_mount_wait(restore_request.mount_wait)

            operation = RestoreOperation(
                handle=self._require_handle(),
                filespace=filespace,
                key=restore_request.key,
                obj_state=obj_state_value,
                obj_type=obj_type_value,
                pit_date=restore_request.pit_date,
                mount_wait=mount_wait_value,
                offset=restore_request.offset,
                length=restore_request.length,
                owner=restore_request.owner or self._get_owner(),
                session_handle=getattr(self._session, '_session_id', None),
                object_key=restore_request.key,
            )

            result = operation.execute()

            # Update logging context/metrics on success
            log_data["context"]["object_id"] = result.get("ObjectId", "")

            return RestoreResult(
                Key=result["Key"],
                Body=result["Body"],
                LastModified=result.get("LastModified"),
                ObjectId=result.get("ObjectId", ""),
                MediaClass=result.get("MediaClass", ""),
                ManagementClass=result.get("ManagementClass", ""),
            )

    def _get_owner(self) -> str:
        """
        Internal: Get the owner name from the session manager.

        Returns
        -------
        str
            Owner name from session manager, or empty string if not available
        """
        if hasattr(self._session, '_session_manager') and self._session._session_manager:
            return self._session._session_manager.owner or ""
        return ""

# Made with Bob
