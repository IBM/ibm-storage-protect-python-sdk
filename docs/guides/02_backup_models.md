# Backup Operation Models - Data Design

## Overview

Backup operation models handle single object, batch, and group backup operations. These models provide flexible data protection capabilities defined in [`data_models/backup.py`](../../src/ibm_storage_protect/data_models/backup.py) and used by [`DataClient`](../../src/ibm_storage_protect/data_client/client.py).

---

## Single Object Backup

### BackupRequest (Input)

**Purpose**: Single object backup specification.

**Usage**: Input to [`DataClient.backup()`](../../src/ibm_storage_protect/data_client/client.py:200)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `key` | `str` | Required | - | `Key` | Cannot be empty | Object key path |
| `body` | `bytes` \| `BufferedIOBase` \| `Generator` | Required | - | `Body` | **≤ 4MB chunks** | Object data source (must yield ≤4MB chunks) |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace name |
| `management_class` | `str` | Optional | `None` | `ManagementClass` | - | Management class name |
| `obj_type` | `ObjectType` | Optional | `ObjectType.FILE` | `ObjType` | - | Object type (FILE/DIRECTORY) |
| `owner` | `str` | Optional | `None` | `Owner` | - | Object owner |
| `size_estimate` | `int` | Optional | `0` | `SizeEstimate` | >= 0 | Estimated size in bytes for buffer allocation |
| `pre_compressed` | `bool` | Optional | `False` | `PreCompressed` | - | Data is pre-compressed |
| `mount_wait` | `MountWaitEnum` | Optional | `WAIT` | `MountWait` | - | Wait for tape mount |
| `obj_info` | `str` \| `bytes` | Optional | `None` | `ObjInfo` | - | Additional object information (max 1024 bytes extended, 255 standard) |
| `disable_dedup` | `bool` | Optional | `False` | `DisableDedup` | - | Disable deduplication |

**CRITICAL CONSTRAINTS**:
- ⚠️ **Chunk Size Limit**: All data chunks MUST be ≤ 4MB (4,194,304 bytes)
- ⚠️ **Memory Efficiency**: Use generators for large files to avoid loading entire file into RAM

**Example**:
```python
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.enums import ObjectType
import os

# Simple backup with small bytes (< 4MB)
backup = BackupRequest(
    Key="/data/myfile.txt",
    Body=b"file content here",
    Filespace="/myfs",
    SizeEstimate=len(b"file content here"),
    ManagementClass="STANDARD"
)

# CORRECT: Backup large file with chunked generator (100GB file)
def chunked_file_reader(filepath, chunk_size=4 * 1024 * 1024):  # 4MB chunks
    """Read file in 4MB chunks to avoid RAM overload"""
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

file_path = "/path/to/large_file.dat"  # 100GB file
file_size = os.path.getsize(file_path)

backup = BackupRequest(
    Key="/data/large_file.dat",
    Body=chunked_file_reader(file_path),
    Filespace="/myfs",
    SizeEstimate=file_size
)

result = client.backup(backup)

# WRONG: Don't load entire large file into memory
# with open("/path/to/100gb_file.dat", "rb") as f:
#     backup = BackupRequest(Key="/data/file.dat", Body=f.read())  # ❌ RAM overflow!
```

---

### BackupResult (Output)

**Purpose**: Result of a single backup operation.

**Usage**: Returned by [`DataClient.backup()`](../../src/ibm_storage_protect/data_client/client.py:200)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status ("success" or "failed") |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `high_level` | `str` | Required | `HighLevel` | High-level path component |
| `low_level` | `str` | Required | `LowLevel` | Low-level path component |
| `stats` | `dict` | Optional | `Stats` | Backup statistics |

**Example Output**:
```python
{
    "status": "success",
    "filespace": "/myfs",
    "high_level": "/data",
    "low_level": "file.txt",
    "stats": {
        "total_bytes_sent": 1024,
        "compressed": True,
        "compressed_size": 512,
        "deduplicated": False,
        "dedup_size": 0
    }
}
```

**Usage**:
```python
result = client.backup(backup)
print(f"Status: {result.status}")
print(f"Path: {result.filespace}{result.high_level}/{result.low_level}")
if result.stats:
    print(f"Bytes sent: {result.stats['total_bytes_sent']}")
    print(f"Compressed: {result.stats['compressed']}")
```

---

### BackupStats (Output)

**Purpose**: Detailed backup statistics.

