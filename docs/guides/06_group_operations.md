# Group Backup Operations - Data Design

## Overview

Group backup operations allow multiple related objects to be backed up as a cohesive unit with a leader-member relationship. This is essential for maintaining consistency across related data files, such as database backups where metadata and data files must be kept together.

Group operations are implemented in [`data_client/backup/group.py`](../../src/ibm_storage_protect/data_client/backup/group.py) and [`data_client/restore/group.py`](../../src/ibm_storage_protect/data_client/restore/group.py).

**CRITICAL REQUIREMENT**: All `BackupRequest` objects used in group operations **MUST** include the `SizeEstimate` parameter. This is essential for proper buffer allocation and optimal performance when backing up multiple related objects.

---

## Core Concepts

### Group Structure
- **Leader**: The primary object that represents the group (typically metadata or manifest)
- **Members**: Related objects that belong to the group (data files, logs, etc.)
- **Group Tag**: Unique identifier for the group
- **Group Leader Object ID**: Server-assigned identifier (hi/lo pair) for the leader

### Group Lifecycle
1. **Create**: Initialize a new group
2. **Add Members**: Add objects to the group
3. **Close**: Finalize the group
4. **Reopen**: Modify an existing group
5. **Query**: Retrieve group contents
6. **Delete**: Remove the entire group

---

## High-Level API (Recommended)

### GroupHandle Object

The SDK provides a high-level [`GroupHandle`](../../src/ibm_storage_protect/data_client/backup/group.py:168) object that simplifies group management.

#### Creating a New Group

**Method 1: Simple Creation with Auto-Leader**
```python
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
import os

# Setup
session = ClientSession()
session.login(LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD")))
client = DataClient(session)

# First member automatically becomes the leader
# IMPORTANT: Always include SizeEstimate for group operations
group = client.create_group("example-group-a")
group.add_member(BackupRequest(
    Key="/groupA/file1.txt",
    Body=b"Group A File 1",
    SizeEstimate=len(b"Group A File 1")  # REQUIRED
))
group.add_member(BackupRequest(
    Key="/groupA/file2.txt",
    Body=b"Group A File 2",
    SizeEstimate=len(b"Group A File 2")  # REQUIRED
))
group.add_member(BackupRequest(
    Key="/groupA/file3.txt",
    Body=b"Group A File 3",
    SizeEstimate=len(b"Group A File 3")  # REQUIRED
))
group.close()

print(f"Group created: {group.name}")
print(f"Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")
```

**Method 2: Explicit Leader Assignment**
```python
group = client.create_group("example-group-b")
group.add_leader(BackupRequest(
    Key="/groupB/leader.txt",
    Body=b"Group B Leader",
    SizeEstimate=len(b"Group B Leader")  # REQUIRED
))
group.add_member(BackupRequest(
    Key="/groupB/member1.txt",
    Body=b"Group B Member 1",
    SizeEstimate=len(b"Group B Member 1")  # REQUIRED
))
group.add_member(BackupRequest(
    Key="/groupB/member2.txt",
    Body=b"Group B Member 2",
    SizeEstimate=len(b"Group B Member 2")  # REQUIRED
))
group.close()
```

**Method 3: Bulk Member Creation**
```python
group = client.create_group(
    "example-group-c",
    members=[
        BackupRequest(Key="/groupC/file1.txt", Body=b"Group C File 1", SizeEstimate=15),
        BackupRequest(Key="/groupC/file2.txt", Body=b"Group C File 2", SizeEstimate=15),
        BackupRequest(Key="/groupC/file3.txt", Body=b"Group C File 3", SizeEstimate=15),
    ]
)
# Group is automatically closed after bulk creation
```

**Method 4: Context Manager (Auto-Close)**
```python
with client.create_group("example-group-d") as group:
    group.add_member(BackupRequest(
        Key="/groupD/file1.txt",
        Body=b"Group D File 1",
        SizeEstimate=15  # REQUIRED
    ))
    group.add_member(BackupRequest(
        Key="/groupD/file2.txt",
        Body=b"Group D File 2",
        SizeEstimate=15  # REQUIRED
    ))
    # Automatically closed when exiting context
```

