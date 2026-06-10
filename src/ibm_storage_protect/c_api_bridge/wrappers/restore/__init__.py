"""
IBM Storage Protect Client API - Restore Operations Package

This package provides Python wrappers for IBM Storage Protect restore operations,
organized by operation type for improved maintainability and code organization.

Modules:
--------
- single: Single object restore operations (RestoreOperation)
- batch: Batch restore operations (BatchRestoreOperation)
- group: Group restore operations (GroupRestoreOperation)

Exported Classes:
-----------------
All restore operation classes are exported at the package level for backward
compatibility with existing code.

Example Usage:
--------------
    # Import from package (recommended)
    from ibm_storage_protect.c_api_bridge.wrappers.restore import (
        RestoreOperation,
        BatchRestoreOperation,
        GroupRestoreOperation
    )

    # Or import from specific modules
    from ibm_storage_protect.c_api_bridge.wrappers.restore.single import RestoreOperation
    from ibm_storage_protect.c_api_bridge.wrappers.restore.batch import BatchRestoreOperation
    from ibm_storage_protect.c_api_bridge.wrappers.restore.group import GroupRestoreOperation
"""

from .single import RestoreOperation
from .batch import BatchRestoreOperation
from .group import GroupRestoreOperation

__all__ = [
    "RestoreOperation",
    "BatchRestoreOperation",
    "GroupRestoreOperation",
]