**Usage**: Part of backup result

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `total_bytes_sent` | `int` | Required | - | `TotalBytesSent` | >= 0 | Total bytes sent |
| `compressed` | `bool` | Required | - | `Compressed` | - | Object was compressed |
| `compressed_size` | `int` | Optional | `0` | `CompressedSize` | >= 0 | Compressed size |
| `deduplicated` | `bool` | Required | - | `Deduplicated` | - | Object was deduplicated |
| `dedup_size` | `int` | Optional | `0` | `DedupSize` | >= 0 | Deduplicated size |
| `group_leader_obj_id` | `str` | Optional | `None` | `GroupLeaderObjId` | - | Group leader object ID |

---

## Batch Backup

### BatchBackupRequest (Input)

**Purpose**: Multiple objects backup in batch.

**Usage**: Input to [`DataClient.batch_backup()`](../../src/ibm_storage_protect/data_client/client.py:232)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `objects` | `List[BackupRequest]` | Required | - | `Objects` | min_items=1 | List of objects to backup |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | - | Filespace for all objects |
| `max_per_txn` | `int` | Optional | `1` | `MaxPerTxn` | >= 1 | Max objects per transaction |

**Example**:
```python
from ibm_storage_protect.data_models.backup import BatchBackupRequest, BackupRequest

batch = BatchBackupRequest(
    objects=[
        BackupRequest(Key="/data/file1.txt", Body=b"content1",SizeEstimate=file_size),
        BackupRequest(Key="/data/file2.txt", Body=b"content2",SizeEstimate=file_size),
        BackupRequest(Key="/data/file3.txt", Body=b"content3",SizeEstimate=file_size)
    ],
    Filespace="/myfs",
    MaxPerTxn=10
)

result = client.batch_backup(batch)
```

**Validation Rules**:
- `objects` list cannot be empty
- All objects in the list must be valid BackupRequest instances

---

### BatchBackupResult (Output)

**Purpose**: Result of batch backup operation.

**Usage**: Returned by [`DataClient.batch_backup()`](../../src/ibm_storage_protect/data_client/client.py:232)

**Fields**:

| Field | Type | Required | Alias | Constraints | Description |
|-------|------|----------|-------|-------------|-------------|
| `status` | `str` | Required | `Status` | - | Overall status ("success", "partial", or "failed") |
| `results` | `List[dict]` | Required | `Results` | - | Individual object results |
| `total_objects` | `int` | Required | `TotalObjects` | >= 0 | Total objects processed |
| `successful` | `int` | Required | `Successful` | >= 0 | Successful backups |
| `failed` | `int` | Required | `Failed` | >= 0 | Failed backups |

**Example Output**:
```python
{
    "status": "success",
    "results": [
        {"Key": "/data/file1.txt", "status": "success", "bytes_sent": 1024},
        {"Key": "/data/file2.txt", "status": "success", "bytes_sent": 2048},
        {"Key": "/data/file3.txt", "status": "failed", "error": "Permission denied"}
    ],
    "total_objects": 3,
    "successful": 2,
    "failed": 1
}
```

---

## Group Backup Operations

Group backups allow multiple related objects to be backed up together as a logical unit with a leader and members. See [06_group_operations.md](06_group_operations.md) for complete documentation.

**IMPORTANT**: When using `BackupRequest` for group operations, the `SizeEstimate` parameter is **REQUIRED** for proper buffer allocation and optimal performance. Unlike single backups where it's optional, group backups need accurate size estimates to efficiently manage multiple objects.

### GroupBackupRequest (Input)

**Purpose**: Group backup specification with leader and members.

**Usage**: Internal - Users should use [`DataClient.create_group()`](../../src/ibm_storage_protect/data_client/client.py:261) instead

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `group_tag` | `str` | Required | - | `GroupTag` | Unique group identifier |
| `leader` | `BackupRequest` | Required | - | `Leader` | Group leader object (required, **must include SizeEstimate**) |
| `members` | `List[BackupRequest]` | Optional | `None` | `Members` | Group member objects (optional, **must include SizeEstimate**) |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Filespace for group |

**Recommended Alternative**:
```python
import os
from ibm_storage_protect.data_models.backup import BackupRequest

# Instead of using GroupBackupRequest directly, use:
group = client.create_group("my-group", filespace="/myfs")

# IMPORTANT: Always provide SizeEstimate for group backups
leader_size = os.path.getsize("/path/to/leader.txt")
group.add_leader(BackupRequest(
    Key="/data/leader.txt",
    Body=open("/path/to/leader.txt", "rb"),
    SizeEstimate=leader_size  # REQUIRED for group operations
))

member_size = os.path.getsize("/path/to/member1.txt")
group.add_member(BackupRequest(
    Key="/data/member1.txt",
    Body=open("/path/to/member1.txt", "rb"),
    SizeEstimate=member_size  # REQUIRED for group operations
))

group.close()
```