#### Reopening an Existing Group

**From Metadata File**
```python
# Load group from persisted metadata
group = client.load_group(".sp_groups.json", "example-group-a")
print(f"Loaded group: {group.name}")
print(f"Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")

# Reopen and add more members
group.reopen()
group.add_member(BackupRequest(
    Key="/groupA/file4.txt",
    Body=b"Group A File 4",
    SizeEstimate=15  # REQUIRED
))
group.add_member(BackupRequest(
    Key="/groupA/file5.txt",
    Body=b"Group A File 5",
    SizeEstimate=15  # REQUIRED
))
group.close()
```

**Using Known Leader ID**
```python
# Get group handle using leader ID (cross-session work)
leader_id = {'hi': 0, 'lo': 8251150}
group = client.get_group("example-group-d", leader_id=leader_id, filespace="/")

# Reopen and modify
group.reopen()
group.add_member(BackupRequest(
    Key="/groupD/file3.txt",
    Body=b"Group D File 3",
    SizeEstimate=15  # REQUIRED
))
group.close()
```

#### Removing Members

```python
# Load group
group = client.load_group(".sp_groups.json", "example-group-a")

# Remove members by key (not object ID)
result = group.remove_members(["/groupA/file2.txt", "/groupA/file4.txt"])
print(f"Remove result: {result.message}")
```

#### Deleting a Group

```python
# Load and delete entire group
group = client.load_group(".sp_groups.json", "example-group-a")
group.delete()
print("Group deleted")
```

#### Querying Group Contents

```python
from ibm_storage_protect import QueryClient
from ibm_storage_protect.data_models.query import GroupQueryRequest

query_client = QueryClient(session)

# Query using leader object ID
group_query = GroupQueryRequest(
    Filespace="/",
    GroupLeaderObjIdHi=group.leader_id['hi'],
    GroupLeaderObjIdLo=group.leader_id['lo']
)

result = query_client.query_group(group_query)
print(f"Total objects: {result.total_count}")

for obj in result.objects:
    role = "LEADER" if obj.is_group_leader else "MEMBER"
    print(f"[{role}] {obj.key} (ID: {obj.obj_id_hi}-{obj.obj_id_lo})")
```

#### Saving Group Metadata

The [`GroupHandle`](../../src/ibm_storage_protect/data_client/backup/group.py:168) automatically persists metadata to `.sp_groups.json` when leaders are added. You can also manually save to a custom location:

```python
# Automatic save (default behavior)
group = client.create_group("my-group")
group.add_member(BackupRequest(
    Key="/data/file.txt",
    Body=b"content",
    SizeEstimate=7  # REQUIRED
))
# Metadata automatically saved to .sp_groups.json

# Manual save to custom location
group.save("custom_groups.json")
```

---

## Group Restore Operations

### GroupRestoreRequest (Input)

**Purpose**: Restore all members of a group backup.

**Usage**: Input to [`DataClient.group_restore()`](../../src/ibm_storage_protect/data_client/client.py:334)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `group_leader_obj_id_hi` | `int` | Required | - | `GroupLeaderObjIdHi` | >= 0 | High part of group leader object ID |
| `group_leader_obj_id_lo` | `int` | Required | - | `GroupLeaderObjIdLo` | >= 0 | Low part of group leader object ID |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace for group |
| `owner` | `str` | Optional | `None` | `Owner` | - | Object owner |
| `obj_type` | `ObjType` | Optional | `FILE` | `ObjType` | - | Object type |
| `mount_wait` | `MountWaitEnum` | Optional | `WAIT` | `MountWait` | - | Wait for tape mount |

