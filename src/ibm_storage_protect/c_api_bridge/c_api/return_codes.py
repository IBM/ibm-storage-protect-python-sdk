"""
IBM Storage Protect Client API Return Codes

This module defines all return codes and reason codes used by the IBM Storage Protect
Client API. Return codes indicate the success or failure of API function calls, while
reason codes provide additional context about why an operation failed.

Return Code Categories:
-----------------------
1. Success/Failure Codes (0, -1)
2. Transaction Abort Reason Codes (1-258, 5200)
3. Server Signon Reject Codes (51-79)
4. General Error Codes (100+)
5. Policy Set Error Codes (180-199)
6. Trusted Communication Agent Codes (161, 200, 292-299)
7. Options Error Codes (400-431)
8. Volume Label Codes (600-610)
9. Message File Processing Codes (610-615)
10. Log Message Codes (620-622)
11. Client-Only Codes (900-999)
12. TCP/IP Error Codes (negative range: -50 to -58)
13. CommTSM Error Codes (-71 to -72)
14. NETBIOS Error Codes (-151 to -161)
15. Named Pipe Error Codes (-190)
16. Shared Memory Protocol Codes (-450 to -452)
17. API Parameter Validation Codes (2000-2090)
18. String Length Validation Codes (2100-2107)
19. Access Control Codes (2110-2120)
20. Query and Buffer Codes (2200-2231)
21. Miscellaneous API Codes (2300-2303)
22. Encryption Codes (4580-4584)
23. Clustering Codes (4600-4606)
24. Proxy Codes (5702-5749)
25. Cryptography/Security Codes (5801-5802)
26. SSL Communication Codes (-361 to -365)
27. Client-Side Deduplication Codes (6300-6302)

Usage:
------
These constants are returned by IBM Storage Protect Client API functions and should
be checked after each API call to determine success or failure and take appropriate
action.

Example:
--------
    rc = lib.dsmInit(...)
    if rc == DSM_RC_SUCCESSFUL:
        print("Initialization successful")
    elif rc == DSM_RC_REJECT_ID_UNKNOWN:
        print("Node name not recognized by server")
    else:
        print(f"Initialization failed with return code: {rc}")

Reference:
----------
For detailed information about return codes and their meanings, see:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapter: "Return Codes" and "Reason Codes"
"""


import ctypes

# =============================================================================
# Type Definitions
# =============================================================================

# RetCode is the standard return type for most API functions
RetCode = ctypes.c_int

# =============================================================================
# Successful/Unsuccessful Return Codes
# =============================================================================

DSM_RC_SUCCESSFUL = 0    # Operation completed successfully
DSM_RC_OK = 0            # Alias for DSM_RC_SUCCESSFUL
DSM_RC_UNSUCCESSFUL = -1  # Generic failure code

# =============================================================================
# Transaction Abort Reason Codes (dsmEndTxn)
# =============================================================================
# These codes are returned as the 'reason' parameter in dsmEndTxn when a
# transaction is aborted. They provide specific information about why the
# transaction failed.