---

### GroupBackupResult (Output)

**Purpose**: Result of group backup operation.

**Usage**: Returned by group backup operations

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `group_tag` | `str` | Required | `GroupTag` | Group tag |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `group_leader_obj_id` | `str` | Required | `GroupLeaderObjId` | Group leader object ID (formatted as hi-lo) |
| `group_leader_obj_id_raw` | `dict` | Required | `GroupLeaderObjIdRaw` | Raw group leader object ID with hi/lo parts |
| `leader` | `LeaderResponse` | Required | `Leader` | Leader object details |
| `members` | `List[MemberResponse]` | Required | `Members` | Member objects |
| `total_objects` | `int` | Required | `TotalObjects` | Total objects in group (>= 1) |
| `duration_ms` | `float` | Required | `DurationMs` | Operation duration in milliseconds |

---

### LeaderResponse (Output)

**Purpose**: Result details for the leader object of a group backup.

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `key` | `str` | Required | `Key` | Leader object key |
| `stats` | `dict` | Required | - | Backup statistics |
| `metadata` | `dict` | Optional | - | Additional metadata |

---

### MemberResponse (Output)

**Purpose**: Result details for a non-leader member object in a group backup.

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `key` | `str` | Required | `Key` | Member object key |
| `stats` | `dict` | Required | - | Backup statistics |

---

## Group Management Operations

### BeginGroupBackupRequest (Input)

**Purpose**: Begin a new group backup operation.

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `group_tag` | `str` | Required | - | `GroupTag` | Unique group identifier |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Filespace for group |

---

### ReopenGroupBackupRequest (Input)

**Purpose**: Reopen an existing group to add more members.

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `group_tag` | `str` | Required | - | `GroupTag` | Group identifier to reopen |
| `group_leader_obj_id_hi` | `int` | Required | - | `GroupLeaderObjIdHi` | High part of group leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | `GroupLeaderObjIdLo` | Low part of group leader object ID (>= 0) |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Filespace for group |

---

### GroupRemoveMembersRequest (Input)

**Purpose**: Remove members from a backup group.

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `group_tag` | `str` | Required | - | `GroupTag` | Group identifier |
| `group_leader_obj_id_hi` | `int` | Required | - | `GroupLeaderObjIdHi` | High part of leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | `GroupLeaderObjIdLo` | Low part of leader object ID (>= 0) |
| `member_obj_ids` | `List[dict]` | Required | - | `MemberObjIds` | List of member object IDs to remove (min_items=1) |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Filespace for group |

---

### GroupAssignToMembersRequest (Input)

**Purpose**: Assign members to a backup group.

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `group_tag` | `str` | Required | - | `GroupTag` | Group identifier |
| `group_leader_obj_id_hi` | `int` | Required | - | `GroupLeaderObjIdHi` | High part of target group leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | `GroupLeaderObjIdLo` | Low part of target group leader object ID (>= 0) |
| `member_obj_ids` | `List[dict]` | Required | - | `MemberObjIds` | List of member object IDs to assign (min_items=1) |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Filespace for group |

---

### GroupDeleteRequest (Input)

**Purpose**: Delete a backup group.

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `group_tag` | `str` | Required | - | `GroupTag` | Group identifier to delete |
| `group_leader_obj_id_hi` | `int` | Required | - | `GroupLeaderObjIdHi` | High part of leader object ID (>= 0) |
| `group_leader_obj_id_lo` | `int` | Required | - | `GroupLeaderObjIdLo` | Low part of leader object ID (>= 0) |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Filespace for group |

---

## Object Specification

### ObjectReference (Input)

**Purpose**: Generic object specification for operations.

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `key` | `str` | Required | - | `Key` | Cannot be empty | Object key path |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace name |
| `obj_state` | `ObjStateEnum` | Optional | `ACTIVE` | `ObjState` | - | Object state |
| `obj_type` | `ObjectType` | Optional | `FILE` | `ObjType` | - | Object type |

**Example**:
```python
from ibm_storage_protect.data_models.backup import ObjectReference
from ibm_storage_protect.enums import ObjState, ObjType

obj = ObjectReference(
    Key="/data/file.txt",
    Filespace="/myfs",
    ObjState=ObjState.ACTIVE,
    ObjType=ObjType.FILE
)
```

---

## Complete Workflow Examples

### Single File Backup
```python
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest

# Setup
session = ClientSession()
session.login(LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD")))
client = DataClient(session)

# Backup
backup = BackupRequest(
    Key="/documents/report.pdf",
    Body=open("/local/path/report.pdf", "rb"),
    Filespace="/documents",
    ManagementClass="STANDARD",
    SizeEstimate=1024000
)

result = client.backup(backup)
print(f"Backup {result.status}: {result.filespace}{result.high_level}/{result.low_level}")

# Cleanup
session.logout()
```

