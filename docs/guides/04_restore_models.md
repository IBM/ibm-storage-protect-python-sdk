# Restore Operation Models - Data Design

## Overview

Restore operation models handle single object, batch, and group restore operations. These models provide flexible data recovery capabilities defined in [`data_models/restore.py`](../../src/ibm_storage_protect/data_models/restore.py) and used by [`DataClient`](../../src/ibm_storage_protect/data_client/client.py).

---

## Single Object Restore

### RestoreRequest (Input)

**Purpose**: Single object restore specification.

**Usage**: Input to [`DataClient.restore()`](../../src/ibm_storage_protect/data_client/client.py:270)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `key` | `str` | Required | - | `Key` | Cannot be empty | Object key path to restore |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace name |
| `obj_state` | `ObjStateEnum` | Optional | `ACTIVE` | `ObjState` | - | Object state (ACTIVE, INACTIVE, ANY) |
| `obj_type` | `ObjectType` | Optional | `FILE` | `ObjType` | - | Object type (FILE/DIRECTORY) |
| `pit_date` | `str` | Optional | `None` | `PitDate` | Format: "YYYY-MM-DD HH:MM:SS" | Point-in-time date for historical restore |
| `offset` | `int` | Optional | `0` | `Offset` | >= 0 | Byte offset to start restore from |
| `length` | `int` | Optional | `0` | `Length` | >= 0 | Number of bytes to restore (0 = all) |
| `mount_wait` | `MountWaitEnum` | Optional | `WAIT` | `MountWait` | - | Wait for tape mount |

**CRITICAL CONSTRAINTS**:
- ⚠️ **Chunk Size**: Restored data is delivered in chunks ≤ 4MB (4,194,304 bytes)
- ⚠️ **Memory Efficiency**: Use the generator pattern to process large restores without loading entire object into RAM

**Example**:
```python
from ibm_storage_protect.data_models.restore import RestoreRequest
from ibm_storage_protect.enums import ObjState, ObjType

# Simple restore (entire object)
restore = RestoreRequest(
    Key="/data/myfile.txt",
    Filespace="/myfs",
    ObjState=ObjState.ACTIVE
)

result = client.restore(restore)

# Write restored data to file
with open("/local/path/myfile.txt", "wb") as f:
    for chunk in result.body:
        f.write(chunk)

# Partial restore (specific byte range)
restore = RestoreRequest(
    Key="/data/largefile.bin",
    Filespace="/myfs",
    Offset=1048576,  # Start at 1MB
    Length=2097152   # Restore 2MB
)

result = client.restore(restore)

# Point-in-time restore
restore = RestoreRequest(
    Key="/data/document.pdf",
    Filespace="/myfs",
    PitDate="2026-01-15 10:30:00"  # Restore version from specific date
)

result = client.restore(restore)
```

---

### RestoreResult (Output)

**Purpose**: Result of a single restore operation.

**Usage**: Returned by [`DataClient.restore()`](../../src/ibm_storage_protect/data_client/client.py:270)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status ("success" or "failed") |
| `key` | `str` | Required | `Key` | Object key path |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `body` | `Generator[bytes, None, None]` | Required | `Body` | Data generator yielding chunks ≤ 4MB |
| `total_bytes` | `int` | Required | `TotalBytes` | Total bytes restored |
| `obj_id_hi` | `int` | Required | `ObjIdHi` | High part of object ID |
| `obj_id_lo` | `int` | Required | `ObjIdLo` | Low part of object ID |
| `backup_date` | `str` | Required | `BackupDate` | Backup timestamp of restored version |
| `stats` | `dict` | Optional | `Stats` | Restore statistics |

**Example Output**:
```python
{
    "status": "success",
    "key": "/data/myfile.txt",
    "filespace": "/myfs",
    "body": <generator object>,
    "total_bytes": 1048576,
    "obj_id_hi": 12345,
    "obj_id_lo": 67890,
    "backup_date": "2026-05-29 09:30:00",
    "stats": {
        "compressed": True,
        "decompressed_size": 2097152,
        "deduplicated": False
    }
}
```