DSM_RS_ABORT_SYSTEM_ERROR = 1              # System error occurred
DSM_RS_ABORT_NO_MATCH = 2                  # No matching objects found
DSM_RS_ABORT_BY_CLIENT = 3                 # Transaction aborted by client request
DSM_RS_ABORT_ACTIVE_NOT_FOUND = 4          # Active object not found
DSM_RS_ABORT_NO_DATA = 5                   # No data available
DSM_RS_ABORT_BAD_VERIFIER = 6              # Invalid password/verifier
DSM_RS_ABORT_NODE_IN_USE = 7               # Node is currently in use
DSM_RS_ABORT_EXPDATE_TOO_LOW = 8           # Expiration date is too low
DSM_RS_ABORT_DATA_OFFLINE = 9              # Data is offline (on tape)
DSM_RS_ABORT_EXCLUDED_BY_SIZE = 10         # Object excluded by size limit
DSM_RS_ABORT_NO_STO_SPACE_SKIP = 11        # No storage space, skip object
DSM_RS_ABORT_NO_REPOSIT_SPACE = DSM_RS_ABORT_NO_STO_SPACE_SKIP  # Alias
DSM_RS_ABORT_MOUNT_NOT_POSSIBLE = 12       # Cannot mount required media
DSM_RS_ABORT_SIZESTIMATE_EXCEED = 13       # Size estimate exceeded
DSM_RS_ABORT_DATA_UNAVAILABLE = 14         # Data temporarily unavailable
DSM_RS_ABORT_RETRY = 15                    # Retry the operation
DSM_RS_ABORT_NO_LOG_SPACE = 16             # Server log space exhausted
DSM_RS_ABORT_NO_DB_SPACE = 17              # Server database space exhausted
DSM_RS_ABORT_NO_MEMORY = 18                # Server out of memory
DSM_RS_ABORT_FS_NOT_DEFINED = 20           # Filespace not defined
DSM_RS_ABORT_NODE_ALREADY_DEFED = 21       # Node already defined
DSM_RS_ABORT_NO_DEFAULT_DOMAIN = 22        # No default domain assigned
DSM_RS_ABORT_INVALID_NODENAME = 23         # Invalid node name
DSM_RS_ABORT_INVALID_POL_BIND = 24         # Invalid policy binding
DSM_RS_ABORT_DEST_NOT_DEFINED = 25         # Destination not defined
DSM_RS_ABORT_WAIT_FOR_SPACE = 26           # Waiting for storage space
DSM_RS_ABORT_NOT_AUTHORIZED = 27           # Not authorized for operation
DSM_RS_ABORT_RULE_ALREADY_DEFED = 28       # Rule already defined
DSM_RS_ABORT_NO_STOR_SPACE_STOP = 29       # No storage space, stop operation
DSM_RS_ABORT_LICENSE_VIOLATION = 30        # License limit exceeded
DSM_RS_ABORT_EXTOBJID_ALREADY_EXISTS = 31  # External object ID already exists
DSM_RS_ABORT_DUPLICATE_OBJECT = 32         # Duplicate object detected
DSM_RS_ABORT_INVALID_OFFSET = 33           # Invalid offset specified
DSM_RS_ABORT_INVALID_LENGTH = 34           # Invalid length specified
DSM_RS_ABORT_STRING_ERROR = 35             # String processing error
DSM_RS_ABORT_NODE_NOT_AUTHORIZED = 36      # Node not authorized
DSM_RS_ABORT_RESTART_NOT_POSSIBLE = 37     # Cannot restart operation
DSM_RS_ABORT_RESTORE_IN_PROGRESS = 38      # Restore already in progress
DSM_RS_ABORT_SYNTAX_ERROR = 39             # Syntax error in command
DSM_RS_ABORT_DATA_SKIPPED = 40             # Data was skipped
DSM_RS_ABORT_EXCEED_MAX_MP = 41            # Exceeded maximum mount points
DSM_RS_ABORT_NO_OBJSET_MATCH = 42          # No object set match
DSM_RS_ABORT_PVR_ERROR = 43                # Point-in-time restore error
DSM_RS_ABORT_BAD_RECOGTOKEN = 44           # Invalid recognition token
DSM_RS_ABORT_MERGE_ERROR = 45              # Error during merge operation
DSM_RS_ABORT_FSRENAME_ERROR = 46           # Filespace rename error
DSM_RS_ABORT_INVALID_OPERATION = 47        # Invalid operation requested
DSM_RS_ABORT_STGPOOL_UNDEFINED = 48        # Storage pool not defined
DSM_RS_ABORT_INVALID_DATA_FORMAT = 49      # Invalid data format
DSM_RS_ABORT_DATAMOVER_UNDEFINED = 50      # Data mover not defined
DSM_RS_ABORT_INVALID_MOVER_TYPE = 231      # Invalid mover type
DSM_RS_ABORT_ITEM_IN_USE = 232             # Item currently in use
DSM_RS_ABORT_LOCK_CONFLICT = 233           # Lock conflict detected
DSM_RS_ABORT_SRV_PLUGIN_COMM_ERROR = 234   # Server plugin communication error
DSM_RS_ABORT_SRV_PLUGIN_OS_ERROR = 235     # Server plugin OS error
DSM_RS_ABORT_CRC_FAILED = 236              # CRC check failed
DSM_RS_ABORT_INVALID_GROUP_ACTION = 237    # Invalid group action
DSM_RS_ABORT_DISK_UNDEFINED = 238          # Disk not defined
DSM_RS_ABORT_BAD_DESTINATION = 239         # Invalid destination
DSM_RS_ABORT_DATAMOVER_NOT_AVAILABLE = 240 # Data mover not available
DSM_RS_ABORT_STGPOOL_COPY_CONT_NO = 241    # Storage pool copy continuation number error
DSM_RS_ABORT_RETRY_SINGLE_TXN = 242        # Retry as single transaction
DSM_RS_ABORT_TOC_CREATION_FAIL = 243       # Table of contents creation failed
DSM_RS_ABORT_TOC_LOAD_FAIL = 244           # Table of contents load failed
DSM_RS_ABORT_PATH_RESTRICTED = 245         # Path is restricted
DSM_RS_ABORT_NO_LANFREE_SCRATCH = 246      # No LAN-free scratch media
DSM_RS_ABORT_INSERT_NOT_ALLOWED = 247      # Insert operation not allowed
DSM_RS_ABORT_DELETE_NOT_ALLOWED = 248      # Delete operation not allowed
DSM_RS_ABORT_TXN_LIMIT_EXCEEDED = 249      # Transaction limit exceeded
DSM_RS_ABORT_OBJECT_ALREADY_HELD = 250     # Object already on legal hold
DSM_RS_ABORT_INVALID_CHUNK_REFERENCE = 254 # Invalid chunk reference (deduplication)
DSM_RS_ABORT_DESTINATION_NOT_DEDUP = 255   # Destination does not support deduplication
DSM_RS_ABORT_DESTINATION_POOL_CHANGED = 257 # Destination pool changed
DSM_RS_ABORT_NOT_ROOT = 258                # Not running as root user
DSM_RS_ABORT_CERTIFICATE_NOT_FOUND = 5200  # SSL certificate not found

