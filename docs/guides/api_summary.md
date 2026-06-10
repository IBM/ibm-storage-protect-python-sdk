# IBM Storage Protect SDK - API Summary

## Quick Reference Table

This document provides a quick reference for all public API models in the IBM Storage Protect Python SDK.

---

## Session Management Models

**Source**: [`session.py`](../../src/ibm_storage_protect/data_models/session.py)

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `LoginCredentials` | Input | Authentication credentials | node, password, owner, platform |
| `SessionDetails` | Output | Active session information | handle, node, server_name, server_host |
| `SessionInfo` | Output | Detailed session configuration | server_name, server_host, server_port, compression |
| `PasswordChange` | Input | Password change request | current_password, new_password, verify_password |
| `SessionState` | Output | Session state tracking | handle, is_connected, error_count, last_error |

---

## Client Classes

**Source**: [`session.py`](../../src/ibm_storage_protect/session.py), [`data_client/client.py`](../../src/ibm_storage_protect/data_client/client.py), [`query.py`](../../src/ibm_storage_protect/query.py), [`control.py`](../../src/ibm_storage_protect/control.py)

| Client | Purpose | Key Methods |
|--------|---------|-------------|
| `ClientSession` | Session management and authentication | `login()`, `logout()`, `get_info()`, `change_password()` |
| `DataClient` | Unified backup/restore operations | `backup()`, `restore()`, `batch_backup()`, `batch_restore()` |
| `QueryClient` | Query operations | `query_backup()`, `list_objects()`, `query_group()`, `list_filespaces()` |
| `ControlClient` | Administrative operations | `register_filespace()`, `delete_by_name()`, `rename()`, `update()` |
| `GroupBackupClient` | Group backup operations | `create_group()`, `load_group()`, `get_group()` |
| `GroupRestoreClient` | Group restore operations | `restore_group()` |

---

## Control Management Models

**Source**: [`filespace.py`](../../src/ibm_storage_protect/data_models/filespace.py), [`object.py`](../../src/ibm_storage_protect/data_models/object.py)

### Filespace Management

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `FilespaceRegisterRequest` | Input | Register new filespace | filespace, fs_type, fs_info, occupancy, capacity |
| `FilespaceUpdateRequest` | Input | Update filespace metadata | filespace, fs_type, fs_info, occupancy, capacity |
| `FilespaceDeleteRequest` | Input | Delete filespace | filespace |
| `FilespaceMetadata` | Output | Filespace information | filespace, fs_type, capacity, occupancy |

### Object Management

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `ObjectDeleteRequest` | Input | Delete object by name | filespace, key, copy_group, obj_type |
| `ObjectDeleteByIdRequest` | Input | Delete object by ID | obj_id_hi, obj_id_lo |
| `ObjectRenameRequest` | Input | Rename object | filespace, key, new_key, merge, obj_type |
| `ObjectUpdateRequest` | Input | Update object metadata | filespace, key, owner, management_class, obj_type |

---

## Backup Operation Models

**Source**: [`backup.py`](../../src/ibm_storage_protect/data_models/backup.py)

### Single Object Operations

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `BackupRequest` | Input | Single object backup specification | key, body, filespace, obj_type, obj_state |
| `BackupResult` | Output | Single backup result | status, filespace, obj_id_hi, obj_id_lo, stats |
| `BackupStats` | Output | Detailed backup statistics | total_bytes_sent, compressed_bytes, deduplication_savings |

### Batch Operations

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `BatchBackupRequest` | Input | Multiple objects backup | objects, filespace, max_per_txn |
| `BatchBackupResult` | Output | Batch backup result | status, results, total_objects, successful, failed |

### Group Operations

**Recommended API**: Use [`GroupBackupClient`](../../src/ibm_storage_protect/data_client/backup/group.py) methods which return a `GroupHandle` object.

**GroupHandle Methods**:
- `add_leader(backup: BackupRequest)` - Add explicit leader
- `add_member(backup: BackupRequest)` - Add member (first becomes leader if no explicit leader)
- `close()` - Finalize group
- `reopen()` - Reopen for modifications
- `remove_members(keys: List[str])` - Remove members by key
- `delete()` - Delete entire group

