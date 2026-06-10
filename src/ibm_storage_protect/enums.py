"""
IBM Storage Protect SDK - Enumeration Definitions

This module defines all enumerations used throughout the IBM Storage Protect SDK.
These enums provide type-safe constants for object states, types, media types,
repositories, and mount behaviors, all backed by C API constant values.

Key Enumerations:
-----------------
1. **ObjState**: Object state for queries (ACTIVE, INACTIVE, ANY)
2. **ObjType**: Object type classification (FILE, DIRECTORY, ANY)
3. **Media**: Media type for storage (DISK, TAPE, NETWORK, etc.)
4. **Repository**: Repository type (BACKUP, ALL)
5. **MountWait**: Mount wait behavior (WAIT, SKIP)

Architecture:
-------------
All enumerations are IntEnum subclasses that map directly to C API constants.
This ensures:
- Type safety in Python code
- Direct compatibility with C API calls
- Clear, readable code instead of magic numbers
- IDE autocomplete support

C API Mapping:
--------------
Each enum value corresponds to a constant from the C API:
- DSM_ACTIVE, DSM_INACTIVE, DSM_ANY_MATCH
- DSM_OBJ_FILE, DSM_OBJ_DIRECTORY, DSM_OBJ_ANY_TYPE
- MEDIA_FIXED, MEDIA_LIBRARY, MEDIA_NETWORK, etc.
- DSM_BACKUP_REP, DSM_REPOS_ALL
- bTrue, bFalse

Usage Example:
--------------
    from ibm_storage_protect.enums import ObjState, ObjType, Media
    from ibm_storage_protect.data_models.query import BackupQueryRequest

    # Use enums in query requests
    query = BackupQueryRequest(
        Filespace="/myfs",
        Key="/data/file.txt",
        ObjState=ObjState.ACTIVE,  # Query only active objects
        ObjType=ObjType.FILE        # Query only files
    )

    # Check media type
    if backup_info.media_type == Media.TAPE:
        print("Object is on tape storage")
    elif backup_info.media_type == Media.DISK:
        print("Object is on disk storage")

    # Use ANY to match all types
    query_all = BackupQueryRequest(
        Filespace="/myfs",
        Key="/data/*",
        ObjState=ObjState.ANY,  # Match any state
        ObjType=ObjType.ANY      # Match any type
    )

Performance Considerations:
---------------------------
- Enums are lightweight integer wrappers
- No runtime overhead compared to raw integers
- Enum comparisons are as fast as integer comparisons
- Memory footprint is minimal

Thread Safety:
--------------
All enumerations are immutable and thread-safe.

Reference:
----------
IBM Storage Protect API Constants:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf

See Also:
---------
- data_models/query.py: Query models that use these enums
- data_models/backup.py: Backup models that use these enums
"""

from enum import (
    IntEnum,
)

from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_ACTIVE,
    DSM_ANY_MATCH,
    DSM_BACKUP_REP,
    DSM_INACTIVE,
    DSM_OBJ_ANY_TYPE,
    DSM_OBJ_DIRECTORY,
    DSM_OBJ_FILE,
    DSM_REPOS_ALL,
    MEDIA_FIXED,
    MEDIA_LIBRARY,
    MEDIA_NETWORK,
    MEDIA_OFFSITE,
    MEDIA_SHELF,
    MEDIA_UNAVAILABLE,
    bFalse,
    bTrue,
)

# Default management classes for backup operations
_DEFAULT_MGMT_CLASSES = ["STANDARD"]


class ObjState(IntEnum):
    """
    Enumeration of object states for query operations.

    Object states determine which versions of objects are returned in queries.
    Active objects are the current versions, while inactive objects are
    previous versions that have been superseded.

    Values
    ------
    ACTIVE : int
        Query only active (current) object versions
    INACTIVE : int
        Query only inactive (superseded) object versions
    ANY : int
        Query all object versions regardless of state

    Notes
    -----
    - ACTIVE is the most commonly used state for queries
    - INACTIVE is useful for retrieving previous versions
    - ANY returns all versions, which can result in large result sets

    Example
    -------
    >>> from ibm_storage_protect.enums import ObjState
    >>> query.ObjState = ObjState.ACTIVE
    >>> print(query.ObjState.name)
    'ACTIVE'
    >>> print(query.ObjState.value)
    1
    """
    ACTIVE   = DSM_ACTIVE
    INACTIVE = DSM_INACTIVE
    ANY      = DSM_ANY_MATCH