# =============================================================================
# Return Codes Mapped from Reason Codes
# =============================================================================
# These return codes mirror the reason codes above for backward compatibility
DSM_RC_ABORT_SYSTEM_ERROR = DSM_RS_ABORT_SYSTEM_ERROR
DSM_RC_ABORT_NO_MATCH = DSM_RS_ABORT_NO_MATCH
DSM_RC_ABORT_BY_CLIENT = DSM_RS_ABORT_BY_CLIENT
DSM_RC_ABORT_ACTIVE_NOT_FOUND = DSM_RS_ABORT_ACTIVE_NOT_FOUND
DSM_RC_ABORT_NO_DATA = DSM_RS_ABORT_NO_DATA
DSM_RC_ABORT_BAD_VERIFIER = DSM_RS_ABORT_BAD_VERIFIER
DSM_RC_ABORT_NODE_IN_USE = DSM_RS_ABORT_NODE_IN_USE
DSM_RC_ABORT_EXPDATE_TOO_LOW = DSM_RS_ABORT_EXPDATE_TOO_LOW
DSM_RC_ABORT_DATA_OFFLINE = DSM_RS_ABORT_DATA_OFFLINE
DSM_RC_ABORT_EXCLUDED_BY_SIZE = DSM_RS_ABORT_EXCLUDED_BY_SIZE
DSM_RC_ABORT_NO_REPOSIT_SPACE = DSM_RS_ABORT_NO_STO_SPACE_SKIP
DSM_RC_ABORT_NO_STO_SPACE_SKIP = DSM_RS_ABORT_NO_STO_SPACE_SKIP
DSM_RC_ABORT_MOUNT_NOT_POSSIBLE = DSM_RS_ABORT_MOUNT_NOT_POSSIBLE
DSM_RC_ABORT_SIZESTIMATE_EXCEED = DSM_RS_ABORT_SIZESTIMATE_EXCEED
DSM_RC_ABORT_DATA_UNAVAILABLE = DSM_RS_ABORT_DATA_UNAVAILABLE
DSM_RC_ABORT_RETRY = DSM_RS_ABORT_RETRY
DSM_RC_ABORT_NO_LOG_SPACE = DSM_RS_ABORT_NO_LOG_SPACE
DSM_RC_ABORT_NO_DB_SPACE = DSM_RS_ABORT_NO_DB_SPACE
DSM_RC_ABORT_NO_MEMORY = DSM_RS_ABORT_NO_MEMORY
DSM_RC_ABORT_FS_NOT_DEFINED = DSM_RS_ABORT_FS_NOT_DEFINED
DSM_RC_ABORT_NODE_ALREADY_DEFED = DSM_RS_ABORT_NODE_ALREADY_DEFED
DSM_RC_ABORT_NO_DEFAULT_DOMAIN = DSM_RS_ABORT_NO_DEFAULT_DOMAIN
DSM_RC_ABORT_INVALID_NODENAME = DSM_RS_ABORT_INVALID_NODENAME
DSM_RC_ABORT_INVALID_POL_BIND = DSM_RS_ABORT_INVALID_POL_BIND
DSM_RC_ABORT_DEST_NOT_DEFINED = DSM_RS_ABORT_DEST_NOT_DEFINED
DSM_RC_ABORT_WAIT_FOR_SPACE = DSM_RS_ABORT_WAIT_FOR_SPACE
DSM_RC_ABORT_NOT_AUTHORIZED = DSM_RS_ABORT_NOT_AUTHORIZED
DSM_RC_ABORT_RULE_ALREADY_DEFED = DSM_RS_ABORT_RULE_ALREADY_DEFED
DSM_RC_ABORT_NO_STOR_SPACE_STOP = DSM_RS_ABORT_NO_STOR_SPACE_STOP
DSM_RC_ABORT_LICENSE_VIOLATION = DSM_RS_ABORT_LICENSE_VIOLATION
DSM_RC_ABORT_EXTOBJID_ALREADY_EXISTS = DSM_RS_ABORT_EXTOBJID_ALREADY_EXISTS
DSM_RC_ABORT_DUPLICATE_OBJECT = DSM_RS_ABORT_DUPLICATE_OBJECT
DSM_RC_ABORT_INVALID_OFFSET = DSM_RS_ABORT_INVALID_OFFSET
DSM_RC_ABORT_INVALID_LENGTH = DSM_RS_ABORT_INVALID_LENGTH
DSM_RC_ABORT_STRING_ERROR = DSM_RS_ABORT_STRING_ERROR
DSM_RC_ABORT_NODE_NOT_AUTHORIZED = DSM_RS_ABORT_NODE_NOT_AUTHORIZED
DSM_RC_ABORT_RESTART_NOT_POSSIBLE = DSM_RS_ABORT_RESTART_NOT_POSSIBLE
DSM_RC_ABORT_RESTORE_IN_PROGRESS = DSM_RS_ABORT_RESTORE_IN_PROGRESS
DSM_RC_ABORT_SYNTAX_ERROR = DSM_RS_ABORT_SYNTAX_ERROR
DSM_RC_ABORT_DATA_SKIPPED = DSM_RS_ABORT_DATA_SKIPPED
DSM_RC_ABORT_EXCEED_MAX_MP = DSM_RS_ABORT_EXCEED_MAX_MP
DSM_RC_ABORT_NO_OBJSET_MATCH = DSM_RS_ABORT_NO_OBJSET_MATCH
DSM_RC_ABORT_PVR_ERROR = DSM_RS_ABORT_PVR_ERROR
DSM_RC_ABORT_BAD_RECOGTOKEN = DSM_RS_ABORT_BAD_RECOGTOKEN
DSM_RC_ABORT_MERGE_ERROR = DSM_RS_ABORT_MERGE_ERROR
DSM_RC_ABORT_FSRENAME_ERROR = DSM_RS_ABORT_FSRENAME_ERROR
DSM_RC_ABORT_INVALID_OPERATION = DSM_RS_ABORT_INVALID_OPERATION
DSM_RC_ABORT_STGPOOL_UNDEFINED = DSM_RS_ABORT_STGPOOL_UNDEFINED
DSM_RC_ABORT_INVALID_DATA_FORMAT = DSM_RS_ABORT_INVALID_DATA_FORMAT
DSM_RC_ABORT_DATAMOVER_UNDEFINED = DSM_RS_ABORT_DATAMOVER_UNDEFINED
DSM_RC_ABORT_INVALID_MOVER_TYPE = DSM_RS_ABORT_INVALID_MOVER_TYPE
DSM_RC_ABORT_ITEM_IN_USE = DSM_RS_ABORT_ITEM_IN_USE
DSM_RC_ABORT_LOCK_CONFLICT = DSM_RS_ABORT_LOCK_CONFLICT
DSM_RC_ABORT_SRV_PLUGIN_COMM_ERROR = DSM_RS_ABORT_SRV_PLUGIN_COMM_ERROR
DSM_RC_ABORT_SRV_PLUGIN_OS_ERROR = DSM_RS_ABORT_SRV_PLUGIN_OS_ERROR
DSM_RC_ABORT_CRC_FAILED = DSM_RS_ABORT_CRC_FAILED
DSM_RC_ABORT_INVALID_GROUP_ACTION = DSM_RS_ABORT_INVALID_GROUP_ACTION
DSM_RC_ABORT_DISK_UNDEFINED = DSM_RS_ABORT_DISK_UNDEFINED
DSM_RC_ABORT_BAD_DESTINATION = DSM_RS_ABORT_BAD_DESTINATION
DSM_RC_ABORT_DATAMOVER_NOT_AVAILABLE = DSM_RS_ABORT_DATAMOVER_NOT_AVAILABLE
DSM_RC_ABORT_STGPOOL_COPY_CONT_NO = DSM_RS_ABORT_STGPOOL_COPY_CONT_NO
DSM_RC_ABORT_RETRY_SINGLE_TXN = DSM_RS_ABORT_RETRY_SINGLE_TXN
DSM_RC_ABORT_TOC_CREATION_FAIL = DSM_RS_ABORT_TOC_CREATION_FAIL
DSM_RC_ABORT_TOC_LOAD_FAIL = DSM_RS_ABORT_TOC_LOAD_FAIL
DSM_RC_ABORT_PATH_RESTRICTED = DSM_RS_ABORT_PATH_RESTRICTED
DSM_RC_ABORT_NO_LANFREE_SCRATCH = DSM_RS_ABORT_NO_LANFREE_SCRATCH
DSM_RC_ABORT_INSERT_NOT_ALLOWED = DSM_RS_ABORT_INSERT_NOT_ALLOWED
DSM_RC_ABORT_DELETE_NOT_ALLOWED = DSM_RS_ABORT_DELETE_NOT_ALLOWED
DSM_RC_ABORT_TXN_LIMIT_EXCEEDED = DSM_RS_ABORT_TXN_LIMIT_EXCEEDED
DSM_RC_ABORT_OBJECT_ALREADY_HELD = DSM_RS_ABORT_OBJECT_ALREADY_HELD
DSM_RC_ABORT_INVALID_CHUNK_REFERENCE = DSM_RS_ABORT_INVALID_CHUNK_REFERENCE
DSM_RC_ABORT_DESTINATION_NOT_DEDUP = DSM_RS_ABORT_DESTINATION_NOT_DEDUP
DSM_RC_ABORT_DESTINATION_POOL_CHANGED = DSM_RS_ABORT_DESTINATION_POOL_CHANGED
DSM_RC_ABORT_NOT_ROOT = DSM_RS_ABORT_NOT_ROOT
DSM_RC_ABORT_CERTIFICATE_NOT_FOUND = DSM_RS_ABORT_CERTIFICATE_NOT_FOUND