**Low-Level Models** (for advanced use):

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `GroupBackupRequest` | Internal | ⚠️ Internal use only - use `GroupHandle` instead | group_tag, leader, members |
| `GroupBackupResult` | Output | Group backup result | status, group_tag, group_leader_obj_id, total_objects |
| `BeginGroupBackupRequest` | Input | Begin new group session | group_tag, filespace |
| `ReopenGroupBackupRequest` | Input | Reopen existing group | group_tag, group_leader_obj_id_hi, group_leader_obj_id_lo |
| `GroupRemoveMembersRequest` | Input | Remove members from group | group_tag, group_leader_obj_id_hi, group_leader_obj_id_lo, member_obj_ids |
| `GroupAssignMembersRequest` | Input | Assign members to group | group_tag, group_leader_obj_id_hi, group_leader_obj_id_lo, member_obj_ids |
| `GroupDeleteRequest` | Input | Delete entire group | group_tag, group_leader_obj_id_hi, group_leader_obj_id_lo |
| `LeaderBackupResult` | Output | Leader object details | key, stats, metadata |
| `MemberBackupResult` | Output | Member object details | key, stats |
| `RemoveMembersResult` | Output | Remove operation result | status, removed_count, removed_keys |
| `AssignMembersResult` | Output | Assign operation result | status, assigned_count, assigned_keys |
| `DeleteGroupResult` | Output | Delete operation result | status, group_tag, leader_key |

---

## Query Operation Models

**Source**: [`query.py`](../../src/ibm_storage_protect/data_models/query.py)

### Backup Queries

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `BackupQueryRequest` | Input | Query specific backup objects | filespace, key, obj_state, obj_type |
| `BackupQueryResult` | Output | Backup query result | objects, total_objects |

### List Operations

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `ListObjectsRequest` | Input | List objects with prefix | prefix, filespace, max_keys |
| `ListObjectsResult` | Output | List operation result | name, prefix, contents, key_count |

### Group Queries

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `GroupQueryRequest` | Input | Query group members | filespace, group_leader_obj_id_hi, group_leader_obj_id_lo |
| `GroupQueryResult` | Output | Group query result | objects, total_objects |

### Filespace Queries

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `ListFilespacesRequest` | Input | Query available filespaces | fs_pattern |
| `ListFilespacesResult` | Output | Filespace query result | filespaces, total_filespaces |

### Object Queries

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `ObjectMetadata` | Output | Complete object metadata | key, size, obj_id_hi, obj_id_lo, is_group_leader, is_open_group |

### Management Class Queries

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `ListManagementClassesRequest` | Input | Query management classes | mc_name, detail |
| `ListManagementClassesResult` | Output | Management class result | management_classes, total_classes |
| `ManagementClassMetadata` | Output | Management class details | name, description, retention_days |

---

## Restore Operation Models

**Source**: [`restore.py`](../../src/ibm_storage_protect/data_models/restore.py)

### Single Object Restore

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `RestoreRequest` | Input | Single object restore specification | key, filespace, obj_state, obj_type, obj_id_hi, obj_id_lo |
| `RestoreResult` | Output | Single restore result | status, key, body, stats |

### Batch Restore

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `BatchRestoreRequest` | Input | Multiple objects restore | objects, filespace |
| `BatchRestoreResult` | Output | Batch restore result | status, results, total_objects, successful, failed |

### Group Restore

| Model | Type | Purpose | Key Fields |
|-------|------|---------|------------|
| `GroupRestoreRequest` | Input | Restore entire group | filespace, group_leader_obj_id_hi, group_leader_obj_id_lo |
| `GroupRestoreResult` | Output | Group restore result | status, group_tag, members, total_objects |

---

## Enumerations

**Source**: [`enums.py`](../../src/ibm_storage_protect/enums.py)

| Enumeration | Values | Purpose |
|-------------|--------|---------|
| `ObjType` | FILE (1), DIRECTORY (2), ANY (255) | Specify object type |
| `ObjState` | ACTIVE (1), INACTIVE (2), ANY (255) | Specify object state |
| `Media` | FIXED (0xC6), REMOVABLE (0xD9), ANY (0) | Specify media type |
| `Repository` | PRIMARY (0), COPY (1), ACTIVE_DATA (2), ANY (255) | Specify repository type |
| `MountWait` | WAIT (True), NO_WAIT (False) | Control tape mount waiting |

---

## Model Categories

### By Usage Pattern

