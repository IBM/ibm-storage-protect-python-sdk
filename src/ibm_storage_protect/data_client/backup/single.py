"""
IBM Storage Protect Client SDK - Single Backup Operation

This module provides single object backup functionality for IBM Storage Protect.
It handles the complete backup workflow for individual objects including validation,
filespace registration, data transformation, C API execution, and result mapping.

Key Responsibilities:
---------------------
1. **Single Object Backup**: Back up individual objects with full control
2. **Data Validation**: Validate and transform user input to internal formats
3. **Filespace Management**: Automatic filespace registration
4. **Error Handling**: Comprehensive error handling with structured logging
5. **Performance Tracking**: Detailed metrics and timing information

Classes:
--------
- SingleBackupClient: Client for single object backup operations

Example Usage:
--------------
    from ibm_storage_protect.data_client.single_backup import SingleBackupClient
    from ibm_storage_protect.data_models.backup import BackupRequest
    
    client = SingleBackupClient(session)
    backup = BackupRequest(
        Key="/data/file.txt",
        Body=b"file content",
        Filespace="/myfs"
    )
    result = client.backup(backup)
    print(f"Backup status: {result.status}")
"""
# pylint: disable=line-too-long

import time

from ibm_storage_protect.c_api_bridge.wrappers.filespace import register_filespace as _register_filespace
from ibm_storage_protect.c_api_bridge.wrappers.backup import BackupOperation
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    encode_obj_info,
    extract_enum_value,
    extract_mount_wait,
    parse_key,
    validate_chunks,
)
from ibm_storage_protect.base import BaseClient
from ibm_storage_protect.data_models.backup import (
    BackupRequest,
    BackupInternal,
    BackupResult,
)
from ibm_storage_protect.enums import ObjType
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import get_logger, log_operation


# Module-level logger for structured logging
_logger = get_logger(__name__)


class SingleBackupClient(BaseClient):
    """
    Client for single object backup operations.
    
    This class provides type-safe, validated methods for backing up individual
    objects to IBM Storage Protect. It handles the complete backup workflow
    including validation, filespace registration, and result mapping.
    
 
    
    Methods
    -------
    backup(backup_request)
        Back up a single object
    
    Notes
    -----
    - Inherits from BaseClient for session management
    - All operations use structured logging
    - Errors are mapped to SDK exceptions
    - Supports context manager protocol
    """

    def backup(self, backup_request: BackupRequest) -> BackupResult:
        """
        Back up a single object to IBM Storage Protect.

        This method handles the complete backup workflow: validation, filespace
        registration, data transformation, C API execution, and result mapping.

        Parameters
        ----------
        backup_request : BackupRequest
            Backup request model with Key, Body, Filespace, etc.

        Returns
        -------
        BackupResult
            Result with status, filespace, high_level, low_level, and stats

        Raises
        ------
        ValueError
            If Key is empty or invalid
        TSMError
            If backup operation fails
        
        Example
        -------
        >>> backup = BackupRequest(Key="/data/file.txt", Body=b"content")
        >>> result = client.backup(backup)
        >>> print(result.status)
        'success'
        """
        # Use provided filespace or default to root
        filespace = backup_request.filespace or "/"

        # Validate key is not empty
        if not backup_request.key or not backup_request.key.strip("/"):
            session_handle = getattr(self._session, '_session_id', None)
            _logger.error(
                "Backup validation failed: empty key",
                extra={
                    'event_type': 'backup.validation_failed',
                    'operation': 'backup',
                    'handle': self._require_handle(),
                    'Key': backup_request.key,
                    'session_handle': session_handle,
                    'object_key': backup_request.key,
                    'error': {'message': 'Key must not be empty', 'error_type': 'ValueError'}
                }
            )
            raise ValueError("Key must not be empty")

        context_details = {
            'key': backup_request.key,
            'obj_type': str(backup_request.obj_type) if backup_request.obj_type else None,
            'size_estimate': backup_request.size_estimate,
            'pre_compressed': backup_request.pre_compressed,
            'disable_dedup': backup_request.disable_dedup,
            'obj_info': backup_request.obj_info,
            'management_class': backup_request.management_class
        }

        with log_operation(
            _logger,
            'backup',
            self,
            filespace=filespace,
            object_key=backup_request.key,
            context_details=context_details,
            handle=self._require_handle()
        ) as log_data:
            # Parse key into high_level and low_level components for C API
            high_level, low_level = parse_key(backup_request.key)

            # Register filespace with server (idempotent operation)
            _register_filespace(
                handle=self._require_handle(),
                filespace=filespace
            )

            # Validate and normalize data chunks (handles bytes, file-like, generators)
            data_source = validate_chunks(backup_request.body)

            # Extract enum values for C API (converts enums to integer constants)
            obj_type_value = extract_enum_value(backup_request.obj_type, ObjType, default=ObjType.FILE.value)
            mount_wait_value = extract_mount_wait(backup_request.mount_wait)

            # Encode object info to bytes if provided
            obj_info_bytes = encode_obj_info(backup_request.obj_info)

            # Create internal model for C API layer
            internal_request = BackupInternal(
                handle=self._require_handle(),
                filespace=filespace,
                high_level=high_level,
                low_level=low_level,
                data_source=data_source,
                obj_type=obj_type_value,
                owner=backup_request.owner or self._get_owner(),
                management_class=backup_request.management_class,
                size_estimate=backup_request.size_estimate,
                pre_compressed=backup_request.pre_compressed,
                mount_wait=mount_wait_value,
                obj_info=obj_info_bytes,
                disable_dedup=backup_request.disable_dedup,
            )

            # Create and execute backup operation
            operation = BackupOperation(
                session=self,
                filespace=internal_request.filespace,
                high_level=internal_request.high_level,
                low_level=internal_request.low_level,
                data_source=internal_request.data_source,
                obj_type=internal_request.obj_type,
                owner=internal_request.owner,
                management_class=internal_request.management_class,
                size_estimate=internal_request.size_estimate,
                pre_compressed=internal_request.pre_compressed,
                mount_wait=internal_request.mount_wait,
                obj_info=internal_request.obj_info,
                disable_dedup=internal_request.disable_dedup,
                session_handle=getattr(self._session, '_session_id', None),
                object_key=backup_request.key,
            )

            # Execute backup operation via C API
            result = operation.execute()

            # Update logging context/metrics on success
            log_data["context"]["result_status"] = result["status"]
            log_data["metrics"]["stats"] = result.get("stats")

            stats_val = result.get("stats")
            # Map C API result to user-facing model
            return BackupResult(
                Status=result["status"],
                Filespace=result["filespace"],
                HighLevel=result["high_level"],
                LowLevel=result["low_level"],
                Stats=stats_val if isinstance(stats_val, dict) else None,
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
