"""
IBM Storage Protect Client API Type Definitions and Data Structures

This module defines all type definitions, constants, enumerations, and data structures
used by the IBM Storage Protect Client API. It provides Python ctypes bindings for
the C structures and types defined in the structs.py header file.

Module Organization:
--------------------
1. Imports: Platform-specific types (dsmapips) and version info (release)
2. Type Definitions: Basic type aliases (ObjID, dsmQueryBuff, etc.)
3. Constants: Maximum field lengths, flags, and configuration values
4. Enumerations: Query types, send types, delete types, etc.
5. Data Structures: Complex structures for API operations

Key Concepts:
-------------
- Object Identification: Objects are identified by filespace, high-level (hl),
  and low-level (ll) names, plus an object type
- Transactions: Operations are grouped into transactions using dsmBeginTxn/dsmEndTxn
- Versioning: All structures have a stVersion field for API version compatibility
- Groups: Objects can be organized into groups for coordinated backup/restore

Maximum Field Lengths:
----------------------
The API defines maximum lengths for various string fields:
- DSM_MAX_FSNAME_LENGTH: 1024 (filespace name)
- DSM_MAX_HL_LENGTH: 1024 (high-level name/directory path)
- DSM_MAX_LL_LENGTH: 256 (low-level name/filename)
- DSM_MAX_OWNER_LENGTH: 64 (object owner)
- DSM_MAX_NODE_LENGTH: 64 (node name)
- DSM_MAX_DESCR_LENGTH: 255 (description)
- DSM_MAX_OBJINFO_LENGTH: 255 (object info)
- DSM_MAX_EXT_OBJINFO_LENGTH: 1500 (extended object info)

Object Types:
-------------
- DSM_OBJ_FILE: Regular file (0x01)
- DSM_OBJ_DIRECTORY: Directory (0x02)
- DSM_OBJ_WILDCARD: Wildcard for queries (0xFE)
- DSM_OBJ_ANY_TYPE: Match any type (0xFF)

Object States:
--------------
- DSM_ACTIVE: Active backup version (0x01)
- DSM_INACTIVE: Inactive backup version (0x02)
- DSM_ANY_MATCH: Match any state (0xFF)

Query Types (dsmQueryType):
----------------------------
- qtBackup: Query backup objects
- qtBackupActive: Query active backup objects only
- qtFilespace: Query filespaces
- qtMC: Query management classes
- qtBackupGroups: Query backup groups
- qtOpenGroups: Query open groups
- qtProxyNodeAuth: Query proxy node authorizations

Send Types (dsmSendType):
--------------------------
- stBackup: Send backup data
- stBackupMountWait: Send backup with mount wait

Delete Types (dsmDelType):
---------------------------
- dtBackup: Delete backup object
- dtBackupID: Delete backup by object ID

Important Structures:
---------------------
- dsmObjName: Object identification (fs, hl, ll, objType)
- ObjAttr: Object attributes (owner, size, compression, etc.)
- DataBlk: Data buffer for send/receive operations
- dsmApiVersion: API version information
- ApiSessInfo: Session information and server details
- dsmInitExIn_t/Out_t: Extended initialization parameters
- qryRespBackupData: Backup query response
- dsmGroupHandlerIn_t/Out_t: Group operation parameters

Usage:
------
These definitions are used by dsmapifp.py to define function signatures and
by higher-level code to construct API calls.

Example:
--------
    from .dsmapitd import dsmObjName, DSM_OBJ_FILE, DSM_MAX_FSNAME_LENGTH

    # Create an object name structure
    obj_name = dsmObjName()
    obj_name.fs = b"/filesystem"
    obj_name.hl = b"/path/to"
    obj_name.ll = b"filename.txt"
    obj_name.objType = DSM_OBJ_FILE

Reference:
----------
For detailed information about data structures and their usage, see:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Data Structures" and "Type Definitions"
"""

import ctypes

# pylint: disable=wildcard-import,unused-wildcard-import,invalid-name,too-few-public-methods,too-many-lines
# =============================================================================
# Imports
# =============================================================================
from .platform_types import *     # Platform-specific base typedefs (dsUint16_t, dsStruct64_t, dsmBool_t, etc.)
from .release import *     # COMMON_VERSION / COMMON_RELEASE / COMMON_LEVEL / COMMON_SUBLEVEL


# =============================================================================
# Type Definitions
# =============================================================================

osChar_t = ctypes.c_char  # Operating system character type

# ObjID is a 64-bit struct/integer abstraction from dsmapips.h
# Used to uniquely identify objects in the IBM Storage Protect server
ObjID = dsStruct64_t

# dsmQueryBuff is an opaque buffer type used for query operations
# Typically used as a pointer (dsmQueryBuff *) which maps to void*
dsmQueryBuff = ctypes.c_void_p


# =============================================================================
# API Version Constants
# =============================================================================
# These constants define the API version to use in dsmApiVersion during dsmInit()
# They are imported from release.py and represent the current API version

DSM_API_VERSION = COMMON_VERSION      # Major version (8)
DSM_API_RELEASE = COMMON_RELEASE      # Release number (2)
DSM_API_LEVEL = COMMON_LEVEL          # Level/minor version (1)
DSM_API_SUBLEVEL = COMMON_SUBLEVEL    # Sub-level/patch version (0)

# =============================================================================
# Maximum Field Length Constants
# =============================================================================
# These constants define the maximum allowed lengths for various string fields
# in API structures. Exceeding these lengths will result in errors.

