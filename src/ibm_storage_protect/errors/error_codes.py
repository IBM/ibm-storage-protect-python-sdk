"""
IBM Storage Protect SDK - Error Code Definitions

This module defines all SDK error codes used throughout the IBM Storage Protect SDK.
Error codes follow a structured format for easy categorization and identification.

Error Code Format:
------------------
All error codes follow the pattern: TSM-XXYY

Where:
- TSM: Prefix indicating IBM Storage Protect (formerly Tivoli Storage Manager)
- XX: Category code (11-91)
- YY: Specific error within category (01-99)

Error Categories:
-----------------
- 11XX: Connection and Network Errors
- 21XX: Authentication and Authorization Errors
- 31XX: Resource and Quota Errors
- 41XX: Object and Filespace Errors
- 51XX: Transaction and Locking Errors
- 61XX: Configuration and Setup Errors
- 71XX: Operation and Command Errors
- 81XX: Data and Integrity Errors
- 91XX: System and Internal Errors

Usage Example:
--------------
    from ibm_storage_protect.errors import SDKErrorCode, TSMConnectionError

    # Create error with specific code
    error = TSMConnectionError(
        error_code=SDKErrorCode.CONNECTION_TIMEOUT,
        message="Connection to server timed out after 60 seconds"
    )

    # Check error code
    if error.error_code == SDKErrorCode.CONNECTION_TIMEOUT:
        print("Retry connection with longer timeout")

Notes:
------
- Error codes are mapped from C API return codes via the mapper module
- Each code includes retry recommendations and suggested delays
- Codes are designed to be machine-readable and human-friendly

See Also:
---------
- exceptions.py: Exception classes that use these codes
- mapper.py: Mapping from C API codes to SDK codes
"""
from enum import Enum




