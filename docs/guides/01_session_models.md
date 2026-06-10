# Session Management Models - Data Design

## Overview

Session management models handle authentication, connection lifecycle, and session state management with the IBM Storage Protect server. These models are defined in [`data_models/session.py`](../../src/ibm_storage_protect/data_models/session.py) and used by [`ClientSession`](../../src/ibm_storage_protect/session.py).

---

## Input Models

### LoginCredentials

**Purpose**: Authentication credentials for establishing a session with IBM Storage Protect server.

**Usage**: Input to [`ClientSession.login()`](../../src/ibm_storage_protect/session.py:237)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `node` | `str` | Optional | `None` | `Node` | - | Client node name registered with server |
| `password` | `str` | Optional | `None` | `Password` | - | Node password (store securely) |
| `owner` | `str` | Optional | `None` | `Owner` | - | Owner name for multi-owner configurations |

**Example**:
```python
from ibm_storage_protect.data_models.session import LoginCredentials

# Basic authentication
credentials = LoginCredentials(
    node=os.getenv("SP_NODE"),
    password=os.getenv("SP_PASSWORD"),
    owner=os.getenv("SP_OWNER", "admin")
)

# Using PascalCase aliases (API style)
credentials = LoginCredentials(
    Node=os.getenv("SP_NODE"),
    Password=os.getenv("SP_PASSWORD"),
    Owner=os.getenv("SP_OWNER", "admin")
)
```

**Validation Rules**:
- All fields are optional (can use defaults from configuration)
- Empty strings are treated as None
- Model is immutable (frozen=True) for security

**Security Note**: Passwords are masked in `__repr__()` output for security.

---

### PasswordChange

**Purpose**: Password change request validation for IBM Storage Protect sessions.

**Usage**: Input to [`ClientSession.change_password()`](../../src/ibm_storage_protect/session.py:745)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `current_password` | `str` | Required | - | `CurrentPassword` | min_length=1 | Current node password |
| `new_password` | `str` | Required | - | `NewPassword` | min_length=1, must differ from current | New node password |

**Example**:
```python
from ibm_storage_protect.data_models.session import PasswordChange

password_change = PasswordChange(
    current_password="<current-password>",
    new_password="<new-password>"
)

session.change_password(password_change)
```

**Validation Rules**:
- Both fields are required
- Minimum length of 1 character
- New password must be different from current password
- Model is immutable (frozen=True) for security
- Server-side validation includes complexity rules, history, and expiration policy

---

## Output Models

### SessionDetails

**Purpose**: Represents an active session with the Storage Protect server.

**Usage**: Returned by [`ClientSession.login()`](../../src/ibm_storage_protect/session.py:237)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `handle` | `int` | Required | - | `Handle` | >= 0 | Session handle from dsmInitEx() |
| `node` | `str` | Optional | `None` | `Node` | - | Authenticated client node name |
| `server_name` | `str` | Optional | `None` | `ServerName` | - | IBM Storage Protect server name |
| `is_active` | `bool` | Optional | `True` | `IsActive` | - | Session active status (client-side flag) |
| `connected_at` | `datetime` | Optional | `datetime.now()` | `ConnectedAt` | - | Session establishment timestamp (ISO 8601) |

**Example Output**:
```python
{
    "handle": 12345,
    "node": "MY_NODE",
    "server_name": "SP_SERVER",
    "is_active": True,
    "connected_at": "2024-05-05T10:00:00Z"
}
```

**Usage**:
```python
from ibm_storage_protect import ClientSession
from ibm_storage_protect.data_models.session import LoginCredentials

session = ClientSession()
session_details = session.login(credentials)

print(f"Session handle: {session_details.handle}")
print(f"Connected to: {session_details.server_name}")
print(f"Active: {session_details.is_active}")
```

**Notes**:
- The handle is the most critical field - all API operations require it
- Session handles are not reusable after termination
- Multiple sessions can exist simultaneously (different handles)
- Sessions should be properly terminated with `logout()` to free resources

