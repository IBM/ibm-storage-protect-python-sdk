"""
IBM Storage Protect Client SDK - Batch Restore Operation

This module provides batch restore functionality for IBM Storage Protect.
It handles restoring multiple objects efficiently, reducing overhead compared
to individual restore operations.

Key Responsibilities:
---------------------
1. **Batch Processing**: Restore multiple objects efficiently
2. **Result Aggregation**: Collect and report results for all objects
3. **Data Streaming**: Memory-efficient data retrieval via generators
4. **Error Handling**: Handle partial failures gracefully
5. **Performance Optimization**: Minimize overhead for multiple objects

Classes:
--------
- BatchRestoreClient: Client for batch restore operations

Example Usage:
--------------
    from ibm_storage_protect.data_client.batch_restore import BatchRestoreClient
    from ibm_storage_protect.data_models.restore import BatchRestoreRequest, RestoreRequest
    
    client = BatchRestoreClient(session)
    batch = BatchRestoreRequest(
        Objects=[
            RestoreRequest(Key="/file1.txt"),
            RestoreRequest(Key="/file2.txt")
        ],
        Filespace="/myfs"
    )
    result = client.batch_restore(batch)
    
    for obj_result in result.results:
        print(f"Restoring {obj_result.key}")
        for chunk in obj_result.body:
            process(chunk)
"""
# pylint: disable=line-too-long

import time

from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    extract_enum_value,
    extract_mount_wait,
)
from ibm_storage_protect.c_api_bridge.wrappers.restore import BatchRestoreOperation
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.restore import (
    BatchRestoreRequest,
    BatchRestoreResult,
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


class BatchRestoreClient(BaseClient):
    """
    Client for batch restore operations.
    
    This class provides type-safe, validated methods for restoring multiple
    objects efficiently in batch. It handles the complete batch restore
    workflow including validation and result aggregation.
    
    Attributes
    ----------
    _session : ClientSession
        Active session with IBM Storage Protect server
    
    Methods
    -------
    batch_restore(batch_request)
        Restore multiple objects in batch
    
    Notes
    -----
    - Inherits from BaseClient for session management
    - All operations use structured logging
    - Errors are mapped to SDK exceptions
    - Body for each object is returned as a generator
    - Supports context manager protocol
    """

    def batch_restore(self, batch_request: BatchRestoreRequest) -> BatchRestoreResult:
        """
        Restore multiple objects in batch for improved efficiency.

        Batch restore reduces overhead by grouping multiple objects into optimized
        operations. This is significantly faster than individual restores for
        multiple objects.

        Parameters
        ----------
        batch_request : BatchRestoreRequest
            Batch restore request with objects list and Filespace

        Returns
        -------
        BatchRestoreResult
            Result with Results list and TotalObjects count

        Raises
        ------
        TSMError
            If batch operation fails

        Notes
        -----
        - Each object can have its own settings (ObjState, PitDate, etc.)
        - Default filespace applies to all objects unless overridden
        - Body for each object is returned as a generator
        
        Example
        -------
        >>> batch = BatchRestoreRequest(
        ...     Objects=[RestoreRequest(Key="/f1.txt")],
        ...     Filespace="/myfs"
        ... )
        >>> result = client.batch_restore(batch)
        >>> print(f"{result.total_objects} objects restored")
        """
        filespace = batch_request.filespace or "/"
        object_key = f"batch_{len(batch_request.objects)}_objects"

        context_details = {
            'total_objects': len(batch_request.objects)
        }

        with log_operation(
            _logger,
            'batch_restore',
            self,
            filespace=filespace,
            object_key=object_key,
            context_details=context_details
        ) as log_data:
            specs = []
            for obj in batch_request.objects:
                obj_state_value = extract_enum_value(obj.obj_state, ObjState, ObjState.ACTIVE)
                obj_type_value = extract_enum_value(obj.obj_type, ObjType, ObjType.FILE)
                mount_wait_value = extract_mount_wait(obj.mount_wait)

                specs.append({
                    "Key": obj.key,
                    "Filespace": obj.filespace or filespace,
                    "ObjState": obj_state_value,
                    "ObjType": obj_type_value,
                    "PitDate": obj.pit_date,
                    "MountWait": mount_wait_value,
                    "Offset": obj.offset,
                    "Length": obj.length,
                    "Owner": obj.owner or self._get_owner(),
                })

            operation = BatchRestoreOperation(
                handle=self._require_handle(),
                specs=specs,
                default_filespace=filespace,
                session_handle=getattr(self._session, '_session_id', None),
                object_key=object_key,
            )

            results = operation.execute()

            # Update logging context/metrics on success
            log_data["metrics"]["total_objects"] = len(results)

            return BatchRestoreResult(
                Results=[
                    RestoreResult(
                        Key=result["Key"],
                        Body=result["Body"],
                        LastModified=result.get("LastModified"),
                        ObjectId=result.get("ObjectId", ""),
                        MediaClass=result.get("MediaClass", ""),
                        ManagementClass=result.get("ManagementClass", ""),
                    )
                    for result in results
                ],
                TotalObjects=len(results),
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