DSM_MAX_CG_DEST_LENGTH = 30          # Copy group destination name max length
DSM_MAX_CG_NAME_LENGTH = 30          # Copy group name max length
DSM_MAX_DESCR_LENGTH = 255           # Description field max length
DSM_MAX_DOMAIN_LENGTH = 30           # Policy domain name max length
DSM_MAX_FSINFO_LENGTH = 500          # Filespace info max length
DSM_MAX_USER_FSINFO_LENGTH = 480     # User-defined filespace info max length
DSM_MAX_FSNAME_LENGTH = 1024         # Filespace name max length
DSM_MAX_FSTYPE_LENGTH = 32           # Filespace type max length
DSM_MAX_HL_LENGTH = 1024             # High-level name (directory path) max length
DSM_MAX_ID_LENGTH = 64               # Node/server ID max length
DSM_MAX_LL_LENGTH = 256              # Low-level name (filename) max length
DSM_MAX_MC_NAME_LENGTH = 30          # Management class name max length
DSM_MAX_OBJINFO_LENGTH = 255         # Object info max length
DSM_MAX_EXT_OBJINFO_LENGTH = 1500    # Extended object info max length
DSM_MAX_OWNER_LENGTH = 64            # Object owner name max length
DSM_MAX_PLATFORM_LENGTH = 16         # Platform identifier max length
DSM_MAX_PS_NAME_LENGTH = 30          # Policy set name max length
DSM_MAX_SERVERTYPE_LENGTH = 32       # Server type string max length
DSM_MAX_VERIFIER_LENGTH = 64         # Password verifier max length
DSM_PATH_MAX = 1024                  # Maximum path length
DSM_NAME_MAX = 255                   # Maximum name length
DSM_MAX_NODE_LENGTH = 64             # Node name max length
DSM_MAX_RC_MSG_LENGTH = 1024         # Return code message max length
DSM_MAX_SERVER_ADDRESS = 1024        # Server address max length

# Derived maximum lengths
DSM_MAX_MC_DESCR_LENGTH = DSM_MAX_DESCR_LENGTH      # Management class description
DSM_MAX_SERVERNAME_LENGTH = DSM_MAX_ID_LENGTH       # Server name
DSM_MAX_GET_OBJ = 4080                              # Maximum objects in single get
DSM_MAX_PARTIAL_GET_OBJ = 1300                      # Maximum partial objects in get
DSM_MAX_COMPRESSTYPE_LENGTH = 32                    # Compression type string max length

# =============================================================================
# Minimum Field Lengths
# =============================================================================

DSM_MIN_COMPRESS_SIZE = 2048  # Minimum object size for compression (bytes)

# =============================================================================
# Multi-threading Flags
# =============================================================================
# Values for mtFlag parameter in dsmSetup call

DSM_MULTITHREAD = bTrue       # Enable multi-threaded mode
DSM_SINGLETHREAD = bFalse     # Single-threaded mode (default)

# =============================================================================
# Object Type Values
# =============================================================================
# Values for objType field in dsmObjName structure
# These identify the type of object being backed up or restored

DSM_OBJ_FILE = 0x01           # Regular file
DSM_OBJ_DIRECTORY = 0x02      # Directory
DSM_OBJ_RESERVED1 = 0x04      # Reserved for future use
DSM_OBJ_RESERVED2 = 0x05      # Reserved for future use
DSM_OBJ_RESERVED3 = 0x06      # Reserved for future use
DSM_OBJ_WILDCARD = 0xFE       # Wildcard for query operations
DSM_OBJ_ANY_TYPE = 0xFF       # Match any object type in queries

# =============================================================================
# Object Compression State
# =============================================================================
# Values for compressedState field in query response structures

DSM_OBJ_COMPRESSED_UNKNOWN = 0  # Compression state unknown
DSM_OBJ_COMPRESSED_YES = 1      # Object is compressed
DSM_OBJ_COMPRESSED_NO = 2       # Object is not compressed

# =============================================================================
# Group Type Values
# =============================================================================
# Values for groupType field in group-related structures
# Groups allow coordinated backup/restore of related objects

DSM_GROUPTYPE_NONE = 0x00       # No group (standalone object)
DSM_GROUPTYPE_RESERVED1 = 0x01  # Reserved for future use
DSM_GROUPTYPE_PEER = 0x02       # Peer group (objects at same level)
DSM_GROUPTYPE_RESERVED2 = 0x03  # Reserved for future use

# =============================================================================
# Group Member Type Values
# =============================================================================
# Values for memberType field in group operations

DSM_MEMBERTYPE_LEADER = 0x01    # Group leader object
DSM_MEMBERTYPE_MEMBER = 0x02    # Group member object

# =============================================================================
# Group Action Type Values
# =============================================================================
# Values for actionType field in dsmGroupHandler operations
# These define the operation to perform on a group

DSM_GROUP_ACTION_BEGIN = 0x01    # Begin a new group
DSM_GROUP_ACTION_OPEN = 0x02     # Open an existing group
DSM_GROUP_ACTION_CLOSE = 0x03    # Close a group
DSM_GROUP_ACTION_ADD = 0x04      # Add member to group
DSM_GROUP_ACTION_ASSIGNTO = 0x05 # Assign object to group
DSM_GROUP_ACTION_REMOVE = 0x06   # Remove member from group

# Copy serialization values
Copy_Serial_Static = 1
Copy_Serial_Shared_Static = 2
Copy_Serial_Shared_Dynamic = 3
Copy_Serial_Dynamic = 4

# Copy mode values
Copy_Mode_Modified = 1
Copy_Mode_Absolute = 2

# =============================================================================
# Object State Values
# =============================================================================
# Values for objState field in backup query operations
# Determines which backup versions to query

DSM_ACTIVE = 0x01      # Active backup version (most recent)
DSM_INACTIVE = 0x02    # Inactive backup version (older versions)
DSM_ANY_MATCH = 0xFF   # Match any state (active or inactive)