# =============================================================================
# Server Signon Reject Codes (51-99)
# =============================================================================
# These codes are returned during dsmInit/dsmInitEx when the server rejects
# the client's signon attempt. They indicate authentication or authorization
# issues, or server-side problems preventing the connection.

DSM_RC_REJECT_NO_RESOURCES = 51            # Server has no resources available
DSM_RC_REJECT_VERIFIER_EXPIRED = 52        # Password has expired
DSM_RC_REJECT_ID_UNKNOWN = 53              # Node name not recognized by server
DSM_RC_REJECT_DUPLICATE_ID = 54            # Duplicate node ID detected
DSM_RC_REJECT_SERVER_DISABLED = 55         # Server is disabled
DSM_RC_REJECT_CLOSED_REGISTER = 56         # Server registration is closed
DSM_RC_REJECT_CLIENT_DOWNLEVEL = 57        # Client version too old for server
DSM_RC_REJECT_SERVER_DOWNLEVEL = 58        # Server version too old for client
DSM_RC_REJECT_ID_IN_USE = 59               # Node ID currently in use
DSM_RC_REJECT_ID_LOCKED = 61               # Node ID is locked
DSM_RC_SIGNONREJECT_LICENSE_MAX = 62       # Maximum licensed nodes exceeded
DSM_RC_REJECT_NO_MEMORY = 63               # Server out of memory
DSM_RC_REJECT_NO_DB_SPACE = 64             # Server database space exhausted
DSM_RC_REJECT_NO_LOG_SPACE = 65            # Server log space exhausted
DSM_RC_REJECT_INTERNAL_ERROR = 66          # Server internal error
DSM_RC_SIGNONREJECT_INVALID_CLI = 67       # Invalid client
DSM_RC_CLIENT_NOT_ARCHRETPROT = 68         # Client not enabled for retention protection
DSM_RC_REJECT_LASTSESS_CANCELED = 69       # Last session was canceled
DSM_RC_REJECT_UNICODE_NOT_ALLOWED = 70     # Unicode not allowed
DSM_RC_REJECT_NOT_AUTHORIZED = 71          # Not authorized for this operation
DSM_RC_REJECT_TOKEN_TIMEOUT = 72           # Authentication token timeout
DSM_RC_REJECT_INVALID_NODE_TYPE = 73       # Invalid node type
DSM_RC_REJECT_INVALID_SESSIONINIT = 74     # Invalid session initialization
DSM_RC_REJECT_WRONG_PORT = 75              # Connected to wrong port
DSM_RC_CLIENT_NOT_SPMRETPROT = 79          # Client not enabled for space management retention protection

# =============================================================================
# General Error Codes (100+)
# =============================================================================
# Common error codes returned by various API functions
DSM_RC_USER_ABORT = 101
DSM_RC_NO_MEMORY = 102
DSM_RC_TA_COMM_DOWN = 2021
DSM_RC_FILE_NOT_FOUND = 104
DSM_RC_PATH_NOT_FOUND = 105
DSM_RC_ACCESS_DENIED = 106
DSM_RC_NO_HANDLES = 107
DSM_RC_FILE_EXISTS = 108
DSM_RC_INVALID_PARM = 109
DSM_RC_INVALID_HANDLE = 110
DSM_RC_DISK_FULL = 111
DSM_RC_PROTOCOL_VIOLATION = 113
DSM_RC_UNKNOWN_ERROR = 114
DSM_RC_UNEXPECTED_ERROR = 115
DSM_RC_FILE_BEING_EXECUTED = 116
DSM_RC_DIR_NO_SPACE = 117
DSM_RC_LOOPED_SYM_LINK = 118
DSM_RC_FILE_NAME_TOO_LONG = 119
DSM_RC_FILE_SPACE_LOCKED = 120
DSM_RC_FINISHED = 121
DSM_RC_UNKNOWN_FORMAT = 122
DSM_RC_NO_AUTHORIZATION = 123
DSM_RC_FILE_SPACE_NOT_FOUND = 124
DSM_RC_TXN_ABORTED = 125
DSM_RC_SUBDIR_AS_FILE = 126
DSM_RC_PROCESS_NO_SPACE = 127
DSM_RC_PATH_TOO_LONG = 128
DSM_RC_NOT_COMPRESSED = 129
DSM_RC_TOO_MANY_BITS = 130
DSM_RC_SYSTEM_ERROR = 131
DSM_RC_NO_SERVER_RESOURCES = 132
DSM_RC_FS_NOT_KNOWN = 133
DSM_RC_NO_LEADING_DIRSEP = 134
DSM_RC_WILDCARD_DIR = 135
DSM_RC_COMM_PROTOCOL_ERROR = 136
DSM_RC_AUTH_FAILURE = 137
DSM_RC_TA_NOT_VALID = 138
DSM_RC_KILLED = 139
DSM_RC_RETRY = 143
DSM_RC_WOULD_BLOCK = 145
DSM_RC_TOO_SMALL = 146
DSM_RC_UNCLOSED = 147
DSM_RC_NO_STARTING_DELIMITER = 148
DSM_RC_NEEDED_DIR_DELIMITER = 149
DSM_RC_UNKNOWN_FILE_DATA_TYPE = 150
DSM_RC_BUFFER_OVERFLOW = 151
DSM_RC_NO_COMPRESS_MEMORY = 154
DSM_RC_COMPRESS_GREW = 155
DSM_RC_INV_COMM_METHOD = 156
DSM_RC_WILL_ABORT = 157
DSM_RC_FS_WRITE_LOCKED = 158
DSM_RC_SKIPPED_BY_USER = 159
DSM_RC_TA_NOT_FOUND = 160
DSM_RC_TA_ACCESS_DENIED = 161
DSM_RC_FS_NOT_READY = 162
DSM_RC_FS_IS_BAD = 163
DSM_RC_FIO_ERROR = 164
DSM_RC_WRITE_FAILURE = 165
DSM_RC_OVER_FILE_SIZE_LIMIT = 166
DSM_RC_CANNOT_MAKE = 167
DSM_RC_NO_PASS_FILE = 168
DSM_RC_VERFILE_OLD = 169
DSM_RC_INPUT_ERROR = 173
DSM_RC_REJECT_PLATFORM_MISMATCH = 174
DSM_RC_TL_NOT_FILE_OWNER = 175
DSM_RC_COMPRESSED_DATA_CORRUPTED = 176
DSM_RC_UNMATCHED_QUOTE = 177
DSM_RC_SIGNON_FAILOVER_MODE = 178
DSM_RC_FAILOVER_MODE_FUNC_BLOCKED = 179