**Input Models** (User provides data):
- `LoginCredentials`, `BackupRequest`, `BatchBackupRequest`
- `BackupQueryRequest`, `ListObjectsRequest`, `GroupQueryRequest`
- `RestoreRequest`, `BatchRestoreRequest`, `GroupRestoreRequest`
- `FilespaceRegisterRequest`, `FilespaceUpdateRequest`, `FilespaceDeleteRequest`
- `ObjectDeleteRequest`, `ObjectDeleteByIdRequest`, `ObjectRenameRequest`, `ObjectUpdateRequest`
- `BeginGroupBackupRequest`, `ReopenGroupBackupRequest` (low-level)
- `GroupRemoveMembersRequest`, `GroupAssignMembersRequest`, `GroupDeleteRequest` (low-level)

**Note**: For group operations, use [`GroupBackupClient.create_group()`](../../src/ibm_storage_protect/data_client/backup/group.py:168) which returns a `GroupHandle` object instead of directly using `GroupBackupRequest`.

**Output Models** (SDK returns data):
- `SessionDetails`, `SessionInfo`, `BackupResult`, `BatchBackupResult`
- `GroupBackupResult`, `BackupQueryResult`, `ListObjectsResult`
- `RestoreResult`, `BatchRestoreResult`, `GroupRestoreResult`
- `FilespaceMetadata`, `ObjectMetadata`, `ManagementClassMetadata`
- `BackupStats`, `SessionState`

---

## Field Naming Conventions

All models support both PascalCase and snake_case field names through aliases:

```python
# Both work identically
backup = BackupRequest(Key="/path", Body=data, Filespace="/fs")
backup = BackupRequest(key="/path", body=data, filespace="/fs")
```

---

## Common Field Types

| Field Type | Description | Example |
|------------|-------------|---------|
| `str` | String value | `"my-node"`, `"/data/file.txt"` |
| `int` | Integer value | `1500`, `8251150` |
| `bool` | Boolean value | `True`, `False` |
| `bytes` | Binary data | `b"file content"` |
| `datetime` | Timestamp | `datetime.now()` |
| `List[T]` | List of type T | `[obj1, obj2]` |
| `Dict[str, Any]` | Dictionary | `{"hi": 0, "lo": 123}` |
| `Generator` | Data generator | `(chunk for chunk in data)` |
| `BufferedIOBase` | File-like object | `open("file.txt", "rb")` |

---

## Required vs Optional Fields

### Notation
- **Required**: Must be provided, no default value
- **Optional**: Has default value or can be None

### Common Defaults
- `filespace`: `"/"` (root filespace)
- `obj_state`: `ObjState.ACTIVE` (active objects)
- `obj_type`: `ObjType.FILE` (file objects)
- `max_keys`: `1000` (list operations)
- `mount_wait`: `MountWait.WAIT` (wait for tape)

---

## Validation Constraints

### Common Constraints
- **Port numbers**: 1-65535
- **Object IDs**: >= 0
- **Counts**: >= 0
- **Keys**: Cannot be empty
- **Filespace**: Cannot be empty
- **List fields**: Minimum 1 item where applicable
- **Body size**: Maximum 4MB per chunk (4,194,304 bytes)

---

## Model Relationships

```
Session Management
├── LoginCredentials → SessionDetails
└── SessionDetails → SessionInfo

Control Management
├── Filespace Operations
│   ├── FilespaceRegisterRequest → FilespaceMetadata
│   ├── FilespaceUpdateRequest → FilespaceMetadata
│   └── FilespaceDeleteRequest → (status)
└── Object Operations
    ├── ObjectDeleteRequest → (status)
    ├── ObjectDeleteByIdRequest → (status)
    ├── ObjectRenameRequest → (status)
    └── ObjectUpdateRequest → (status)

Backup Operations
├── BackupRequest → BackupResult
├── BatchBackupRequest → BatchBackupResult
└── GroupBackupRequest → GroupBackupResult

Query Operations
├── BackupQueryRequest → BackupQueryResult
├── ListObjectsRequest → ListObjectsResult
├── GroupQueryRequest → GroupQueryResult
└── ListFilespacesRequest → ListFilespacesResult

Restore Operations
├── RestoreRequest → RestoreResult
├── BatchRestoreRequest → BatchRestoreResult
└── GroupRestoreRequest → GroupRestoreResult
```