# =============================================================================
# Date Boundary Values
# =============================================================================
# Special values for dsmDate.year field to represent infinite dates

DATE_MINUS_INFINITE = 0x0000  # Represents earliest possible date
DATE_PLUS_INFINITE = 0xFFFF   # Represents latest possible date (no expiration)

# Bit masks for update action parameter on dsmUpdateFS()
DSM_FSUPD_FSTYPE = 0x00000002
DSM_FSUPD_FSINFO = 0x00000004
DSM_FSUPD_BACKSTARTDATE = 0x00000008
DSM_FSUPD_BACKCOMPLETEDATE = 0x00000010
DSM_FSUPD_OCCUPANCY = 0x00000020
DSM_FSUPD_CAPACITY = 0x00000040
DSM_FSUPD_RESERVED1 = 0x00000100

# Bit masks for backup/archive update action parameter on dsmUpdateObj()
DSM_BACKUPD_OWNER = 0x00000001
DSM_BACKUPD_OBJINFO = 0x00000002
DSM_BACKUPD_MC = 0x00000004

DSM_ARCHUPD_OWNER = 0x00000001
DSM_ARCHUPD_OBJINFO = 0x00000002
DSM_ARCHUPD_DESCR = 0x00000004

# repository parameter on dsmDeleteFS()
DSM_ARCHIVE_REP = 0x0A
DSM_BACKUP_REP = 0x0B
DSM_REPOS_ALL = 0x01

# vote parameter on dsmEndTxn()
DSM_VOTE_COMMIT = 1
DSM_VOTE_ABORT = 2

# ApiSessInfo flags
COMPRESS_YES = 1
COMPRESS_NO = 2
COMPRESS_CD = 3

ARCHDEL_YES = 1
ARCHDEL_NO = 2

BACKDEL_YES = 1
BACKDEL_NO = 2

# optStruct flags
DSM_PASSWD_GENERATE = 1
DSM_PASSWD_PROMPT = 0

DSM_COMM_TCP = 1
DSM_COMM_NAMEDPIPE = 2
DSM_COMM_SHM = 3

# obsolete commmethods (kept for compatibility)
DSM_COMM_PVM_IUCV = 12
DSM_COMM_3270 = 12
DSM_COMM_IUCV = 12
DSM_COMM_PWSCS = 12
DSM_COMM_SNA_LU6_2 = 12
DSM_COMM_IPXSPX = 12
DSM_COMM_NETBIOS = 12
DSM_COMM_400COMM = 12
DSM_COMM_CLIO = 12

# userNameAuthorities in dsmInitEx
DSM_USERAUTH_NONE = 0x0000
DSM_USERAUTH_ACCESS = 0x0001
DSM_USERAUTH_OWNER = 0x0002
DSM_USERAUTH_POLICY = 0x0004
DSM_USERAUTH_SYSTEM = 0x0008

# encryptionType
DSM_ENCRYPT_NO = 0x00
DSM_ENCRYPT_USER = 0x01
DSM_ENCRYPT_CLIENTENCRKEY = 0x02
DSM_ENCRYPT_DES_56BIT = 0x04
DSM_ENCRYPT_AES_128BIT = 0x08
DSM_ENCRYPT_AES_256BIT = 0x10

# mediaClass hierarchy
MEDIA_FIXED = 0x10
MEDIA_LIBRARY = 0x20
MEDIA_NETWORK = 0x30
MEDIA_SHELF = 0x40
MEDIA_OFFSITE = 0x50
MEDIA_UNAVAILABLE = 0xF0

# Partial object data structure version
PartialObjDataVersion = 1

# apiVersionEx
apiVersionExVer = 2

# appVersion
appVersionVer = 1

# del* versions
delBackVersion = 1
delArchVersion = 1
delBackIDVersion = 1

# ObjAttr version
ObjAttrVersion = 4

# mcBindKey version
mcBindKeyVersion = 1

# dsmGetList versions
dsmGetListVersion = 2
dsmGetListPORVersion = 3

# DataBlk version
DataBlkVersion = 3

# qryMCData version
qryMCDataVersion = 1

# RETINIT values
ARCH_RETINIT_CREATE = 0
ARCH_RETINIT_EVENT = 1

# qryRespMCDetailData version
qryRespMCDetailDataVersion = 4

# qryRespMCData version
qryRespMCDataVersion = 1

# qryArchiveData version
qryArchiveDataVersion = 1

# retentionInitiated values
DSM_ARCH_RETINIT_UNKNOWN = 0
DSM_ARCH_RETINIT_STARTED = 1
DSM_ARCH_RETINIT_PENDING = 2

# objHeld values
DSM_ARCH_HELD_UNKNOWN = 0
DSM_ARCH_HELD_FALSE = 1
DSM_ARCH_HELD_TRUE = 2

# qryRespArchiveData version
qryRespArchiveDataVersion = 7

# sndArchiveData version
sndArchiveDataVersion = 1

# qryBackupData version
qryBackupDataVersion = 2

# qryRespBackupData version
qryRespBackupDataVersion = 8

# qryABackupData version
qryABackupDataVersion = 1

# qryARespBackupData version
qryARespBackupDataVersion = 2

# qryBackupGroups version
qryBackupGroupsVersion = 3

# qryProxyNodeData version
qryProxyNodeDataVersion = 1

# qryRespProxyNodeData version
qryRespProxyNodeDataVersion = 1

# dsmFSUpd version
dsmFSUpdVersion = 1

# qryFSData version
qryFSDataVersion = 1

# qryRespFSData version
qryRespFSDataVersion = 4

# regFSData version
regFSDataVersion = 1

