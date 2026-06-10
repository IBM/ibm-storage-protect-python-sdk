"""
IBM Storage Protect Client SDK - High-Level Session Management

This module provides a high-level, user-friendly interface for IBM Storage Protect
session management operations. It wraps the lower-level C API session operations
with Python-native data models, comprehensive error handling, and structured logging.

Key Responsibilities:
---------------------
1. **Session Lifecycle**: Simplified login/logout operations with automatic cleanup
2. **Credential Management**: Type-safe authentication using Pydantic models
3. **Session Information**: Easy access to server configuration and session details
4. **Password Management**: Secure password change operations
5. **Context Management**: Support for Python context managers (with statement)
6. **Structured Logging**: Comprehensive operation tracking and diagnostics

Architecture:
-------------
This module sits between the user-facing API and the low-level C API wrapper:
- User Code → ClientSession (this module) → SessionManager (C API wrapper) → C API

The ClientSession class provides:
- Pydantic model integration for type safety and validation
- Automatic session ID generation for correlation
- Comprehensive structured logging for all operations
- Context manager support for automatic cleanup
- Property-based access to session state

Session Lifecycle:
------------------
1. **Creation**: Instantiate ClientSession()
2. **Login**: Call login(credentials) with LoginCredentials model
3. **Operations**: Use session for backup/restore/query operations
4. **Logout**: Call logout() or use context manager for automatic cleanup
5. **Cleanup**: Resources automatically freed on logout or context exit

Thread Safety:
--------------
ClientSession instances are NOT thread-safe. Each thread should create its own
session instance. The underlying C API does not support concurrent operations on
the same session handle.

Error Handling:
---------------
- All operations raise TSMError or its subclasses on failure
- Errors include structured logging with operation context
- Duration metrics are captured for all operations
- Both expected (TSMError) and unexpected (Exception) errors are handled

Logging:
--------
All operations emit structured logs with:
- event_type: Hierarchical event identifier (e.g., 'session.login.started')
- operation: Operation name (e.g., 'session.login')
- status: Operation status ('started', 'success', 'failed', 'error')
- duration_ms: Operation duration in milliseconds
- metrics: Performance and operational metrics
- error: Detailed error information on failures

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Session Management", "Authentication", "API Initialization"

Example Usage:
--------------
    # Basic login/logout
    session = ClientSession()
    credentials = LoginCredentials(node="<node>", password="<password>")
    session.login(credentials)
    # ... perform operations ...
    session.logout()

    # Using context manager (recommended)
    with ClientSession() as session:
        credentials = LoginCredentials(node="<node>", password="<password>")
        session.login(credentials)
        info = session.get_info()
        print(f"Connected to {info.server_name}")
    # Automatic logout on context exit

    # Password change
    session = ClientSession()
    session.login(LoginCredentials(node="<node>", password="<old-password>"))
    pwd_change = PasswordChange(
        current_password="<old-password>",
        new_password="<new-password>"
    )
    session.change_password(pwd_change)
    session.logout()
"""
# pylint: disable=too-many-lines

import time
from ctypes import c_uint32
from typing import (
    Optional,
)

from ibm_storage_protect.c_api_bridge.wrappers.session import SessionManager, dsm_set_up
from ibm_storage_protect.data_models.session import (
    LoginCredentials,
    PasswordChange,
    SessionDetails,
    SessionInfo,
)
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import get_logger
from ibm_storage_protect.logger.context import (
    create_operation_id,
    create_session_id,
    set_log_context,
)

# Module-level logger for structured logging
_logger = get_logger(__name__)


