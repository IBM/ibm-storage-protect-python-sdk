"""
IBM Storage Protect Client SDK - Data Client Package

This package provides high-level client interfaces for IBM Storage Protect
data operations including backup, restore, and data management.

The package is organized into specialized modules for different operation types:
- single_backup: Single object backup operations
- batch_backup: Batch backup operations
- group_backup: Group backup operations and management
- single_restore: Single object restore operations
- batch_restore: Batch restore operations
- group_restore: Group restore operations
- client: Unified DataClient interface

Main Classes:
-------------
- DataClient: Unified interface for all data operations (recommended)
- SingleBackupClient: Direct access to single backup operations
- BatchBackupClient: Direct access to batch backup operations
- GroupBackupClient: Direct access to group backup operations
- SingleRestoreClient: Direct access to single restore operations
- BatchRestoreClient: Direct access to batch restore operations
- GroupRestoreClient: Direct access to group restore operations
- GroupHandle: Handle for managing group backup operations

Example Usage:
--------------
    # Using the unified DataClient (recommended)
    from ibm_storage_protect.data_client import DataClient
    from ibm_storage_protect.data_models.backup import BackupRequest
    
    client = DataClient(session)
    backup = BackupRequest(Key="/data/file.txt", Body=b"content")
    result = client.backup(backup)
    
    # Using specialized clients directly (advanced)
    from ibm_storage_protect.data_client import SingleBackupClient
    
    backup_client = SingleBackupClient(session)
    result = backup_client.backup(backup)

Notes:
------
- DataClient is the recommended interface for most use cases
- Specialized clients are available for advanced scenarios
- All clients support context manager protocol
- All operations use structured logging
- Errors are mapped to SDK exceptions
"""

from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.data_client.backup.single import SingleBackupClient
from ibm_storage_protect.data_client.backup.batch import BatchBackupClient
from ibm_storage_protect.data_client.backup.group import GroupBackupClient
from ibm_storage_protect.data_client.restore.single import SingleRestoreClient
from ibm_storage_protect.data_client.restore.batch import BatchRestoreClient
from ibm_storage_protect.data_client.restore.group import GroupRestoreClient

__all__ = [
    # Unified interface (recommended)
    "DataClient",
    
    # Backup clients
    "SingleBackupClient",
    "BatchBackupClient",
    "GroupBackupClient",
    
    # Restore clients
    "SingleRestoreClient",
    "BatchRestoreClient",
    "GroupRestoreClient",
    
]

# Made with Bob