### Batch Backup
```python
import os
from ibm_storage_protect.data_models.backup import BatchBackupRequest, BackupRequest

# Prepare batch
files_to_backup = []
for filename in os.listdir("/local/data"):
    filepath = os.path.join("/local/data", filename)
    if os.path.isfile(filepath):
        files_to_backup.append(
            BackupRequest(
                Key=f"/backup/data/{filename}",
                Body=open(filepath, "rb"),
                SizeEstimate=os.path.getsize(filepath)
            )
        )

# Execute batch backup
batch = BatchBackupRequest(
    objects=files_to_backup,
    Filespace="/backup",
    MaxPerTxn=50
)

result = client.batch_backup(batch)
print(f"Batch complete: {result.successful}/{result.total_objects} successful")
```

### Streaming Backup
```python
def generate_log_data():
    """Generate log data in chunks"""
    with open("/var/log/application.log", "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            yield chunk

backup = BackupRequest(
    Key="/logs/application.log",
    Body=generate_log_data(),
    Filespace="/logs",
    SizeEstimate=10485760  # 10MB estimate
)

result = client.backup(backup)
```

---

## Best Practices

### 1. Size Estimation
```python
import os

# Provide accurate size estimates for better performance
file_size = os.path.getsize("/path/to/file")
backup = BackupRequest(
    Key="/data/file.txt",
    Body=open("/path/to/file", "rb"),
    SizeEstimate=file_size
)
```

### 2. Batch Operations
```python
# Group related files in batches
batch = BatchBackupRequest(
    objects=[...],  # Related files
    MaxPerTxn=100  # Optimize transaction size
)
```

### 3. Error Handling
```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    result = client.backup(backup)
    if result.status != "success":
        print(f"Backup warning: {result.status}")
except TSMError as e:
    print(f"Backup failed: {e}")
    # Handle error
```

### 4. Resource Management
```python
# Use context managers for file handles
with open("/path/to/file", "rb") as f:
    backup = BackupRequest(Key="/data/file.txt", Body=f)
    result = client.backup(backup)
# File automatically closed
```

---

## Performance Considerations

### Compression
```python
# Pre-compressed data
backup = BackupRequest(
    Key="/data/archive.gz",
    Body=compressed_data,
    PreCompressed=True  # Skip server compression
)
```

### Deduplication
```python
# Disable dedup for unique data
backup = BackupRequest(
    Key="/data/unique.bin",
    Body=data,
    DisableDedup=True  # Skip dedup processing
)
```

### Batch Size
```python
# Optimize batch size based on object sizes
small_files_batch = BatchBackupRequest(
    objects=[...],  # Many small files
    MaxPerTxn=1000  # Higher transaction limit
)

large_files_batch = BatchBackupRequest(
    objects=[...],  # Few large files
    MaxPerTxn=10  # Lower transaction limit
)
```

---

## Validation Rules

### BackupRequest
- `key` cannot be empty
- `body` must be bytes, file-like object, or generator
- `filespace` cannot be empty (defaults to "/")
- `size_estimate` must be non-negative
- `obj_type` must be valid ObjectType enum value

### BatchBackupRequest
- `objects` list must contain at least 1 item
- All objects must be valid BackupRequest instances
- `max_per_txn` must be >= 1

### ObjectReference
- `key` cannot be empty or whitespace-only
- `filespace` cannot be empty or whitespace-only

---

## Error Scenarios

### Invalid Input
```python
# Empty key
try:
    backup = BackupRequest(Key="", Body=b"data")
except ValueError as e:
    print(f"Validation error: {e}")

# Empty batch
try:
    batch = BatchBackupRequest(objects=[])
except ValueError as e:
    print(f"Validation error: {e}")
```

### Backup Failures
```python
# File not found
try:
    backup = BackupRequest(
        Key="/data/file.txt",
        Body=open("/nonexistent/file.txt", "rb")
    )
except FileNotFoundError as e:
    print(f"File error: {e}")

# Server error
try:
    result = client.backup(backup)
except TSMError as e:
    print(f"Backup error: {e}")
```

---

## Internal Models (Not for Direct Use)

The following internal models are used by the SDK implementation and should not be used directly:

- `BackupInternal`: Internal backup model for C API layer
- `BatchBackupInternal`: Internal batch backup model
- `GroupBackupInternal`: Internal group backup model

These models handle low-level C API parameter mapping and are automatically created by the SDK.

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0