# =============================================================================
# Policy Set Error Codes (180-199)
# =============================================================================
# Errors related to policy set configuration and management class binding

DSM_RC_PS_MULTBCG = 181                    # Multiple backup copy groups
DSM_RC_PS_MULTACG = 182                    # Multiple archive copy groups (not supported)
DSM_RC_PS_NODFLTMC = 183                   # No default management class
DSM_RC_TL_NOBCG = 184                      # No backup copy group
DSM_RC_TL_EXCLUDED = 185                   # Object excluded by policy
DSM_RC_TL_NOACG = 186                      # No archive copy group (not supported)
DSM_RC_PS_INVALID_ARCHMC = 187             # Invalid archive management class (not supported)
DSM_RC_NO_PS_DATA = 188                    # No policy set data
DSM_RC_PS_INVALID_DIRMC = 189              # Invalid directory management class
DSM_RC_PS_NO_CG_IN_DIR_MC = 190            # No copy group in directory management class
DSM_RC_WIN32_UNSUPPORTED_FILE_TYPE = 280   # Unsupported file type on Windows

# =============================================================================
# Trusted Communication Agent Codes
# =============================================================================
# Errors related to the Trusted Communication Agent (TCA) on Unix/Linux
DSM_RC_TCA_NOT_ROOT = 161
DSM_RC_TCA_ATTACH_SHR_MEM_ERR = 200
DSM_RC_TCA_SHR_MEM_BLOCK_ERR = 200
DSM_RC_TCA_SHR_MEM_IN_USE = 200
DSM_RC_TCA_SHARED_MEMORY_ERROR = 200
DSM_RC_TCA_SEGMENT_MISMATCH = 200
DSM_RC_TCA_FORK_FAILED = 292
DSM_RC_TCA_DIED = 294
DSM_RC_TCA_INVALID_REQUEST = 295
DSM_RC_TCA_SEMGET_ERROR = 297
DSM_RC_TCA_SEM_OP_ERROR = 298
DSM_RC_TCA_NOT_ALLOWED = 299

# =============================================================================
# Options Error Codes (400-431)
# =============================================================================
# Errors related to configuration file parsing and option processing

DSM_RC_INVALID_OPT = 400                   # Invalid option specified
DSM_RC_NO_HOST_ADDR = 405                  # No host address specified
DSM_RC_NO_OPT_FILE = 406                   # Options file not found
DSM_RC_MACHINE_SAME = 408                  # Machine name same as server
DSM_RC_INVALID_SERVER = 409                # Invalid server name
DSM_RC_INVALID_KEYWORD = 410               # Invalid keyword in options file
DSM_RC_PATTERN_TOO_COMPLEX = 411           # Include/exclude pattern too complex
DSM_RC_NO_CLOSING_BRACKET = 412            # Missing closing bracket in pattern
DSM_RC_OPT_CLIENT_NOT_ACCEPTING = 417      # Client not accepting this option
DSM_RC_OPT_CLIENT_DOES_NOT_WANT = 418      # Client does not want this option
DSM_RC_OPT_NO_INCLEXCL_FILE = 419          # Include/exclude file not found
DSM_RC_OPT_OPEN_FAILURE = 420              # Failed to open options file
DSM_RC_OPT_INV_NODENAME = 421              # Invalid node name in options
DSM_RC_OPT_NODENAME_INVALID = 423          # Node name format invalid
DSM_RC_OPT_ERRORLOG_CONFLICT = 424         # Error log option conflict
DSM_RC_OPT_SCHEDLOG_CONFLICT = 425         # Schedule log option conflict
DSM_RC_CANNOT_OPEN_TRACEFILE = 426         # Cannot open trace file
DSM_RC_CANNOT_OPEN_LOGFILE = 427           # Cannot open log file
DSM_RC_OPT_SESSINIT_LF_CONFLICT = 428      # Session init LAN-free conflict
DSM_RC_OPT_OPTION_IGNORE = 429             # Option ignored
DSM_RC_OPT_DEDUP_CONFLICT = 430            # Deduplication option conflict
DSM_RC_OPT_HSMLOG_CONFLICT = 431           # HSM log option conflict

# =============================================================================
# Volume Label Codes (600-610)
# =============================================================================
DSM_RC_DUP_LABEL = 600
DSM_RC_NO_LABEL = 601