---

### SessionInfo

**Purpose**: Comprehensive session configuration and server information.

**Usage**: Returned by [`ClientSession.get_info()`](../../src/ibm_storage_protect/session.py:583)

**Fields**:

| Field | Type | Required | Alias | Constraints | Description |
|-------|------|----------|-------|-------------|-------------|
| `server_name` | `str` | Required | `serverName` | - | IBM Storage Protect server logical name |
| `server_host` | `str` | Required | `serverHost` | - | Server hostname or IP address |
| `server_port` | `int` | Required | `serverPort` | 1-65535 | Server TCP port number (typically 1500) |
| `server_type` | `str` | Required | `serverType` | - | Server platform type (AIX, Linux, Windows, etc.) |
| `server_version` | `int` | Required | `serverVer` | - | Server major version number |
| `server_release` | `int` | Required | `serverRel` | - | Server release number |
| `server_level` | `int` | Required | `serverLev` | - | Server maintenance level number |
| `server_sublevel` | `int` | Required | `serverSubLev` | - | Server fix pack sublevel number |
| `server_date` | `str` | Optional | `serverDate` | - | Server build date (may be None) |
| `server_address` | `str` | Required | `serverAddress` | - | Full server address with protocol |
| `archive_retention` | `bool` | Required | `archiveRetention` | - | Archive retention protection enabled |
| `node_type` | `str` | Required | `nodeType` | - | Client node type (Client, NAS, Server, etc.) |
| `fs_delimiter` | `str` | Required | `fsdelim` | - | Filespace name delimiter character (/ or \\) |
| `hl_delimiter` | `str` | Required | `hldelim` | - | High-level (directory) name delimiter (/ or \\) |
| `compression` | `int` | Required | - | >= 0 | Compression setting (0=None, 1=Client, 2=Server) |
| `compress_always` | `bool` | Required | `compressAlways` | - | Always attempt compression regardless of file type |
| `archive_delete` | `int` | Required | `archDel` | - | Archive delete permission level |
| `backup_delete` | `int` | Required | `backDel` | - | Backup delete permission level |
| `max_obj_per_txn` | `int` | Required | `maxObjPerTxn` | >= 0 | Maximum objects per transaction (0=unlimited) |
| `max_bytes_per_txn` | `int` | Required | `maxBytesPerTxn` | >= 0 | Maximum bytes per transaction (0=unlimited) |
| `node_name` | `str` | Required | `nodeName` | - | Authenticated client node name |
| `access_node` | `str` | Required | `accessNode` | - | Access node for proxy operations |
| `owner` | `str` | Required | - | - | Owner name (empty if not multi-owner) |
| `conf_file` | `str` | Required | `confFile` | - | Client configuration file path (dsm.opt/dsm.sys) |
| `dsmi_dir` | `str` | Required | `dsmiDir` | - | DSMI directory path for client state files |
| `comm_method` | `str` | Required | `commMethod` | - | Communication method (TCPip, SharedMem, NAMEDPIPE) |
| `password_access` | `str` | Required | `passwordAccess` | - | Password access mode (prompt, generate, file) |
| `domain_name` | `str` | Required | `domainName` | - | Policy domain name assigned to this node |
| `policy_set_name` | `str` | Required | `policySetName` | - | Active policy set name within the domain |
| `pol_act_date` | `str` | Optional | `polActDate` | - | Policy activation date |
| `dflt_mc_name` | `str` | Required | `dfltMCName` | - | Default management class name |
| `gp_back_retn` | `int` | Required | `gpBackRetn` | >= 0 | Group backup retention period in days |
| `gp_arch_retn` | `int` | Required | `gpArchRetn` | >= 0 | Group archive retention period in days |
| `lan_free_enabled` | `bool` | Required | `lanFreeEnabled` | - | LAN-free data transfer enabled (direct SAN access) |
| `dedup_type` | `int` | Required | `dedupType` | - | Deduplication type (0=None, 1=Client, 2=Server, 3=Both) |
| `failover_cfg_type` | `int` | Required | `failOverCfgType` | - | Failover configuration type |
| `repl_server_name` | `str` | Required | `replServerName` | - | Replication server name (empty if not configured) |
| `home_server_name` | `str` | Required | `homeServerName` | - | Home (primary) server name |
| `repl_server_host` | `str` | Required | `replServerHost` | - | Replication server hostname or IP |
| `repl_server_port` | `int` | Required | `replServerPort` | 0-65535 | Replication server TCP port number |