**Usage**:
```python
result = client.restore(restore)
print(f"Status: {result.status}")
print(f"Restoring: {result.key}")
print(f"Total bytes: {result.total_bytes}")
print(f"Backup date: {result.backup_date}")

# Process data in chunks (memory efficient)
with open("/local/restored.txt", "wb") as f:
    for chunk in result.body:
        f.write(chunk)
        print(f"Received {len(chunk)} bytes")

# WRONG: Don't try to load all data at once
# data = b"".join(result.body)  # ❌ May cause RAM overflow for large files!
```

---

### RestoreStats (Output)

**Purpose**: Detailed restore statistics.

**Usage**: Part of restore result

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `total_bytes_received` | `int` | Required | - | `TotalBytesReceived` | >= 0 | Total bytes received |
| `compressed` | `bool` | Required | - | `Compressed` | - | Object was compressed |
| `decompressed_size` | `int` | Optional | `0` | `DecompressedSize` | >= 0 | Decompressed size |
| `deduplicated` | `bool` | Required | - | `Deduplicated` | - | Object was deduplicated |
| `encrypted` | `bool` | Required | - | `Encrypted` | - | Object was encrypted |

---

## Batch Restore

### BatchRestoreRequest (Input)

**Purpose**: Multiple objects restore in batch.

**Usage**: Input to [`DataClient.batch_restore()`](../../src/ibm_storage_protect/data_client/client.py:302)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `objects` | `List[RestoreRequest]` | Required | - | `Objects` | min_items=1 | List of objects to restore |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | - | Filespace for all objects |
| `max_per_txn` | `int` | Optional | `1` | `MaxPerTxn` | >= 1 | Max objects per transaction |

**Example**:
```python
from ibm_storage_protect.data_models.restore import BatchRestoreRequest, RestoreRequest

batch = BatchRestoreRequest(
    objects=[
        RestoreRequest(Key="/data/file1.txt"),
        RestoreRequest(Key="/data/file2.txt"),
        RestoreRequest(Key="/data/file3.txt")
    ],
    Filespace="/myfs",
    MaxPerTxn=10
)

result = client.batch_restore(batch)

# Process each restored object
for obj_result in result.results:
    print(f"Restoring: {obj_result['key']}")
    with open(f"/local/{obj_result['key']}", "wb") as f:
        for chunk in obj_result['body']:
            f.write(chunk)
```

**Validation Rules**:
- `objects` list cannot be empty
- All objects in the list must be valid RestoreRequest instances

---

### BatchRestoreResult (Output)

**Purpose**: Result of batch restore operation.

**Usage**: Returned by [`DataClient.batch_restore()`](../../src/ibm_storage_protect/data_client/client.py:302)

**Fields**:

| Field | Type | Required | Alias | Constraints | Description |
|-------|------|----------|-------|-------------|-------------|
| `status` | `str` | Required | `Status` | - | Overall status ("success", "partial", or "failed") |
| `results` | `List[dict]` | Required | `Results` | - | Individual object results |
| `total_objects` | `int` | Required | `TotalObjects` | >= 0 | Total objects processed |
| `successful` | `int` | Required | `Successful` | >= 0 | Successful restores |
| `failed` | `int` | Required | `Failed` | >= 0 | Failed restores |

**Example Output**:
```python
{
    "status": "success",
    "results": [
        {"key": "/data/file1.txt", "status": "success", "body": <generator>, "total_bytes": 1024},
        {"key": "/data/file2.txt", "status": "success", "body": <generator>, "total_bytes": 2048},
        {"key": "/data/file3.txt", "status": "failed", "error": "Object not found"}
    ],
    "total_objects": 3,
    "successful": 2,
    "failed": 1
}
```

---

## Group Restore Operations

Group restores allow multiple related objects to be restored together as a logical unit. See [06_group_operations.md](06_group_operations.md) for complete documentation.

### GroupRestoreRequest (Input)

**Purpose**: Group restore specification by leader object ID.