# Message file processing (610-615)
DSM_RC_NLS_CANT_OPEN_TXT = 610
DSM_RC_NLS_CANT_READ_HDR = 611
DSM_RC_NLS_INVALID_CNTL_REC = 612
DSM_RC_NLS_INVALID_DATE_FMT = 613
DSM_RC_NLS_INVALID_TIME_FMT = 614
DSM_RC_NLS_INVALID_NUM_FMT = 615

# Log message codes (620-622)
DSM_RC_LOG_CANT_BE_OPENED = 620
DSM_RC_LOG_ERROR_WRITING_TO_LOG = 621
DSM_RC_LOG_NOT_SPECIFIED = 622

# Client-only codes (900-999)
DSM_RC_NOT_ADSM_AUTHORIZED = 927
DSM_RC_REJECT_USERID_UNKNOWN = 940
DSM_RC_FILE_IS_SYMLINK = 959
DSM_RC_DIRECT_STORAGE_AGENT_UNSUPPORTED = 961
DSM_RC_FS_NAMESPACE_DOWNLEVEL = 963
DSM_RC_CONTINUE_NEW_CONSUMER = 972
DSM_RC_CONTINUE_NEW_CONSUMER_NODEDUP = 973
DSM_RC_CONTINUE_NEW_CONSUMER_NOCOMPRESS = 976
DSM_RC_SERVER_SUPPORTS_FUNC = 994
DSM_RC_SERVER_AND_SA_SUPPORT_FUNC = 995
DSM_RC_SERVER_DOWNLEVEL_FUNC = 996
DSM_RC_STORAGEAGENT_DOWNLEVEL = 997
DSM_RC_SERVER_AND_SA_DOWNLEVEL = 998

# =============================================================================
# TCP/IP Error Codes (Negative Range: -50 to -58)
# =============================================================================
# Network communication errors

DSM_RC_TCPIP_FAILURE = -50                 # TCP/IP communication failure
DSM_RC_CONN_TIMEDOUT = -51                 # Connection timed out
DSM_RC_CONN_REFUSED = -52                  # Connection refused by server
DSM_RC_BAD_HOST_NAME = -53                 # Invalid or unresolvable hostname
DSM_RC_NETWORK_UNREACHABLE = -54           # Network unreachable
DSM_RC_WINSOCK_MISSING = -55               # Winsock library missing (Windows)
DSM_RC_TCPIP_DLL_LOADFAILURE = -56         # Failed to load TCP/IP DLL
DSM_RC_TCPIP_LOADFAILURE = -57             # Failed to load TCP/IP library
DSM_RC_TCPIP_USER_ABORT = -58              # User aborted TCP/IP operation

# =============================================================================
# CommTSM Error Codes (-71 to -72)
# =============================================================================
# Communication errors specific to TSM protocol

DSM_RC_TSM_FAILURE = -71                   # TSM communication failure
DSM_RC_TSM_ABORT = -72                     # TSM communication aborted

# Deprecated comm3270 codes (no longer used)
DSM_RC_COMM_TIMEOUT = 2021
DSM_RC_EMULATOR_INACTIVE = 2021
DSM_RC_BAD_HOST_ID = 2021
DSM_RC_HOST_SESS_BUSY = 2021
DSM_RC_3270_CONNECT_FAILURE = 2021
DSM_RC_NO_ACS3ELKE_DLL = 2021
DSM_RC_EMULATOR_ERROR = 2021
DSM_RC_EMULATOR_BACKLEVEL = 2021
DSM_RC_CKSUM_FAILURE = 2021
DSM_RC_3270COMMError_DLL = 2021
DSM_RC_3270COMMError_GetProc = 2021
DSM_RC_EHLLAPIError_DLL = 2021
DSM_RC_EHLLAPIError_GetProc = 2021
DSM_RC_EHLLAPIError_HostConnect = 2021
DSM_RC_EHLLAPIError_AllocBuff = 2021
DSM_RC_EHLLAPIError_SendKey = 2021
DSM_RC_EHLLAPIError_PacketChk = 2021
DSM_RC_EHLLAPIError_ChkSum = 2021
DSM_RC_EHLLAPIError_HostTimeOut = 2021
DSM_RC_EHLLAPIError_Send = 2021
DSM_RC_EHLLAPIError_Recv = 2021
DSM_RC_EHLLAPIError_General = 2021
DSM_RC_PC3270_MISSING_DLL = 2021
DSM_RC_3270COMM_MISSING_DLL = 2021

# NETBIOS error codes (-151 to -161)
DSM_RC_NETB_ERROR = -151
DSM_RC_NETB_NO_DLL = -152
DSM_RC_NETB_LAN_ERR = -155
DSM_RC_NETB_NAME_ERR = -158
DSM_RC_NETB_TIMEOUT = -159
DSM_RC_NETB_NOTINST = -160
DSM_RC_NETB_REBOOT = -161

# Named Pipe error codes
DSM_RC_NP_ERROR = -190

# Deprecated CPIC codes (no longer used)
DSM_RC_CPIC_ALLOCATE_FAILURE = 2021
DSM_RC_CPIC_TYPE_MISMATCH = 2021
DSM_RC_CPIC_PIP_NOT_SPECIFY_ERR = 2021
DSM_RC_CPIC_SECURITY_NOT_VALID = 2021
DSM_RC_CPIC_SYNC_LVL_NO_SUPPORT = 2021
DSM_RC_CPIC_TPN_NOT_RECOGNIZED = 2021
DSM_RC_CPIC_TP_ERROR = 2021
DSM_RC_CPIC_PARAMETER_ERROR = 2021
DSM_RC_CPIC_PROD_SPECIFIC_ERR = 2021
DSM_RC_CPIC_PROGRAM_ERROR = 2021
DSM_RC_CPIC_RESOURCE_ERROR = 2021
DSM_RC_CPIC_DEALLOCATE_ERROR = 2021
DSM_RC_CPIC_SVC_ERROR = 2021
DSM_RC_CPIC_PROGRAM_STATE_CHECK = 2021
DSM_RC_CPIC_PROGRAM_PARAM_CHECK = 2021
DSM_RC_CPIC_UNSUCCESSFUL = 2021
DSM_RC_UNKNOWN_CPIC_PROBLEM = 2021
DSM_RC_CPIC_MISSING_LU = 2021
DSM_RC_CPIC_MISSING_TP = 2021
DSM_RC_CPIC_SNA6000_LOAD_FAIL = 2021
DSM_RC_CPIC_STARTUP_FAILURE = 2021