class SDKErrorCode(Enum):
    """
    Enumeration of all IBM Storage Protect SDK error codes.

    This enum defines standardized error codes for all error conditions in the SDK.
    Each code follows the TSM-XXYY format where XX indicates the error category
    and YY is the specific error within that category.

    Error codes are organized into the following categories:
    - 11XX: Connection and network errors
    - 21XX: Authentication and authorization errors
    - 31XX: Resource exhaustion and quota errors
    - 41XX: Object and filespace errors
    - 51XX: Transaction and locking errors
    - 61XX: Configuration and setup errors
    - 71XX: Operation and command errors
    - 81XX: Data corruption and validation errors
    - 91XX: System and internal errors

    Each error code is mapped to appropriate exception classes and includes
    metadata about retry recommendations and suggested delays.

    Example
    -------
    >>> from ibm_storage_protect.errors import SDKErrorCode
    >>> code = SDKErrorCode.CONNECTION_TIMEOUT
    >>> print(code.value)
    'TSM-1102'
    >>> print(code.name)
    'CONNECTION_TIMEOUT'
    """

    # Connection and Network Errors (11XX)
    NETWORK_ERROR = "TSM-1101"
    CONNECTION_TIMEOUT = "TSM-1102"
    CONNECTION_REFUSED = "TSM-1103"
    SERVER_UNAVAILABLE = "TSM-1104"
    SERVER_NOT_READY = "TSM-1105"
    HOST_NOT_FOUND = "TSM-1106"
    NETWORK_UNREACHABLE = "TSM-1107"
    CONNECTION_LOST = "TSM-1108"
    SESSION_REJECTED = "TSM-1109"
    PROTOCOL_ERROR = "TSM-1110"

    INVALID_CREDENTIALS = "TSM-2101"
    PASSWORD_EXPIRED = "TSM-2102"
    ACCOUNT_LOCKED = "TSM-2103"
    INSUFFICIENT_PRIVILEGES = "TSM-2104"
    NODE_NOT_AUTHORIZED = "TSM-2105"
    ACCESS_DENIED = "TSM-2106"
    SESSION_IN_USE = "TSM-2107"
    AUTHENTICATION_REQUIRED = "TSM-2108"
    INVALID_NODE_NAME = "TSM-2109"
    LICENSE_VIOLATION = "TSM-2110"

    STORAGE_FULL = "TSM-3101"
    QUOTA_EXCEEDED = "TSM-3102"
    INSUFFICIENT_MEMORY = "TSM-3103"
    DATABASE_FULL = "TSM-3104"
    LOG_FULL = "TSM-3105"
    RESOURCE_BUSY = "TSM-3106"
    TOO_MANY_SESSIONS = "TSM-3107"
    STORAGE_POOL_UNAVAILABLE = "TSM-3108"
    MEDIA_UNAVAILABLE = "TSM-3109"
    SIZE_LIMIT_EXCEEDED = "TSM-3110"

    OBJECT_NOT_FOUND = "TSM-4101"
    OBJECT_ALREADY_EXISTS = "TSM-4102"
    INVALID_OBJECT_NAME = "TSM-4103"
    INVALID_OBJECT_TYPE = "TSM-4104"
    OBJECT_LOCKED = "TSM-4105"
    OBJECT_EXPIRED = "TSM-4106"
    OBJECT_OFFLINE = "TSM-4107"
    OBJECT_CORRUPTED = "TSM-4108"
    NO_MATCHING_OBJECTS = "TSM-4109"
    FILESPACE_NOT_FOUND = "TSM-4110"

    TRANSACTION_ABORTED = "TSM-5101"
    TRANSACTION_CONFLICT = "TSM-5102"
    TRANSACTION_TIMEOUT = "TSM-5103"
    NO_ACTIVE_TRANSACTION = "TSM-5104"
    TRANSACTION_IN_PROGRESS = "TSM-5105"
    COMMIT_FAILED = "TSM-5106"
    ROLLBACK_FAILED = "TSM-5107"
    LOCK_CONFLICT = "TSM-5108"
    DEADLOCK_DETECTED = "TSM-5109"
    INVALID_TRANSACTION_STATE = "TSM-5110"

    INVALID_CONFIGURATION = "TSM-6101"
    MISSING_CONFIGURATION = "TSM-6102"
    INVALID_PARAMETER = "TSM-6103"
    CONFIGURATION_FILE_ERROR = "TSM-6104"
    POLICY_NOT_FOUND = "TSM-6105"
    MANAGEMENT_CLASS_ERROR = "TSM-6106"
    PLATFORM_MISMATCH = "TSM-6107"
    VERSION_MISMATCH = "TSM-6108"
    INVALID_OPTION = "TSM-6109"
    SETUP_FAILED = "TSM-6110"

    OPERATION_NOT_SUPPORTED = "TSM-7101"
    OPERATION_FAILED = "TSM-7102"
    OPERATION_TIMEOUT = "TSM-7103"
    OPERATION_CANCELLED = "TSM-7104"
    OPERATION_IN_PROGRESS = "TSM-7105"
    INVALID_OPERATION = "TSM-7106"
    BACKUP_FAILED = "TSM-7107"
    RESTORE_FAILED = "TSM-7108"
    QUERY_FAILED = "TSM-7109"
    DELETE_FAILED = "TSM-7110"

    DATA_CORRUPTION = "TSM-8101"
    CHECKSUM_MISMATCH = "TSM-8102"
    COMPRESSION_FAILED = "TSM-8103"
    DECOMPRESSION_FAILED = "TSM-8104"
    ENCRYPTION_FAILED = "TSM-8105"
    DECRYPTION_FAILED = "TSM-8106"
    INVALID_DATA_FORMAT = "TSM-8107"
    DATA_VALIDATION_FAILED = "TSM-8108"
    ENCODING_ERROR = "TSM-8109"
    TRANSFER_ERROR = "TSM-8110"

    INTERNAL_ERROR = "TSM-9101"
    SYSTEM_ERROR = "TSM-9102"
    RESOURCE_INITIALIZATION_FAILED = "TSM-9103"
    RESOURCE_CLEANUP_FAILED = "TSM-9104"
    UNEXPECTED_ERROR = "TSM-9105"
    NOT_IMPLEMENTED = "TSM-9106"
    DEPRECATED_FEATURE = "TSM-9107"
    LIBRARY_ERROR = "TSM-9108"
    THREAD_ERROR = "TSM-9109"
    CALLBACK_ERROR = "TSM-9110"

    # Additional error codes for comprehensive C API mapping
    CHECK_REASON_CODE = "TSM-5111"
    TRANSACTION_VOTE_ABORT = "TSM-5112"
    NEED_ROOT_PRIVILEGES = "TSM-6111"
    NEED_BIND_MC = "TSM-6112"
    DEDUP_SIZE_EXCEEDED = "TSM-5113"
    TCPIP_FAILURE = "TSM-1111"
    CONNECTION_TIMEDOUT_TCPIP = "TSM-1112"
    CONNECTION_REFUSED_TCPIP = "TSM-1113"
    BAD_HOSTNAME = "TSM-1114"
    NETWORK_UNREACHABLE_TCPIP = "TSM-1115"
    WINSOCK_ERROR = "TSM-1116"
    TCPIP_DLL_ERROR = "TSM-1117"
    TSM_COMM_FAILURE = "TSM-1118"
    TSM_COMM_ABORT = "TSM-1119"
    NETBIOS_ERROR = "TSM-1120"
    NAMED_PIPE_ERROR = "TSM-1121"
    SHARED_MEMORY_ERROR = "TSM-1122"
    SSL_NOT_SUPPORTED = "TSM-1123"
    SSL_INIT_FAILED = "TSM-1124"
    SSL_KEYFILE_ERROR = "TSM-1125"
    SSL_CERTIFICATE_ERROR = "TSM-1126"
    PROXY_REJECT = "TSM-2111"
    PROXY_INVALID = "TSM-2112"
    CRYPTO_ERROR = "TSM-8111"
    DIGEST_VALIDATION_ERROR = "TSM-8112"
    DATA_FINGERPRINT_ERROR = "TSM-8113"
    DATA_DEDUP_ERROR_GENERAL = "TSM-8114"
    CLUSTER_ERROR = "TSM-6113"
    ENCRYPTION_KEY_ERROR = "TSM-8115"
    ENCRYPTION_NOT_AUTHORIZED = "TSM-8116"
    ENCRYPTION_TYPE_UNKNOWN = "TSM-8117"
    TCA_ERROR = "TSM-6114"
    VOLUME_LABEL_ERROR = "TSM-3111"
    NLS_MESSAGE_ERROR = "TSM-6115"
    LOG_FILE_ERROR = "TSM-6116"
    CLIENT_AUTHORIZATION_ERROR = "TSM-2113"
    SYMLINK_ERROR = "TSM-4111"
    STORAGE_AGENT_ERROR = "TSM-3112"
    NAMESPACE_DOWNLEVEL = "TSM-6117"
    SERVER_FUNCTION_SUPPORT = "TSM-6118"
    MORE_DATA_AVAILABLE = "TSM-4112"
    BUFFER_TOO_SMALL = "TSM-8118"
    API_CONFIG_ERROR = "TSM-6119"
    NULL_PARAMETER = "TSM-6120"
    INVALID_DS_HANDLE = "TSM-6121"
    INVALID_REPOSITORY = "TSM-6122"
    INVALID_OBJSTATE = "TSM-7111"
    INVALID_SENDTYPE = "TSM-7112"
    INVALID_ACTYPE = "TSM-6123"
    INVALID_DRIVE = "TSM-6124"
    NUMOBJ_EXCEEDED = "TSM-7113"
    PASSWORD_CHANGE_REQUIRED = "TSM-2114"
    OWNER_NOT_REQUIRED = "TSM-6125"
    NODE_NOT_REQUIRED = "TSM-6126"
    KEY_ERROR = "TSM-8119"
    BAD_CALL_SEQUENCE = "TSM-7114"
    INVALID_TSMBUFFER = "TSM-8120"
    TOO_MANY_BYTES = "TSM-8121"
    MUST_RELEASE_BUFFER = "TSM-8122"
    BUFFER_ARRAY_ERROR = "TSM-8123"
    INVALID_DATABLK = "TSM-8124"
    ENCRYPTION_NOT_ALLOWED = "TSM-8125"
    OBJECT_COMPRESSED = "TSM-8126"
    OBJECT_ENCRYPTED = "TSM-8127"
    WILDCARD_NOT_ALLOWED = "TSM-7115"
    POR_NOT_ALLOWED = "TSM-7116"
    NO_ENCRYPTION_KEY = "TSM-8128"
    ENCRYPTION_CONFLICT = "TSM-8129"
    FSNAME_NOT_FOUND = "TSM-4113"
    FS_NOT_REGISTERED = "TSM-4114"
    FS_ALREADY_REGISTERED = "TSM-4115"
    OBJID_NOT_FOUND = "TSM-4116"
    WRONG_VERSION = "TSM-6127"
    NEED_END_TXN = "TSM-5114"
    OBJECT_EXCLUDED = "TSM-4117"
    OBJECT_NO_BCG = "TSM-4118"
    OBJECT_NO_ACG = "TSM-4119"
    API_SYSTEM_ERROR = "TSM-9111"
    STRING_TOO_LONG = "TSM-6128"
    INVALID_ACCESS_TYPE = "TSM-6129"
    QUERY_COMM_FAILURE = "TSM-7117"
    NO_FILES_BACKUP = "TSM-7118"
    NO_FILES_ARCHIVE = "TSM-7119"
    INVALID_SETACCESS = "TSM-6130"
    NO_POR_SUPPORT = "TSM-7120"
    SENDDATA_ZERO_SIZE = "TSM-8130"
