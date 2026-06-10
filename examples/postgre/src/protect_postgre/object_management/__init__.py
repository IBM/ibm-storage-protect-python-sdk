"""
Object Management Module for PostgreSQL Backups
================================================

This module provides examples of object management operations on backed-up
PostgreSQL database files in IBM Storage Protect.

Available Examples
------------------
- single.py: Object management on single backed-up objects
- group.py: Object management on group-backed-up objects
- batch.py: Object management on batch-backed-up objects
- delete_filespace.py: Complete filespace deletion (final cleanup)

Operations Demonstrated
-----------------------
1. Rename objects (change object paths)
2. Update object attributes (owner, management class)
3. Delete objects by name
4. Delete objects by ID
5. Delete entire filespace

Usage Order
-----------
1. Run backup examples first (single.py, group.py, batch.py from backup/)
2. Run object management examples (single.py, group.py, batch.py)
3. Run delete_filespace.py for final cleanup

⚠️ WARNING
----------
- Object deletion operations are IRREVERSIBLE
- Filespace deletion removes ALL objects permanently
- Always verify object IDs before deletion
"""

__all__ = [
    'single',
    'group',
    'batch',
    'delete_filespace'
]

# Made with Bob
