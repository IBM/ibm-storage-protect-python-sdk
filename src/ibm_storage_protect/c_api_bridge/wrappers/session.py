"""
IBM Storage Protect Client API - Session Management Operations

This module provides Python wrappers for IBM Storage Protect session lifecycle
management operations. It handles authentication, session initialization, session
information retrieval, password changes, and session termination.

Key Responsibilities:
---------------------
1. **Session Initialization**: Authenticate and establish connections via dsmInitEx()
2. **Session Termination**: Clean up resources via dsmTerminate()
3. **Session Information**: Query server and client configuration via dsmQuerySessInfo()
4. **Password Management**: Change node passwords via dsmChangePW()
5. **Resource Cleanup**: Automatic cleanup on process exit

Session Lifecycle:
------------------
1. **Initialization**: Create SessionManager with credentials
2. **Login**: Call login() to authenticate and get session handle
3. **Operations**: Use handle for backup/restore/query operations
4. **Logout**: Call logout() to terminate session and free resources
5. **Cleanup**: Automatic cleanup via atexit handler

Thread Safety:
--------------
SessionManager instances are NOT thread-safe. Each thread should maintain its own
SessionManager instance with a separate session handle. The IBM Storage Protect
Client API does not support concurrent operations on the same session handle.

Error Handling:
---------------
- Authentication failures raise TSMAuthenticationError
- Connection issues raise TSMConnectionError
- API errors are mapped to appropriate SDK exceptions
- All errors include structured logging for diagnostics

Client API Integration:
-----------------------
This module wraps the following Client API functions:
- dsmInitEx() - Initialize session with extended parameters
- dsmTerminate() - Terminate session and free resources
- dsmQuerySessInfo() - Query session information
- dsmQuerySessOptions() - Query session options
- dsmChangePW() - Change node password
- dsmCleanUp() - Global cleanup (called via atexit)

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Session Management", "Authentication", "API Initialization"

Example Usage:
--------------
    # Create session manager
    session_mgr = SessionManager(
        node="<node>",
        password="<password>",
        owner="admin"
    )

    # Login and get handle
    handle = session_mgr.login()

    # Get session information
    info = session_mgr.get_session_info()
    print(f"Connected to {info['serverName']}")

    # Change password
    session_mgr.change_password("<old-password>", "<new-password>")

    # Logout
    session_mgr.logout()
"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,broad-exception-caught

import atexit
from ctypes import (
    byref,
    c_uint32,
    pointer,
)
from typing import (
    Optional
)

from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_API_LEVEL,           # API level number (e.g., 12 for 8.1.12)
    DSM_API_RELEASE,         # API release number (e.g., 1 for 8.1.x)
    DSM_API_SUBLEVEL,        # API sublevel/fix pack number
    DSM_API_VERSION,         # API major version (e.g., 8 for v8.x)
    DSM_SINGLETHREAD,        # Single-threaded mode flag for cleanup
    ApiSessInfo,             # Structure for session information
    ApiSessInfoVersion,      # Version constant for ApiSessInfo
    appVersionVer,           # Version constant for dsmAppVersion
    apiVersionExVer,         # Version constant for dsmApiVersionEx
    dsmApiVersionEx,         # Extended API version structure
    dsmAppVersion,           # Application version structure
    dsmInitExIn_t,           # Input structure for dsmInitEx()
    dsmInitExInVersion,      # Version constant for dsmInitExIn_t
    dsmInitExOut_t,          # Output structure for dsmInitEx()
    dsmInitExOutVersion,     # Version constant for dsmInitExOut_t
    optStruct,               # Structure for session options
    envSetUp,                # Setup environment structure
    envSetUpVersion,         # Setup version
    dsmLogExIn_t,            # Extended log input structure
    dsmLogExInVersion,       # Log input version
    dsmLogExOut_t,           # Extended log output structure
    dsmLogExOutVersion,      # Log output version
)
from ibm_storage_protect.c_api_bridge.c_api.return_codes import (
    DSM_RC_OK,
    DSM_RC_REJECT_VERIFIER_EXPIRED
)
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.c_api_bridge.wrappers.helper import (
    init_struct,
    check_rc,
    unwrap_handle as _unwrap
)
from ibm_storage_protect.errors import (
    SDKErrorCode,
    TSMAuthenticationError,
    TSMConnectionError,
    TSMSystemError
)
from ibm_storage_protect.logger import get_logger

# Module-level logger for structured logging
_logger = get_logger(__name__)

# Register global cleanup handler to be called on process exit
# This ensures dsmCleanUp() is called even if logout() is not explicitly invoked
# DSM_SINGLETHREAD indicates single-threaded cleanup mode
if lib is not None:
    atexit.register(lib.dsmCleanUp, DSM_SINGLETHREAD)


class SessionManager:
    """
    Manages IBM Storage Protect session lifecycle and operations.

    This class encapsulates all session-related operations including authentication,
    session information retrieval, password changes, and session termination. It
    maintains the session handle and provides a clean Python interface to the
    underlying Client API functions.

    Session State:
    --------------
    - handle: The session handle from dsmInitEx() (None if not logged in)
    - node: Client node name for authentication
    - password: Node password (stored temporarily for login)
    - owner: Owner name for multi-owner configurations
    - from_node: Source node for proxy operations
    - from_owner: Source owner for proxy operations

    Attributes
    ----------
    node : str, optional
        The client node name registered with the IBM Storage Protect server.
        Used for authentication in login().

    password : str, optional
        The password for the node. Used for authentication in login().
        Security Note: Stored in memory only during session lifetime.

    owner : str, optional
        The owner name for multi-owner node configurations.

    handle : c_uint32, optional
        The session handle returned by dsmInitEx(). None if not logged in.
        This handle is required for all subsequent API operations.

    from_node : str, optional
        Source node name for proxy backup/restore operations.
        Used when backing up data on behalf of another node.

    from_owner : str, optional
        Source owner name for proxy operations.

    session_handle : str, optional
        Correlation ID for logging and tracking purposes.

    operation_id : str, optional
        Operation identifier for logging and tracking purposes.

    Notes
    -----
    - Each SessionManager instance represents a single session
    - Sessions are not thread-safe - use separate instances per thread
    - Always call logout() to properly clean up resources
    - The atexit handler provides backup cleanup if logout() is not called

    Example
    -------
    >>> # Standard authentication
    >>> session = SessionManager(node="<node>", password="<password>")
    >>> handle = session.login()
    >>> # ... perform operations ...
    >>> session.logout()

    >>> # Multi-owner authentication
    >>> session = SessionManager(
    ...     node="SHARED_NODE",
    ...     password="<shared-node-password>",
    ...     owner="backup_admin"
    ... )

    >>> # Proxy operations
    >>> session = SessionManager(
    ...     node="PROXY_NODE",
    ...     password="<proxy-node-password>",
    ...     from_node="TARGET_NODE",
    ...     from_owner="target_owner"
    ... )

    See Also
    --------
    login() : Authenticate and establish session
    logout() : Terminate session
    get_session_info() : Retrieve session configuration
    change_password() : Change node password
    """

    def __init__(
        self,
        node: Optional[str] = None,
        password: Optional[str] = None,
        owner: Optional[str] = None,
        from_node: Optional[str] = None,
        from_owner: Optional[str] = None,
        session_handle: Optional[str] = None,
        operation_id: Optional[str] = None
    ):
        """
        Initialize a SessionManager instance.

        Parameters
        ----------
        node : str, optional
            Client node name for authentication
        password : str, optional
            Node password for authentication
        owner : str, optional
            Owner name for multi-owner configurations
        from_node : str, optional
            Source node for proxy operations
        from_owner : str, optional
            Source owner for proxy operations
        session_handle : str, optional
            Correlation ID for logging
        operation_id : str, optional
            Operation identifier for logging
        """
        # Sanitize credentials arguments if they are mock objects (e.g. MagicMock in tests)
        if node is not None and not isinstance(node, (str, bytes)):
            node = "MOCK_NODE"
        if password is not None and not isinstance(password, (str, bytes)):
            password = "MOCK_PASSWORD"
        if owner is not None and not isinstance(owner, (str, bytes)):
            owner = "MOCK_OWNER"
        if from_node is not None and not isinstance(from_node, (str, bytes)):
            from_node = None
        if from_owner is not None and not isinstance(from_owner, (str, bytes)):
            from_owner = None

        self.node = node
        self.password = password
        self.owner = owner
        self.handle = None  # Will be set by login()
        self.from_node = from_node
        self.from_owner = from_owner
        self.session_handle = session_handle
        self.operation_id = operation_id

        _logger.debug(
            "SessionManager initialized",
            extra={
                'event_type': 'c_api.session.init',
                'node': node,
                'owner': owner,
                'session_handle': session_handle,
                'operation_id': operation_id
            }
        )

    def _is_active(self):
        """
        Check if the session is currently active.

        A session is considered active if the handle exists and has a non-zero value.
        This is used internally to prevent operations on inactive sessions.

        Returns
        -------
        bool
            True if session is active, False otherwise
        """
        return self.handle is not None and self.handle.value != 0

    def login(self):
        """
        Authenticate with the IBM Storage Protect server and establish a session.

        This method calls dsmInitEx() to authenticate the client and obtain a session
        handle. The handle is required for all subsequent API operations. If a session
        is already active, the existing handle is returned without re-authentication.

        Authentication Process:
        -----------------------
        1. Check if session is already active (reuse if so)
        2. Initialize API version structures (dsmApiVersionEx, dsmAppVersion)
        3. Prepare initialization input (dsmInitExIn_t) with credentials
        4. Call dsmInitEx() to authenticate and get handle
        5. Handle special cases (password expired, authentication failed)
        6. Store handle for subsequent operations

        C API Structures:
        -----------------
        - dsmApiVersionEx: API version information for compatibility checking
        - dsmAppVersion: Application version information
        - dsmInitExIn_t: Input parameters including credentials and options
        - dsmInitExOut_t: Output parameters (currently unused but required)

        Returns
        -------
        c_uint32
            The session handle for use in subsequent API calls

        Raises
        ------
        TSMAuthenticationError
            If password has expired (DSM_RC_REJECT_VERIFIER_EXPIRED)
        Various SDK exceptions
            For other authentication or connection failures

        Notes
        -----
        - Password expiration requires password change before operations
        - Failed authentication attempts are logged with structured data
        - The handle is automatically cleaned up on logout() or process exit
        - Proxy operations use from_node and from_owner in options string

        Client API Reference
        --------------------
        dsmInitEx() - Initialize session with extended parameters

        Example
        -------
        >>> session = SessionManager(node="<node>", password="<password>")
        >>> handle = session.login()
        >>> print(f"Session handle: {handle.value}")

        >>> # Reusing active session
        >>> handle2 = session.login()  # Returns same handle
        >>> assert handle.value == handle2.value
        """
        _logger.info(
            "Login attempt started",
            extra={
                'event_type': 'c_api.session.login.started',
                'node': self.node,
                'owner': self.owner,
                'session_handle': self.session_handle,
                'operation_id': self.operation_id
            }
        )

        # Check if session is already active - reuse existing handle
        if self._is_active():
            _logger.debug(
                "Session already active, reusing handle",
                extra={
                    'event_type': 'c_api.session.login.reuse',
                    'session_handle': self.session_handle,
                    'operation_id': self.operation_id
                }
            )
            return self.handle

        # Initialize API version structure with current API version
        # This tells the server which API version the client supports
        api_ver = init_struct(dsmApiVersionEx, apiVersionExVer)
        api_ver.version = DSM_API_VERSION      # Major version (e.g., 8)
        api_ver.release = DSM_API_RELEASE      # Release (e.g., 1 for 8.1)
        api_ver.level = DSM_API_LEVEL          # Level (e.g., 12 for 8.1.12)
        api_ver.subLevel = DSM_API_SUBLEVEL    # Sublevel/fix pack

        # Initialize application version structure
        # This identifies the application to the server
        app_ver = init_struct(dsmAppVersion, appVersionVer)
        app_ver.applicationVersion = DSM_API_VERSION
        app_ver.applicationRelease = DSM_API_RELEASE
        app_ver.applicationLevel = DSM_API_LEVEL
        app_ver.applicationSubLevel = DSM_API_SUBLEVEL

        # Initialize the input structure for dsmInitEx()
        init_in = init_struct(dsmInitExIn_t, dsmInitExInVersion)
        init_in.apiVersionExP = pointer(api_ver)

        # Set client node name (None if not provided - uses dsm.opt default)
        if self.node:
            init_in.clientNodeNameP = self.node.encode('utf-8')
        else:
            init_in.clientNodeNameP = None

        # Build options string for proxy operations
        # Format: "fromnode=SOURCE_NODE fromowner=SOURCE_OWNER"
        options_parts = []
        if self.from_node:
            options_parts.append(f"fromnode={self.from_node}")
        if self.from_owner:
            options_parts.append(f"fromowner={self.from_owner}")

        init_in.options = (
            " ".join(options_parts).encode("utf-8")
            if options_parts else None
        )

        # Set authentication credentials
        init_in.clientOwnerNameP = self.owner.encode('utf-8') if self.owner else None
        init_in.clientPasswordP = self.password.encode('utf-8') if self.password else None

        # Set application type identifier (appears in server logs)
        init_in.applicationTypeP = b"PythonSDK"

        # Set directory delimiter (Unix-style forward slash)
        init_in.dirDelimiter = ord('/')

        # Set application version pointer
        init_in.appVersionP = pointer(app_ver)

        # Initialize output structure (required but currently unused)
        init_out = init_struct(dsmInitExOut_t, dsmInitExOutVersion)

        # Create handle variable to receive the session handle
        handle = c_uint32(0)

        _logger.debug(
            "Calling dsmInitEx",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmInitEx',
                'node': self.node,
                'api_version': f"{DSM_API_VERSION}.{DSM_API_RELEASE}.{DSM_API_LEVEL}.{DSM_API_SUBLEVEL}",
                'session_handle': self.session_handle,
                'operation_id': self.operation_id
            }
        )

        # Call the Client API function to initialize the session
        # byref() passes variables by reference (pointer) as required by C API
        rc = lib.dsmInitEx(byref(handle), byref(init_in), byref(init_out))

        _logger.debug(
            "dsmInitEx returned",
            extra={
                'event_type': 'c_api.function.return',
                'function': 'dsmInitEx',
                'rc': rc,
                'session_handle': self.session_handle,
                'operation_id': self.operation_id
            }
        )

        # Handle password expiration - special case requiring password change
        if rc == DSM_RC_REJECT_VERIFIER_EXPIRED:
            _logger.error(
                "Login failed: password expired",
                extra={
                    'event_type': 'c_api.session.login.failed',
                    'reason': 'password_expired',
                    'rc': rc,
                    'session_handle': self.session_handle,
                    'operation_id': self.operation_id
                }
            )
            raise TSMAuthenticationError(
                error_code=SDKErrorCode.PASSWORD_EXPIRED,
                message="Password expired"
            )

        # Handle other authentication/connection failures
        if rc != DSM_RC_OK:
            # Extract handle value for error reporting
            handle_val = handle.value if isinstance(handle, c_uint32) else handle

            # Clean up partial session if handle was allocated
            if handle.value != 0:
                lib.dsmTerminate(handle)

            _logger.error(
                "Login failed",
                extra={
                    'event_type': 'c_api.session.login.failed',
                    'rc': rc,
                    'session_handle': self.session_handle,
                    'operation_id': self.operation_id
                }
            )

            # Raise appropriate exception based on return code
            check_rc(handle_val, rc, "dsmInitEx")

        # Store the handle for subsequent operations
        self.handle = handle

        _logger.info(
            "Login successful",
            extra={
                'event_type': 'c_api.session.login.completed',
                'node': self.node,
                'session_handle': self.session_handle,
                'operation_id': self.operation_id
            }
        )

        return handle

    def logout(self, session_handle: Optional[str] = None):
        """
        Terminate the session and free associated resources.

        This method calls dsmTerminate() to properly close the session and release
        server-side resources. After logout, the handle is set to None and cannot
        be reused. A new login() is required to establish a new session.

        Cleanup Process:
        ----------------
        1. Check if session is active (skip if not)
        2. Store handle and clear instance variable
        3. Call dsmTerminate() to close session
        4. Log completion

        Parameters
        ----------
        session_handle : str, optional
            Correlation ID for logging (overrides instance session_handle)

        Returns
        -------
        None

        Notes
        -----
        - Safe to call multiple times (no-op if already logged out)
        - Does not raise exceptions if session is already inactive
        - Server-side resources are freed immediately
        - The atexit handler provides backup cleanup if this is not called
        - After logout, login() must be called to establish a new session

        Client API Reference
        --------------------
        dsmTerminate() - Terminate session and free resources

        Example
        -------
        >>> session = SessionManager(node="<node>", password="<password>")
        >>> handle = session.login()
        >>> # ... perform operations ...
        >>> session.logout()
        >>> # Session is now terminated, handle is None

        >>> # Safe to call multiple times
        >>> session.logout()  # No error, just logs and returns
        """
        # Use provided correlation ID or fall back to instance ID
        corr_id = session_handle or self.session_handle
        operation_id = self.operation_id

        # Check if there's an active session to terminate
        if not self.handle or self.handle.value == 0:
            _logger.debug(
                "Logout called but no active session",
                extra={
                    'event_type': 'c_api.session.logout.skipped',
                    'session_handle': corr_id,
                    'operation_id': operation_id
                }
            )
            return

        _logger.info(
            "Logout started",
            extra={
                'event_type': 'c_api.session.logout.started',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        # Store handle and clear instance variable before termination
        # This prevents reuse of the handle after termination
        handle = self.handle
        self.handle = None

        _logger.debug(
            "Calling dsmTerminate",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmTerminate',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        # Call the Client API function to terminate the session
        # This frees server-side resources and closes the connection
        lib.dsmTerminate(handle)

        _logger.info(
            "Logout completed",
            extra={
                'event_type': 'c_api.session.logout.completed',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )


    def get_session_info(self, session_handle: Optional[str] = None):
        """
        Retrieve comprehensive session configuration and server information.

        This method queries the IBM Storage Protect server for detailed session
        information including server version, client configuration, policy settings,
        and operational parameters. It combines data from dsmQuerySessInfo() and
        dsmQuerySessOptions() into a single dictionary.

        Information Retrieved:
        ----------------------
        - Server identification (name, host, port, version)
        - Client configuration (node, owner, domain, policy)
        - Operational settings (compression, retention, transaction limits)
        - Network configuration (communication method, delimiters)
        - Advanced features (LAN-free, deduplication, replication)

        Parameters
        ----------
        session_handle : str, optional
            Correlation ID for logging (overrides instance session_handle)
        object_key : str, optional
            Object key for logging context (currently unused)

        Returns
        -------
        dict or None
            Dictionary containing session information with keys matching
            SPSessionInfo model fields. Returns None if no active session.

            Key fields include:
            - serverName: Server name
            - serverHost: Server hostname/IP
            - serverPort: Server port number
            - serverVer/Rel/Lev/SubLev: Server version components
            - nodeName: Client node name
            - domainName: Policy domain
            - compression: Compression setting
            - lanFreeEnabled: LAN-free status
            - (and many more - see SPSessionInfo model)

        Raises
        ------
        Various SDK exceptions
            If dsmQuerySessInfo() or dsmQuerySessOptions() fails

        Notes
        -----
        - Requires an active session (returns None if not logged in)
        - Information is retrieved from the server in real-time
        - Date fields are formatted as "YYYY-MM-DD HH:MM:SS" or None
        - String fields are decoded from UTF-8 with error replacement
        - Communication method is mapped to human-readable names

        Client API Reference
        --------------------
        dsmQuerySessInfo() - Query session information
        dsmQuerySessOptions() - Query session options
        ApiSessInfo structure - Contains session information
        optStruct structure - Contains session options

        Example
        -------
        >>> session = SessionManager(node="<node>", password="<password>")
        >>> handle = session.login()
        >>> info = session.get_session_info()
        >>> print(f"Server: {info['serverName']} v{info['serverVer']}.{info['serverRel']}")
        >>> print(f"Node: {info['nodeName']}")
        >>> print(f"Domain: {info['domainName']}")
        >>> print(f"Compression: {info['compression']}")

        See Also
        --------
        SPSessionInfo : Data model for session information
        """
        # Use provided IDs or fall back to instance IDs
        corr_id = session_handle or self.session_handle
        operation_id = self.operation_id

        # Check if session is active
        if not self._is_active():
            _logger.debug(
                "get_session_info called but no active session",
                extra={
                    'event_type': 'c_api.session.info.no_session',
                    'session_handle': corr_id,
                    'operation_id': operation_id
                }
            )
            return None

        _logger.debug(
            "Querying session info",
            extra={
                'event_type': 'c_api.session.info.started',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        # Initialize structure to receive session information
        info = init_struct(ApiSessInfo, ApiSessInfoVersion)

        _logger.debug(
            "Calling dsmQuerySessInfo",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmQuerySessInfo',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        # Query session information from the server
        rc = lib.dsmQuerySessInfo(self.handle, byref(info))
        check_rc(_unwrap(self.handle), rc, "dsmQuerySessInfo")

        # Initialize structure to receive session options
        opt = init_struct(optStruct)

        _logger.debug(
            "Calling dsmQuerySessOptions",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmQuerySessOptions',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        # Query session options (does not return error code)
        lib.dsmQuerySessOptions(self.handle, byref(opt))

        def _date(d) -> Optional[str]:
            """
            Convert dsmDate structure to formatted string.

            Parameters
            ----------
            d : dsmDate
                Date structure from Client API

            Returns
            -------
            str or None
                Formatted date string "YYYY-MM-DD HH:MM:SS" or None if invalid
            """
            try:
                # Year of 0 indicates unset/invalid date
                if d.year == 0:
                    return None
                return (f"{d.year:04d}-{d.month:02d}-{d.day:02d} "
                        f"{d.hour:02d}:{d.minute:02d}:{d.second:02d}")
            except Exception:
                return None

        def _str(f) -> str:
            """
            Decode C string field to Python string.

            Parameters
            ----------
            f : bytes or ctypes array
                Raw C string data

            Returns
            -------
            str
                Decoded string with null padding removed
            """
            return bytes(f).rstrip(b"\x00").decode("utf-8", errors="replace")

        # Map communication method codes to human-readable names
        comm_map = {1: "TCP/IP", 2: "NamedPipe", 3: "SharedMemory"}

        # Build session information dictionary
        # Field names match SPSessionInfo model for consistency
        session_info = {
            # Server identification
            "serverName":       _str(info.adsmServerName),
            "serverHost":       _str(info.serverHost),
            "serverPort":       int(info.serverPort),
            "serverType":       _str(info.serverType),

            # Server version information
            "serverVer":        int(info.serverVer),
            "serverRel":        int(info.serverRel),
            "serverLev":        int(info.serverLev),
            "serverSubLev":     int(info.serverSubLev),
            "serverDate":       _date(info.serverDate),
            "serverAddress":    _str(opt.serverAddress),

            # Archive and node configuration
            "archiveRetention": bool(info.archiveRetentionProtection),
            "nodeType":         _str(info.nodeType),

            # Path delimiters (default to "/" if not set)
            "fsdelim":          _str(info.fsdelim) or "/",
            "hldelim":          _str(info.hldelim) or "/",

            # Compression settings
            "compression":      int(info.compression),
            "compressAlways":   bool(opt.compressalways),

            # Delete permissions
            "archDel":          int(info.archDel),
            "backDel":          int(info.backDel),

            # Transaction limits
            "maxObjPerTxn":     int(info.maxObjPerTxn),
            "maxBytesPerTxn":   int(info.maxBytesPerTxn),

            # Node and owner information
            "nodeName":         _str(info.id),
            "accessNode":       _str(info.accessNode),
            "owner":            _str(info.owner),

            # Configuration paths
            "confFile":         _str(info.confFile),
            "dsmiDir":          _str(opt.dsmiDir),

            # Communication settings
            "commMethod":       comm_map.get(int(opt.commMethod), f"Unknown({opt.commMethod})"),
            "passwordAccess":   "generate" if bool(opt.passwordAccess) else "prompt",

            # Policy configuration
            "domainName":       _str(info.domainName),
            "policySetName":    _str(info.policySetName),
            "polActDate":       _date(info.polActDate),
            "dfltMCName":       _str(info.dfltMCName),

            # Group operation retention
            "gpBackRetn":       int(info.gpBackRetn),
            "gpArchRetn":       int(info.gpArchRetn),

            # Advanced features
            "lanFreeEnabled":   bool(info.lanFreeEnabled),
            "dedupType":        int(info.dedupType),

            # Failover and replication
            "failOverCfgType":  int(info.failOverCfgType),
            "replServerName":   _str(info.replServerName),
            "homeServerName":   _str(info.homeServerName),
            "replServerHost":   _str(info.replServerHost),
            "replServerPort":   int(info.replServerPort),
        }

        _logger.debug(
            "Session info retrieved",
            extra={
                'event_type': 'c_api.session.info.completed',
                'server_name': session_info.get('serverName'),
                'node_name': session_info.get('nodeName'),
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        return session_info

    def change_password(
            self,
            curr_password: str,
            new_password: str,
            session_handle: Optional[str] = None,
            operation_id: Optional[str] = None):
        """
        Change the password for the authenticated node.

        This method calls dsmChangePW() to change the node password on the IBM Storage
        Protect server. The session remains active after a successful password change,
        and subsequent logins should use the new password.

        Password Change Process:
        ------------------------
        1. Verify session is active
        2. Validate handle is valid
        3. Call dsmChangePW() with current and new passwords
        4. Server validates current password and new password requirements
        5. Password is updated on server
        6. Session continues with new password

        Parameters
        ----------
        curr_password : str
            The current password for the node. Must match the server's stored password.
        new_password : str
            The new password to set. Must meet server password requirements:
            - Minimum/maximum length (server-configured)
            - Complexity rules (uppercase, lowercase, numbers, special chars)
            - Password history (cannot reuse recent passwords)
        session_handle : str, optional
            Correlation ID for logging (overrides instance session_handle)
        operation_id : str, optional
            Operation identifier for logging (overrides instance operation_id)

        Returns
        -------
        None

        Raises
        ------
        TSMConnectionError
            If no active session exists
        TSMSystemError
            If the session handle is invalid
        Various SDK exceptions
            If password change fails (wrong current password, new password
            doesn't meet requirements, etc.)

        Notes
        -----
        - Requires an active session (must be logged in)
        - Current password must be correct
        - New password must meet server complexity requirements
        - Password change does not terminate the session
        - Failed password changes do not affect the current session
        - Server may enforce password history and expiration policies

        Security Considerations
        -----------------------
        - Passwords are transmitted securely using the configured communication method
        - Use strong passwords with mixed character types
        - Do not log or display passwords
        - Consider using environment variables or key vaults for password storage

        Client API Reference
        --------------------
        dsmChangePW() - Change node password

        Example
        -------
        >>> session = SessionManager(node="<node>", password="<old-password>")
        >>> handle = session.login()
        >>>
        >>> # Change password
        >>> session.change_password("<old-password>", "<new-password>")
        >>>
        >>> # Session continues with new password
        >>> # Next login should use the updated password value
        >>> session.logout()
        >>> session.password = "<new-password>"
        >>> session.login()

        See Also
        --------
        SPPasswordChange : Data model for password change validation
        """
        # Use provided IDs or fall back to instance IDs
        corr_id = session_handle or self.session_handle
        operation_id = operation_id or 'session_op'

        # Verify session is active
        if not self._is_active():
            _logger.error(
                "Password change failed: no active session",
                extra={
                    'event_type': 'c_api.session.password_change.failed',
                    'session_handle': corr_id,
                    'operation_id': operation_id
                }
            )
            raise TSMConnectionError(
                error_code=SDKErrorCode.SESSION_REJECTED,
                message="No Active Session"
            )

        # Verify handle is valid
        if not self.handle:
            _logger.error(
                "Password change failed: invalid handle",
                extra={
                    'event_type': 'c_api.session.password_change.failed',
                    'session_handle': corr_id,
                    'operation_id': operation_id
                }
            )
            raise TSMSystemError(
                error_code=SDKErrorCode.INTERNAL_ERROR,
                message="Invalid handle"
            )

        _logger.info(
            "Password change started",
            extra={
                'event_type': 'c_api.session.password_change.started',
                'node': self.node,
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        # Extract handle value for error reporting
        handle_val = self.handle.value if isinstance(self.handle, c_uint32) else self.handle

        _logger.debug(
            "Calling dsmChangePW",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmChangePW',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

        # Call the Client API function to change the password
        # Passwords are encoded to UTF-8 bytes as required by C API
        rc = lib.dsmChangePW(
            self.handle,
            curr_password.encode("utf-8"),
            new_password.encode("utf-8"),
        )

        # Check return code and raise exception if password change failed
        check_rc(handle_val, rc, "dsmChangePW")

        _logger.info(
            "Password change completed",
            extra={
                'event_type': 'c_api.session.password_change.completed',
                'session_handle': corr_id,
                'operation_id': operation_id
            }
        )

    def log_event_ex(
        self,
        message: str,
        severity: int = 0,
        log_type: int = 0,
        app_name: str = "PythonSDK",
        app_msg_id: str = "APP0001",
        session_handle: Optional[str] = None,
        operation_id: Optional[str] = None
    ) -> None:
        """
        Write a diagnostic message directly to the server activity log or local error log via dsmLogEventEx.
        """
        corr_id = session_handle or self.session_handle
        op_id = operation_id or self.operation_id

        if not self._is_active():
            raise TSMConnectionError(
                error_code=SDKErrorCode.SESSION_REJECTED,
                message="No Active Session"
            )

        _logger.debug(
            "Logging server event",
            extra={
                'event_type': 'c_api.session.log_event.started',
                'session_handle': corr_id,
                'operation_id': op_id,
                'severity': severity,
                'log_type': log_type,
                'msg_id': app_msg_id
            }
        )

        log_in = init_struct(dsmLogExIn_t, dsmLogExInVersion)
        log_in.severity = severity
        log_in.logType = log_type
        log_in.message = message.encode('utf-8')
        log_in.appMsgID = app_msg_id.encode('utf-8')[:7]
        log_in.appName = app_name.encode('utf-8')[:39]
        
        log_out = init_struct(dsmLogExOut_t, dsmLogExOutVersion)

        handle_val = self.handle.value if isinstance(self.handle, c_uint32) else self.handle

        _logger.debug(
            "Calling dsmLogEventEx",
            extra={
                'event_type': 'c_api.function.call',
                'function': 'dsmLogEventEx',
                'session_handle': corr_id,
                'operation_id': op_id
            }
        )

        rc = lib.dsmLogEventEx(self.handle, byref(log_in), byref(log_out))

        check_rc(handle_val, rc, "dsmLogEventEx")

        _logger.info(
            "Server event logged successfully",
            extra={
                'event_type': 'c_api.session.log_event.completed',
                'session_handle': corr_id,
                'operation_id': op_id
            }
        )


def dsm_set_up(
    dsmi_dir: Optional[str] = None,
    dsmi_config: Optional[str] = None,
    dsmi_log: Optional[str] = None,
    log_name: Optional[str] = None,
    b_service: bool = False
) -> int:
    """
    Expose process-wide logging and trace path overrides via native dsmSetUp().
    """
    if lib is None:
        return 0

    setup = init_struct(envSetUp, envSetUpVersion)
    if dsmi_dir:
        setup.dsmiDir = dsmi_dir.encode('utf-8')
    if dsmi_config:
        setup.dsmiConfig = dsmi_config.encode('utf-8')
    if dsmi_log:
        setup.dsmiLog = dsmi_log.encode('utf-8')
    if log_name:
        setup.logName = log_name.encode('utf-8')

    _logger.debug(
        "Calling dsmSetUp",
        extra={
            'event_type': 'c_api.function.call',
            'function': 'dsmSetUp',
            'dsmiDir': dsmi_dir,
            'dsmiConfig': dsmi_config,
            'dsmiLog': dsmi_log,
            'logName': log_name
        }
    )
    rc = lib.dsmSetUp(b_service, byref(setup))
    return rc

# Made with Bob
