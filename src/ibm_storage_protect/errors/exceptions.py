"""
IBM Storage Protect SDK - Exception Classes

This module defines the exception hierarchy for the IBM Storage Protect SDK.
All exceptions inherit from TSMError and provide rich error context including
error codes, severity levels, retry recommendations, and detailed error information.

Exception Hierarchy:
--------------------
TSMError (base exception)
├── TSMConnectionError - Network and connection failures
├── TSMAuthenticationError - Authentication and authorization issues
├── TSMResourceError - Resource exhaustion and quota limits
├── TSMObjectError - Object-related errors (not found, exists, etc.)
├── TSMTransactionError - Transaction and locking problems
├── TSMConfigurationError - Configuration and setup issues
├── TSMOperationError - Operation execution failures
├── TSMDataError - Data corruption and validation errors
└── TSMSystemError - Internal and system-level errors

Key Features:
-------------
1. **Rich Error Context**: Every exception includes error code, message, and details
2. **Severity Levels**: Errors are classified by severity (LOW, MEDIUM, HIGH, CRITICAL)
3. **Retry Logic**: Automatic retry recommendations with suggested delays
4. **Categorization**: Errors are automatically categorized by error code
5. **Serialization**: All exceptions can be converted to dictionaries for logging

Error Severity Levels:
----------------------
- LOW (1): Minor issues that don't prevent operation
- MEDIUM (2): Significant issues requiring attention
- HIGH (3): Serious problems affecting functionality
- CRITICAL (4): Severe failures requiring immediate action

Usage Example:
--------------
    from ibm_storage_protect.errors import BackupError, SDKErrorCode

    try:
        # Perform backup
        client.backup(data)
    except BackupError as e:
        # Access error details
        print(f"Error: {e.message}")
        print(f"Code: {e.error_code.value}")
        print(f"Category: {e.category}")
        print(f"Severity: {e.severity_level}")

        # Check if retry is recommended
        if e.is_retryable:
            print(f"Retry after {e.retry_after} seconds")
            time.sleep(e.retry_after)
            # Retry operation

        # Get full error details as dictionary
        error_dict = e.to_dict()
        logger.error("Backup failed", extra={'error': error_dict})

Notes:
------
- All exceptions include timestamps for tracking
- Internal C API error codes are preserved for debugging
- Exceptions are designed to be JSON-serializable for logging
- Retry recommendations are based on error type and severity

See Also:
---------
- error_codes.py: Complete list of SDK error codes
- mapper.py: Mapping from C API codes to SDK exceptions
"""
from datetime import datetime
from enum import IntEnum
from typing import (
    Any,
    Dict,
    Optional,
)

from ibm_storage_protect.errors.error_codes import SDKErrorCode


class ErrorSeverity(IntEnum):
    """
    Severity levels for SDK exceptions.

    - LOW: Minor issues that do not disrupt the overall operation
    - MEDIUM: Significant issues requiring attention or potential retry
    - HIGH: Serious problems preventing successful operation completion
    - CRITICAL: Severe failures causing execution abort or data risk
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TSMError(Exception):
    """
    Base exception class for all IBM Storage Protect SDK errors.

    Encapsulates standard error details, severity levels, categories,
    and automatic retry recommendations.
    """

    SDK_ERROR_CODE = None
    CATEGORY = "UNKNOWN"
    SEVERITY = ErrorSeverity.MEDIUM
    RETRY_RECOMMENDED = False
    RETRY_DELAY = 0

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        error_code: SDKErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retry_recommended: Optional[bool] = None,
        retry_after: Optional[int] = None
    ):
        """
        Initialize the TSMError.

        Parameters
        ----------
        error_code : SDKErrorCode
            Structured SDK-specific error code.
        message : str
            Human-readable explanation of the error.
        details : dict, optional
            Additional diagnostic context or key-value parameters.
        retry_recommended : bool, optional
            Override recommendation for retrying the operation.
        retry_after : int, optional
            Override delay in seconds before retrying.
        """
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.retry_recommended = (
            retry_recommended if retry_recommended is not None else self.RETRY_RECOMMENDED
        )
        self.retry_after = retry_after if retry_after is not None else self.RETRY_DELAY
        self.timestamp = datetime.now()
        self._internal_c_code: Optional[int] = None

        super().__init__(f"[{error_code.value}] {message}")

    def __str__(self) -> str:
        """
        Return the informal string representation of the exception.

        Returns
        -------
        str
            A formatted string containing the error code and message.
        """
        return f"[{self.error_code.value}] {self.message}"

    def __repr__(self) -> str:
        """
        Return the official string representation of the exception.

        Returns
        -------
        str
            Developer-friendly representation of the error instance.
        """
        return (
            f"{self.__class__.__name__}("
            f"error_code={self.error_code.value}, "
            f"message={self.message!r})"
        )

    @property
    def category(self) -> str:
        """
        Get the error category category string.

        Returns
        -------
        str
            The category (e.g. CONNECTION, RESOURCE, OBJECT).
        """
        code_num = int(self.error_code.value.split('-')[1][:2])
        categories = {
            11: "CONNECTION",
            21: "AUTHENTICATION",
            31: "RESOURCE",
            41: "OBJECT",
            51: "TRANSACTION",
            61: "CONFIGURATION",
            71: "OPERATION",
            81: "DATA",
            91: "SYSTEM"
        }
        return categories.get(code_num, "UNKNOWN")

    @property
    def is_retryable(self) -> bool:
        """
        Check if the operation is recommended to be retried.

        Returns
        -------
        bool
            True if retryable, False otherwise.
        """
        return self.retry_recommended

    @property
    def severity_level(self) -> str:
        """
        Get the name of the error severity level.

        Returns
        -------
        str
            The severity level string (e.g. 'MEDIUM', 'HIGH').
        """
        return self.SEVERITY.name

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the exception data to a dictionary.

        Returns
        -------
        dict
            A dictionary containing all exception details suitable for logging.
        """
        return {
            'error_code': self.error_code.value,
            'error_name': self.error_code.name,
            'message': self.message,
            'category': self.category,
            'severity': self.severity_level,
            'retry_recommended': self.retry_recommended,
            'retry_after': self.retry_after,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }


class TSMConnectionError(TSMError):
    """Exception raised when a connection error occurs with the IBM Storage Protect server."""
    CATEGORY = "CONNECTION"
    SEVERITY = ErrorSeverity.HIGH
    RETRY_RECOMMENDED = True
    RETRY_DELAY = 30


class TSMAuthenticationError(TSMError):
    """Exception raised when authentication with the IBM Storage Protect server fails."""
    CATEGORY = "AUTHENTICATION"
    SEVERITY = ErrorSeverity.HIGH
    RETRY_RECOMMENDED = False


class TSMResourceError(TSMError):
    """Exception raised when a required server resource or storage pool limit is exceeded."""
    CATEGORY = "RESOURCE"
    SEVERITY = ErrorSeverity.MEDIUM
    RETRY_RECOMMENDED = True
    RETRY_DELAY = 300


class TSMObjectError(TSMError):
    """Exception raised for object-level validation, naming, or retrieval issues."""
    CATEGORY = "OBJECT"
    SEVERITY = ErrorSeverity.LOW
    RETRY_RECOMMENDED = False


class TSMTransactionError(TSMError):
    """Exception raised when a C API transaction operation fails or is aborted."""
    CATEGORY = "TRANSACTION"
    SEVERITY = ErrorSeverity.MEDIUM
    RETRY_RECOMMENDED = True
    RETRY_DELAY = 30


class TSMConfigurationError(TSMError):
    """Exception raised when there is a misconfiguration in the connection
    parameters or environment."""
    CATEGORY = "CONFIGURATION"
    SEVERITY = ErrorSeverity.HIGH
    RETRY_RECOMMENDED = False


class TSMOperationError(TSMError):
    """Exception raised when a backup, restore, or query operation fails during execution."""
    CATEGORY = "OPERATION"
    SEVERITY = ErrorSeverity.MEDIUM
    RETRY_RECOMMENDED = False


class TSMDataError(TSMError):
    """Exception raised when corrupt data, invalid buffers, or parsing errors are encountered."""
    CATEGORY = "DATA"
    SEVERITY = ErrorSeverity.HIGH
    RETRY_RECOMMENDED = False


class TSMSystemError(TSMError):
    """Exception raised for critical system-level failures or unmapped errors."""
    CATEGORY = "SYSTEM"
    SEVERITY = ErrorSeverity.CRITICAL
    RETRY_RECOMMENDED = False


IBMStorageProtectError = TSMError
SessionError = TSMConnectionError
LoginError = TSMAuthenticationError
AuthenticationError = TSMAuthenticationError
# pylint: disable=redefined-builtin
ConnectionError = TSMConnectionError
# pylint: enable=redefined-builtin
BackupError = TSMOperationError
TransactionError = TSMTransactionError
ObjectExistsError = TSMObjectError
StoragePoolFullError = TSMResourceError
RestoreError = TSMOperationError
ObjectNotFoundError = TSMObjectError
VersionNotFoundError = TSMObjectError
CorruptDataError = TSMDataError
QueryError = TSMOperationError
InvalidQueryError = TSMOperationError
NoResultsError = TSMObjectError
ObjectMgmtError = TSMObjectError
FsRegisterError = TSMConfigurationError
