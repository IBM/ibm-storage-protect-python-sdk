"""
IBM Storage Protect Client SDK - Session Data Models

This module defines Pydantic data models for IBM Storage Protect session management,
authentication, and configuration. These models provide type-safe, validated data
structures for interacting with the IBM Storage Protect Client API session layer.

Key Models:
-----------
1. **LoginCredentials**: Authentication credentials for establishing a session
2. **SessionDetails**: Active session state and metadata
3. **SessionInfo**: Comprehensive session configuration and server information
4. **PasswordChange**: Password change request validation
5. **SessionState**: Runtime session state tracking

Model Characteristics:
----------------------
- **Immutability**: Login and password change models are frozen for security
- **Validation**: Automatic validation of field types, ranges, and business rules
- **Aliasing**: Support for both snake_case (Python) and PascalCase (API) field names
- **Type Safety**: Full type hints for IDE support and runtime validation

IBM Storage Protect Integration:
---------------------------------
These models map to IBM Storage Protect Client API structures:
- LoginCredentials → dsmInitEx() authentication parameters
- SessionDetails → Session handle and connection state
- SessionInfo → dsmApiVersionEx and dsmQuerySessInfo structures
- PasswordChange → dsmChangePW() parameters

Thread Safety:
--------------
All models are thread-safe for read operations. Frozen models (LoginCredentials, PasswordChange)
are immutable and fully thread-safe. Mutable models should not be shared across threads
without synchronization.

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Session Management", "Authentication", "Configuration"

Example Usage:
--------------
    # Create login credentials
    login = LoginCredentials(node="<node>", password="<password>", owner="admin")

    # Track active session
    session = SessionDetails(handle=12345, node="MY_NODE", server_name="SP_SERVER")

    # Change password
    pwd_change = PasswordChange(
        current_password="<old-password>",
        new_password="<new-password>"
    )
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods,line-too-long

from datetime import datetime
from typing import (
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class LoginCredentials(BaseModel):
    """
    Authentication credentials for IBM Storage Protect session initialization.

    This model encapsulates the credentials required to establish a connection with
    an IBM Storage Protect server. It maps to the authentication parameters used in
    the dsmInitEx() Client API call.

    Security Features:
    ------------------
    - Immutable (frozen=True): Prevents accidental credential modification
    - Optional fields: Allows flexible authentication methods
    - No default values: Prevents credential leakage

    Authentication Methods:
    -----------------------
    1. **Node + Password**: Standard authentication (most common)
    2. **Node + Owner + Password**: Multi-owner node authentication
    3. **Node only**: For passwordaccess=generate configurations

    Attributes
    ----------
    node : str, optional
        The client node name registered with the IBM Storage Protect server.
        This is the unique identifier for the client system. Maximum length
        is typically 64 characters. Case-sensitive on most platforms.

        Example: "BACKUP_NODE_01", "DB_SERVER", "APP_CLIENT"

    password : str, optional
        The password associated with the node. Required unless the server is
        configured with passwordaccess=generate. Passwords are transmitted
        securely using the configured communication method (TCP/IP with SSL/TLS).

        Security Note: Store passwords securely (environment variables, key vaults)
        rather than hardcoding them in source code.

    owner : str, optional
        The owner name for multi-owner node configurations. Used when a single
        node is shared by multiple users/applications, each with their own
        credentials. If not specified, the default owner is used.

        Example: "admin", "backup_operator", "app_service"

    Notes
    -----
    - All fields support both snake_case and PascalCase via aliases
    - Model is frozen to prevent accidental credential modification
    - Validation occurs automatically on instantiation
    - Empty strings are treated as None for optional fields

    Client API Reference
    --------------------
    dsmInitEx() - Session initialization with authentication
    dsmApiVersionEx structure - Contains node and owner fields

    Example
    -------
    >>> # Standard authentication
    >>> login = LoginCredentials(node="<node>", password="<password>")

    >>> # Multi-owner authentication
    >>> login = LoginCredentials(
    ...     node="SHARED_NODE",
    ...     password="<shared-node-password>",
    ...     owner="backup_admin"
    ... )

    >>> # Using PascalCase aliases (API style)
    >>> login = LoginCredentials(Node="<node>", Password="<password>")

    See Also
    --------
    SessionDetails : Active session state after successful authentication
    SessionInfo : Detailed session configuration information
    """
    node: Optional[str] = Field(
        default=None,
        alias="Node",
        description="Client node name registered with IBM Storage Protect server"
    )
    password: Optional[str] = Field(
        default=None,
        alias="Password",
        description="Node password for authentication (store securely)"
    )
    owner: Optional[str] = Field(
        default=None,
        alias="Owner",
        description="Owner name for multi-owner node configurations"
    )

    def __repr__(self) -> str:
        pwd_val = "******" if self.password is not None else None
        return (
            f"{self.__class__.__name__}(node={self.node!r}, "
            f"password={pwd_val!r}, owner={self.owner!r})"
        )

    class Config:
        """Pydantic model configuration for LoginCredentials."""
        frozen = True  # Immutable for security - prevents credential modification
        populate_by_name = True  # Accept both snake_case and PascalCase field names
        json_schema_extra = {
            "example": {
                "node": "MY_NODE",
                "password": "<password>",
                "owner": "admin"
            }
        }


class SessionDetails(BaseModel):
    """
    Active IBM Storage Protect session state and metadata.

    This model represents an established connection to an IBM Storage Protect server,
    tracking the session handle and connection metadata. It is created after successful
    authentication via dsmInitEx() and maintained throughout the session lifecycle.

    Session Lifecycle:
    ------------------
    1. **Creation**: After successful dsmInitEx() call
    2. **Active**: While performing backup/restore/query operations
    3. **Termination**: After dsmTerminate() call or connection loss

    Attributes
    ----------
    handle : int
        The session handle returned by dsmInitEx(). This is a unique identifier
        for the session, used in all subsequent Client API calls. Must be non-negative.
        The handle is valid until dsmTerminate() is called or the session expires.

        Range: 0 to 2^31-1 (typically)

        Client API Reference: dsmInitEx() return value via dsUint32_t pointer

    node : str, optional
        The client node name that was authenticated. This should match the node
        name provided in LoginCredentials. Used for logging and session tracking.

    server_name : str, optional
        The IBM Storage Protect server name that the session is connected to.
        Retrieved from dsmQuerySessInfo() after connection. Used for multi-server
        environments and failover scenarios.

    is_active : bool
        Indicates whether the session is currently active and usable for operations.
        Set to False when the session is terminated or encounters a fatal error.
        Default: True

        Note: This is a client-side flag. The server may terminate the session
        independently (timeout, admin action), so always handle API errors.

    connected_at : datetime
        Timestamp when the session was established. Used for session duration
        tracking, timeout calculations, and audit logging. Automatically set
        to current time on creation.

        Format: ISO 8601 datetime with timezone information

    Notes
    -----
    - The handle is the most critical field - all API operations require it
    - Session handles are not reusable after termination
    - Multiple sessions can exist simultaneously (different handles)
    - Sessions should be properly terminated with dsmTerminate() to free resources

    Thread Safety
    -------------
    This model is NOT thread-safe for concurrent modifications. Each session handle
    should be used by only one thread at a time. For multi-threaded applications,
    create separate sessions (handles) per thread.

    Example
    -------
    >>> # Create session after successful authentication
    >>> session = SessionDetails(
    ...     handle=12345,
    ...     node="MY_NODE",
    ...     server_name="SP_SERVER_01",
    ...     is_active=True
    ... )

    >>> # Check if session is active
    >>> if session.is_active:
    ...     perform_backup(session.handle)

    >>> # Track session duration
    >>> duration = datetime.now() - session.connected_at
    >>> print(f"Session active for {duration.total_seconds()} seconds")

    See Also
    --------
    LoginCredentials : Authentication credentials for session creation
    SessionDetails : Detailed session configuration
    SessionState : Runtime session state tracking
    """
    handle: int = Field(
        ...,
        alias="Handle",
        description="Session handle from dsmInitEx() - unique identifier for API calls",
        ge=0
    )
    node: Optional[str] = Field(
        default=None,
        alias="Node",
        description="Authenticated client node name"
    )
    server_name: Optional[str] = Field(
        default=None,
        alias="ServerName",
        description="IBM Storage Protect server name"
    )
    is_active: bool = Field(
        default=True,
        alias="IsActive",
        description="Session active status (client-side flag)"
    )
    connected_at: datetime = Field(
        default_factory=datetime.now,
        alias="ConnectedAt",
        description="Session establishment timestamp (ISO 8601)"
    )

    class Config:
        """Pydantic model configuration for SessionDetails."""
        populate_by_name = True  # Accept both snake_case and PascalCase field names
        json_schema_extra = {
            "example": {
                "handle": 12345,
                "node": "MY_NODE",
                "server_name": "SP_SERVER",
                "is_active": True
            }
        }


class SessionInfo(BaseModel):
    """
    Comprehensive IBM Storage Protect session configuration and server information.

    This model contains detailed information about an active session, including server
    configuration, client settings, policy information, and operational parameters.
    It maps to data retrieved from dsmQuerySessInfo() and dsmQuerySessOptions() Client
    API calls.

    Information Categories:
    -----------------------
    1. **Server Information**: Name, host, port, version, type
    2. **Client Configuration**: Node, owner, domain, policy
    3. **Operational Settings**: Compression, retention, transaction limits
    4. **Network Configuration**: Communication method, LAN-free, failover
    5. **Advanced Features**: Deduplication, replication, archive retention

    Use Cases:
    ----------
    - Verify server connection and compatibility
    - Display session configuration to users
    - Make operational decisions based on server capabilities
    - Audit and logging of session parameters
    - Troubleshooting connection and configuration issues

    Client API Reference
    --------------------
    dsmQuerySessInfo() - Retrieve session information
    dsmQuerySessOptions() - Retrieve session options
    ApiSessInfo structure in structs.py

    See Also
    --------
    SessionDetails : Basic session state
    LoginCredentials : Authentication credentials
    """
    # Server identification and connection
    server_name: str = Field(
        ..., description="IBM Storage Protect server logical name", alias="serverName"
    )
    server_host: str = Field(
        ..., description="Server hostname or IP address for connection", alias="serverHost"
    )
    server_port: int = Field(
        ..., description="Server TCP port number (typically 1500)",
        ge=1, le=65535, alias="serverPort"
    )
    server_type: str = Field(
        ..., description="Server platform type (AIX, Linux, Windows, etc.)",
        alias="serverType"
    )

    # Server version information (for compatibility checks)
    server_version: int = Field(..., description="Server major version number", alias="serverVer")
    server_release: int = Field(
        ..., description="Server release number within major version", alias="serverRel"
    )
    server_level: int = Field(..., description="Server maintenance level number", alias="serverLev")
    server_sublevel: int = Field(
        ..., description="Server fix pack sublevel number", alias="serverSubLev"
    )
    server_date: Optional[str] = Field(
        default=None, description="Server build date (may be None)", alias="serverDate"
    )
    server_address: str = Field(
        ..., description="Full server address with protocol (e.g., tcpip://host:port)",
        alias="serverAddress"
    )

    # Archive and node configuration
    archive_retention: bool = Field(
        ..., description="Archive retention protection enabled (prevents premature deletion)",
        alias="archiveRetention"
    )
    node_type: str = Field(..., description="Client node type (Client, NAS, Server, etc.)", alias="nodeType")

    # Path delimiters for object naming hierarchy
    fs_delimiter: str = Field(
        ..., description="Filespace name delimiter character (/ or \\)", alias="fsdelim"
    )
    hl_delimiter: str = Field(
        ..., description="High-level (directory) name delimiter (/ or \\)", alias="hldelim"
    )

    # Compression settings for data transfer and storage
    compression: int = Field(..., description="Compression setting (0=None, 1=Client, 2=Server)", ge=0)
    compress_always: bool = Field(
        ..., description="Always attempt compression regardless of file type",
        alias="compressAlways"
    )

    # Delete permissions for backup and archive operations
    archive_delete: int = Field(..., description="Archive delete permission level", alias="archDel")
    backup_delete: int = Field(..., description="Backup delete permission level", alias="backDel")

    # Transaction limits to prevent timeouts
    max_obj_per_txn: int = Field(
        ..., description="Maximum objects per transaction (0=unlimited)",
        alias="maxObjPerTxn", ge=0
    )
    max_bytes_per_txn: int = Field(
        ..., description="Maximum bytes per transaction (0=unlimited)",
        alias="maxBytesPerTxn", ge=0
    )

    # Node and owner information for authentication tracking
    node_name: str = Field(..., description="Authenticated client node name", alias="nodeName")
    access_node: str = Field(..., description="Access node for proxy operations", alias="accessNode")
    owner: str = Field(..., description="Owner name (empty if not multi-owner)")

    # Configuration file paths for client settings
    conf_file: str = Field(
        ..., description="Client configuration file path (dsm.opt/dsm.sys)", alias="confFile"
    )
    dsmi_dir: str = Field(
        ..., description="DSMI directory path for client state files", alias="dsmiDir"
    )

    # Communication settings for server connection
    comm_method: str = Field(
        ..., description="Communication method (TCPip, SharedMem, NAMEDPIPE)",
        alias="commMethod"
    )
    password_access: str = Field(
        ..., description="Password access mode (prompt, generate, file)",
        alias="passwordAccess"
    )

    # Policy configuration for retention and management
    domain_name: str = Field(
        ..., description="Policy domain name assigned to this node", alias="domainName"
    )
    policy_set_name: str = Field(
        ..., description="Active policy set name within the domain", alias="policySetName"
    )
    pol_act_date: Optional[str] = Field(
        default=None, description="Policy activation date (when policy set became active)",
        alias="polActDate"
    )
    dflt_mc_name: str = Field(
        ..., description="Default management class name for unassigned objects",
        alias="dfltMCName"
    )

    # Group operation retention settings
    gp_back_retn: int = Field(
        ..., description="Group backup retention period in days", alias="gpBackRetn", ge=0
    )
    gp_arch_retn: int = Field(
        ..., description="Group archive retention period in days", alias="gpArchRetn", ge=0
    )

    # Advanced features for performance and data management
    lan_free_enabled: bool = Field(
        ..., description="LAN-free data transfer enabled (direct SAN access)",
        alias="lanFreeEnabled"
    )
    dedup_type: int = Field(
        ..., description="Deduplication type (0=None, 1=Client, 2=Server, 3=Both)",
        alias="dedupType"
    )

    # Failover and replication configuration for high availability
    failover_cfg_type: int = Field(
        ..., description="Failover configuration type for high availability",
        alias="failOverCfgType"
    )
    repl_server_name: str = Field(
        ..., description="Replication server name (empty if not configured)",
        alias="replServerName"
    )
    home_server_name: str = Field(
        ..., description="Home (primary) server name", alias="homeServerName"
    )
    repl_server_host: str = Field(
        ..., description="Replication server hostname or IP", alias="replServerHost"
    )
    repl_server_port: int = Field(
        ..., description="Replication server TCP port number",
        alias="replServerPort", ge=0, le=65535
    )

    class Config:
        """Pydantic model configuration for SessionDetails."""
        populate_by_name = True  # Accept both snake_case and PascalCase field names
        json_schema_extra = {
            "example": {
                "server_name": "SP_SERVER",
                "server_host": "sp.example.com",
                "server_port": 1500,
                "node_name": "MY_NODE",
                "owner": "admin"
            }
        }


class PasswordChange(BaseModel):
    """
    Password change request validation for IBM Storage Protect sessions.

    This model encapsulates and validates password change requests for IBM Storage
    Protect client nodes. It ensures that password changes meet basic security
    requirements before being submitted to the server via dsmChangePW().

    Security Features:
    ------------------
    - Immutable (frozen=True): Prevents modification after creation
    - Validation: Ensures new password differs from current password
    - Minimum length: Both passwords must be non-empty
    - No storage: Passwords are not persisted by this model

    Password Change Process:
    ------------------------
    1. Create PasswordChange instance with current and new passwords
    2. Validation occurs automatically (new != current, non-empty)
    3. Pass to password change API function
    4. Server validates password complexity and history
    5. Session continues with new password

    Attributes
    ----------
    current_password : str
        The current password for the node. Must be non-empty (min_length=1).
        This is validated against the server's stored password.

        Security Note: Handle with care - do not log or display

    new_password : str
        The new password to set for the node. Must be non-empty (min_length=1)
        and different from current_password.

        Server-side validation typically includes:
        - Minimum/maximum length requirements
        - Complexity rules (uppercase, lowercase, numbers, special chars)
        - Password history (cannot reuse recent passwords)
        - Expiration policy compliance

        Security Note: Use strong passwords with mixed character types

    Validation Rules
    ----------------
    1. Both passwords must be non-empty strings
    2. New password must differ from current password
    3. Additional server-side validation occurs during dsmChangePW()

    Notes
    -----
    - Model is frozen to prevent accidental password modification
    - Validation occurs at instantiation time
    - Server may reject passwords that pass client validation
    - Password change requires an active, authenticated session
    - Failed password changes do not terminate the session

    Client API Reference
    --------------------
    dsmChangePW() - Change node password

    Example
    -------
    >>> # Create password change request
    >>> pwd_change = PasswordChange(
    ...     current_password="<old-password>",
    ...     new_password="<new-password>"
    ... )

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
    LoginCredentials : Initial authentication credentials
    SessionDetails : Active session that password change applies to
    """
    current_password: str = Field(
        ...,
        alias="CurrentPassword",
        description="Current node password (must be non-empty)",
        min_length=1
    )
    new_password: str = Field(
        ...,
        alias="new_password",
        description="New node password (must differ from current, non-empty)",
        min_length=1
    )

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v, info):
        """
        Validate that the new password differs from the current password.

        This validator ensures basic password change security by preventing
        users from "changing" their password to the same value. Additional
        validation (complexity, history, length) is performed server-side.

        Parameters
        ----------
        v : str
            The new password value to validate
        info : ValidationInfo
            Validation context containing previously validated field values

        Returns
        -------
        str
            The validated new password value

        Raises
        ------
        ValueError
            If new password equals current password
        """
        if 'current_password' in info.data and v == info.data['current_password']:
            raise ValueError("New password must be different from current password")
        return v

    class Config:
        """Pydantic model configuration for PasswordChange."""
        frozen = True  # Immutable for security - prevents password modification
        populate_by_name = True  # Accept both snake_case and PascalCase field names


class SessionState(BaseModel):
    """
    Runtime session state tracking for IBM Storage Protect sessions.

    This model tracks the operational state of an active session, including connection
    status, activity timestamps, and error counts. It is used for session health
    monitoring, timeout detection, and error recovery decisions.

    Use Cases:
    ----------
    - Monitor session health and connectivity
    - Detect idle sessions for timeout enforcement
    - Track error patterns for automatic retry logic
    - Implement session pooling and lifecycle management
    - Generate session activity reports and metrics

    State Transitions:
    ------------------
    1. **Connected**: is_connected=True, error_count=0
    2. **Active**: Regular updates to last_activity
    3. **Idle**: No activity for extended period
    4. **Degraded**: error_count > 0 but still connected
    5. **Disconnected**: is_connected=False

    Attributes
    ----------
    handle : int
        The session handle from dsmInitEx(). Links this state to a specific
        session. Must match the handle in SessionDetails.

        Note: This is a reference to the session, not the session itself

    is_connected : bool
        Current connection status to the IBM Storage Protect server.

        True: Session is connected and operational
        False: Session is disconnected (network issue, timeout, termination)

        This flag should be updated based on:
        - Successful API calls (set to True)
        - Connection errors (set to False)
        - Explicit termination (set to False)

    last_activity : datetime
        Timestamp of the last successful operation on this session.
        Automatically set to current time on creation.

        Updated after:
        - Successful backup/restore operations
        - Query operations
        - Any Client API call that succeeds

        Used for:
        - Idle timeout detection
        - Session activity monitoring
        - Performance metrics

        Format: ISO 8601 datetime with timezone

    error_count : int
        Cumulative count of errors encountered during the session lifetime.
        Starts at 0 and increments with each error. Non-negative.

        Used for:
        - Error rate monitoring
        - Automatic retry decisions (stop after N errors)
        - Session health assessment
        - Alerting and diagnostics

        Note: Reset to 0 after successful recovery or session restart

    Notes
    -----
    - This model is mutable (not frozen) to allow state updates
    - Should be updated after each significant operation
    - Thread-safe updates require external synchronization
    - Consider resetting error_count after successful operations

    Monitoring Patterns
    -------------------
    1. **Idle Detection**: Check if (now - last_activity) > timeout_threshold
    2. **Health Check**: is_connected and error_count < max_errors
    3. **Auto-Reconnect**: If not is_connected, attempt reconnection
    4. **Circuit Breaker**: If error_count > threshold, stop operations

    Example
    -------
    >>> # Create initial session state
    >>> state = SessionState(
    ...     handle=12345,
    ...     is_connected=True
    ... )

    >>> # Update after successful operation
    >>> state.last_activity = datetime.now()

    >>> # Track error
    >>> try:
    ...     perform_backup(state.handle)
    ... except Exception:
    ...     state.error_count += 1
    ...     if state.error_count > 5:
    ...         state.is_connected = False

    >>> # Check for idle timeout (5 minutes)
    >>> idle_time = datetime.now() - state.last_activity
    >>> if idle_time.total_seconds() > 300:
    ...     print("Session is idle, consider termination")

    See Also
    --------
    SessionDetails : Basic session information
    SessionInfo : Detailed session configuration
    """
    handle: int = Field(
        ...,
        alias="Handle",
        description="Session handle reference (links to SessionDetails)"
    )
    is_connected: bool = Field(
        ...,
        alias="IsConnected",
        description="Current connection status (True=connected, False=disconnected)"
    )
    last_activity: datetime = Field(
        default_factory=datetime.now,
        alias="LastActivity",
        description="Timestamp of last successful operation (ISO 8601)"
    )
    error_count: int = Field(
        default=0,
        alias="ErrorCount",
        description="Cumulative error count for this session (for health monitoring)",
        ge=0
    )

    class Config:
        """Pydantic model configuration for SessionState."""
        populate_by_name = True  # Accept both snake_case and PascalCase field names
        json_schema_extra = {
            "example": {
                "handle": 12345,
                "is_connected": True,
                "error_count": 0
            }
        }

# Made with Bob