# ApiSessInfo version
#changed
ApiSessInfoVersion = 6

# qryRespAccessData version
qryRespAccessDataVersion = 1

# envSetUp version
envSetUpVersion = 4

# dsmInitEx versions
dsmInitExInVersion = 5
dsmInitExOutVersion = 3

# dsmLogEx versions
dsmLogExInVersion = 2
dsmLogExOutVersion = 1

# dsmRename versions
dsmRenameInVersion = 1
dsmRenameOutVersion = 1

# dsmEndSendObjEx versions
dsmEndSendObjExInVersion = 1
dsmEndSendObjExOutVersion = 3

# dsmGroupHandler versions
dsmGroupHandlerInVersion = 1
dsmGroupHandlerOutVersion = 1

# dsmEndTxnEx versions
dsmEndTxnExInVersion = 1
dsmEndTxnExOutVersion = 1

# dsmEndGetDataEx versions
dsmEndGetDataExInVersion = 1
dsmEndGetDataExOutVersion = 1

# dsmObjlist version
dsmObjlistVersion = 1

# dsmRetentionEvent versions
dsmRetentionEventInVersion = 1
dsmRetentionEventOutVersion = 1

# request/release/get/send buffer versions
requestBufferInVersion = 1
requestBufferOutVersion = 1
releaseBufferInVersion = 1
releaseBufferOutVersion = 1
getBufferDataInVersion = 1
getBufferDataOutVersion = 1
sendBufferDataInVersion = 1
sendBufferDataOutVersion = 1

# dsmUpdateObjEx versions
dsmUpdateObjExInVersion = 1
dsmUpdateObjExOutVersion = 1


# =============================================================================
# Enumeration Types
# =============================================================================
# Python doesn't have native enums in the C sense, so we use integer constants
# with type aliases for documentation purposes

# Default enum base type: C 'enum' is typically 'int'
_dsm_enum_t = ctypes.c_int32

# -----------------------------------------------------------------------------
# dsmGetType: Type of data retrieval operation
# -----------------------------------------------------------------------------
dsmGetType = _dsm_enum_t
gtBackup = 0x00   # Retrieve backup data
gtArchive = 0x01  # Retrieve archive data (not supported in current SDK)

# -----------------------------------------------------------------------------
# dsmQueryType: Type of query operation
# -----------------------------------------------------------------------------
dsmQueryType = _dsm_enum_t
qtArchive = 0x00         # Query archive objects (not supported)
qtBackup = 0x01          # Query backup objects (all versions)
qtBackupActive = 0x02    # Query active backup objects only
qtFilespace = 0x03       # Query filespaces
qtMC = 0x04              # Query management classes
qtReserved1 = 0x05       # Reserved for future use
qtReserved2 = 0x06       # Reserved for future use
qtReserved3 = 0x07       # Reserved for future use
qtReserved4 = 0x08       # Reserved for future use
qtBackupGroups = 0x09    # Query backup groups
qtOpenGroups = 0x0A      # Query open groups
qtReserved5 = 0x0B       # Reserved for future use
qtProxyNodeAuth = 0x0C   # Query proxy node authorizations
qtProxyNodePeer = 0x0D   # Query proxy node peers
qtReserved6 = 0x0E       # Reserved for future use
qtReserved7 = 0x0F       # Reserved for future use
qtReserved8 = 0x10       # Reserved for future use

# -----------------------------------------------------------------------------
# dsmSendType: Type of data send operation
# -----------------------------------------------------------------------------
dsmSendType = _dsm_enum_t
stBackup = 0x00              # Send backup data
stArchive = 0x01             # Send archive data (not supported)
stBackupMountWait = 0x02     # Send backup with mount wait
stArchiveMountWait = 0x03    # Send archive with mount wait (not supported)

# -----------------------------------------------------------------------------
# dsmDelType: Type of delete operation
# -----------------------------------------------------------------------------
dsmDelType = _dsm_enum_t
dtArchive = 0x00   # Delete archive object (not supported)
dtBackup = 0x01    # Delete backup object by name
dtBackupID = 0x02  # Delete backup object by ID

# -----------------------------------------------------------------------------
# dsmAccessType: Type of access control operation
# -----------------------------------------------------------------------------
dsmAccessType = _dsm_enum_t
atBackup = 0x00   # Backup access control
atArchive = 0x01  # Archive access control (not supported)

dsmDedupType = _dsm_enum_t
dedupServerOnly = 0x00
dedupClientOrServer = 0x01

dsmFailOvrCfgType = _dsm_enum_t
failOvrNotConfigured = 0x00
failOvrConfigured = 0x01
failOvrConnectedToReplServer = 0x02

dsmLogType = _dsm_enum_t
logServer = 0x00
logLocal = 0x01
logBoth = 0x02
logNone = 0x03

dsmLogSeverity = _dsm_enum_t
logSevInfo = 0x00
logSevWarning = 0x01
logSevError = 0x02
logSevSevere = 0x03
logSevLicense = 0x04
logSevTryBuy = 0x05

dsmEventType_t = _dsm_enum_t
eventRetentionActivate = 0x00
eventHoldObj = 0x01
eventReleaseObj = 0x02


# =============================================================================
# Structs / Unions
# =============================================================================

class PartialObjData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("partialObjOffset", dsStruct64_t),
        ("partialObjLength", dsStruct64_t),
    ]


class dsmDate(ctypes.Structure):
    _fields_ = [
        ("year", dsUint16_t),
        ("month", dsUint8_t),
        ("day", dsUint8_t),
        ("hour", dsUint8_t),
        ("minute", dsUint8_t),
        ("second", dsUint8_t),
    ]