**Usage**: Input to [`DataClient.group_restore()`](../../src/ibm_storage_protect/data_client/client.py:334)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `group_leader_obj_id_hi` | `int` | Required | - | `GroupLeaderObjIdHi` | >= 0 | High part of group leader object ID |
| `group_leader_obj_id_lo` | `int` | Required | - | `GroupLeaderObjIdLo` | >= 0 | Low part of group leader object ID |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace for group |
| `include_leader` | `bool` | Optional | `True` | `IncludeLeader` | - | Include leader in restore |
| `pit_date` | `str` | Optional | `None` | `PitDate` | Format: "YYYY-MM-DD HH:MM:SS" | Point-in-time date for restore |

**Example**:
```python
from ibm_storage_protect.data_models.restore import GroupRestoreRequest

# Restore entire group
restore = GroupRestoreRequest(
    GroupLeaderObjIdHi=12345,
    GroupLeaderObjIdLo=67890,
    Filespace="/myfs",
    IncludeLeader=True
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

### GroupRestoreResult (Output)

**Purpose**: Result of group restore operation.

**Usage**: Returned by [`DataClient.group_restore()`](../../src/ibm_storage_protect/data_client/client.py:334)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `group_leader_obj_id` | `str` | Required | `GroupLeaderObjId` | Group leader object ID (formatted as hi-lo) |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `leader` | `dict` | Optional | `Leader` | Leader object restore result |
| `members` | `List[dict]` | Required | `Members` | Member objects restore results |
| `total_objects` | `int` | Required | `TotalObjects` | Total objects restored |
| `total_bytes` | `int` | Required | `TotalBytes` | Total bytes restored |
| `duration_ms` | `float` | Required | `DurationMs` | Operation duration in milliseconds |

---

## Object Specification

### RestoreObjectReference (Input)

**Purpose**: Generic object specification for restore operations.

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `key` | `str` | Required | - | `Key` | Cannot be empty | Object key path |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace name |
| `obj_state` | `ObjStateEnum` | Optional | `ACTIVE` | `ObjState` | - | Object state |
| `obj_type` | `ObjectType` | Optional | `FILE` | `ObjType` | - | Object type |
| `pit_date` | `str` | Optional | `None` | `PitDate` | Format: "YYYY-MM-DD HH:MM:SS" | Point-in-time date |

**Example**:
```python
from ibm_storage_protect.data_models.restore import RestoreObjectReference
from ibm_storage_protect.enums import ObjState, ObjType

obj = RestoreObjectReference(
    Key="/data/file.txt",
    Filespace="/myfs",
    ObjState=ObjState.ACTIVE,
    ObjType=ObjType.FILE,
    PitDate="2026-01-15 10:30:00"
)
```

---

## Complete Workflow Examples

### Single File Restore
```python
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.restore import RestoreRequest

