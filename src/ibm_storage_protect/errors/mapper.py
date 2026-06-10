"""
IBM Storage Protect SDK - C API Error Mapper

This module provides comprehensive mapping from IBM Storage Protect C API error
codes to SDK exception classes. It translates low-level C API return codes into
high-level Python exceptions with rich context and retry recommendations.

Key Responsibilities:
---------------------
1. **Error Code Translation**: Map C API integer codes to SDK error codes
2. **Exception Creation**: Instantiate appropriate exception classes
3. **Retry Logic**: Determine if errors are retryable and suggest delays
4. **Logging**: Log all error mappings for debugging and monitoring
5. **Fallback Handling**: Handle unmapped errors gracefully

Mapping Strategy:
-----------------
The mapper maintains a comprehensive dictionary of C API error codes to SDK
error information tuples containing:
- SDKErrorCode: The standardized SDK error code
- Default Message: Human-readable error description
- Retry Recommended: Boolean indicating if retry is suggested
- Retry Delay: Suggested delay in seconds before retry

Error Code Ranges:
------------------
- Positive codes (1-999): Standard TSM server errors
- Negative codes (-50 to -500): Communication and protocol errors
- 2000-2999: API parameter validation errors
- 4000+: Advanced features (encryption, clustering, etc.)

Usage Example:
--------------
    from ibm_storage_protect.errors.mapper import _map_internal_error

    # Map C API error code to SDK exception
    c_error_code = 2021  # Network communication failure
    exception = _map_internal_error(
        c_error_code=c_error_code,
        context="Failed to connect to server"
    )

    # Exception is now a TSMConnectionError with:
    # - error_code = SDKErrorCode.NETWORK_ERROR
    # - message = "Failed to connect to server"
    # - retry_recommended = True
    # - retry_after = 30

    raise exception

Unmapped Errors:
----------------
If a C API error code is not found in the mapping dictionary, the mapper:
1. Creates a TSMSystemError with SDKErrorCode.UNEXPECTED_ERROR
2. Includes the original C error code in the exception details
3. Logs a warning for developers to add the mapping
4. Preserves the original error context

Performance Considerations:
---------------------------
- Mapping dictionary is initialized once at module load
- Lookups are O(1) dictionary operations
- Exception creation is lightweight
- Logging is structured for efficient parsing

Thread Safety:
--------------
The mapper is thread-safe as the mapping dictionary is read-only after
initialization and exception creation is stateless.

Reference:
----------
IBM Storage Protect API Return Codes:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf

See Also:
---------
- error_codes.py: SDK error code definitions
- exceptions.py: Exception class implementations
"""
# pylint: disable=protected-access
import logging
from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
    Type,
)

from ibm_storage_protect.errors.error_codes import SDKErrorCode
from ibm_storage_protect.errors.exceptions import (
    TSMAuthenticationError,
    TSMConfigurationError,
    TSMConnectionError,
    TSMDataError,
    TSMError,
    TSMObjectError,
    TSMOperationError,
    TSMResourceError,
    TSMSystemError,
    TSMTransactionError,
)


