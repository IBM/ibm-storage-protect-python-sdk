"""
IBM Storage Protect Client API - Backup Operations Package

This package provides Python wrappers for IBM Storage Protect backup operations,
organized by operation type for improved maintainability and code organization.

Modules:
--------
- single: Single object backup operations (BackupOperation)
- batch: Batch backup operations (BatchBackupOperation)
- group: Group backup operations (GroupBackupOperation)

Exported Classes:
-----------------
All backup operation classes are exported at the package level for backward
compatibility with existing code.

Example Usage:
--------------
    # Import from package (recommended)
    from ibm_storage_protect.c_api_bridge.wrappers.backup import (
        BackupOperation,
        BatchBackupOperation,
        GroupBackupOperation
    )

    # Or import from specific modules
    from ibm_storage_protect.c_api_bridge.wrappers.backup.single import BackupOperation
    from ibm_storage_protect.c_api_bridge.wrappers.backup.batch import BatchBackupOperation
    from ibm_storage_protect.c_api_bridge.wrappers.backup.group import GroupBackupOperation
"""

from .single import BackupOperation
from .batch import BatchBackupOperation
from .group import GroupBackupOperation

__all__ = [
    "BackupOperation",
    "BatchBackupOperation",
    "GroupBackupOperation",
]