# Setup
session = ClientSession()
session.login(LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD")))
client = DataClient(session)

# Restore
restore = RestoreRequest(
    Key="/documents/report.pdf",
    Filespace="/documents"
)

result = client.restore(restore)
print(f"Restore {result.status}: {result.key}")
print(f"Total bytes: {result.total_bytes}")
print(f"Backup date: {result.backup_date}")

# Save to file
with open("/local/restored_report.pdf", "wb") as f:
    for chunk in result.body:
        f.write(chunk)

# Cleanup
session.logout()
```

### Batch Restore
```python
from ibm_storage_protect.data_models.restore import BatchRestoreRequest, RestoreRequest
import os

# Prepare batch
files_to_restore = [
    RestoreRequest(Key="/backup/data/file1.txt"),
    RestoreRequest(Key="/backup/data/file2.txt"),
    RestoreRequest(Key="/backup/data/file3.txt")
]

# Execute batch restore
batch = BatchRestoreRequest(
    objects=files_to_restore,
    Filespace="/backup",
    MaxPerTxn=50
)

result = client.batch_restore(batch)
print(f"Batch complete: {result.successful}/{result.total_objects} successful")

# Save each restored file
for obj_result in result.results:
    if obj_result['status'] == 'success':
        filename = os.path.basename(obj_result['key'])
        with open(f"/local/restored/{filename}", "wb") as f:
            for chunk in obj_result['body']:
                f.write(chunk)
```

### Partial Restore (Byte Range)
```python
# Restore specific byte range from large file
restore = RestoreRequest(
    Key="/data/large_database.db",
    Filespace="/databases",
    Offset=10485760,   # Start at 10MB
    Length=104857600   # Restore 100MB
)

result = client.restore(restore)

# Process partial data
with open("/local/partial_restore.db", "wb") as f:
    for chunk in result.body:
        f.write(chunk)

print(f"Restored {result.total_bytes} bytes (offset {restore.offset})")
```

### Point-in-Time Restore
```python
# Restore version from specific date
restore = RestoreRequest(
    Key="/config/application.conf",
    Filespace="/config",
    PitDate="2026-01-01 00:00:00"  # New Year's version
)

result = client.restore(restore)
print(f"Restoring version from: {result.backup_date}")

with open("/local/application_jan1.conf", "wb") as f:
    for chunk in result.body:
        f.write(chunk)
```

### Streaming Restore
```python
def process_restored_data(data_generator):
    """Process restored data in streaming fashion"""
    total_processed = 0
    for chunk in data_generator:
        # Process chunk (e.g., parse, transform, etc.)
        total_processed += len(chunk)
        print(f"Processed {total_processed} bytes")
        yield chunk

restore = RestoreRequest(
    Key="/logs/application.log",
    Filespace="/logs"
)

result = client.restore(restore)

# Stream and process data
with open("/local/processed.log", "wb") as f:
    for processed_chunk in process_restored_data(result.body):
        f.write(processed_chunk)
```

---

## Best Practices

### 1. Memory-Efficient Processing
```python
# CORRECT: Stream data to file
with open("/local/large_file.bin", "wb") as f:
    for chunk in result.body:
        f.write(chunk)

# WRONG: Load entire file into memory
# data = b"".join(result.body)  # ❌ May cause RAM overflow!
```

### 2. Partial Restores
```python
# Restore only needed portion
restore = RestoreRequest(
    Key="/data/huge_file.bin",
    Offset=1048576,  # Skip first 1MB
    Length=2097152   # Get next 2MB only
)
```

### 3. Point-in-Time Recovery
```python
# Restore specific version
restore = RestoreRequest(
    Key="/data/document.txt",
    PitDate="2026-01-15 10:30:00"
)
```

### 4. Error Handling
```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    result = client.restore(restore)
    if result.status != "success":
        print(f"Restore warning: {result.status}")
    
    with open("/local/file.txt", "wb") as f:
        for chunk in result.body:
            f.write(chunk)
except TSMError as e:
    print(f"Restore failed: {e}")
    # Handle error
except IOError as e:
    print(f"File write error: {e}")
    # Handle file error
```

### 5. Batch Operations
```python
# Group related files in batches
batch = BatchRestoreRequest(
    objects=[...],  # Related files
    MaxPerTxn=100  # Optimize transaction size
)
```

---

## Performance Considerations

### Chunk Processing
```python
# Process chunks as they arrive (don't buffer)
bytes_written = 0
with open("/local/file.bin", "wb") as f:
    for chunk in result.body:
        f.write(chunk)
        bytes_written += len(chunk)
        # Update progress
        progress = (bytes_written / result.total_bytes) * 100
        print(f"Progress: {progress:.1f}%")
```

### Parallel Batch Restores
```python
# Restore multiple files in parallel (if supported)
batch = BatchRestoreRequest(
    objects=[...],  # Many small files
    MaxPerTxn=100  # Higher transaction limit
)
```

### Partial Restore for Large Files
```python
# Restore large file in segments
file_size = 10737418240  # 10GB
segment_size = 104857600  # 100MB segments

for offset in range(0, file_size, segment_size):
    restore = RestoreRequest(
        Key="/data/huge_file.bin",
        Offset=offset,
        Length=segment_size
    )
    result = client.restore(restore)
    
    # Process segment
    with open(f"/local/segment_{offset}.bin", "wb") as f:
        for chunk in result.body:
            f.write(chunk)
```

---

## Validation Rules

### RestoreRequest
- `key` cannot be empty
- `filespace` cannot be empty (defaults to "/")
- `offset` must be non-negative
- `length` must be non-negative (0 = restore all)
- `pit_date` must be in format "YYYY-MM-DD HH:MM:SS" if provided

### BatchRestoreRequest
- `objects` list must contain at least 1 item
- All objects must be valid RestoreRequest instances
- `max_per_txn` must be >= 1

### GroupRestoreRequest
- `group_leader_obj_id_hi` must be >= 0
- `group_leader_obj_id_lo` must be >= 0
- `filespace` cannot be empty (defaults to "/")

---

## Error Scenarios

### Object Not Found
```python
try:
    restore = RestoreRequest(Key="/nonexistent.txt", Filespace="/myfs")
    result = client.restore(restore)
except TSMError as e:
    if "not found" in str(e).lower():
        print("Object does not exist in backup")
    else:
        print(f"Restore error: {e}")
```

### Invalid Date Format
```python
try:
    restore = RestoreRequest(
        Key="/data/file.txt",
        PitDate="invalid-date"  # Wrong format
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

### Restore Failures
```python
# Network error during restore
try:
    result = client.restore(restore)
    with open("/local/file.txt", "wb") as f:
        for chunk in result.body:
            f.write(chunk)
except TSMError as e:
    print(f"Restore failed: {e}")
    # Retry or handle error
```

### Disk Space Issues
```python
import os

# Check available space before restore
restore = RestoreRequest(Key="/data/large_file.bin", Filespace="/myfs")
result = client.restore(restore)

stat = os.statvfs("/local")
available_space = stat.f_bavail * stat.f_frsize

if result.total_bytes > available_space:
    print(f"Insufficient disk space: need {result.total_bytes}, have {available_space}")
    # Handle error
else:
    with open("/local/large_file.bin", "wb") as f:
        for chunk in result.body:
            f.write(chunk)
```

---

## Advanced Use Cases

### Restore with Verification
```python
import hashlib

def restore_with_checksum(restore_request, output_path):
    """Restore file and compute checksum"""
    result = client.restore(restore_request)
    
    hasher = hashlib.sha256()
    with open(output_path, "wb") as f:
        for chunk in result.body:
            f.write(chunk)
            hasher.update(chunk)
    
    checksum = hasher.hexdigest()
    print(f"Restored {result.total_bytes} bytes")
    print(f"SHA256: {checksum}")
    return checksum

checksum = restore_with_checksum(
    RestoreRequest(Key="/data/important.bin", Filespace="/myfs"),
    "/local/important.bin"
)
```

### Restore to Memory (Small Files Only)
```python
def restore_to_memory(restore_request):
    """Restore small file to memory (use with caution!)"""
    result = client.restore(restore_request)
    
    if result.total_bytes > 10485760:  # 10MB limit
        raise ValueError("File too large for memory restore")
    
    data = b"".join(result.body)
    return data

# Only for small files
data = restore_to_memory(
    RestoreRequest(Key="/config/small.conf", Filespace="/config")
)
print(f"Restored {len(data)} bytes to memory")
```

### Restore with Progress Tracking
```python
def restore_with_progress(restore_request, output_path):
    """Restore with progress bar"""
    result = client.restore(restore_request)
    
    bytes_written = 0
    with open(output_path, "wb") as f:
        for chunk in result.body:
            f.write(chunk)
            bytes_written += len(chunk)
            
            # Update progress
            if result.total_bytes > 0:
                progress = (bytes_written / result.total_bytes) * 100
                print(f"\rProgress: {progress:.1f}% ({bytes_written}/{result.total_bytes} bytes)", end="")
    
    print()  # New line after completion

restore_with_progress(
    RestoreRequest(Key="/data/large.bin", Filespace="/myfs"),
    "/local/large.bin"
)
```

---

## Internal Models (Not for Direct Use)

The following internal models are used by the SDK implementation and should not be used directly:

- `RestoreInternal`: Internal restore model for C API layer
- `BatchRestoreInternal`: Internal batch restore model
- `GroupRestoreInternal`: Internal group restore model

These models handle low-level C API parameter mapping and are automatically created by the SDK.

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0