class ObjType(IntEnum):
    """
    Enumeration of object types for classification and filtering.

    Object types distinguish between files, directories, and other object
    types in the IBM Storage Protect system.

    Values
    ------
    FILE : int
        Regular file object
    DIRECTORY : int
        Directory object
    ANY : int
        Any object type (files, directories, etc.)

    Notes
    -----
    - FILE is the most common object type
    - DIRECTORY objects store directory metadata
    - ANY is useful for queries that should match all object types

    Example
    -------
    >>> from ibm_storage_protect.enums import ObjType
    >>> if obj.type == ObjType.FILE:
    ...     print("This is a file")
    >>> elif obj.type == ObjType.DIRECTORY:
    ...     print("This is a directory")
    """
    FILE      = DSM_OBJ_FILE
    DIRECTORY = DSM_OBJ_DIRECTORY
    ANY       = DSM_OBJ_ANY_TYPE


class Media(IntEnum):
    """
    Enumeration of media types for storage classification.

    Media types indicate where backed-up data is physically stored in the
    IBM Storage Protect system.

    Values
    ------
    DISK : int
        Data stored on disk storage pools
    TAPE : int
        Data stored on tape library
    NETWORK : int
        Data stored on network-attached storage
    OFFSITE : int
        Data stored at offsite location
    SHELF : int
        Data on tape stored on shelf (not in library)
    UNAVAILABLE : int
        Media is currently unavailable

    Notes
    -----
    - DISK provides fastest access times
    - TAPE is used for long-term archival storage
    - OFFSITE indicates data is at a remote location
    - UNAVAILABLE means data cannot be accessed immediately

    Example
    -------
    >>> from ibm_storage_protect.enums import Media
    >>> if backup.media == Media.TAPE:
    ...     print("Data is on tape - restore may take longer")
    >>> elif backup.media == Media.DISK:
    ...     print("Data is on disk - fast restore available")
    """
    DISK       = MEDIA_FIXED
    TAPE       = MEDIA_LIBRARY
    NETWORK    = MEDIA_NETWORK
    OFFSITE    = MEDIA_OFFSITE
    SHELF      = MEDIA_SHELF
    UNAVAILABLE = MEDIA_UNAVAILABLE


class Repository(IntEnum):
    """
    Enumeration of repository types for data classification.

    Repositories distinguish between backup data and archive data in the
    IBM Storage Protect system.

    Values
    ------
    BACKUP : int
        Backup repository (version-based retention)
    ALL : int
        All repositories (backup and archive)

    Notes
    -----
    - BACKUP repository uses version-based retention policies
    - Archive repository uses date-based retention policies
    - ALL is useful for queries across all data types

    Example
    -------
    >>> from ibm_storage_protect.enums import Repository
    >>> query.repository = Repository.BACKUP
    """
    BACKUP = DSM_BACKUP_REP
    ALL    = DSM_REPOS_ALL


class MountWait(IntEnum):
    """
    Enumeration of mount wait behaviors for tape operations.

    Mount wait determines whether operations should wait for tape mounts
    or skip objects that require unavailable tapes.

    Values
    ------
    WAIT : int
        Wait for tape mount if needed (bTrue)
    SKIP : int
        Skip objects requiring tape mount (bFalse)

    Notes
    -----
    - WAIT may cause operations to pause until tape is mounted
    - SKIP allows operations to continue without waiting
    - Only relevant for tape-based storage

    Example
    -------
    >>> from ibm_storage_protect.enums import MountWait
    >>> restore.mount_wait = MountWait.SKIP  # Don't wait for tapes
    """
    WAIT = bTrue
    SKIP = bFalse

# Made with Bob