class _InternalErrorMapper:
    """
    Internal error mapper that translates IBM Storage Protect C API return codes
    into SDK exceptions.
    """

    def __init__(self):
        """
        Initialize the error mapper and populate the translation dictionary.
        """
        self._logger = logging.getLogger('ibm_storage_protect.errors.mapper')
        self._c_to_sdk_map: Dict[int, Tuple[SDKErrorCode, str, bool, int]] = {}
        self._initialize_mappings()

    def _initialize_mappings(self):

        self._c_to_sdk_map.update({
            2021: (SDKErrorCode.NETWORK_ERROR, "Network communication failure", True, 30),
            136: (SDKErrorCode.PROTOCOL_ERROR, "Communication protocol error", True, 30),
            156: (SDKErrorCode.PROTOCOL_ERROR, "Invalid communication method", False, 0),
            178: (SDKErrorCode.CONNECTION_TIMEOUT, "Connection timeout", True, 60),
            109: (SDKErrorCode.SESSION_REJECTED, "Session rejected - invalid parameter", False, 0),
            132: (SDKErrorCode.SERVER_UNAVAILABLE, "No server resources available", True, 60),
            162: (SDKErrorCode.SERVER_NOT_READY, "Server not ready", True, 60),
            51: (SDKErrorCode.SERVER_UNAVAILABLE, "Server has no resources", True, 60),
            55: (SDKErrorCode.SERVER_UNAVAILABLE, "Server is disabled", False, 0),
        })

        self._c_to_sdk_map.update({
            53: (SDKErrorCode.INVALID_NODE_NAME, "Node name unknown", False, 0),
            123: (SDKErrorCode.INSUFFICIENT_PRIVILEGES, "No authorization", False, 0),
            137: (SDKErrorCode.INVALID_CREDENTIALS, "Authentication failure", False, 0),
            52: (SDKErrorCode.PASSWORD_EXPIRED, "Password has expired", False, 0),
            169: (SDKErrorCode.PASSWORD_EXPIRED, "Password file is old", False, 0),
            61: (SDKErrorCode.ACCOUNT_LOCKED, "Node ID is locked", False, 0),
            71: (SDKErrorCode.INSUFFICIENT_PRIVILEGES, "Not authorized", False, 0),
            106: (SDKErrorCode.ACCESS_DENIED, "Access denied", False, 0),
            161: (SDKErrorCode.ACCESS_DENIED, "Access denied", False, 0),
            54: (SDKErrorCode.SESSION_IN_USE, "Duplicate session ID", False, 0),
            59: (SDKErrorCode.SESSION_IN_USE, "Node ID already in use", False, 0),
            62: (SDKErrorCode.LICENSE_VIOLATION, "License maximum exceeded", False, 0),
            56: (SDKErrorCode.AUTHENTICATION_REQUIRED, "Registration is closed", False, 0),
            57: (SDKErrorCode.VERSION_MISMATCH, "Client is downlevel", False, 0),
            58: (SDKErrorCode.VERSION_MISMATCH, "Server is downlevel", False, 0),
        })

        self._c_to_sdk_map.update({
            11: (SDKErrorCode.STORAGE_FULL, "No storage space available", True, 300),
            26: (SDKErrorCode.STORAGE_FULL, "Waiting for storage space", True, 300),
            29: (SDKErrorCode.STORAGE_FULL, "No storage space - stop", False, 0),
            102: (SDKErrorCode.INSUFFICIENT_MEMORY, "Insufficient memory", True, 60),
            18: (SDKErrorCode.INSUFFICIENT_MEMORY, "Server out of memory", True, 60),
            63: (SDKErrorCode.INSUFFICIENT_MEMORY, "Server rejected - no memory", True, 60),
            154: (SDKErrorCode.INSUFFICIENT_MEMORY, "No compression memory", True, 60),
            17: (SDKErrorCode.DATABASE_FULL, "No database space", True, 300),
            64: (SDKErrorCode.DATABASE_FULL, "Server rejected - no DB space", True, 300),
            16: (SDKErrorCode.LOG_FULL, "No log space", True, 300),
            65: (SDKErrorCode.LOG_FULL, "Server rejected - no log space", True, 300),
            111: (SDKErrorCode.STORAGE_FULL, "Disk full", True, 300),
            120: (SDKErrorCode.RESOURCE_BUSY, "Filespace is locked", True, 30),
            158: (SDKErrorCode.RESOURCE_BUSY, "Filespace write locked", True, 30),
            232: (SDKErrorCode.RESOURCE_BUSY, "Item in use", True, 30),
            13: (SDKErrorCode.QUOTA_EXCEEDED, "Size estimate exceeded", False, 0),
            41: (SDKErrorCode.QUOTA_EXCEEDED, "Maximum mount points exceeded", False, 0),
            166: (SDKErrorCode.SIZE_LIMIT_EXCEEDED, "Over file size limit", False, 0),
            249: (SDKErrorCode.QUOTA_EXCEEDED, "Transaction limit exceeded", False, 0),
            48: (SDKErrorCode.STORAGE_POOL_UNAVAILABLE, "Storage pool undefined", False, 0),
            12: (SDKErrorCode.MEDIA_UNAVAILABLE, "Mount not possible", True, 60),
        })

        self._c_to_sdk_map.update({
            2: (SDKErrorCode.OBJECT_NOT_FOUND, "No matching objects", False, 0),
            4: (SDKErrorCode.OBJECT_NOT_FOUND, "Active backup not found", False, 0),
            42: (SDKErrorCode.NO_MATCHING_OBJECTS, "No object set match", False, 0),
            104: (SDKErrorCode.OBJECT_NOT_FOUND, "File not found", False, 0),
            105: (SDKErrorCode.OBJECT_NOT_FOUND, "Path not found", False, 0),
            124: (SDKErrorCode.FILESPACE_NOT_FOUND, "Filespace not found", False, 0),
            133: (SDKErrorCode.FILESPACE_NOT_FOUND, "Filespace not known", False, 0),
            160: (SDKErrorCode.OBJECT_NOT_FOUND, "Object not found", False, 0),
            21: (SDKErrorCode.OBJECT_ALREADY_EXISTS, "Node already defined", False, 0),
            31: (SDKErrorCode.OBJECT_ALREADY_EXISTS, "External object ID exists", False, 0),
            32: (SDKErrorCode.OBJECT_ALREADY_EXISTS, "Duplicate object", False, 0),
            108: (SDKErrorCode.OBJECT_ALREADY_EXISTS, "File exists", False, 0),
            134: (SDKErrorCode.INVALID_OBJECT_NAME, "No leading directory separator", False, 0),
            149: (SDKErrorCode.INVALID_OBJECT_NAME, "Directory delimiter needed", False, 0),
            150: (SDKErrorCode.INVALID_OBJECT_TYPE, "Unknown file data type", False, 0),
            9: (SDKErrorCode.OBJECT_OFFLINE, "Data is offline", True, 300),
            14: (SDKErrorCode.OBJECT_OFFLINE, "Data unavailable", True, 300),
            250: (SDKErrorCode.OBJECT_LOCKED, "Object already held", True, 30),
            176: (SDKErrorCode.OBJECT_CORRUPTED, "Compressed data corrupted", False, 0),
            236: (SDKErrorCode.OBJECT_CORRUPTED, "CRC check failed", False, 0),
        })

        self._c_to_sdk_map.update({
            1: (SDKErrorCode.TRANSACTION_ABORTED, "System error - transaction aborted", True, 30),
            3: (SDKErrorCode.TRANSACTION_ABORTED, "Aborted by client", False, 0),
            15: (SDKErrorCode.TRANSACTION_ABORTED, "Retry transaction", True, 30),
            125: (SDKErrorCode.TRANSACTION_ABORTED, "Transaction aborted", True, 30),
            242: (SDKErrorCode.TRANSACTION_ABORTED, "Retry single transaction", True, 30),
            38: (SDKErrorCode.TRANSACTION_CONFLICT, "Restore in progress", True, 60),
            233: (SDKErrorCode.LOCK_CONFLICT, "Lock conflict", True, 30),
            37: (SDKErrorCode.INVALID_TRANSACTION_STATE, "Restart not possible", False, 0),
        })

        self._c_to_sdk_map.update({
            39: (SDKErrorCode.INVALID_CONFIGURATION, "Syntax error", False, 0),
            173: (SDKErrorCode.INVALID_CONFIGURATION, "Input error", False, 0),
            405: (SDKErrorCode.INVALID_CONFIGURATION, "No host address", False, 0),
            409: (SDKErrorCode.INVALID_CONFIGURATION, "Invalid server", False, 0),
            410: (SDKErrorCode.INVALID_CONFIGURATION, "Invalid keyword", False, 0),
            20: (SDKErrorCode.MISSING_CONFIGURATION, "Filespace not defined", False, 0),
            22: (SDKErrorCode.MISSING_CONFIGURATION, "No default domain", False, 0),
            24: (SDKErrorCode.MISSING_CONFIGURATION, "Invalid policy bind", False, 0),
            25: (SDKErrorCode.MISSING_CONFIGURATION, "Destination not defined", False, 0),
            168: (SDKErrorCode.MISSING_CONFIGURATION, "No password file", False, 0),
            188: (SDKErrorCode.MISSING_CONFIGURATION, "No policy data", False, 0),
            183: (SDKErrorCode.POLICY_NOT_FOUND, "No default management class", False, 0),
            187: (
                SDKErrorCode.MANAGEMENT_CLASS_ERROR, "Invalid archive management class", False, 0
            ),
            189: (
                SDKErrorCode.MANAGEMENT_CLASS_ERROR, "Invalid directory management class", False, 0
            ),
            174: (SDKErrorCode.PLATFORM_MISMATCH, "Platform mismatch", False, 0),
            400: (SDKErrorCode.INVALID_OPTION, "Invalid option", False, 0),
            406: (SDKErrorCode.CONFIGURATION_FILE_ERROR, "No option file", False, 0),
            2016: (SDKErrorCode.INVALID_CONFIGURATION, "Invalid filespace name", False, 0),
        })

        self._c_to_sdk_map.update({
            231: (SDKErrorCode.OPERATION_NOT_SUPPORTED, "Invalid mover type", False, 0),
            45: (SDKErrorCode.OPERATION_FAILED, "Merge error", False, 0),
            46: (SDKErrorCode.OPERATION_FAILED, "Filespace rename error", False, 0),
            164: (SDKErrorCode.OPERATION_FAILED, "File I/O error", False, 0),
            165: (SDKErrorCode.OPERATION_FAILED, "Write failure", False, 0),
            101: (SDKErrorCode.OPERATION_CANCELLED, "User abort", False, 0),
            139: (SDKErrorCode.OPERATION_CANCELLED, "Killed", False, 0),
            47: (SDKErrorCode.INVALID_OPERATION, "Invalid operation", False, 0),
            237: (SDKErrorCode.INVALID_OPERATION, "Invalid group action", False, 0),
        })

        self._c_to_sdk_map.update({
            49: (SDKErrorCode.INVALID_DATA_FORMAT, "Invalid data format", False, 0),
            122: (SDKErrorCode.INVALID_DATA_FORMAT, "Unknown format", False, 0),
            129: (SDKErrorCode.COMPRESSION_FAILED, "Not compressed", False, 0),
            155: (SDKErrorCode.COMPRESSION_FAILED, "Compression grew", False, 0),
        })

        self._c_to_sdk_map.update({
            66: (SDKErrorCode.INTERNAL_ERROR, "Internal error", False, 0),
            131: (SDKErrorCode.SYSTEM_ERROR, "System error", False, 0),
            114: (SDKErrorCode.UNEXPECTED_ERROR, "Unknown error", False, 0),
            115: (SDKErrorCode.UNEXPECTED_ERROR, "Unexpected error", False, 0),
        })

        # Additional general error codes (100-200)
        self._c_to_sdk_map.update({
            107: (SDKErrorCode.RESOURCE_BUSY, "No handles available", True, 30),
            110: (SDKErrorCode.INVALID_PARAMETER, "Invalid handle", False, 0),
            113: (SDKErrorCode.PROTOCOL_ERROR, "Protocol violation", False, 0),
            116: (SDKErrorCode.OPERATION_FAILED, "File being executed", False, 0),
            117: (SDKErrorCode.STORAGE_FULL, "Directory no space", True, 300),
            118: (SDKErrorCode.INVALID_OBJECT_NAME, "Looped symbolic link", False, 0),
            119: (SDKErrorCode.INVALID_OBJECT_NAME, "File name too long", False, 0),
            121: (SDKErrorCode.OPERATION_FAILED, "Operation finished", False, 0),
            126: (SDKErrorCode.INVALID_OBJECT_TYPE, "Subdirectory as file", False, 0),
            127: (SDKErrorCode.INSUFFICIENT_MEMORY, "Process no space", True, 60),
            128: (SDKErrorCode.INVALID_OBJECT_NAME, "Path too long", False, 0),
            130: (SDKErrorCode.COMPRESSION_FAILED, "Too many bits", False, 0),
            135: (SDKErrorCode.INVALID_OBJECT_NAME, "Wildcard directory", False, 0),
            138: (SDKErrorCode.INVALID_PARAMETER, "TA not valid", False, 0),
            143: (SDKErrorCode.TRANSACTION_ABORTED, "Retry operation", True, 30),
            145: (SDKErrorCode.OPERATION_FAILED, "Would block", True, 10),
            146: (SDKErrorCode.BUFFER_TOO_SMALL, "Buffer too small", False, 0),
            147: (SDKErrorCode.INVALID_DATA_FORMAT, "Unclosed delimiter", False, 0),
            148: (SDKErrorCode.INVALID_DATA_FORMAT, "No starting delimiter", False, 0),
            151: (SDKErrorCode.BUFFER_TOO_SMALL, "Buffer overflow", False, 0),
            159: (SDKErrorCode.OPERATION_CANCELLED, "Skipped by user", False, 0),
            163: (SDKErrorCode.OBJECT_CORRUPTED, "Filesystem is bad", False, 0),
            167: (SDKErrorCode.OPERATION_FAILED, "Cannot make", False, 0),
            177: (SDKErrorCode.INVALID_DATA_FORMAT, "Unmatched quote", False, 0),
            179: (SDKErrorCode.OPERATION_NOT_SUPPORTED, "Failover mode function blocked", False, 0),
        })

        # Policy set error codes (180-199)
        self._c_to_sdk_map.update({
            181: (SDKErrorCode.POLICY_NOT_FOUND, "Multiple backup copy groups", False, 0),
            182: (SDKErrorCode.POLICY_NOT_FOUND, "Multiple archive copy groups", False, 0),
            184: (SDKErrorCode.POLICY_NOT_FOUND, "No backup copy group", False, 0),
            185: (SDKErrorCode.OBJECT_EXCLUDED, "Object excluded", False, 0),
            186: (SDKErrorCode.POLICY_NOT_FOUND, "No archive copy group", False, 0),
            190: (SDKErrorCode.MANAGEMENT_CLASS_ERROR, "No copy group in directory MC", False, 0),
            280: (SDKErrorCode.INVALID_OBJECT_TYPE, "Unsupported file type", False, 0),
        })

        # TCA (Trusted Communication Agent) codes (200, 292-299)
        self._c_to_sdk_map.update({
            200: (SDKErrorCode.TCA_ERROR, "Shared memory error", False, 0),
            292: (SDKErrorCode.TCA_ERROR, "Fork failed", False, 0),
            294: (SDKErrorCode.TCA_ERROR, "TCA died", False, 0),
            295: (SDKErrorCode.TCA_ERROR, "Invalid request", False, 0),
            297: (SDKErrorCode.TCA_ERROR, "Semaphore get error", False, 0),
            298: (SDKErrorCode.TCA_ERROR, "Semaphore operation error", False, 0),
            299: (SDKErrorCode.TCA_ERROR, "TCA not allowed", False, 0),
        })

        # Options error codes (400-431)
        self._c_to_sdk_map.update({
            408: (SDKErrorCode.INVALID_CONFIGURATION, "Machine same", False, 0),
            411: (SDKErrorCode.INVALID_CONFIGURATION, "Pattern too complex", False, 0),
            412: (SDKErrorCode.INVALID_CONFIGURATION, "No closing bracket", False, 0),
            417: (SDKErrorCode.INVALID_CONFIGURATION, "Client not accepting", False, 0),
            418: (SDKErrorCode.INVALID_CONFIGURATION, "Client does not want", False, 0),
            419: (SDKErrorCode.MISSING_CONFIGURATION, "No include/exclude file", False, 0),
            420: (SDKErrorCode.CONFIGURATION_FILE_ERROR, "Option open failure", False, 0),
            421: (SDKErrorCode.INVALID_NODE_NAME, "Invalid node name in options", False, 0),
            423: (SDKErrorCode.INVALID_NODE_NAME, "Node name invalid", False, 0),
            424: (SDKErrorCode.INVALID_CONFIGURATION, "Error log conflict", False, 0),
            425: (SDKErrorCode.INVALID_CONFIGURATION, "Schedule log conflict", False, 0),
            426: (SDKErrorCode.CONFIGURATION_FILE_ERROR, "Cannot open trace file", False, 0),
            427: (SDKErrorCode.CONFIGURATION_FILE_ERROR, "Cannot open log file", False, 0),
            428: (SDKErrorCode.INVALID_CONFIGURATION, "Session init LF conflict", False, 0),
            429: (SDKErrorCode.INVALID_CONFIGURATION, "Option ignored", False, 0),
            430: (SDKErrorCode.INVALID_CONFIGURATION, "Dedup conflict", False, 0),
            431: (SDKErrorCode.INVALID_CONFIGURATION, "HSM log conflict", False, 0),
        })

        # Volume label codes (600-601)
        self._c_to_sdk_map.update({
            600: (SDKErrorCode.VOLUME_LABEL_ERROR, "Duplicate label", False, 0),
            601: (SDKErrorCode.VOLUME_LABEL_ERROR, "No label", False, 0),
        })

        # Message file processing (610-615)
        self._c_to_sdk_map.update({
            610: (SDKErrorCode.NLS_MESSAGE_ERROR, "Cannot open text file", False, 0),
            611: (SDKErrorCode.NLS_MESSAGE_ERROR, "Cannot read header", False, 0),
            612: (SDKErrorCode.NLS_MESSAGE_ERROR, "Invalid control record", False, 0),
            613: (SDKErrorCode.NLS_MESSAGE_ERROR, "Invalid date format", False, 0),
            614: (SDKErrorCode.NLS_MESSAGE_ERROR, "Invalid time format", False, 0),
            615: (SDKErrorCode.NLS_MESSAGE_ERROR, "Invalid number format", False, 0),
        })

        # Log message codes (620-622)
        self._c_to_sdk_map.update({
            620: (SDKErrorCode.LOG_FILE_ERROR, "Log cannot be opened", False, 0),
            621: (SDKErrorCode.LOG_FILE_ERROR, "Error writing to log", False, 0),
            622: (SDKErrorCode.LOG_FILE_ERROR, "Log not specified", False, 0),
        })

        # Client-only codes (900-999)
        self._c_to_sdk_map.update({
            927: (SDKErrorCode.CLIENT_AUTHORIZATION_ERROR, "Not ADSM authorized", False, 0),
            940: (SDKErrorCode.INVALID_CREDENTIALS, "User ID unknown", False, 0),
            959: (SDKErrorCode.SYMLINK_ERROR, "File is symbolic link", False, 0),
            961: (SDKErrorCode.STORAGE_AGENT_ERROR, "Direct storage agent unsupported", False, 0),
            963: (SDKErrorCode.NAMESPACE_DOWNLEVEL, "Filespace namespace downlevel", False, 0),
            972: (SDKErrorCode.OPERATION_FAILED, "Continue new consumer", False, 0),
            973: (SDKErrorCode.OPERATION_FAILED, "Continue new consumer no dedup", False, 0),
            976: (SDKErrorCode.OPERATION_FAILED, "Continue new consumer no compress", False, 0),
            994: (SDKErrorCode.SERVER_FUNCTION_SUPPORT, "Server supports function", False, 0),
            995: (SDKErrorCode.SERVER_FUNCTION_SUPPORT, "Server and SA support function", False, 0),
            996: (SDKErrorCode.VERSION_MISMATCH, "Server downlevel function", False, 0),
            997: (SDKErrorCode.VERSION_MISMATCH, "Storage agent downlevel", False, 0),
            998: (SDKErrorCode.VERSION_MISMATCH, "Server and SA downlevel", False, 0),
        })

        # TCP/IP error codes (negative range)
        self._c_to_sdk_map.update({
            -50: (SDKErrorCode.TCPIP_FAILURE, "TCP/IP failure", True, 30),
            -51: (SDKErrorCode.CONNECTION_TIMEDOUT_TCPIP, "Connection timed out", True, 60),
            -52: (SDKErrorCode.CONNECTION_REFUSED_TCPIP, "Connection refused", True, 30),
            -53: (SDKErrorCode.BAD_HOSTNAME, "Bad host name", False, 0),
            -54: (SDKErrorCode.NETWORK_UNREACHABLE_TCPIP, "Network unreachable", True, 60),
            -55: (SDKErrorCode.WINSOCK_ERROR, "Winsock missing", False, 0),
            -56: (SDKErrorCode.TCPIP_DLL_ERROR, "TCP/IP DLL load failure", False, 0),
            -57: (SDKErrorCode.TCPIP_DLL_ERROR, "TCP/IP load failure", False, 0),
            -58: (SDKErrorCode.OPERATION_CANCELLED, "TCP/IP user abort", False, 0),
        })

        # CommTSM error codes (-71 to -72)
        self._c_to_sdk_map.update({
            -71: (SDKErrorCode.TSM_COMM_FAILURE, "TSM communication failure", True, 30),
            -72: (SDKErrorCode.TSM_COMM_ABORT, "TSM communication abort", False, 0),
        })

        # NETBIOS error codes (-151 to -161)
        self._c_to_sdk_map.update({
            -151: (SDKErrorCode.NETBIOS_ERROR, "NetBIOS error", True, 30),
            -152: (SDKErrorCode.NETBIOS_ERROR, "NetBIOS no DLL", False, 0),
            -155: (SDKErrorCode.NETBIOS_ERROR, "NetBIOS LAN error", True, 30),
            -158: (SDKErrorCode.NETBIOS_ERROR, "NetBIOS name error", False, 0),
            -159: (SDKErrorCode.NETBIOS_ERROR, "NetBIOS timeout", True, 60),
            -160: (SDKErrorCode.NETBIOS_ERROR, "NetBIOS not installed", False, 0),
            -161: (SDKErrorCode.NETBIOS_ERROR, "NetBIOS reboot required", False, 0),
        })

        # Named Pipe error codes
        self._c_to_sdk_map.update({
            -190: (SDKErrorCode.NAMED_PIPE_ERROR, "Named pipe error", True, 30),
        })

        # SSL communication codes (-361 to -365)
        self._c_to_sdk_map.update({
            -361: (SDKErrorCode.SSL_NOT_SUPPORTED, "SSL not supported", False, 0),
            -362: (SDKErrorCode.SSL_INIT_FAILED, "SSL initialization failed", False, 0),
            -363: (SDKErrorCode.SSL_KEYFILE_ERROR, "SSL keyfile open failed", False, 0),
            -364: (SDKErrorCode.SSL_KEYFILE_ERROR, "SSL keyfile bad password", False, 0),
            -365: (SDKErrorCode.SSL_CERTIFICATE_ERROR, "SSL bad certificate", False, 0),
        })

        # Shared Memory Protocol codes (-450 to -452)
        self._c_to_sdk_map.update({
            -450: (SDKErrorCode.SHARED_MEMORY_ERROR, "Shared memory TCP/IP failure", True, 30),
            -451: (SDKErrorCode.SHARED_MEMORY_ERROR, "Shared memory failure", True, 30),
            -452: (SDKErrorCode.SHARED_MEMORY_ERROR, "Shared memory not authorized", False, 0),
        })

        # API parameter validation (2000-2090)
        self._c_to_sdk_map.update({
            2000: (SDKErrorCode.NULL_PARAMETER, "NULL object name", False, 0),
            2001: (SDKErrorCode.NULL_PARAMETER, "NULL data block pointer", False, 0),
            2002: (SDKErrorCode.NULL_PARAMETER, "NULL message", False, 0),
            2004: (SDKErrorCode.NULL_PARAMETER, "NULL object attribute pointer", False, 0),
            2006: (SDKErrorCode.NULL_PARAMETER, "No session block", False, 0),
            2007: (SDKErrorCode.NULL_PARAMETER, "No policy block", False, 0),
            2008: (SDKErrorCode.INVALID_PARAMETER, "Zero buffer length", False, 0),
            2009: (SDKErrorCode.NULL_PARAMETER, "NULL buffer pointer", False, 0),
            2010: (SDKErrorCode.INVALID_OBJECT_TYPE, "Invalid object type", False, 0),
            2011: (SDKErrorCode.INVALID_PARAMETER, "Invalid vote", False, 0),
            2012: (SDKErrorCode.INVALID_PARAMETER, "Invalid action", False, 0),
            2014: (SDKErrorCode.INVALID_DS_HANDLE, "Invalid DS handle", False, 0),
            2015: (SDKErrorCode.INVALID_REPOSITORY, "Invalid repository", False, 0),
            2017: (SDKErrorCode.INVALID_OBJECT_NAME, "Invalid object name", False, 0),
            2018: (SDKErrorCode.INVALID_OBJECT_NAME, "Invalid low-level name", False, 0),
            2019: (SDKErrorCode.INVALID_PARAMETER, "Invalid object owner", False, 0),
            2020: (SDKErrorCode.INVALID_ACTYPE, "Invalid AC type", False, 0),
            2022: (SDKErrorCode.INVALID_SENDTYPE, "Invalid send type", False, 0),
            2023: (SDKErrorCode.INVALID_PARAMETER, "Invalid parameter", False, 0),
            2024: (SDKErrorCode.INVALID_OBJSTATE, "Invalid object state", False, 0),
            2025: (SDKErrorCode.MANAGEMENT_CLASS_ERROR, "Invalid MC name", False, 0),
            2026: (SDKErrorCode.INVALID_DRIVE, "Invalid drive character", False, 0),
            2027: (SDKErrorCode.NULL_PARAMETER, "NULL filespace name", False, 0),
            2028: (SDKErrorCode.INVALID_OBJECT_NAME, "Invalid high-level name", False, 0),
            2029: (SDKErrorCode.NUMOBJ_EXCEEDED, "Number of objects exceeded", False, 0),
            2030: (SDKErrorCode.PASSWORD_CHANGE_REQUIRED, "New password required", False, 0),
            2031: (SDKErrorCode.PASSWORD_CHANGE_REQUIRED, "Old password required", False, 0),
            2032: (SDKErrorCode.OWNER_NOT_REQUIRED, "No owner required", False, 0),
            2033: (SDKErrorCode.NODE_NOT_REQUIRED, "No node required", False, 0),
            2034: (SDKErrorCode.KEY_ERROR, "Key missing", False, 0),
            2035: (SDKErrorCode.KEY_ERROR, "Key bad", False, 0),
            2041: (SDKErrorCode.BAD_CALL_SEQUENCE, "Bad call sequence", False, 0),
            2042: (SDKErrorCode.INVALID_TSMBUFFER, "Invalid TSM buffer", False, 0),
            2043: (SDKErrorCode.TOO_MANY_BYTES, "Too many bytes", False, 0),
            2044: (SDKErrorCode.MUST_RELEASE_BUFFER, "Must release buffer", False, 0),
            2045: (SDKErrorCode.BUFFER_ARRAY_ERROR, "Buffer array error", False, 0),
            2046: (SDKErrorCode.INVALID_DATABLK, "Invalid data block", False, 0),
            2047: (SDKErrorCode.ENCRYPTION_NOT_ALLOWED, "Encryption not allowed", False, 0),
            2048: (SDKErrorCode.OBJECT_COMPRESSED, "Object compressed", False, 0),
            2049: (SDKErrorCode.OBJECT_ENCRYPTED, "Object encrypted", False, 0),
            2050: (SDKErrorCode.WILDCARD_NOT_ALLOWED, "Wildcard not allowed", False, 0),
            2051: (SDKErrorCode.POR_NOT_ALLOWED, "Point of restart not allowed", False, 0),
            2052: (SDKErrorCode.NO_ENCRYPTION_KEY, "No encryption key", False, 0),
            2053: (SDKErrorCode.ENCRYPTION_CONFLICT, "Encryption conflict", False, 0),
            2060: (SDKErrorCode.FSNAME_NOT_FOUND, "Filespace name not found", False, 0),
            2061: (SDKErrorCode.FS_NOT_REGISTERED, "Filespace not registered", False, 0),
            2062: (SDKErrorCode.FS_ALREADY_REGISTERED, "Filespace already registered", False, 0),
            2063: (SDKErrorCode.OBJID_NOT_FOUND, "Object ID not found", False, 0),
            2064: (SDKErrorCode.WRONG_VERSION, "Wrong version", False, 0),
            2065: (SDKErrorCode.WRONG_VERSION, "Wrong version parameter", False, 0),
            2070: (SDKErrorCode.NEED_END_TXN, "Need to end transaction", False, 0),
            2080: (SDKErrorCode.OBJECT_EXCLUDED, "Object excluded", False, 0),
            2081: (SDKErrorCode.OBJECT_NO_BCG, "Object has no backup copy group", False, 0),
            2082: (SDKErrorCode.OBJECT_NO_ACG, "Object has no archive copy group", False, 0),
            2090: (SDKErrorCode.API_SYSTEM_ERROR, "API system error", False, 0),
        })

        # String length validation (2100-2107)
        self._c_to_sdk_map.update({
            2100: (SDKErrorCode.STRING_TOO_LONG, "Description too long", False, 0),
            2101: (SDKErrorCode.STRING_TOO_LONG, "Object info too long", False, 0),
            2102: (SDKErrorCode.STRING_TOO_LONG, "High-level name too long", False, 0),
            2103: (SDKErrorCode.STRING_TOO_LONG, "Password too long", False, 0),
            2104: (SDKErrorCode.STRING_TOO_LONG, "Filespace too long", False, 0),
            2105: (SDKErrorCode.STRING_TOO_LONG, "Low-level name too long", False, 0),
            2106: (SDKErrorCode.STRING_TOO_LONG, "Filespace info too long", False, 0),
            2107: (SDKErrorCode.SENDDATA_ZERO_SIZE, "Send data with zero size", False, 0),
        })

        # Access control codes (2110-2120)
        self._c_to_sdk_map.update({
            2110: (SDKErrorCode.INVALID_ACCESS_TYPE, "Invalid access type", False, 0),
            2111: (SDKErrorCode.QUERY_COMM_FAILURE, "Query communication failure", True, 30),
            2112: (SDKErrorCode.NO_FILES_BACKUP, "No files for backup", False, 0),
            2113: (SDKErrorCode.NO_FILES_ARCHIVE, "No files for archive", False, 0),
            2114: (SDKErrorCode.INVALID_SETACCESS, "Invalid set access", False, 0),
            2120: (SDKErrorCode.STRING_TOO_LONG, "String too long", False, 0),
        })

        # Query and buffer codes (2200-2231)
        self._c_to_sdk_map.update({
            2200: (SDKErrorCode.MORE_DATA_AVAILABLE, "More data available", False, 0),
            2210: (SDKErrorCode.BUFFER_TOO_SMALL, "Buffer too small", False, 0),
            2228: (SDKErrorCode.API_CONFIG_ERROR, "No API config file", False, 0),
            2229: (SDKErrorCode.API_CONFIG_ERROR, "No include/exclude file", False, 0),
            2230: (SDKErrorCode.API_CONFIG_ERROR, "No system or include/exclude", False, 0),
            2231: (SDKErrorCode.NO_POR_SUPPORT, "No point of restart support", False, 0),
        })

        # Miscellaneous API codes (2300-2303) - CRITICAL: includes 2302
        self._c_to_sdk_map.update({
            2300: (SDKErrorCode.NEED_ROOT_PRIVILEGES, "Need root privileges", False, 0),
            2301: (SDKErrorCode.NEED_BIND_MC, "Need to call bind MC", False, 0),
            2302: (
                SDKErrorCode.CHECK_REASON_CODE,
                "Check reason code - transaction vote ABORT",
                False,
                0,
            ),
            2303: (
                SDKErrorCode.DEDUP_SIZE_EXCEEDED,
                "Need to end transaction - dedup size exceeded",
                False,
                0,
            ),
        })

        # Encryption codes (4580-4584)
        self._c_to_sdk_map.update({
            4580: (SDKErrorCode.ENCRYPTION_KEY_ERROR, "Wrong encryption key", False, 0),
            4582: (SDKErrorCode.ENCRYPTION_NOT_AUTHORIZED, "Encryption not authorized", False, 0),
            4584: (SDKErrorCode.ENCRYPTION_TYPE_UNKNOWN, "Encryption type unknown", False, 0),
        })

        # Clustering codes (4600-4606)
        self._c_to_sdk_map.update({
            4600: (SDKErrorCode.CLUSTER_ERROR, "Cluster info library not loaded", False, 0),
            4601: (SDKErrorCode.CLUSTER_ERROR, "Cluster library invalid", False, 0),
            4602: (SDKErrorCode.CLUSTER_ERROR, "Cluster library not loaded", False, 0),
            4603: (SDKErrorCode.CLUSTER_ERROR, "Not member of cluster", False, 0),
            4604: (SDKErrorCode.CLUSTER_ERROR, "Cluster not enabled", False, 0),
            4605: (SDKErrorCode.CLUSTER_ERROR, "Cluster not supported", False, 0),
            4606: (SDKErrorCode.CLUSTER_ERROR, "Cluster unknown error", False, 0),
        })

        # Proxy codes (5702-5749)
        self._c_to_sdk_map.update({
            5702: (SDKErrorCode.PROXY_REJECT, "Proxy reject - no resources", True, 60),
            5705: (SDKErrorCode.PROXY_REJECT, "Proxy reject - duplicate ID", False, 0),
            5710: (SDKErrorCode.PROXY_REJECT, "Proxy reject - ID in use", True, 30),
            5717: (SDKErrorCode.PROXY_REJECT, "Proxy reject - internal error", False, 0),
            5722: (SDKErrorCode.PROXY_REJECT, "Proxy reject - not authorized", False, 0),
            5746: (SDKErrorCode.PROXY_INVALID, "Proxy invalid from node", False, 0),
            5747: (SDKErrorCode.PROXY_INVALID, "Proxy invalid server free", False, 0),
            5748: (SDKErrorCode.PROXY_INVALID, "Proxy invalid cluster", False, 0),
            5749: (SDKErrorCode.PROXY_INVALID, "Proxy invalid function", False, 0),
        })

        # Cryptography/Security codes (5801-5802)
        self._c_to_sdk_map.update({
            5801: (SDKErrorCode.CRYPTO_ERROR, "Crypto ICC error", False, 0),
            5802: (SDKErrorCode.CRYPTO_ERROR, "Crypto ICC cannot load", False, 0),
        })

        # Client-side deduplication codes (6300-6302)
        self._c_to_sdk_map.update({
            6300: (SDKErrorCode.DIGEST_VALIDATION_ERROR, "Digest validation error", False, 0),
            6301: (SDKErrorCode.DATA_FINGERPRINT_ERROR, "Data fingerprint error", False, 0),
            6302: (SDKErrorCode.DATA_DEDUP_ERROR_GENERAL, "Data deduplication error", False, 0),
        })

    def _get_exception_class(self, sdk_code: SDKErrorCode) -> Type[TSMError]:
        code_num = int(sdk_code.value.split('-')[1][:2])
        class_map = {
            11: TSMConnectionError,
            21: TSMAuthenticationError,
            31: TSMResourceError,
            41: TSMObjectError,
            51: TSMTransactionError,
            61: TSMConfigurationError,
            71: TSMOperationError,
            81: TSMDataError,
            91: TSMSystemError
        }
        return class_map.get(code_num, TSMError)

    def map_c_error(self, c_error_code: int, context: Optional[str] = None) -> TSMError:
        """
        Map a C API error code to a Python SDK exception.

        Parameters
        ----------
        c_error_code : int
            The C API return code.
        context : str, optional
            Custom diagnostic error message context.

        Returns
        -------
        TSMError
            The translated exception object.
        """
        if c_error_code in self._c_to_sdk_map:
            sdk_code, default_msg, retry, retry_delay = self._c_to_sdk_map[c_error_code]
            message = context if context else default_msg

            exception_class = self._get_exception_class(sdk_code)
            error = exception_class(
                error_code=sdk_code,
                message=message,
                retry_recommended=retry,
                retry_after=retry_delay
            )
            error._internal_c_code = c_error_code

            log_level = logging.WARNING if retry else logging.ERROR
            self._logger.log(
                log_level,
                "C API error mapped: %s - %s",
                sdk_code.value,
                message,
                extra={
                    'event_type': 'error.mapped',
                    'c_error_code': c_error_code,
                    'sdk_error_code': sdk_code.value,
                    'error_name': sdk_code.name,
                    'c_api_message': context,
                    'category': error.category,
                    'severity': error.severity_level,
                    'retry_recommended': retry,
                    'retry_after': retry_delay
                }
            )

            return error

        message = context if context else f"Unknown error code: {c_error_code}"
        full_message = f"Unmapped C API error {c_error_code}: {message}"
        error = TSMSystemError(
            error_code=SDKErrorCode.UNEXPECTED_ERROR,
            message=full_message
        )
        error._internal_c_code = c_error_code

        self._logger.error(
            "Unmapped C API error: %s - %s",
            c_error_code,
            message,
            extra={
                'event_type': 'error.unmapped',
                'c_error_code': c_error_code,
                'c_api_message': context,
                'sdk_error_code': SDKErrorCode.UNEXPECTED_ERROR.value,
                'action_required': 'Add mapping to _initialize_mappings()'
            }
        )

        return error


