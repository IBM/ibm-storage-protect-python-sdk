"""
IBM Storage Protect Client API - Consolidated Wrappers Package

This package provides consolidated Python wrappers for IBM Storage Protect Client API operations,
unifying the former c_api_internal and c_api_controlpath packages.
"""

from .backup import BackupOperation, BatchBackupOperation, GroupBackupOperation
from .restore import RestoreOperation, BatchRestoreOperation, GroupRestoreOperation
from .query import QueryOperation
from .session import SessionManager
from .filespace import register_filespace, update_filespace, delete_filespace
from .object import DeleteObjectOperation, RenameObjectOperation, UpdateObjectOperation

__all__ = [
    # Backup operations
    "BackupOperation",
    "BatchBackupOperation",
    "GroupBackupOperation",
    # Restore operations
    "RestoreOperation",
    "BatchRestoreOperation",
    "GroupRestoreOperation",
    # Query operations
    "QueryOperation",
    # Session management
    "SessionManager",
    # Filespace management
    "register_filespace",
    "update_filespace",
    "delete_filespace",
    # Object management
    "DeleteObjectOperation",
    "RenameObjectOperation",
    "UpdateObjectOperation"
]