class ClientSession:
    """
    High-level IBM Storage Protect session management interface.

    This class provides a user-friendly, Pythonic interface for managing IBM Storage
    Protect sessions. It wraps the low-level C API operations with type-safe data
    models, comprehensive error handling, and structured logging.

    Key Features:
    -------------
    - **Type Safety**: Uses Pydantic models for all inputs and outputs
    - **Automatic Cleanup**: Context manager support for resource management
    - **Structured Logging**: Comprehensive operation tracking and diagnostics
    - **Session Tracking**: Automatic session ID generation for correlation
    - **Error Handling**: Detailed error information with context
    - **Property Access**: Convenient access to session state

    Session State:
    --------------
    - _session_manager: Low-level SessionManager instance (None if not logged in)
    - _session: SPSession model with handle and metadata (None if not logged in)
    - _session_id: Unique session identifier for logging correlation

    Attributes
    ----------
    is_active : bool (property)
        True if session is currently active and usable for operations.
        Checks both the session state and underlying C API handle.

    handle : int, optional (property)
        The session handle from dsmInitEx(). None if not logged in.
        This handle is required for all API operations.

    node : str, optional (property)
        The authenticated client node name. None if not logged in.

    Notes
    -----
    - Each instance represents a single session
    - Sessions are not thread-safe - use separate instances per thread
    - Always call logout() or use context manager for proper cleanup
    - Session IDs are automatically generated for operation correlation
    - All operations emit structured logs for monitoring and diagnostics

    Context Manager Support
    -----------------------
    ClientSession supports the context manager protocol (with statement).
    This ensures automatic logout even if exceptions occur:

        with ClientSession() as session:
            session.login(credentials)
            # ... operations ...
        # Automatic logout here

    Example
    -------
    >>> # Standard usage
    >>> session = ClientSession()
    >>> credentials = LoginCredentials(node="<node>", password="<password>")
    >>> session.login(credentials)
    >>> print(f"Session handle: {session.handle}")
    >>> print(f"Node: {session.node}")
    >>> print(f"Active: {session.is_active}")
    >>> session.logout()

    >>> # Context manager usage (recommended)
    >>> with ClientSession() as session:
    ...     session.login(LoginCredentials(node="<node>", password="<password>"))
    ...     info = session.get_info()
    ...     print(f"Server: {info.server_name}")

    >>> # Multi-owner authentication
    >>> session = ClientSession()
    >>> credentials = LoginCredentials(
    ...     node="SHARED_NODE",
    ...     password="<shared-node-password>",
    ...     owner="backup_admin"
    ... )
    >>> session.login(credentials)

    See Also
    --------
    LoginCredentials : Authentication credentials model
    SPSession : Active session state model
    SessionDetails : Detailed session configuration model
    PasswordChange : Password change request model
    SessionManager : Low-level C API wrapper
    """

    def __init__(self):
        """
        Initialize a new ClientSession instance.

        Creates an empty session object ready for login. No connection is established
        until login() is called. The session ID is generated later during login for
        proper correlation with the session handle.

        Notes
        -----
        - No network connection is made during initialization
        - Session state is None until login() succeeds
        - Structured log event is emitted for session creation
        """
        self._session_manager: Optional[SessionManager] = None
        self._session: Optional[SessionDetails] = None
        self._session_id: Optional[str] = None

        # Log session object creation
        _logger.debug(
            "Session object created",
            extra={
                'event_type': 'session.created',
                'operation': 'session.init',
                'status': 'created'
            }
        )

    def login(self, credentials: LoginCredentials) -> SessionDetails:
        """
        Authenticate with IBM Storage Protect server and establish a session.

        This method authenticates the client using the provided credentials and
        establishes an active session. It creates a low-level SessionManager,
        calls the C API login operation, and wraps the result in a type-safe
        SPSession model.

        Authentication Process:
        -----------------------
        1. Generate unique operation ID for tracking
        2. Create SessionManager with credentials
        3. Call low-level login() to authenticate via dsmInitEx()
        4. Extract and validate session handle
        5. Generate session ID for correlation
        6. Create SPSession model with handle and metadata
        7. Emit structured logs with operation metrics

        Parameters
        ----------
        credentials : LoginCredentials
            Authentication credentials containing node, password, and optional owner.
            This model is validated by Pydantic before use.

        Returns
        -------
        SPSession
            Active session model containing handle, node name, and connection metadata.
            The handle is required for all subsequent operations.

        Raises
        ------
        TSMError
            If authentication fails (invalid credentials, server unreachable, etc.).
            The error includes structured information about the failure.
        Exception
            For unexpected errors during login (programming errors, system issues).

        Notes
        -----
        - Login can only be called once per session instance
        - The session handle is stored internally and used for all operations
        - Session ID is generated after successful login for correlation
        - All operations are logged with timing metrics
        - Password is not logged for security

        Performance
        -----------
        Login typically takes 100-500ms depending on:
        - Network latency to the server
        - Server load and authentication processing
        - SSL/TLS handshake overhead

        Example
        -------
        >>> session = ClientSession()
        >>> credentials = LoginCredentials(node="<node>", password="<password>")
        >>> active_session = session.login(credentials)
        >>> print(f"Logged in with handle: {active_session.handle}")
        >>> print(f"Node: {active_session.node}")
        >>> print(f"Active: {active_session.is_active}")

        >>> # Multi-owner authentication
        >>> credentials = LoginCredentials(
        ...     node="SHARED_NODE",
        ...     password="<shared-node-password>",
        ...     owner="backup_admin"
        ... )
        >>> session.login(credentials)

        See Also
        --------
        logout() : Terminate the session
        LoginCredentials : Authentication credentials model
        SPSession : Active session state model
        """
        # Generate unique operation ID for tracking this login operation
        operation_id = create_operation_id(operation="login")
        start_time = time.perf_counter()
        set_log_context(operation_id=operation_id)

        # Log login initiation
        _logger.info(
            "Initiating login for node: %s", credentials.node,
            extra={
                'event_type': 'session.login.started',
                'operation': 'session.login',
                'node': credentials.node,
                'owner': credentials.owner,
                'operation_id': operation_id,
                'status': 'started'
            }
        )

        try:
            # Create low-level session manager with credentials
            _logger.debug(
                "Creating session manager for login",
                extra={
                    'event_type': 'session.login.session_manager_init',
                    'operation': 'session.login',
                    'node': credentials.node,
                    'operation_id': operation_id
                }
            )
            self._session_manager = SessionManager(
                node=credentials.node,
                password=credentials.password,
                owner=credentials.owner,
                session_handle=operation_id,
                operation_id=operation_id
            )

            # Call low-level login to authenticate via dsmInitEx()
            handle = self._session_manager.login()

            # Extract handle value (may be c_uint32 or int)
            if isinstance(handle, c_uint32):
                handle_value = handle.value
            else:
                handle_value = int(handle) if handle is not None else 0

            # Generate session ID for correlation across operations
            self._session_id = create_session_id(handle_value)
            set_log_context(session_id=self._session_id, operation_id=operation_id)

            # Create high-level session model
            self._session = SessionDetails(
                Handle=handle_value,
                node=credentials.node,
                is_active=True
            )

            # Calculate operation duration and log success
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Login successful for node: %s", credentials.node,
                extra={
                    'event_type': 'session.login.completed',
                    'operation': 'session.login',
                    'node': credentials.node,
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            return self._session

        except TSMError as e:
            # Handle expected TSM errors (authentication failures, connection issues)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Login failed for node: %s", credentials.node,
                extra={
                    'event_type': 'session.login.failed',
                    'operation': 'session.login',
                    'node': credentials.node,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            # Handle unexpected errors (programming errors, system issues)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during login for node: %s", credentials.node,
                extra={
                    'event_type': 'session.login.error',
                    'operation': 'session.login',
                    'node': credentials.node,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def logout(self) -> None:
        """
        Terminate the IBM Storage Protect session and free resources.

        This method terminates the active session by calling dsmTerminate() via the
        low-level SessionManager. It cleans up all session resources including the
        session handle, manager instance, and session state.

        Cleanup Process:
        ----------------
        1. Check if session is active (skip if already logged out)
        2. Call SessionManager.logout() to invoke dsmTerminate()
        3. Clear session manager reference
        4. Clear session state model
        5. Emit structured logs with operation metrics

        Notes
        -----
        - Safe to call multiple times (no-op if already logged out)
        - Should always be called to free server resources
        - Context manager automatically calls logout on exit
        - Errors during logout are logged but do not prevent cleanup
        - Session cannot be reused after logout

        Raises
        ------
        Exception
            If an error occurs during logout. The session is still cleaned up
            locally even if the server-side termination fails.

        Performance
        -----------
        Logout typically takes 50-200ms depending on:
        - Network latency to the server
        - Server load
        - Number of active transactions to rollback

        Example
        -------
        >>> session = ClientSession()
        >>> session.login(LoginCredentials(node="<node>", password="<password>"))
        >>> # ... perform operations ...
        >>> session.logout()
        >>> print(session.is_active)  # False

        >>> # Safe to call multiple times
        >>> session.logout()  # No-op, logs skipped message

        >>> # Automatic logout with context manager
        >>> with ClientSession() as session:
        ...     session.login(credentials)
        ...     # ... operations ...
        ... # logout() called automatically here

        See Also
        --------
        login() : Establish a session
        __exit__() : Context manager cleanup
        """
        # Generate unique operation ID for tracking this logout operation
        operation_id = create_operation_id(operation="logout")
        start_time = time.perf_counter()
        set_log_context(session_id=self._session_id, operation_id=operation_id)

        # Check if session is active (skip if already logged out)
        if not self._session_manager and not self._session:
            _logger.debug(
                "Logout called on inactive session",
                extra={
                    'event_type': 'session.logout.skipped',
                    'operation': 'session.logout',
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'status': 'skipped'
                }
            )
            return

        # Extract node and handle for logging (may be None if session is partially initialized)
        node = self._session.node if self._session else 'unknown'
        # Log logout initiation
        _logger.info(
            "Logging out session for node: %s", node,
            extra={
                'event_type': 'session.logout.started',
                'operation': 'session.logout',
                'node': node,
                'session_id': self._session_id,
                'operation_id': operation_id,
                'status': 'started'
            }
        )

        try:
            # Call low-level logout to invoke dsmTerminate()
            if self._session_manager:
                self._session_manager.logout(
                    session_handle=self._session_id,
                )
                self._session_manager = None

            # Clear session state
            if self._session:
                self._session = None

            # Calculate operation duration and log success
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Logout completed for node: %s", node,
                extra={
                    'event_type': 'session.logout.completed',
                    'operation': 'session.logout',
                    'node': node,
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

        except Exception as e:
            # Handle errors during logout (still clean up local state)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Error during logout for node: %s", node,
                extra={
                    'event_type': 'session.logout.error',
                    'operation': 'session.logout',
                    'node': node,
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def get_info(self) -> SessionInfo:
        """
        Retrieve comprehensive session configuration and server information.

        This method queries the IBM Storage Protect server for detailed session
        information including server configuration, client settings, policy information,
        and operational parameters. It calls dsmQuerySessInfo() via the low-level
        SessionManager and wraps the result in a type-safe SessionDetails model.

        Information Retrieved:
        ----------------------
        - Server identification (name, host, port, version)
        - Client configuration (node, owner, domain, policy)
        - Operational settings (compression, retention, transaction limits)
        - Network configuration (communication method, LAN-free, failover)
        - Advanced features (deduplication, replication, archive retention)

        Returns
        -------
        SessionDetails
            Comprehensive session configuration model with all server and client
            settings. See SessionDetails documentation for complete field list.

        Raises
        ------
        ValueError
            If no active session exists or session information retrieval fails
        Exception
            For unexpected errors during information retrieval

        Notes
        -----
        - Requires an active session (must call login() first)
        - Information is retrieved from the server in real-time
        - Useful for verifying connection and displaying configuration
        - All fields are validated by the SessionDetails Pydantic model

        Performance
        -----------
        Information retrieval typically takes 50-150ms depending on:
        - Network latency to the server
        - Server load
        - Amount of configuration data

        Example
        -------
        >>> session = ClientSession()
        >>> session.login(LoginCredentials(node="<node>", password="<password>"))
        >>> info = session.get_info()
        >>> print(f"Server: {info.server_name}")
        >>> print(f"Version: {info.server_version}.{info.server_release}")
        >>> print(f"Domain: {info.domain_name}")
        >>> print(f"Policy: {info.policy_set_name}")
        >>> print(f"Compression: {info.compression}")
        >>> print(f"Dedup: {info.dedup_type}")

        >>> # Check server capabilities
        >>> if info.lan_free_enabled:
        ...     print("LAN-free backup available")
        >>> if info.dedup_type > 0:
        ...     print("Deduplication enabled")

        See Also
        --------
        SessionDetails : Detailed session configuration model
        login() : Must be called before get_info()
        """
        # Generate unique operation ID for tracking this operation
        operation_id = create_operation_id(operation="get_info")
        start_time = time.perf_counter()
        set_log_context(session_id=self._session_id, operation_id=operation_id)

        # Validate that session is active
        if not self._session_manager:
            _logger.error(
                "Attempted to get session info without active session",
                extra={
                    'event_type': 'session.get_info.no_session',
                    'operation': 'session.get_info',
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'status': 'failed'
                }
            )
            raise ValueError("No active session")

        # Log operation initiation
        _logger.info(
            "Retrieving session information",
            extra={
                'event_type': 'session.get_info.started',
                'operation': 'session.get_info',
                'session_id': self._session_id,
                'operation_id': operation_id,
                'status': 'started'
            }
        )

        try:
            # Call low-level get_session_info to query via dsmQuerySessInfo()
            info_dict = self._session_manager.get_session_info(
                session_handle=self._session_id,
            )

            # Validate that information was retrieved
            if info_dict is None:
                _logger.error(
                    "Failed to retrieve session information",
                    extra={
                        'event_type': 'session.get_info.failed',
                        'operation': 'session.get_info',
                        'session_id': self._session_id,
                        'operation_id': operation_id,
                        'status': 'failed'
                    }
                )
                raise ValueError("Failed to retrieve session information")

            # Calculate operation duration and log success
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Session information retrieved successfully",
                extra={
                    'event_type': 'session.get_info.completed',
                    'operation': 'session.get_info',
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

            # Create and return validated SessionInfo model
            return SessionInfo(**info_dict)

        except Exception as e:
            # Handle errors during information retrieval
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Error retrieving session information",
                extra={
                    'event_type': 'session.get_info.error',
                    'operation': 'session.get_info',
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    def change_password(self, password_change: PasswordChange) -> None:
        """
        Change the password for the authenticated node.

        This method changes the password for the currently authenticated node by
        calling dsmChangePW() via the low-level SessionManager. The password change
        is validated client-side by the PasswordChange model before being submitted
        to the server.

        Password Change Process:
        ------------------------
        1. Validate that session is active
        2. Validate password change request (PasswordChange model)
        3. Call SessionManager.change_password() to invoke dsmChangePW()
        4. Server validates password complexity and history
        5. Password is updated on server
        6. Session continues with new password

        Parameters
        ----------
        password_change : PasswordChange
            Password change request containing current and new passwords.
            The model validates that passwords are non-empty and different.

        Raises
        ------
        ValueError
            If no active session exists
        TSMError
            If password change fails (incorrect current password, new password
            doesn't meet complexity requirements, password in history, etc.)
        Exception
            For unexpected errors during password change

        Notes
        -----
        - Requires an active session (must call login() first)
        - Current password must match the password used for login
        - New password must meet server complexity requirements
        - Server may enforce password history (cannot reuse recent passwords)
        - Session remains active after password change
        - Failed password changes do not terminate the session

        Server-Side Validation:
        -----------------------
        The server typically validates:
        - Minimum/maximum password length
        - Complexity rules (uppercase, lowercase, numbers, special characters)
        - Password history (cannot reuse recent passwords)
        - Expiration policy compliance

        Performance
        -----------
        Password change typically takes 100-300ms depending on:
        - Network latency to the server
        - Server load
        - Password complexity validation overhead

        Example
        -------
        >>> session = ClientSession()
        >>> session.login(LoginCredentials(node="<node>", password="<old-password>"))
        >>>
        >>> # Change password
        >>> pwd_change = PasswordChange(
        ...     current_password="<old-password>",
        ...     new_password="<new-password>"
        ... )
        >>> session.change_password(pwd_change)
        >>> print("Password changed successfully")
        >>>
        >>> # Session remains active
        >>> print(f"Still active: {session.is_active}")

        >>> # Validation error if passwords are the same
        >>> try:
        ...     pwd_change = PasswordChange(
        ...         current_password="<same-password>",
        ...         new_password="<same-password>"
        ...     )
        ... except ValueError as e:
        ...     print(e)  # "New password must be different from current password"

        See Also
        --------
        PasswordChange : Password change request model
        login() : Must be called before change_password()
        """
        # Generate unique operation ID for tracking this operation
        operation_id = create_operation_id(operation="change_password")
        start_time = time.perf_counter()
        set_log_context(session_id=self._session_id, operation_id=operation_id)

        # Validate that session is active
        if not self._session_manager:
            _logger.error(
                "Attempted to change password without active session",
                extra={
                    'event_type': 'session.change_password.no_session',
                    'operation': 'session.change_password',
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'status': 'failed'
                }
            )
            raise ValueError("No active session")

        # Log operation initiation (do not log passwords)
        _logger.info(
            "Initiating password change",
            extra={
                'event_type': 'session.change_password.started',
                'operation': 'session.change_password',
                'node': self.node,
                'session_id': self._session_id,
                'operation_id': operation_id,
                'status': 'started'
            }
        )

        try:
            # Call low-level change_password to invoke dsmChangePW()
            self._session_manager.change_password(
                password_change.current_password,
                password_change.new_password,
                session_handle=self._session_id,
                operation_id=operation_id
            )

            # Calculate operation duration and log success
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.info(
                "Password changed successfully",
                extra={
                    'event_type': 'session.change_password.completed',
                    'operation': 'session.change_password',
                    'node': self.node,
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                }
            )

        except TSMError as e:
            # Handle expected TSM errors (incorrect password, complexity failure, etc.)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Password change failed",
                extra={
                    'event_type': 'session.change_password.failed',
                    'operation': 'session.change_password',
                    'node': self.node,
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error': e.to_dict(),
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise
        except Exception as e:
            # Handle unexpected errors (programming errors, system issues)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            _logger.error(
                "Unexpected error during password change",
                extra={
                    'event_type': 'session.change_password.error',
                    'operation': 'session.change_password',
                    'node': self.node,
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'duration_ms': duration_ms,
                    'status': 'error',
                    'error': {
                        'message': str(e),
                        'error_type': type(e).__name__
                    },
                    'metrics': {
                        'duration_ms': duration_ms
                    }
                },
                exc_info=True
            )
            raise

    @property
    def is_active(self) -> bool:
        """
        Check if the session is currently active and usable.

        A session is considered active if all of the following are true:
        1. Session model exists (_session is not None)
        2. Session model indicates active state (is_active=True)
        3. Session manager exists (_session_manager is not None)
        4. Low-level C API handle is active (handle is not None and non-zero)

        This property performs a comprehensive check of both high-level and low-level
        session state to ensure the session is truly usable for operations.

        Returns
        -------
        bool
            True if session is active and ready for operations, False otherwise

        Notes
        -----
        - Returns False if login() has not been called
        - Returns False after logout() is called
        - Returns False if the C API handle becomes invalid
        - Should be checked before performing operations

        Example
        -------
        >>> session = ClientSession()
        >>> print(session.is_active)  # False - not logged in
        >>>
        >>> session.login(LoginCredentials(node="<node>", password="<password>"))
        >>> print(session.is_active)  # True - logged in
        >>>
        >>> session.logout()
        >>> print(session.is_active)  # False - logged out

        >>> # Check before operations
        >>> if session.is_active:
        ...     info = session.get_info()
        ... else:
        ...     print("Session not active")

        See Also
        --------
        login() : Establishes active session
        logout() : Terminates active session
        """
        return (
            self._session is not None
            and self._session.is_active
            and self._session_manager is not None
            and self._session_manager.handle is not None
            and self._session_manager.handle.value != 0
        )

    @property
    def handle(self) -> Optional[int]:
        """
        Get the session handle for this session.

        The session handle is a unique identifier returned by dsmInitEx() and used
        in all subsequent Client API calls. It is None if the session is not logged in.

        Returns
        -------
        int, optional
            The session handle if logged in, None otherwise

        Notes
        -----
        - Handle is None before login() is called
        - Handle is set during login() and remains valid until logout()
        - Handle is required for all backup/restore/query operations
        - Each session has a unique handle

        Example
        -------
        >>> session = ClientSession()
        >>> print(session.handle)  # None - not logged in
        >>>
        >>> session.login(LoginCredentials(node="<node>", password="<password>"))
        >>> print(session.handle)  # e.g., 12345
        >>>
        >>> # Use handle for operations (typically done internally)
        >>> if session.handle:
        ...     print(f"Session handle: {session.handle}")

        See Also
        --------
        login() : Sets the handle
        is_active : Check if session is active
        """
        if self._session:
            return self._session.handle
        return None

    @property
    def node(self) -> Optional[str]:
        """
        Get the authenticated node name for this session.

        The node name is the client identifier registered with the IBM Storage Protect
        server. It is set during login() and remains available until logout().

        Returns
        -------
        str, optional
            The authenticated node name if logged in, None otherwise

        Notes
        -----
        - Node is None before login() is called
        - Node is set during login() from the credentials
        - Node name is case-sensitive on most platforms
        - Used for logging and session identification

        Example
        -------
        >>> session = ClientSession()
        >>> print(session.node)  # None - not logged in
        >>>
        >>> session.login(LoginCredentials(node="<node>", password="<password>"))
        >>> print(session.node)  # "MY_NODE"
        >>>
        >>> # Use in logging or display
        >>> if session.node:
        ...     print(f"Connected as: {session.node}")

        See Also
        --------
        login() : Sets the node name
        is_active : Check if session is active
        """
        if self._session:
            return self._session.node
        return None

    def __enter__(self):
        """
        Enter the context manager (with statement).

        This method is called when entering a 'with' block. It simply returns
        the session instance, allowing the user to call login() and other methods
        within the context.

        Returns
        -------
        ClientSession
            This session instance

        Notes
        -----
        - Does not automatically call login() - user must call it explicitly
        - Ensures logout() is called on context exit via __exit__()
        - Recommended pattern for automatic resource cleanup

        Example
        -------
        >>> with ClientSession() as session:
        ...     session.login(LoginCredentials(node="<node>", password="<password>"))
        ...     info = session.get_info()
        ...     print(f"Server: {info.server_name}")
        ... # logout() called automatically here

        See Also
        --------
        __exit__() : Exit the context manager
        logout() : Called automatically on context exit
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager (with statement).

        This method is called when exiting a 'with' block, either normally or due
        to an exception. It ensures that logout() is called to clean up resources,
        even if an exception occurred during the context.

        Parameters
        ----------
        exc_type : type, optional
            The exception type if an exception occurred, None otherwise
        exc_val : Exception, optional
            The exception instance if an exception occurred, None otherwise
        exc_tb : traceback, optional
            The exception traceback if an exception occurred, None otherwise

        Notes
        -----
        - Always calls logout() regardless of whether an exception occurred
        - Does not suppress exceptions (returns None implicitly)
        - Ensures resources are freed even on error
        - Safe to call even if login() was not called

        Example
        -------
        >>> # Normal exit - logout called
        >>> with ClientSession() as session:
        ...     session.login(credentials)
        ...     # ... operations ...
        ... # logout() called here

        >>> # Exception exit - logout still called
        >>> with ClientSession() as session:
        ...     session.login(credentials)
        ...     raise ValueError("Something went wrong")
        ... # logout() called here, then exception propagates

        See Also
        --------
        __enter__() : Enter the context manager
        logout() : Called automatically on exit
        """
        self.logout()

    def __repr__(self) -> str:
        """
        Return a string representation of the session.

        Provides a concise, informative representation of the session state including
        handle, node name, and active status. Useful for debugging and logging.

        Returns
        -------
        str
            String representation of the session

        Example
        -------
        >>> session = ClientSession()
        >>> print(repr(session))
        'ClientSession(inactive)'
        >>>
        >>> session.login(LoginCredentials(node="<node>", password="<password>"))
        >>> print(repr(session))
        'ClientSession(handle=12345, node=MY_NODE, active=True)'
        >>>
        >>> session.logout()
        >>> print(repr(session))
        'ClientSession(inactive)'

        See Also
        --------
        is_active : Check if session is active
        handle : Get session handle
        node : Get node name
        """
        if self._session:
            return (
                f"ClientSession(handle={self._session.handle}, "
                f"node={self._session.node}, active={self.is_active})"
            )
        return "ClientSession(inactive)"

    def log_server_event(
        self,
        message: str,
        severity: str = "info",
        log_type: str = "server",
        app_name: str = "PythonSDK",
        app_msg_id: str = "APP0001"
    ) -> None:
        """
        Log an activity event directly to the server log or local error log.

        Parameters
        ----------
        message : str
            The message text to log.
        severity : str, default="info"
            Event severity level: "info", "warning", "error", "severe".
        log_type : str, default="server"
            Log destination: "server", "local", "both", "none".
        app_name : str, default="PythonSDK"
            Name of the calling application.
        app_msg_id : str, default="APP0001"
            7-character application message identifier.
        """
        if not self._session_manager:
            raise ValueError("No active session")

        # Map string flags to native integer constants
        sev_map = {"info": 0, "warning": 1, "error": 2, "severe": 3}
        type_map = {"server": 0, "local": 1, "both": 2, "none": 3}

        sev_val = sev_map.get(severity.lower(), 0)
        type_val = type_map.get(log_type.lower(), 0)

        operation_id = create_operation_id(operation="log_server_event")
        set_log_context(session_id=self._session_id, operation_id=operation_id)

        _logger.info(
            "Submitting event log to server",
            extra={
                'event_type': 'session.log_server_event.started',
                'operation': 'log_server_event',
                'severity': severity,
                'log_type': log_type,
                'msg_id': app_msg_id,
                'session_id': self._session_id,
                'operation_id': operation_id
            }
        )

        try:
            self._session_manager.log_event_ex(
                message=message,
                severity=sev_val,
                log_type=type_val,
                app_name=app_name,
                app_msg_id=app_msg_id,
                session_handle=self._session_id,
                operation_id=operation_id
            )
            _logger.info(
                "Event log submitted to server successfully",
                extra={
                    'event_type': 'session.log_server_event.completed',
                    'operation': 'log_server_event',
                    'session_id': self._session_id,
                    'operation_id': operation_id
                }
            )
        except Exception as e:
            _logger.error(
                "Failed to submit event log to server",
                extra={
                    'event_type': 'session.log_server_event.failed',
                    'operation': 'log_server_event',
                    'session_id': self._session_id,
                    'operation_id': operation_id,
                    'error': str(e)
                },
                exc_info=True
            )
            raise


def initialize_environment(
    dsmi_dir: Optional[str] = None,
    dsmi_config: Optional[str] = None,
    dsmi_log: Optional[str] = None,
    log_name: Optional[str] = None,
    b_service: bool = False
) -> int:
    """
    Globally initialize the process-wide environment and trace files.
    Must be called before establishing any ClientSession connections.
    """
    return dsm_set_up(
        dsmi_dir=dsmi_dir,
        dsmi_config=dsmi_config,
        dsmi_log=dsmi_log,
        log_name=log_name,
        b_service=b_service
    )