# Deprecated IPX/SPX codes (-300 to -307, no longer used)
DSM_RC_TLI_ERROR = 2021
DSM_RC_IPXSPX_FAILURE = 2021
DSM_RC_TLI_DLL_MISSING = 2021
DSM_RC_DLL_LOADFAILURE = 2021
DSM_RC_DLL_FUNCTION_LOADFAILURE = 2021
DSM_RC_IPXCONN_REFUSED = 2021
DSM_RC_IPXCONN_TIMEDOUT = 2021
DSM_RC_IPXADDR_UNREACHABLE = 2021
DSM_RC_CPIC_MISSING_DLL = 2021
DSM_RC_CPIC_DLL_LOADFAILURE = 2021
DSM_RC_CPIC_FUNC_LOADFAILURE = 2021

# Shared Memory Protocol codes (-450 to -452)
DSM_RC_SHM_TCPIP_FAILURE = -450
DSM_RC_SHM_FAILURE = -451
DSM_RC_SHM_NOTAUTH = -452

# =============================================================================
# API Parameter Validation Codes (2000-2090)
# =============================================================================
# These codes indicate invalid parameters passed to API functions

DSM_RC_NULL_OBJNAME = 2000                 # Object name pointer is NULL
DSM_RC_NULL_DATABLKPTR = 2001              # Data block pointer is NULL
DSM_RC_NULL_MSG = 2002                     # Message pointer is NULL
DSM_RC_NULL_OBJATTRPTR = 2004              # Object attribute pointer is NULL
DSM_RC_NO_SESS_BLK = 2006                  # No session block provided
DSM_RC_NO_POLICY_BLK = 2007                # No policy block provided
DSM_RC_ZERO_BUFLEN = 2008                  # Buffer length is zero
DSM_RC_NULL_BUFPTR = 2009                  # Buffer pointer is NULL
DSM_RC_INVALID_OBJTYPE = 2010              # Invalid object type
DSM_RC_INVALID_VOTE = 2011                 # Invalid vote parameter (dsmEndTxn)
DSM_RC_INVALID_ACTION = 2012               # Invalid action parameter
DSM_RC_INVALID_DS_HANDLE = 2014            # Invalid session handle
DSM_RC_INVALID_REPOS = 2015                # Invalid repository type
DSM_RC_INVALID_FSNAME = 2016               # Invalid filespace name
DSM_RC_INVALID_OBJNAME = 2017              # Invalid object name
DSM_RC_INVALID_LLNAME = 2018               # Invalid low-level name
DSM_RC_INVALID_OBJOWNER = 2019             # Invalid object owner
DSM_RC_INVALID_ACTYPE = 2020               # Invalid access type
DSM_RC_INVALID_RETCODE = 2021              # Invalid return code
DSM_RC_INVALID_SENDTYPE = 2022             # Invalid send type
DSM_RC_INVALID_PARAMETER = 2023            # Invalid parameter (generic)
DSM_RC_INVALID_OBJSTATE = 2024             # Invalid object state
DSM_RC_INVALID_MCNAME = 2025               # Invalid management class name
DSM_RC_INVALID_DRIVE_CHAR = 2026           # Invalid drive character
DSM_RC_NULL_FSNAME = 2027                  # Filespace name is NULL
DSM_RC_INVALID_HLNAME = 2028               # Invalid high-level name
DSM_RC_NUMOBJ_EXCEED = 2029                # Number of objects exceeded limit
DSM_RC_NEWPW_REQD = 2030                   # New password required
DSM_RC_OLDPW_REQD = 2031                   # Old password required
DSM_RC_NO_OWNER_REQD = 2032                # Owner not required
DSM_RC_NO_NODE_REQD = 2033                 # Node not required
DSM_RC_KEY_MISSING = 2034                  # Encryption key missing
DSM_RC_KEY_BAD = 2035                      # Encryption key invalid
DSM_RC_BAD_CALL_SEQUENCE = 2041            # API functions called in wrong order
DSM_RC_INVALID_TSMBUFFER = 2042            # Invalid TSM buffer
DSM_RC_TOO_MANY_BYTES = 2043               # Too many bytes specified
DSM_RC_MUST_RELEASE_BUFFER = 2044          # Must release buffer before continuing
DSM_RC_BUFF_ARRAY_ERROR = 2045             # Buffer array error
DSM_RC_INVALID_DATABLK = 2046              # Invalid data block
DSM_RC_ENCR_NOT_ALLOWED = 2047             # Encryption not allowed
DSM_RC_OBJ_COMPRESSED = 2048               # Object is compressed
DSM_RC_OBJ_ENCRYPTED = 2049                # Object is encrypted
DSM_RC_WILDCHAR_NOTALLOWED = 2050          # Wildcard characters not allowed
DSM_RC_POR_NOT_ALLOWED = 2051              # Point-in-time restore not allowed
DSM_RC_NO_ENCRYPTION_KEY = 2052            # No encryption key available
DSM_RC_ENCR_CONFLICT = 2053                # Encryption setting conflict
DSM_RC_FSNAME_NOTFOUND = 2060              # Filespace name not found
DSM_RC_FS_NOT_REGISTERED = 2061            # Filespace not registered
DSM_RC_FS_ALREADY_REGED = 2062             # Filespace already registered
DSM_RC_OBJID_NOTFOUND = 2063               # Object ID not found
DSM_RC_WRONG_VERSION = 2064                # Wrong API version
DSM_RC_WRONG_VERSION_PARM = 2065           # Wrong version parameter
DSM_RC_NEEDTO_ENDTXN = 2070                # Must call dsmEndTxn
DSM_RC_OBJ_EXCLUDED = 2080                 # Object excluded by policy
DSM_RC_OBJ_NOBCG = 2081                    # Object has no backup copy group
DSM_RC_OBJ_NOACG = 2082                    # Object has no archive copy group (not supported)
DSM_RC_APISYSTEM_ERROR = 2090              # API system error

# =============================================================================
# String Length Validation Codes (2100-2107)
# =============================================================================
# Errors when string parameters exceed maximum allowed lengths

