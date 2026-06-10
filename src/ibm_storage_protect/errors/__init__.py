"""
IBM Storage Protect SDK - Error Handling Module

This module provides the public interface for error handling in the IBM Storage
Protect SDK. It exports all exception classes, error codes, and error severity
levels used throughout the SDK.

Key Components:
---------------
1. **SDKErrorCode**: Enumeration of all SDK error codes
2. **TSMError**: Base exception class with rich error context
3. **Category-Specific Exceptions**: Specialized exception classes for different error types
4. **ErrorSeverity**: Enumeration for error severity levels

Exception Hierarchy:
--------------------
TSMError (base)
├── TSMConnectionError (network and connection issues)
├── TSMAuthenticationError (authentication and authorization)
├── TSMResourceError (resource exhaustion and limits)
├── TSMObjectError (object-related errors)
├── TSMTransactionError (transaction and locking issues)
├── TSMConfigurationError (configuration problems)
├── TSMOperationError (operation failures)
├── TSMDataError (data corruption and validation)
└── TSMSystemError (internal and system errors)

Error Code Format:
------------------
All error codes follow the format TSM-XXYY where:
- XX: Category (11=Connection, 21=Auth, 31=Resource, etc.)
- YY: Specific error within category

Usage Example:
--------------
    from ibm_storage_protect.errors import (
        TSMError,
        BackupError,
        SDKErrorCode
    )

    try:
        # Perform backup operation
        client.backup(data)
    except BackupError as e:
        print(f"Backup failed: {e.message}")
        print(f"Error code: {e.error_code.value}")
        print(f"Retry recommended: {e.is_retryable}")
        if e.is_retryable:
            print(f"Retry after: {e.retry_after} seconds")

See Also:
---------
- error_codes.py: Complete list of SDK error codes
- exceptions.py: Exception class implementations
- mapper.py: C API to SDK error code mapping
"""

# pylint: disable=redefined-builtin

__version__ = "0.1.0"

from .error_codes import SDKErrorCode
from .exceptions import (
    ErrorSeverity,
    TSMError,
    TSMConnectionError,
    TSMAuthenticationError,
    TSMResourceError,
    TSMObjectError,
    TSMTransactionError,
    TSMConfigurationError,
    TSMOperationError,
    TSMDataError,
    TSMSystemError,
    IBMStorageProtectError,
    SessionError,
    BackupError,
    RestoreError,
    QueryError,
    ObjectMgmtError,
    LoginError,
    AuthenticationError,
    ConnectionError,  # pylint: disable=redefined-builtin
    TransactionError,
    ObjectExistsError,
    ObjectNotFoundError,
    FsRegisterError,
    StoragePoolFullError,
    VersionNotFoundError,
    CorruptDataError,
    InvalidQueryError,
    NoResultsError
)

__all__ = [
    "SDKErrorCode",
    "ErrorSeverity",
    "TSMError",
    "TSMConnectionError",
    "TSMAuthenticationError",
    "TSMResourceError",
    "TSMObjectError",
    "TSMTransactionError",
    "TSMConfigurationError",
    "TSMOperationError",
    "TSMDataError",
    "TSMSystemError",
    "IBMStorageProtectError",
    "SessionError",
    "BackupError",
    "RestoreError",
    "QueryError",
    "FsRegisterError",
    "ObjectMgmtError",
    "ConnectionError",
    "TransactionError",
    "ObjectExistsError",
    "ObjectNotFoundError",
    "LoginError",
    "AuthenticationError",
    "StoragePoolFullError",
    "VersionNotFoundError",
    "CorruptDataError",
    "InvalidQueryError",
    "NoResultsError"
]

# Made with Bob