**Example**:
```python
from ibm_storage_protect.data_models.restore import GroupRestoreRequest

# Restore entire group
restore = GroupRestoreRequest(
    GroupLeaderObjIdHi=12345,
    GroupLeaderObjIdLo=67890,
    Filespace="/myfs"
)

result = client.group_restore(restore)

# Process leader
if result.leader:
    print(f"Leader: {result.leader['key']}")
    with open(f"/local/{result.leader['key']}", "wb") as f:
        for chunk in result.leader['body']:
            f.write(chunk)

# Process members
for member in result.members:
    print(f"Member: {member['key']}")
    with open(f"/local/{member['key']}", "wb") as f:
        for chunk in member['body']:
            f.write(chunk)
```

---

## Internal API Models

**⚠️ IMPORTANT**: The models and methods in this section are **INTERNAL** to the SDK and should **NOT** be used directly by end users. They are documented here for SDK developers and contributors only.

**Users should ONLY use:**
- [`client.create_group()`](../../src/ibm_storage_protect/data_client/backup/group.py:594) - Create new groups
- [`client.load_group()`](../../src/ibm_storage_protect/data_client/backup/group.py:631) - Load existing groups
- [`client.get_group()`](../../src/ibm_storage_protect/data_client/backup/group.py:685) - Get group by leader ID
- [`GroupHandle`](../../src/ibm_storage_protect/data_client/backup/group.py:168) methods (`.add_member()`, `.close()`, `.reopen()`, `.delete()`, `.save()`)

### Internal Input Models

#### BeginGroupBackupRequest (Internal)

**Purpose**: Internal model to begin a new group backup session. **Do not use directly** - use [`client.create_group()`](../../src/ibm_storage_protect/data_client/backup/group.py:594) instead.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `group_tag` | `str` | Required | - | Unique group identifier |
| `filespace` | `str` | Optional | `"/"` | Filespace for group |

---

#### ReopenGroupBackupRequest (Internal)

**Purpose**: Internal model to reopen an existing group backup. **Do not use directly** - use [`GroupHandle.reopen()`](../../src/ibm_storage_protect/data_client/backup/group.py:348) instead.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `group_tag` | `str` | Required | - | Group identifier to reopen |
| `group_leader_obj_id_hi` | `int` | Required | - | High part of group leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | Low part of group leader object ID (>= 0) |
| `filespace` | `str` | Optional | `"/"` | Filespace for group |

---

#### GroupRemoveMembersRequest (Internal)

**Purpose**: Internal model to remove members from a group. **Do not use directly** - use [`GroupHandle.remove_members()`](../../src/ibm_storage_protect/data_client/backup/group.py:381) instead.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `group_tag` | `str` | Required | - | Group identifier |
| `group_leader_obj_id_hi` | `int` | Required | - | High part of leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | Low part of leader object ID (>= 0) |
| `member_obj_ids` | `List[dict]` | Required | - | List of member object IDs to remove (min: 1) |
| `filespace` | `str` | Optional | `"/"` | Filespace for group |

**Member Object ID Format**:
```python
{"hi": 0, "lo": 8251151}
```

---

#### GroupAssignToMembersRequest (Internal)

**Purpose**: Internal model to assign members to a group. **This API is for internal use only.**

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `group_tag` | `str` | Required | - | Group identifier |
| `group_leader_obj_id_hi` | `int` | Required | - | High part of target group leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | Low part of target group leader object ID (>= 0) |
| `member_obj_ids` | `List[dict]` | Required | - | List of member object IDs to assign (min: 1) |
| `filespace` | `str` | Optional | `"/"` | Filespace for group |

---

#### GroupDeleteRequest (Internal)

**Purpose**: Internal model to delete a group. **Do not use directly** - use [`GroupHandle.delete()`](../../src/ibm_storage_protect/data_client/backup/group.py:438) instead.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `group_tag` | `str` | Required | - | Group identifier to delete |
| `group_leader_obj_id_hi` | `int` | Required | - | High part of leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | Low part of leader object ID (>= 0) |
| `filespace` | `str` | Optional | `"/"` | Filespace for group |