**Example Output**:
```python
{
    "server_name": "SP_SERVER",
    "server_host": "sp.example.com",
    "server_port": 1500,
    "server_version": 8,
    "server_release": 1,
    "server_level": 12,
    "node_name": "MY_NODE",
    "owner": "admin",
    "compression": 1,
    "max_obj_per_txn": 1000,
    "max_bytes_per_txn": 10485760,
    "domain_name": "STANDARD",
    "policy_set_name": "ACTIVE",
    "dflt_mc_name": "STANDARD"
}
```

**Usage**:
```python
session_info = session.get_info()

print(f"Server: {session_info.server_name} ({session_info.server_host}:{session_info.server_port})")
print(f"Version: {session_info.server_version}.{session_info.server_release}.{session_info.server_level}")
print(f"Compression: {'Enabled' if session_info.compression else 'Disabled'}")
print(f"Max objects per transaction: {session_info.max_obj_per_txn}")
```

---

### SessionState

**Purpose**: Runtime session state tracking for monitoring and health checks.

**Usage**: Internal tracking of session state

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `handle` | `int` | Required | - | `Handle` | - | Session handle reference |
| `is_connected` | `bool` | Required | - | `IsConnected` | - | Current connection status |
| `last_activity` | `datetime` | Optional | `datetime.now()` | `LastActivity` | - | Timestamp of last successful operation (ISO 8601) |
| `error_count` | `int` | Optional | `0` | `ErrorCount` | >= 0 | Cumulative error count for health monitoring |

**Example Output**:
```python
{
    "handle": 12345,
    "is_connected": True,
    "last_activity": "2024-05-05T10:30:00Z",
    "error_count": 0
}
```

**Use Cases**:
- Monitor session health and connectivity
- Detect idle sessions for timeout enforcement
- Track error patterns for automatic retry logic
- Implement session pooling and lifecycle management

---

## Complete Workflow Example

```python
from ibm_storage_protect import ClientSession, initialize_environment
from ibm_storage_protect.data_models.session import LoginCredentials, PasswordChange

# 1. Initialize environment (optional - sets up paths)
initialize_environment(
    dsmi_dir="/opt/tivoli/tsm/client/api/bin64",
    dsmi_config="/opt/tivoli/tsm/client/api/bin64/dsm.opt"
)

# 2. Create session object
session = ClientSession()

# 3. Login with credentials
credentials = LoginCredentials(
    node=os.getenv("SP_NODE"),
    password=os.getenv("SP_PASSWORD"),
    owner=os.getenv("SP_OWNER", "admin")
)

session_details = session.login(credentials)
print(f"Connected to {session_details.server_name}")
print(f"Session handle: {session_details.handle}")

# 4. Get detailed session information
detailed_info = session.get_info()
print(f"Server version: {detailed_info.server_version}.{detailed_info.server_release}")
print(f"Max objects per transaction: {detailed_info.max_obj_per_txn}")
print(f"Compression: {detailed_info.compression}")

# 5. Change password (optional)
password_change = PasswordChange(
    current_password="<current-password>",
    new_password="<new-password>"
)
session.change_password(password_change)
print("Password changed successfully")

# 6. Perform operations...
# (backup, restore, query operations)

# 7. Logout
session.logout()
print("Session closed")
```