class dsmApiVersion(ctypes.Structure):
    _fields_ = [
        ("version", dsUint16_t),
        ("release", dsUint16_t),
        ("level", dsUint16_t),
    ]


class dsmApiVersionEx(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("version", dsUint16_t),
        ("release", dsUint16_t),
        ("level", dsUint16_t),
        ("subLevel", dsUint16_t),
        ("unicode", dsmBool_t),
    ]


class dsmAppVersion(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("applicationVersion", dsUint16_t),
        ("applicationRelease", dsUint16_t),
        ("applicationLevel", dsUint16_t),
        ("applicationSubLevel", dsUint16_t),
    ]


class dsmObjName(ctypes.Structure):
    _fields_ = [
        ("fs", ctypes.c_char * (DSM_MAX_FSNAME_LENGTH + 1)),
        ("hl", ctypes.c_char * (DSM_MAX_HL_LENGTH + 1)),
        ("ll", ctypes.c_char * (DSM_MAX_LL_LENGTH + 1)),
        ("objType", dsUint8_t),
    ]


class delBack(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objNameP", ctypes.POINTER(dsmObjName)),
        ("copyGroup", dsUint32_t),
    ]


class delArch(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objId", dsStruct64_t),
    ]


class delBackID(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objId", dsStruct64_t),
    ]


class dsmDelInfo(ctypes.Union):
    _fields_ = [
        ("backInfo", delBack),
        ("archInfo", delArch),
        ("backIDInfo", delBackID),
    ]


class ObjAttr(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("owner", ctypes.c_char * (DSM_MAX_OWNER_LENGTH + 1)),
        ("sizeEstimate", dsStruct64_t),
        ("objCompressed", dsmBool_t),
        ("objInfoLength", dsUint16_t),
        ("objInfo", ctypes.c_char_p),
        ("mcNameP", ctypes.c_char_p),
        ("disableDeduplication", dsmBool_t),
        ("useExtObjInfo", dsmBool_t),
    ]


class mcBindKey(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("mcName", ctypes.c_char * (DSM_MAX_MC_NAME_LENGTH + 1)),
        ("backup_cg_exists", dsmBool_t),
        ("archive_cg_exists", dsmBool_t),
        ("backup_copy_dest", ctypes.c_char * (DSM_MAX_CG_DEST_LENGTH + 1)),
        ("archive_copy_dest", ctypes.c_char * (DSM_MAX_CG_DEST_LENGTH + 1)),
    ]


class dsmGetList(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("numObjId", dsUint32_t),
        ("objId", ctypes.POINTER(ObjID)),
        ("partialObjData", ctypes.POINTER(PartialObjData)),
    ]


class DataBlk(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("bufferLen", dsUint32_t),
        ("numBytes", dsUint32_t),
        ("bufferPtr", ctypes.c_char_p),
        ("numBytesCompressed", dsUint32_t),
        ("reserved", dsUint16_t),
    ]


class qryMCData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("mcName", ctypes.c_char_p),
        ("mcDetail", dsmBool_t),
    ]


class archDetailCG(ctypes.Structure):
    _fields_ = [
        ("cgName", ctypes.c_char * (DSM_MAX_CG_NAME_LENGTH + 1)),
        ("frequency", dsUint16_t),
        ("retainVers", dsUint16_t),
        ("copySer", dsUint8_t),
        ("copyMode", dsUint8_t),
        ("destName", ctypes.c_char * (DSM_MAX_CG_DEST_LENGTH + 1)),
        ("bLanFreeDest", dsmBool_t),
        ("reserved", dsmBool_t),
        ("retainInit", dsUint8_t),
        ("retainMin", dsUint16_t),
        ("bDeduplicate", dsmBool_t),
    ]


class backupDetailCG(ctypes.Structure):
    _fields_ = [
        ("cgName", ctypes.c_char * (DSM_MAX_CG_NAME_LENGTH + 1)),
        ("frequency", dsUint16_t),
        ("verDataExst", dsUint16_t),
        ("verDataDltd", dsUint16_t),
        ("retXtraVers", dsUint16_t),
        ("retOnlyVers", dsUint16_t),
        ("copySer", dsUint8_t),
        ("copyMode", dsUint8_t),
        ("destName", ctypes.c_char * (DSM_MAX_CG_DEST_LENGTH + 1)),
        ("bLanFreeDest", dsmBool_t),
        ("reserved", dsmBool_t),
        ("bDeduplicate", dsmBool_t),
    ]


class qryRespMCDetailData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("mcName", ctypes.c_char * (DSM_MAX_MC_NAME_LENGTH + 1)),
        ("mcDesc", ctypes.c_char * (DSM_MAX_MC_DESCR_LENGTH + 1)),
        ("archDet", archDetailCG),
        ("backupDet", backupDetailCG),
    ]


class qryRespMCData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("mcName", ctypes.c_char * (DSM_MAX_MC_NAME_LENGTH + 1)),
        ("mcDesc", ctypes.c_char * (DSM_MAX_MC_DESCR_LENGTH + 1)),
    ]


class qryArchiveData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objName", ctypes.POINTER(dsmObjName)),
        ("owner", ctypes.c_char_p),
        ("insDateLowerBound", dsmDate),
        ("insDateUpperBound", dsmDate),
        ("expDateLowerBound", dsmDate),
        ("expDateUpperBound", dsmDate),
        ("descr", ctypes.c_char_p),
    ]