DSM_RC_DESC_TOOLONG = 2100                 # Description string too long
DSM_RC_OBJINFO_TOOLONG = 2101              # Object info string too long
DSM_RC_HL_TOOLONG = 2102                   # High-level name too long
DSM_RC_PASSWD_TOOLONG = 2103               # Password too long
DSM_RC_FILESPACE_TOOLONG = 2104            # Filespace name too long
DSM_RC_LL_TOOLONG = 2105                   # Low-level name too long
DSM_RC_FSINFO_TOOLONG = 2106               # Filespace info too long
DSM_RC_SENDDATA_WITH_ZERO_SIZE = 2107      # Attempting to send zero-size data

# =============================================================================
# Access Control Codes (2110-2120)
# =============================================================================
# Errors related to access control and authorization

DSM_RC_INVALID_ACCESS_TYPE = 2110          # Invalid access type specified
DSM_RC_QUERY_COMM_FAILURE = 2111           # Query communication failure
DSM_RC_NO_FILES_BACKUP = 2112              # No files available for backup
DSM_RC_NO_FILES_ARCHIVE = 2113             # No files available for archive (not supported)
DSM_RC_INVALID_SETACCESS = 2114            # Invalid set access operation
DSM_RC_STRING_TOO_LONG = 2120              # String parameter too long

# =============================================================================
# Query and Buffer Codes (2200-2231)
# =============================================================================
# Codes related to query operations and buffer management

DSM_RC_MORE_DATA = 2200                    # More data available (continue querying)
DSM_RC_BUFF_TOO_SMALL = 2210               # Buffer too small for data
DSM_RC_NO_API_CONFIGFILE = 2228            # API configuration file not found
DSM_RC_NO_INCLEXCL_FILE = 2229             # Include/exclude file not found
DSM_RC_NO_SYS_OR_INCLEXCL = 2230           # No system or include/exclude file
DSM_RC_REJECT_NO_POR_SUPPORT = 2231        # Point-in-time restore not supported

# =============================================================================
# Miscellaneous API Codes (2300-2303)
# =============================================================================

DSM_RC_NEED_ROOT = 2300                    # Must run as root user
DSM_RC_NEEDTO_CALL_BINDMC = 2301           # Must call dsmBindMC first
DSM_RC_CHECK_REASON_CODE = 2302            # Check reason code for details
DSM_RC_NEEDTO_ENDTXN_DEDUP_SIZE_EXCEEDED = 2303  # Must end transaction, dedup size exceeded

# =============================================================================
# Encryption Codes (4580-4584)
# =============================================================================
# Errors related to data encryption

DSM_RC_ENC_WRONG_KEY = 4580                # Wrong encryption key
DSM_RC_ENC_NOT_AUTHORIZED = 4582           # Not authorized for encryption
DSM_RC_ENC_TYPE_UNKNOWN = 4584             # Unknown encryption type

# =============================================================================
# Clustering Codes (4600-4606)
# =============================================================================
# Errors related to cluster configuration and operations

DSM_RC_CLUSTER_INFO_LIBRARY_NOT_LOADED = 4600  # Cluster info library not loaded
DSM_RC_CLUSTER_LIBRARY_INVALID = 4601      # Cluster library invalid
DSM_RC_CLUSTER_LIBRARY_NOT_LOADED = 4602   # Cluster library not loaded
DSM_RC_CLUSTER_NOT_MEMBER_OF_CLUSTER = 4603  # Not a member of cluster
DSM_RC_CLUSTER_NOT_ENABLED = 4604          # Clustering not enabled
DSM_RC_CLUSTER_NOT_SUPPORTED = 4605        # Clustering not supported
DSM_RC_CLUSTER_UNKNOWN_ERROR = 4606        # Unknown cluster error

# =============================================================================
# Proxy Codes (5702-5749)
# =============================================================================
# Errors related to proxy node operations

DSM_RC_PROXY_REJECT_NO_RESOURCES = 5702    # Proxy: no resources available
DSM_RC_PROXY_REJECT_DUPLICATE_ID = 5705    # Proxy: duplicate ID
DSM_RC_PROXY_REJECT_ID_IN_USE = 5710       # Proxy: ID in use
DSM_RC_PROXY_REJECT_INTERNAL_ERROR = 5717  # Proxy: internal error
DSM_RC_PROXY_REJECT_NOT_AUTHORIZED = 5722  # Proxy: not authorized
DSM_RC_PROXY_INVALID_FROMNODE = 5746       # Proxy: invalid from node
DSM_RC_PROXY_INVALID_SERVERFREE = 5747     # Proxy: invalid server free
DSM_RC_PROXY_INVALID_CLUSTER = 5748        # Proxy: invalid cluster
DSM_RC_PROXY_INVALID_FUNCTION = 5749       # Proxy: invalid function

# =============================================================================
# Cryptography/Security Codes (5801-5802)
# =============================================================================
# Errors related to cryptographic operations

DSM_RC_CRYPTO_ICC_ERROR = 5801             # ICC (cryptography) error
DSM_RC_CRYPTO_ICC_CANNOT_LOAD = 5802       # Cannot load ICC library

# =============================================================================
# SSL Communication Codes (-361 to -365)
# =============================================================================
# Errors related to SSL/TLS secure communication

DSM_RC_SSL_NOT_SUPPORTED = -361            # SSL not supported
DSM_RC_SSL_INIT_FAILED = -362              # SSL initialization failed
DSM_RC_SSL_KEYFILE_OPEN_FAILED = -363      # Cannot open SSL key file
DSM_RC_SSL_KEYFILE_BAD_PASSWORD = -364     # Bad password for SSL key file
DSM_RC_SSL_BAD_CERTIFICATE = -365          # Invalid SSL certificate

# =============================================================================
# Client-Side Deduplication Codes (6300-6302)
# =============================================================================
# Errors related to client-side deduplication operations

DSM_RC_DIGEST_VALIDATION_ERROR = 6300      # Digest validation error
DSM_RC_DATA_FINGERPRINT_ERROR = 6301       # Data fingerprint error
DSM_RC_DATA_DEDUP_ERROR = 6302             # Data deduplication error