---

## Usage Frequency

### Most Common Models
1. `LoginCredentials` - Required for all operations
2. `BackupRequest` - Primary backup operation
3. `BackupResult` - Primary backup response
4. `ListObjectsRequest` - Common query operation
5. `GroupHandle` - Group operations (via `GroupBackupClient`)

### Specialized Models
- `FilespaceRegisterRequest`, `FilespaceUpdateRequest`, `FilespaceDeleteRequest` - Filespace management
- `ObjectDeleteRequest`, `ObjectRenameRequest`, `ObjectUpdateRequest` - Object management
- `GroupRemoveMembersRequest` - Advanced group management
- `GroupAssignMembersRequest` - Advanced group management
- `ListManagementClassesRequest` - Administrative queries
- `PasswordChange` - Security operations

---

## Quick Start Examples

### Basic Backup
```python
from ibm_storage_protect.data_models.backup import BackupRequest

backup = BackupRequest(key="/data/file.txt", body=b"content")
result = client.backup(backup)
```

### Group Backup
```python
from ibm_storage_protect.data_client.backup.group import GroupBackupClient
from ibm_storage_protect.data_models.backup import BackupRequest

# Create and manage group using GroupHandle
group_client = GroupBackupClient(session)
group = group_client.create_group("my-group")
group.add_member(BackupRequest(key="/data/file1.txt", body=b"content1"))
group.add_member(BackupRequest(key="/data/file2.txt", body=b"content2"))
group.close()

# Load and modify existing group
group = group_client.load_group(".sp_groups.json", "my-group")
group.reopen()
group.add_member(BackupRequest(key="/data/file3.txt", body=b"content3"))
group.close()
```

### Query Objects
```python
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.data_models.query import ListObjectsRequest

query_client = QueryClient(session)
list_req = ListObjectsRequest(filespace="/", prefix="/data")
result = query_client.list_objects(list_req)
```

### Restore Object
```python
from ibm_storage_protect.data_models.restore import RestoreRequest

restore = RestoreRequest(key="/data/file.txt", filespace="/")
result = client.restore(restore)
```

### Control Management
```python
from ibm_storage_protect.control import ControlClient
from ibm_storage_protect.data_models.filespace import FilespaceRegisterRequest
from ibm_storage_protect.data_models.object import ObjectDeleteRequest

control_client = ControlClient(session)

# Register filespace
fs_reg = FilespaceRegisterRequest(filespace="/myfs")
result = control_client.register_filespace(fs_reg)

# Delete object
obj_del = ObjectDeleteRequest(filespace="/myfs", key="/data/file.txt")
result = control_client.delete_by_name(obj_del)
```

### Session Management
```python
from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_models.session import LoginCredentials

# Create session and login
session = ClientSession()
credentials = LoginCredentials(
    node=os.getenv("SP_NODE"),
    password=os.getenv("SP_PASSWORD"),
    owner=os.getenv("SP_OWNER", ""),
    platform="Linux"
)
session_details = session.login(credentials)

# Get session info
session_info = session.get_info()

# Logout
session.logout()
```

---

## Import Paths

### Data Models
```python
from ibm_storage_protect.data_models.session import LoginCredentials, SessionDetails, SessionInfo
from ibm_storage_protect.data_models.backup import BackupRequest, BackupResult, BatchBackupRequest
from ibm_storage_protect.data_models.restore import RestoreRequest, RestoreResult, GroupRestoreRequest
from ibm_storage_protect.data_models.query import ListObjectsRequest, BackupQueryRequest, ObjectMetadata
from ibm_storage_protect.data_models.filespace import FilespaceRegisterRequest, FilespaceMetadata
from ibm_storage_protect.data_models.object import ObjectDeleteRequest, ObjectRenameRequest
```

### Client Classes
```python
from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.control import ControlClient
from ibm_storage_protect.data_client.backup.group import GroupBackupClient
from ibm_storage_protect.data_client.restore.group import GroupRestoreClient
```

### Enumerations
```python
from ibm_storage_protect.enums import ObjType, ObjState, Media, Repository, MountWait
```

### Logger
```python
from ibm_storage_protect.logger import configure_logging, get_logger, LogConfig
```

---

**Last Updated**: 2026-05-29
**SDK Version**: 0.1.0