class qryRespArchiveData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objName", dsmObjName),
        ("copyGroup", dsUint32_t),
        ("mcName", ctypes.c_char * (DSM_MAX_MC_NAME_LENGTH + 1)),
        ("owner", ctypes.c_char * (DSM_MAX_OWNER_LENGTH + 1)),
        ("objId", dsStruct64_t),
        ("reserved", dsStruct64_t),
        ("mediaClass", dsUint8_t),
        ("insDate", dsmDate),
        ("expDate", dsmDate),
        ("descr", ctypes.c_char * (DSM_MAX_DESCR_LENGTH + 1)),
        ("objInfolen", dsUint16_t),
        ("reservedObjInfo", ctypes.c_char * DSM_MAX_OBJINFO_LENGTH),
        ("restoreOrderExt", dsUint160_t),
        ("sizeEstimate", dsStruct64_t),
        ("compressType", dsUint8_t),
        ("retentionInitiated", dsUint8_t),
        ("objHeld", dsUint8_t),
        ("encryptionType", dsUint8_t),
        ("clientDeduplicated", dsmBool_t),
        ("objInfo", ctypes.c_char * DSM_MAX_EXT_OBJINFO_LENGTH),
        ("compressAlg", ctypes.c_char * (DSM_MAX_COMPRESSTYPE_LENGTH + 1)),
    ]


class sndArchiveData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("descr", ctypes.c_char_p),
    ]


class qryBackupData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objName", ctypes.POINTER(dsmObjName)),
        ("owner", ctypes.c_char_p),
        ("objState", dsUint8_t),
        ("pitDate", dsmDate),
    ]


class reservedInfo_t(ctypes.Structure):
    _fields_ = [
        ("reserved1", dsUint8_t),
        ("reserved2", dsStruct64_t),
    ]


class qryRespBackupData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objName", dsmObjName),
        ("copyGroup", dsUint32_t),
        ("mcName", ctypes.c_char * (DSM_MAX_MC_NAME_LENGTH + 1)),
        ("owner", ctypes.c_char * (DSM_MAX_OWNER_LENGTH + 1)),
        ("objId", dsStruct64_t),
        ("reserved", dsStruct64_t),
        ("mediaClass", dsUint8_t),
        ("objState", dsUint8_t),
        ("insDate", dsmDate),
        ("expDate", dsmDate),
        ("objInfolen", dsUint16_t),
        ("reservedObjInfo", ctypes.c_char * DSM_MAX_OBJINFO_LENGTH),
        ("restoreOrderExt", dsUint160_t),
        ("sizeEstimate", dsStruct64_t),
        ("baseObjId", dsStruct64_t),
        ("baseObjInfolen", dsUint16_t),
        ("baseObjInfo", dsUint8_t * DSM_MAX_OBJINFO_LENGTH),
        ("baseRestoreOrder", dsUint160_t),
        ("fsID", dsUint32_t),
        ("compressType", dsUint8_t),
        ("isGroupLeader", dsmBool_t),
        ("isOpenGroup", dsmBool_t),
        ("reserved1", dsUint8_t),
        ("reserved2", dsmBool_t),
        ("reserved3", dsUint16_t),
        ("reserved4", ctypes.POINTER(reservedInfo_t)),
        ("encryptionType", dsUint8_t),
        ("clientDeduplicated", dsmBool_t),
        ("objInfo", ctypes.c_char * DSM_MAX_EXT_OBJINFO_LENGTH),
        ("compressAlg", ctypes.c_char * (DSM_MAX_COMPRESSTYPE_LENGTH + 1)),
    ]


class qryABackupData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objName", ctypes.POINTER(dsmObjName)),
    ]


class qryARespBackupData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("objName", dsmObjName),
        ("copyGroup", dsUint32_t),
        ("mcName", ctypes.c_char * (DSM_MAX_MC_NAME_LENGTH + 1)),
        ("owner", ctypes.c_char * (DSM_MAX_OWNER_LENGTH + 1)),
        ("insDate", dsmDate),
        ("objInfolen", dsUint16_t),
        ("reservedObjInfo", ctypes.c_char * DSM_MAX_OBJINFO_LENGTH),
        ("objInfo", ctypes.c_char * DSM_MAX_EXT_OBJINFO_LENGTH),
    ]


class qryBackupGroups(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("groupType", dsUint8_t),
        ("fsName", ctypes.c_char_p),
        ("owner", ctypes.c_char_p),
        ("groupLeaderObjId", dsStruct64_t),
        ("objType", dsUint8_t),
        ("noRestoreOrder", dsmBool_t),
        ("noGroupInfo", dsmBool_t),
        ("hl", ctypes.c_char_p),
    ]


class qryProxyNodeData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("targetNodeName", ctypes.c_char_p),
    ]


class qryRespProxyNodeData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("targetNodeName", ctypes.c_char * (DSM_MAX_ID_LENGTH + 1)),
        ("peerNodeName", ctypes.c_char * (DSM_MAX_ID_LENGTH + 1)),
        ("hlAddress", ctypes.c_char * (DSM_MAX_ID_LENGTH + 1)),
        ("llAddress", ctypes.c_char * (DSM_MAX_ID_LENGTH + 1)),
    ]


class dsmDosFSAttrib(ctypes.Structure):
    _fields_ = [
        ("driveLetter", ctypes.c_char),
        ("fsInfoLength", dsUint16_t),
        ("fsInfo", ctypes.c_char * DSM_MAX_FSINFO_LENGTH),
    ]


class dsmUnixFSAttrib(ctypes.Structure):
    _fields_ = [
        ("fsInfoLength", dsUint16_t),
        ("fsInfo", ctypes.c_char * DSM_MAX_FSINFO_LENGTH),
    ]


# typedef dsmUnixFSAttrib dsmNetwareFSAttrib;
dsmNetwareFSAttrib = dsmUnixFSAttrib


