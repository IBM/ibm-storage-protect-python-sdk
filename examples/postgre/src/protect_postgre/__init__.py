"""
PostgreSQL Database Protection Module
======================================

Provides backup and restore functionality for PostgreSQL databases using
IBM Storage Protect SDK.

Modules:
- postgres_backup: Backup operations (normal, batch, group)
- postgres_restore: Restore operations (normal, batch, group, PIT, partial)
"""

from protect_postgre.postgres_backup import (
    backup_normal,
    backup_batch,
    backup_group,
)

from protect_postgre.postgres_restore import (
    restore_normal,
    restore_batch,
    restore_group,
    restore_pit,
    restore_partial,
)

__all__ = [
    # Backup functions
    'backup_normal',
    'backup_batch',
    'backup_group',
    # Restore functions
    'restore_normal',
    'restore_batch',
    'restore_group',
    'restore_pit',
    'restore_partial',
]

# Made with Bob