---

## Complete Workflow Example

### Database Backup Scenario

```python
from ibm_storage_protect import ClientSession, DataClient, QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.data_models.query import GroupQueryRequest

# 1. Establish session
session = ClientSession()
credentials = LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD"))
session.login(credentials)

client = DataClient(session)
query_client = QueryClient(session)

# 2. Create database backup group
db_group = client.create_group("postgres-backup-2024-05-05")

# Add metadata as leader
db_group.add_leader(BackupRequest(
    Key="/db/backup/metadata.json",
    Body=b'{"database": "production", "timestamp": "2024-05-05T10:00:00Z"}'
))

# Add database files as members
db_group.add_member(BackupRequest(
    Key="/db/backup/data.sql",
    Body=open("/var/lib/postgresql/data.sql", "rb")
))

db_group.add_member(BackupRequest(
    Key="/db/backup/schema.sql",
    Body=open("/var/lib/postgresql/schema.sql", "rb")
))

db_group.add_member(BackupRequest(
    Key="/db/backup/indexes.sql",
    Body=open("/var/lib/postgresql/indexes.sql", "rb")
))

# Close the group
db_group.close()

print(f"Database backup group created: {db_group.name}")
print(f"Leader ID: {db_group.leader_id['hi']}-{db_group.leader_id['lo']}")

# 3. Later: Add transaction logs to existing group
db_group_reopen = client.load_group(".sp_groups.json", "postgres-backup-2024-05-05")
db_group_reopen.reopen()

db_group_reopen.add_member(BackupRequest(
    Key="/db/backup/transaction_log_001.log",
    Body=open("/var/lib/postgresql/pg_wal/000000010000000000000001", "rb")
))

db_group_reopen.close()

# 4. Verify group contents
query = GroupQueryRequest(
    Filespace="/",
    GroupLeaderObjIdHi=db_group.leader_id['hi'],
    GroupLeaderObjIdLo=db_group.leader_id['lo']
)

result = query_client.query_group(query)
print(f"\nBackup group contains {result.total_count} objects:")
for obj in result.objects:
    role = "LEADER" if obj.is_group_leader else "MEMBER"
    print(f"  [{role}] {obj.key} - {obj.size} bytes")

# 5. Cleanup
session.logout()
```

---

## GroupHandle API Reference

### Client Methods

#### [`create_group(name, filespace="/", members=None, metadata_file=".sp_groups.json")`](../../src/ibm_storage_protect/data_client/backup/group.py:594)
Create a new group backup operation.

**Parameters**:
- `name`: Unique group name
- `filespace`: Target filespace (default: "/")
- `members`: Optional list of BackupRequest objects
- `metadata_file`: Metadata file path (default: ".sp_groups.json")

**Returns**: GroupHandle

---

#### [`load_group(filepath, name, filespace="/")`](../../src/ibm_storage_protect/data_client/backup/group.py:631)
Load an existing group from metadata file.

**Parameters**:
- `filepath`: Path to JSON metadata file
- `name`: Group name to load
- `filespace`: Filespace override (default: "/")

**Returns**: GroupHandle

---

#### [`get_group(name, leader_id, filespace="/", metadata_file=".sp_groups.json")`](../../src/ibm_storage_protect/data_client/backup/group.py:685)
Get a group handle using known leader ID.

**Parameters**:
- `name`: Group name
- `leader_id`: Leader object ID dict with 'hi' and 'lo' keys
- `filespace`: Target filespace (default: "/")
- `metadata_file`: Metadata file path (default: ".sp_groups.json")

**Returns**: GroupHandle

---

### GroupHandle Instance Methods

#### [`add_leader(backup_item)`](../../src/ibm_storage_protect/data_client/backup/group.py:244)
Explicitly set the group leader.

**Parameters**: `backup_item` (BackupRequest)

**Returns**: dict with leader information

---