class dsmFSAttr(ctypes.Union):
    _fields_ = [
        ("netwareFSAttr", dsmNetwareFSAttrib),
        ("unixFSAttr", dsmUnixFSAttrib),
        ("dosFSAttr", dsmDosFSAttrib),
    ]


class dsmFSUpd(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("fsType", ctypes.c_char_p),
        ("occupancy", dsStruct64_t),
        ("capacity", dsStruct64_t),
        ("fsAttr", dsmFSAttr),
    ]


class qryFSData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("fsName", ctypes.c_char_p),
    ]


class qryRespFSData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("fsName", ctypes.c_char * (DSM_MAX_FSNAME_LENGTH + 1)),
        ("fsType", ctypes.c_char * (DSM_MAX_FSTYPE_LENGTH + 1)),
        ("occupancy", dsStruct64_t),
        ("capacity", dsStruct64_t),
        ("fsAttr", dsmFSAttr),
        ("backStartDate", dsmDate),
        ("backCompleteDate", dsmDate),
        ("reserved1", dsmDate),
        ("lastReplStartDate", dsmDate),
        ("lastReplCmpltDate", dsmDate),
        ("lastBackOpDateFromServer", dsmDate),
        ("lastArchOpDateFromServer", dsmDate),
        ("lastSpMgOpDateFromServer", dsmDate),
        ("lastBackOpDateFromLocal", dsmDate),
        ("lastArchOpDateFromLocal", dsmDate),
        ("lastSpMgOpDateFromLocal", dsmDate),
        ("failOverWriteDelay", dsInt32_t),
    ]


class regFSData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("fsName", ctypes.c_char_p),
        ("fsType", ctypes.c_char_p),
        ("occupancy", dsStruct64_t),
        ("capacity", dsStruct64_t),
        ("fsAttr", dsmFSAttr),
    ]


class ApiSessInfo(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("stVersion", dsUint16_t),

        ("serverHost", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("serverPort", dsUint16_t),
        ("serverDate", dsmDate),
        ("serverType", ctypes.c_char * (DSM_MAX_SERVERTYPE_LENGTH + 1)),
        ("serverVer", dsUint16_t),
        ("serverRel", dsUint16_t),
        ("serverLev", dsUint16_t),
        ("serverSubLev", dsUint16_t),

        ("nodeType", ctypes.c_char * (DSM_MAX_PLATFORM_LENGTH + 1)),
        ("fsdelim", ctypes.c_char),
        ("hldelim", ctypes.c_char),
        ("compression", dsUint8_t),
        ("archDel", dsUint8_t),
        ("backDel", dsUint8_t),
        ("maxBytesPerTxn", dsUint32_t),
        ("maxObjPerTxn", dsUint16_t),

        ("id", ctypes.c_char * (DSM_MAX_ID_LENGTH + 1)),
        ("owner", ctypes.c_char * (DSM_MAX_OWNER_LENGTH + 1)),
        ("confFile", ctypes.c_char * (DSM_PATH_MAX + DSM_NAME_MAX + 1)),
        ("opNoTrace", dsUint8_t),

        ("domainName", ctypes.c_char * (DSM_MAX_DOMAIN_LENGTH + 1)),
        ("policySetName", ctypes.c_char * (DSM_MAX_PS_NAME_LENGTH + 1)),
        ("polActDate", dsmDate),
        ("dfltMCName", ctypes.c_char * (DSM_MAX_MC_NAME_LENGTH + 1)),
        ("gpBackRetn", dsUint16_t),
        ("gpArchRetn", dsUint16_t),
        ("adsmServerName", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("archiveRetentionProtection", dsmBool_t),
        ("maxBytesPerTxn_64", dsStruct64_t),
        ("lanFreeEnabled", dsmBool_t),
        ("dedupType", dsmDedupType),
        ("accessNode", ctypes.c_char * (DSM_MAX_ID_LENGTH + 1)),

        ("failOverCfgType", dsmFailOvrCfgType),
        ("replServerName", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("homeServerName", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("replServerHost", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("replServerPort", dsInt32_t),
    ]


class optStruct(ctypes.Structure):
    _fields_ = [
        ("dsmiDir", ctypes.c_char * (DSM_PATH_MAX + DSM_NAME_MAX + 1)),
        ("dsmiConfig", ctypes.c_char * (DSM_PATH_MAX + DSM_NAME_MAX + 1)),
        ("serverName", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("commMethod", dsInt16_t),
        ("serverAddress", ctypes.c_char * DSM_MAX_SERVER_ADDRESS),
        ("nodeName", ctypes.c_char * (DSM_MAX_NODE_LENGTH + 1)),
        ("compression", dsmBool_t),
        ("compressalways", dsmBool_t),
        ("passwordAccess", dsmBool_t),
    ]


class logInfo(ctypes.Structure):
    _fields_ = [
        ("message", ctypes.c_char_p),
        ("logType", dsmLogType),
    ]


class qryRespAccessData(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("node", ctypes.c_char * (DSM_MAX_ID_LENGTH + 1)),
        ("owner", ctypes.c_char * (DSM_MAX_OWNER_LENGTH + 1)),
        ("objName", dsmObjName),
        ("accessType", dsmAccessType),
        ("ruleNumber", dsUint32_t),
    ]


class envSetUp(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmiDir", ctypes.c_char * (DSM_PATH_MAX + DSM_NAME_MAX + 1)),
        ("dsmiConfig", ctypes.c_char * (DSM_PATH_MAX + DSM_NAME_MAX + 1)),
        ("dsmiLog", ctypes.c_char * (DSM_PATH_MAX + DSM_NAME_MAX + 1)),
        ("argv", ctypes.POINTER(ctypes.c_char_p)),
        ("logName", ctypes.c_char * (DSM_NAME_MAX + 1)),
        ("reserved1", dsmBool_t),
        ("reserved2", dsmBool_t),
    ]


class dsmInitExIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("apiVersionExP", ctypes.POINTER(dsmApiVersionEx)),
        ("clientNodeNameP", ctypes.c_char_p),
        ("clientOwnerNameP", ctypes.c_char_p),
        ("clientPasswordP", ctypes.c_char_p),
        ("userNameP", ctypes.c_char_p),
        ("userPasswordP", ctypes.c_char_p),
        ("applicationTypeP", ctypes.c_char_p),
        ("configfile", ctypes.c_char_p),
        ("options", ctypes.c_char_p),
        ("dirDelimiter", ctypes.c_char),
        ("useUnicode", dsmBool_t),
        ("bCrossPlatform", dsmBool_t),
        ("bService", dsmBool_t),
        ("bEncryptKeyEnabled", dsmBool_t),
        ("encryptionPasswordP", ctypes.c_char_p),
        ("useTsmBuffers", dsmBool_t),
        ("numTsmBuffers", dsUint8_t),
        ("appVersionP", ctypes.POINTER(dsmAppVersion)),
    ]


class dsmInitExOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("userNameAuthorities", dsInt16_t),
        ("infoRC", dsInt16_t),
        ("adsmServerName", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("serverVer", dsUint16_t),
        ("serverRel", dsUint16_t),
        ("serverLev", dsUint16_t),
        ("serverSubLev", dsUint16_t),
        ("bIsFailOverMode", dsmBool_t),
        ("replServerName", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
        ("homeServerName", ctypes.c_char * (DSM_MAX_SERVERNAME_LENGTH + 1)),
    ]


class dsmLogExIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("severity", dsmLogSeverity),
        ("appMsgID", ctypes.c_char * 8),
        ("logType", dsmLogType),
        ("message", ctypes.c_char_p),
        ("appName", ctypes.c_char * DSM_MAX_PLATFORM_LENGTH),
        ("osPlatform", ctypes.c_char * DSM_MAX_PLATFORM_LENGTH),
        ("appVersion", ctypes.c_char * DSM_MAX_PLATFORM_LENGTH),
    ]


class dsmLogExOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
    ]


class dsmRenameIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
        ("repository", dsUint8_t),
        ("objNameP", ctypes.POINTER(dsmObjName)),
        ("newHl", ctypes.c_char * (DSM_MAX_HL_LENGTH + 1)),
        ("newLl", ctypes.c_char * (DSM_MAX_LL_LENGTH + 1)),
        ("merge", dsmBool_t),
        ("objId", ObjID),
    ]


class dsmRenameOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
    ]


class dsmEndSendObjExIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
    ]


class dsmEndSendObjExOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("totalBytesSent", dsStruct64_t),
        ("objCompressed", dsmBool_t),
        ("totalCompressSize", dsStruct64_t),
        ("totalLFBytesSent", dsStruct64_t),
        ("encryptionType", dsUint8_t),
        ("objDeduplicated", dsmBool_t),
        ("totalDedupSize", dsStruct64_t),
    ]


class dsmGroupHandlerIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
        ("groupType", dsUint8_t),
        ("actionType", dsUint8_t),
        ("memberType", dsUint8_t),
        ("leaderObjId", dsStruct64_t),
        ("uniqueGroupTagP", ctypes.c_char_p),
        ("objNameP", ctypes.POINTER(dsmObjName)),
        ("memberObjList", dsmGetList),
    ]


class dsmGroupHandlerOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
    ]


class dsmEndTxnExIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
        ("vote", dsUint8_t),
    ]


class dsmEndTxnExOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("reason", dsUint16_t),
        ("groupLeaderObjId", dsStruct64_t),
        ("reserved1", dsUint8_t),
        ("reserved2", dsUint16_t),
    ]


class dsmEndGetDataExIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
    ]


class dsmEndGetDataExOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("reason", dsUint16_t),
        ("totalLFBytesRecv", dsStruct64_t),
    ]


class dsmObjList_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("numObjId", dsUint32_t),
        ("objId", ctypes.POINTER(ObjID)),
    ]


class dsmRetentionEventIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
        ("eventType", dsmEventType_t),
        ("objList", dsmObjList_t),
    ]


class dsmRetentionEventOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
    ]


class requestBufferIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
    ]


class requestBufferOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("tsmBufferHandle", dsUint8_t),
        ("dataPtr", ctypes.c_char_p),
        ("bufferLen", dsUint32_t),
    ]


class releaseBufferIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
        ("tsmBufferHandle", dsUint8_t),
        ("dataPtr", ctypes.c_char_p),
    ]


class releaseBufferOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
    ]


class getBufferDataIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
    ]


class getBufferDataOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("tsmBufferHandle", dsUint8_t),
        ("dataPtr", ctypes.c_char_p),
        ("numBytes", dsUint32_t),
    ]


class sendBufferDataIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
        ("tsmBufferHandle", dsUint8_t),
        ("dataPtr", ctypes.c_char_p),
        ("numBytes", dsUint32_t),
    ]


class sendBufferDataOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
    ]


class dsmUpdateObjExIn_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
        ("dsmHandle", dsUint32_t),
        ("sendType", dsmSendType),
        ("descrP", ctypes.c_char_p),
        ("objNameP", ctypes.POINTER(dsmObjName)),
        ("objAttrPtr", ctypes.POINTER(ObjAttr)),
        ("objUpdAct", dsUint32_t),
        ("archObjId", ObjID),
    ]


class dsmUpdateObjExOut_t(ctypes.Structure):
    _fields_ = [
        ("stVersion", dsUint16_t),
    ]