---

## Context Manager Support

```python
from ibm_storage_protect import ClientSession
from ibm_storage_protect.data_models.session import LoginCredentials

# Automatic session cleanup with context manager
credentials = LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD"))

with ClientSession() as session:
    session.login(credentials)
    # Perform operations
    # Session automatically logged out on exit
```

---

## Best Practices

### 1. Secure Credential Handling
```python
import os
from ibm_storage_protect.data_models.session import LoginCredentials

# Use environment variables
credentials = LoginCredentials(
    node=os.getenv("SP_NODE"),
    password=os.getenv("SP_PASSWORD"),
    owner=os.getenv("SP_OWNER")
)
```

### 2. Session Lifecycle Management
```python
# Use try-finally for cleanup
session = ClientSession()
try:
    session.login(credentials)
    # Perform operations
finally:
    if session.is_active():
        session.logout()
```

### 3. Error Handling
```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    session.login(credentials)
except TSMError as e:
    print(f"Login failed: {e}")
    # Handle error appropriately
```

### 4. Session Information Caching
```python
# Cache session info to avoid repeated queries
session_info = session.get_info()
max_objects = session_info.max_obj_per_txn
max_bytes = session_info.max_bytes_per_txn

# Use cached values for batch operations
```

---

## Validation Rules

### LoginCredentials
- All fields are optional
- Empty strings are converted to None
- Model is immutable (frozen=True)

### PasswordChange
- Both fields are required
- Minimum length: 1 character
- New password must differ from current password
- Model is immutable (frozen=True)

### SessionDetails
- Handle must be non-negative integer
- connected_at defaults to current time if not provided

### SessionInfo
- Port numbers must be in range 1-65535
- All count fields must be non-negative
- Supports both PascalCase and snake_case field names

---

## Error Scenarios

### Login Failures
```python
# Invalid credentials
try:
    session.login(LoginCredentials(node="<invalid-node>", password="<invalid-password>"))
except TSMError as e:
    print(f"Authentication failed: {e}")

# Network issues
try:
    session.login(credentials)
except ConnectionError as e:
    print(f"Cannot connect to server: {e}")
```

### Password Change Failures
```python
# Same password
try:
    session.change_password(PasswordChange(
        current_password="<same-password>",
        new_password="<same-password>"  # Same as current
    ))
except ValueError as e:
    print(f"Validation error: {e}")

# Wrong current password
try:
    session.change_password(password_change)
except TSMError as e:
    print(f"Password change failed: {e}")
```

---

## API Reference

### ClientSession Class

Defined in [`session.py`](../../src/ibm_storage_protect/session.py:120)

**Methods**:
- [`login(credentials: LoginCredentials) -> SessionDetails`](../../src/ibm_storage_protect/session.py:237)
- [`logout() -> None`](../../src/ibm_storage_protect/session.py:435)
- [`get_info() -> SessionInfo`](../../src/ibm_storage_protect/session.py:583)
- [`change_password(password_change: PasswordChange) -> None`](../../src/ibm_storage_protect/session.py:745)
- [`is_active() -> bool`](../../src/ibm_storage_protect/session.py:938)
- [`log_server_event(message, severity, log_type, app_name, app_msg_id) -> None`](../../src/ibm_storage_protect/session.py:1194)

**Properties**:
- [`handle -> int`](../../src/ibm_storage_protect/session.py:994)
- [`node -> str`](../../src/ibm_storage_protect/session.py:1035)

### initialize_environment Function

Defined in [`session.py`](../../src/ibm_storage_protect/session.py:1278)

**Purpose**: Initialize IBM Storage Protect client environment variables.

**Parameters**:
- `dsmi_dir`: DSMI directory path
- `dsmi_config`: Configuration file path
- `dsmi_log`: Log directory path
- `log_name`: Log file name
- `b_service`: Service name

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0