_mapper_instance = _InternalErrorMapper()


def _map_internal_error(c_error_code: int, context: Optional[str] = None) -> TSMError:
    return _mapper_instance.map_c_error(c_error_code, context)


map_c_code_to_exception = _map_internal_error


def get_error_info(c_error_code: int) -> Dict[str, Any]:
    """
    Get diagnostic error info for a given C API error code.

    Parameters
    ----------
    c_error_code : int
        The C API return code.

    Returns
    -------
    dict
        A dictionary containing SDK error code, exception class, category, default message,
        and retry recommendation settings.
    """
    if c_error_code in _mapper_instance._c_to_sdk_map:
        sdk_code, default_msg, retry, retry_delay = _mapper_instance._c_to_sdk_map[c_error_code]
        exception_class = _mapper_instance._get_exception_class(sdk_code)

        return {
            'c_error_code': c_error_code,
            'sdk_error_code': sdk_code.value,
            'error_class': exception_class.__name__,
            'category': sdk_code.value.split('-')[1][:2],
            'message': default_msg,
            'retry_recommended': retry,
            'retry_delay': retry_delay
        }

    return {
        'c_error_code': c_error_code,
        'sdk_error_code': 'TSM-9105',
        'error_class': 'TSMSystemError',
        'category': '91',
        'message': 'Unknown error',
        'retry_recommended': False,
        'retry_delay': 0
    }