#### [`add_member(backup_item)`](../../src/ibm_storage_protect/data_client/backup/group.py:281)
Add a member to the group. First member becomes leader if no explicit leader set.

**Parameters**: `backup_item` (BackupRequest)

**Returns**: dict with member information

---

#### [`close()`](../../src/ibm_storage_protect/data_client/backup/group.py:319)
Close the group (required before reopening or querying).

**Returns**: dict with close result

---

#### [`reopen()`](../../src/ibm_storage_protect/data_client/backup/group.py:348)
Reopen a closed group for modifications.

**Returns**: GroupHandle (self)

---

#### [`remove_members(member_keys)`](../../src/ibm_storage_protect/data_client/backup/group.py:381)
Remove members by their keys (not object IDs).

**Parameters**: `member_keys` (list of strings)

**Returns**: GroupOperationResult

---

#### [`delete()`](../../src/ibm_storage_protect/data_client/backup/group.py:438)
Delete the entire group.

**Returns**: GroupOperationResult

---

#### [`save(filepath=None)`](../../src/ibm_storage_protect/data_client/backup/group.py:468)
Manually save group metadata to a file.

**Parameters**: `filepath` (optional string)

---

### GroupHandle Properties

#### [`name`](../../src/ibm_storage_protect/data_client/backup/group.py:483)
Get the group name.

#### [`leader_id`](../../src/ibm_storage_protect/data_client/backup/group.py:488)
Get the leader object ID (dict with 'hi' and 'lo' keys).

#### [`is_open`](../../src/ibm_storage_protect/data_client/backup/group.py:493)
Check if group is currently open.

#### [`is_closed`](../../src/ibm_storage_protect/data_client/backup/group.py:498)
Check if group is currently closed.

---

## Best Practices

### 1. Use Meaningful Group Tags
```python
# Good: Descriptive and timestamped
group = client.create_group("postgres-backup-2024-05-05-10-00")

# Bad: Generic or unclear
group = client.create_group("group1")
```

### 2. Always Close Groups
```python
# Preferred: Use context manager
with client.create_group("my-group") as group:
    group.add_member(backup)
    # Automatically closed

# Alternative: Explicit close
group = client.create_group("my-group")
try:
    group.add_member(backup)
finally:
    group.close()
```

### 3. Leverage Automatic Metadata Persistence
```python
# Groups are automatically saved to .sp_groups.json when leader is added
group = client.create_group("my-group")
group.add_member(BackupRequest(Key="/data/file.txt", Body=b"content"))
# Metadata automatically persisted

# Load later for modifications
group = client.load_group(".sp_groups.json", "my-group")

# Or save to custom location
group.save("custom_location.json")
```

### 4. Verify Operations with Queries
```python
# After modifications, verify the group state
result = query_client.query_group(group_query)
assert result.total_count == expected_count
```

### 5. Handle Errors Gracefully
```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    group.reopen()
    group.add_member(backup)
    group.close()
except TSMError as e:
    print(f"Group operation failed: {e}")
    # Handle error appropriately
```

---

## Validation Rules

### Group Tag
- Cannot be empty or whitespace-only
- Should be unique within the filespace
- Recommended format: `{purpose}-{timestamp}`

### Object IDs
- Must be non-negative integers
- High and low parts are both required
- Format: `{"hi": int, "lo": int}`

### Member Operations
- At least one member required for remove/assign operations
- Cannot remove the leader object
- Member keys must exist in the group

### Group State
- Cannot add members to a closed group without reopening
- Cannot close an already closed group
- Cannot reopen a deleted group

---

## Performance Considerations

### Batch Operations
- Add multiple members before closing to reduce server round-trips
- Use bulk creation when possible

### Query Optimization
- Query groups only when necessary
- Cache leader IDs for repeated operations
- Use specific object types in queries to reduce result set

### Resource Management
- Close groups promptly to release server resources
- Use context managers for automatic cleanup
- Logout sessions when done

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0