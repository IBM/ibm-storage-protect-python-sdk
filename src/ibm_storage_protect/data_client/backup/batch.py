"""
IBM Storage Protect Client SDK - Batch Backup Operation

This module provides batch backup functionality for IBM Storage Protect.
It handles backing up multiple objects efficiently in optimized transactions,
significantly improving performance compared to individual backups.

Key Responsibilities:
---------------------
1. **Batch Processing**: Back up multiple objects in optimized transactions
2. **Transaction Management**: Group objects into efficient transaction batches
3. **Result Aggregation**: Collect and report results for all objects
4. **Error Handling**: Handle partial failures gracefully
5. **Performance Optimization**: Minimize overhead for multiple small objects

Classes:
--------
- BatchBackupClient: Client for batch backup operations

Example Usage:
--------------
    from ibm_storage_protect.data_client.batch_backup import BatchBackupClient
    from ibm_storage_protect.data_models.backup import BatchBackupRequest, BackupRequest
    
    client = BatchBackupClient(session)
    batch = BatchBackupRequest(
        Objects=[
            BackupRequest(Key="/file1.txt", Body=b"content1"),
            BackupRequest(Key="/file2.txt", Body=b"content2")
        ],
        Filespace="/myfs",
        MaxPerTxn=10
    )
    result = client.batch_backup(batch)
    print(f"Success: {result.successful}/{result.total_objects}")
"""
# pylint: disable=line-too-long

import time

from ibm_storage_protect.c_api_bridge.wrappers.filespace import register_filespace as _register_filespace
from ibm_storage_protect.c_api_bridge.wrappers.backup import BatchBackupOperation
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    encode_obj_info,
    extract_enum_value,
    extract_mount_wait,
    validate_chunks,
)
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.backup import (
    BatchBackupRequest,
    BatchBackupInternal,
    BatchBackupResult,
)
from ibm_storage_protect.enums import ObjType
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import get_logger, log_operation
from ibm_storage_protect.logger.context import set_log_context
from ibm_storage_protect.session import ClientSession

# Module-level logger for structured logging
_logger = get_logger(__name__)


class BatchBackupClient(BaseClient):
    """
    Client for batch backup operations.
    
    This class provides type-safe, validated methods for backing up multiple
    objects efficiently in batch transactions. It handles the complete batch
    backup workflow including validation, transaction management, and result
    aggregation.
    
    Attributes
    ----------
    _session : ClientSession
        Active session with IBM Storage Protect server
    
    Methods
    -------
    batch_backup(batch_request)
        Back up multiple objects in batch
    
    Notes
    -----
    - Inherits from BaseClient for session management
    - All operations use structured logging
    - Errors are mapped to SDK exceptions
    - Supports partial success scenarios
    - Supports context manager protocol
    """

    def batch_backup(self, batch_request: BatchBackupRequest) -> BatchBackupResult:
        """
        Back up multiple objects in batch for improved efficiency.

        Batch backup reduces overhead by grouping multiple objects into optimized
        transactions. This is significantly faster than individual backups for
        multiple small objects.

        Parameters
        ----------
        batch_request : BatchBackupRequest
            Batch backup request with Objects list, Filespace, and MaxPerTxn

        Returns
        -------
        BatchBackupResult
            Result with status, results list, total_objects, successful, and failed counts

        Raises
        ------
        TSMError
            If batch operation fails completely
        
        Example
        -------
        >>> batch = BatchBackupRequest(
        ...     Objects=[BackupRequest(Key="/f1.txt", Body=b"c1")],
        ...     Filespace="/myfs"
        ... )
        >>> result = client.batch_backup(batch)
        >>> print(f"{result.successful} successful")
        """
        filespace = batch_request.filespace or "/"
        object_key = f"batch_{len(batch_request.objects)}_objects"

        context_details = {
            'total_objects': len(batch_request.objects)
        }

        with log_operation(
            _logger,
            'batch_backup',
            self,
            filespace=filespace,
            object_key=object_key,
            context_details=context_details
        ) as log_data:
            # Register filespace with server (idempotent operation)
            _register_filespace(
                handle=self._require_handle(),
                filespace=filespace
            )

            # Transform each object from user model to internal format
            objects = []
            for obj in batch_request.objects:
                # Validate and normalize data chunks
                data_source = validate_chunks(obj.body)

                # Extract enum values for C API
                obj_type_value = extract_enum_value(obj.obj_type, ObjType, default=ObjType.FILE.value)
                mount_wait_value = extract_mount_wait(obj.mount_wait)
                obj_info_bytes = encode_obj_info(obj.obj_info)

                # Build object dictionary for internal model
                objects.append({
                    "Key": obj.key,
                    "Body": data_source,
                    "ObjType": obj_type_value,
                    "Owner": obj.owner or self._get_owner(),
                    "ManagementClass": obj.management_class,
                    "SizeEstimate": obj.size_estimate,
                    "PreCompressed": obj.pre_compressed,
                    "MountWait": mount_wait_value,
                    "ObjInfo": obj_info_bytes,
                    "DisableDedup": obj.disable_dedup,
                })

            # Create internal batch backup model
            internal_request = BatchBackupInternal(
                handle=self._require_handle(),
                objects=objects,
                filespace=filespace,
                max_per_txn=batch_request.max_per_txn,
            )

            # Create and execute batch backup operation
            operation = BatchBackupOperation(
                session=self,
                objects=internal_request.objects,
                filespace=internal_request.filespace,
                max_per_txn=internal_request.max_per_txn,
                session_handle=getattr(self._session, '_session_id', None),
                object_key=object_key,
            )

            # Execute batch backup via C API
            results = operation.execute()

            # Calculate success/failure counts
            successful = sum(1 for r in results if r.get("status") == "success")
            failed = len(results) - successful

            # Update logging context/metrics on success
            log_data["metrics"]["total_objects"] = len(results)

            # Map results to user-facing model
            return BatchBackupResult(
                status="success" if failed == 0 else "partial",
                results=results,
                total_objects=len(results),
                successful=successful,
                failed=failed,
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
