# Control Management Operations - Data Design

## Overview

Control management operations handle filespace and object metadata management without transferring actual data content. These operations are defined in [`control.py`](../../src/ibm_storage_protect/control.py) and use models from [`data_models/filespace.py`](../../src/ibm_storage_protect/data_models/filespace.py) and [`data_models/object.py`](../../src/ibm_storage_protect/data_models/object.py).

Control operations are distinct from data operations (backup/restore) - they manipulate metadata and object properties on the server without data transfer.

---

## Control Client

### ControlClient

**Purpose**: Manage filespaces and backed-up objects through control path operations.

**Location**: [`control.py`](../../src/ibm_storage_protect/control.py:227)

**Constructor**:
```python
ControlClient(session: ClientSession)
```

**Methods**:

**Filespace Operations:**
- [`register_filespace()`](../../src/ibm_storage_protect/control.py:282): Create a new filespace
- [`update_filespace()`](../../src/ibm_storage_protect/control.py:446): Modify filespace attributes
- [`delete_filespace()`](../../src/ibm_storage_protect/control.py:628): Remove filespace and all objects

**Object Operations:**
- [`delete_by_name()`](../../src/ibm_storage_protect/control.py:792): Delete object using filespace and key
- [`delete_by_id()`](../../src/ibm_storage_protect/control.py:989): Delete object using object ID
- [`rename()`](../../src/ibm_storage_protect/control.py:1173): Change object names
- [`update()`](../../src/ibm_storage_protect/control.py:1381): Modify object attributes

**Example**:
```python
from ibm_storage_protect import ClientSession, ControlClient
from ibm_storage_protect.data_models.session import LoginCredentials

session = ClientSession()
session.login(LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD")))
control_client = ControlClient(session)

# Use control operations
result = control_client.register_filespace(...)
```

---

## Filespace Management

Filespaces are logical containers that organize backed-up objects, typically representing filesystems, application namespaces, or data sources.

### FilespaceRegisterRequest (Input)

**Purpose**: Create a new filespace on the server.

**Usage**: Input to [`ControlClient.register_filespace()`](../../src/ibm_storage_protect/control.py:282)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `filespace` | `str` | Required | - | `Filespace` | Cannot be empty | Filespace name (e.g., "/backup/data") |

**Example**:
```python
from ibm_storage_protect.data_models.filespace import FilespaceRegisterRequest

# Register a filespace
register = FilespaceRegisterRequest(Filespace="/backup/database")

result = control_client.register_filespace(register)
print(f"Registered: {result.filespace}")
```

**Notes**:
- Idempotent operation (safe to call multiple times)
- Required before backing up objects to the filespace
- Filespace names are case-sensitive on most platforms

---

### FilespaceRegisterResult (Output)

**Purpose**: Result of filespace registration operation.

**Usage**: Returned by [`ControlClient.register_filespace()`](../../src/ibm_storage_protect/control.py:282)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status ("success" or "failed") |
| `filespace` | `str` | Required | `Filespace` | Name of the registered filespace |

**Example Output**:
```python
{
    "status": "success",
    "filespace": "/backup/database"
}
```

---

### FilespaceUpdateRequest (Input)

**Purpose**: Modify filespace attributes.

**Usage**: Input to [`ControlClient.update_filespace()`](../../src/ibm_storage_protect/control.py:446)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `filespace` | `str` | Required | - | `Filespace` | Cannot be empty | Filespace name |
| `fs_type` | `str` | Optional | `None` | `FsType` | - | Filespace type (e.g., "Python-SDK", "PostgreSQL") |
| `fs_info` | `str` | Optional | `None` | `FsInfo` | - | Descriptive information |
| `occupancy` | `int` | Optional | `None` | `Occupancy` | >= 0 | Current storage usage in bytes |
| `capacity` | `int` | Optional | `None` | `Capacity` | >= 0 | Total storage capacity in bytes |

**Example**:
```python
from ibm_storage_protect.data_models.filespace import FilespaceUpdateRequest

# Update filespace metrics
update = FilespaceUpdateRequest(
    Filespace="/backup/database",
    Occupancy=5000000000,  # 5GB used
    Capacity=10000000000,  # 10GB total
    FsInfo="Production database backup"
)

result = control_client.update_filespace(update)
```

**Notes**:
- Only provided fields are updated; others remain unchanged
- Selective updates via optional parameters

---

### FilespaceUpdateResult (Output)

**Purpose**: Result of filespace update operation.

**Usage**: Returned by [`ControlClient.update_filespace()`](../../src/ibm_storage_protect/control.py:446)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `filespace` | `str` | Required | `Filespace` | Name of the updated filespace |

---

### FilespaceDeleteRequest (Input)

**Purpose**: Remove filespace and all its objects.

**Usage**: Input to [`ControlClient.delete_filespace()`](../../src/ibm_storage_protect/control.py:628)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `filespace` | `str` | Required | - | `Filespace` | Cannot be empty | Filespace name to delete |

**⚠️ WARNING**: This operation is **irreversible** and deletes **ALL objects** within the filespace from **all repositories** (backup and archive).

**Example**:
```python
from ibm_storage_protect.data_models.filespace import FilespaceDeleteRequest

# Delete filespace and all objects
delete = FilespaceDeleteRequest(Filespace="/backup/old_data")

result = control_client.delete_filespace(delete)
print(f"Deleted: {result.filespace}")
```

---

### FilespaceDeleteResult (Output)

**Purpose**: Result of filespace deletion operation.

**Usage**: Returned by [`ControlClient.delete_filespace()`](../../src/ibm_storage_protect/control.py:628)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `filespace` | `str` | Required | `Filespace` | Name of the deleted filespace |

---

## Object Management

Object management operations manipulate backed-up objects without transferring data content.

### ObjectDeleteRequest (Input)

**Purpose**: Delete object using filespace and key path.

**Usage**: Input to [`ControlClient.delete_by_name()`](../../src/ibm_storage_protect/control.py:792)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `filespace` | `str` | Required | - | `Filespace` | Cannot be empty | Filespace name |
| `key` | `str` | Required | - | `Key` | Cannot be empty | Object key path (e.g., "/path/to/file.txt") |
| `copy_group` | `int` | Optional | `1` | `CopyGroup` | >= 1 | Copy group number |
| `obj_type` | `ObjType` | Optional | `FILE` | `ObjType` | - | Object type (FILE/DIRECTORY) |

**Example**:
```python
from ibm_storage_protect.data_models.object import ObjectDeleteRequest
from ibm_storage_protect.enums import ObjType

# Delete a file
delete = ObjectDeleteRequest(
    Filespace="/backup/data",
    Key="/documents/report.pdf",
    CopyGroup=1,
    ObjType=ObjType.FILE
)

result = control_client.delete_by_name(delete)
print(f"Deleted: {result.key}")
```

**Notes**:
- Operation is wrapped in a transaction for atomicity
- Supports copy group specification

---

### ObjectDeleteResult (Output)

**Purpose**: Result of object deletion by name.

**Usage**: Returned by [`ControlClient.delete_by_name()`](../../src/ibm_storage_protect/control.py:792)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `key` | `str` | Required | `Key` | Path of the deleted object |

---

### ObjectDeleteByIdRequest (Input)

**Purpose**: Delete object using unique object ID.

**Usage**: Input to [`ControlClient.delete_by_id()`](../../src/ibm_storage_protect/control.py:989)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `obj_id_hi` | `int` | Required | - | `ObjIdHi` | >= 0 | High 32 bits of object ID |
| `obj_id_lo` | `int` | Required | - | `ObjIdLo` | >= 0 | Low 32 bits of object ID |

**Example**:
```python
from ibm_storage_protect.data_models.object import ObjectDeleteByIdRequest

# Delete by object ID (more efficient when ID is known)
delete = ObjectDeleteByIdRequest(
    ObjIdHi=12345,
    ObjIdLo=67890
)

result = control_client.delete_by_id(delete)
print(f"Deleted object: {result.obj_id_hi}-{result.obj_id_lo}")
```

**Notes**:
- More efficient than delete by name when object ID is known
- Operation is wrapped in a transaction for atomicity

---

### ObjectDeleteByIdResult (Output)

**Purpose**: Result of object deletion by ID.

**Usage**: Returned by [`ControlClient.delete_by_id()`](../../src/ibm_storage_protect/control.py:989)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `obj_id_hi` | `int` | Required | `ObjIdHi` | High 32 bits of deleted object's ID |
| `obj_id_lo` | `int` | Required | `ObjIdLo` | Low 32 bits of deleted object's ID |

---

### ObjectRenameRequest (Input)

**Purpose**: Change object's high-level and/or low-level names.

**Usage**: Input to [`ControlClient.rename()`](../../src/ibm_storage_protect/control.py:1173)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `filespace` | `str` | Required | - | `Filespace` | Cannot be empty | Filespace name |
| `key` | `str` | Required | - | `Key` | Cannot be empty | Current object key path |
| `new_key` | `str` | Required | - | `NewKey` | Cannot be empty | New object key path |
| `merge` | `bool` | Optional | `False` | `Merge` | - | Merge with existing object at NewKey |
| `obj_type` | `ObjType` | Optional | `FILE` | `ObjType` | - | Object type |

**Example**:
```python
from ibm_storage_protect.data_models.object import ObjectRenameRequest

# Rename an object
rename = ObjectRenameRequest(
    Filespace="/backup/data",
    Key="/old/path/file.txt",
    NewKey="/new/path/file.txt",
    Merge=False
)

result = control_client.rename(rename)
print(f"Renamed: {result.old_key} -> {result.new_key}")
```

**Notes**:
- Operation is wrapped in a transaction for atomicity
- `Merge=True` combines with existing object at NewKey location

---

### ObjectRenameResult (Output)

**Purpose**: Result of object rename operation.

**Usage**: Returned by [`ControlClient.rename()`](../../src/ibm_storage_protect/control.py:1173)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `old_key` | `str` | Required | `OldKey` | Original path of the object |
| `new_key` | `str` | Required | `NewKey` | New path of the object |

---

### ObjectUpdateRequest (Input)

**Purpose**: Modify object attributes (owner, management class).

**Usage**: Input to [`ControlClient.update()`](../../src/ibm_storage_protect/control.py:1381)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `filespace` | `str` | Required | - | `Filespace` | Cannot be empty | Filespace name |
| `key` | `str` | Required | - | `Key` | Cannot be empty | Object key path |
| `owner` | `str` | Optional | `None` | `Owner` | - | New owner |
| `management_class` | `str` | Optional | `None` | `ManagementClass` | - | New management class |
| `obj_type` | `ObjType` | Optional | `FILE` | `ObjType` | - | Object type |

**Example**:
```python
from ibm_storage_protect.data_models.object import ObjectUpdateRequest

# Update object attributes
update = ObjectUpdateRequest(
    Filespace="/backup/data",
    Key="/path/file.txt",
    Owner="admin",
    ManagementClass="STANDARD"
)

result = control_client.update(update)
print(f"Updated: {result.key}")
```

**Notes**:
- Only provided fields are updated; others remain unchanged
- No explicit transaction required

---

### ObjectUpdateResult (Output)

**Purpose**: Result of object update operation.

**Usage**: Returned by [`ControlClient.update()`](../../src/ibm_storage_protect/control.py:1381)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Operation status |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `key` | `str` | Required | `Key` | Path of the updated object |

---

## Complete Workflow Examples

### Filespace Lifecycle
```python
from ibm_storage_protect import ClientSession, ControlClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.filespace import (
    FilespaceRegisterRequest,
    FilespaceUpdateRequest,
    FilespaceDeleteRequest
)

# Setup
session = ClientSession()
session.login(LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD")))
control_client = ControlClient(session)

# 1. Register filespace
register = FilespaceRegisterRequest(Filespace="/backup/database")
result = control_client.register_filespace(register)
print(f"Registered: {result.filespace}")

# 2. Update filespace metrics
update = FilespaceUpdateRequest(
    Filespace="/backup/database",
    Occupancy=5000000000,  # 5GB
    Capacity=10000000000,  # 10GB
    FsInfo="Production PostgreSQL backup"
)
result = control_client.update_filespace(update)
print(f"Updated: {result.filespace}")

# 3. Delete filespace (when no longer needed)
delete = FilespaceDeleteRequest(Filespace="/backup/database")
result = control_client.delete_filespace(delete)
print(f"Deleted: {result.filespace}")

# Cleanup
session.logout()
```

### Object Management
```python
from ibm_storage_protect.data_models.object import (
    ObjectDeleteRequest,
    ObjectRenameRequest,
    ObjectUpdateRequest
)

# Delete an object
delete = ObjectDeleteRequest(
    Filespace="/backup/data",
    Key="/temp/old_file.txt"
)
result = control_client.delete_by_name(delete)
print(f"Deleted: {result.key}")

# Rename an object
rename = ObjectRenameRequest(
    Filespace="/backup/data",
    Key="/documents/draft.pdf",
    NewKey="/documents/final.pdf"
)
result = control_client.rename(rename)
print(f"Renamed: {result.old_key} -> {result.new_key}")

# Update object attributes
update = ObjectUpdateRequest(
    Filespace="/backup/data",
    Key="/documents/final.pdf",
    Owner="admin",
    ManagementClass="LONG_TERM"
)
result = control_client.update(update)
print(f"Updated: {result.key}")
```

### Delete by Object ID
```python
from ibm_storage_protect.data_models.object import ObjectDeleteByIdRequest

# Get object ID from query
from ibm_storage_protect import QueryClient
from ibm_storage_protect.data_models.query import BackupQueryRequest

query_client = QueryClient(session)
query = BackupQueryRequest(
    Key="/data/file.txt",
    Filespace="/backup"
)
results = query_client.query_objects(query)

if results.total_objects > 0:
    obj = results.objects[0]
    
    # Parse ObjectId string "hi-lo" into components
    obj_id_parts = obj['ObjectId'].split('-')
    obj_id_hi = int(obj_id_parts[0])
    obj_id_lo = int(obj_id_parts[1])
    
    # Delete using object ID
    delete = ObjectDeleteByIdRequest(
        ObjIdHi=obj_id_hi,
        ObjIdLo=obj_id_lo
    )
    result = control_client.delete_by_id(delete)
    print(f"Deleted object: {result.obj_id_hi}-{result.obj_id_lo}")
```

---

## Best Practices

### 1. Filespace Registration
```python
# Register filespace before first backup
register = FilespaceRegisterRequest(Filespace="/backup/app")
control_client.register_filespace(register)

# Safe to call multiple times (idempotent)
control_client.register_filespace(register)  # No error
```

### 2. Selective Updates
```python
# Update only specific fields
update = FilespaceUpdateRequest(
    Filespace="/backup/app",
    Occupancy=1000000000  # Only update occupancy
    # Other fields remain unchanged
)
```

### 3. Error Handling
```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    result = control_client.delete_by_name(delete)
    if result.status != "success":
        print(f"Delete warning: {result.status}")
except TSMError as e:
    print(f"Delete failed: {e}")
    # Handle error
```

### 4. Object ID vs. Name
```python
# Use delete_by_id when ID is known (more efficient)
delete_by_id = ObjectDeleteByIdRequest(ObjIdHi=12345, ObjIdLo=67890)
result = control_client.delete_by_id(delete_by_id)

# Use delete_by_name when only path is known
delete_by_name = ObjectDeleteRequest(Filespace="/backup", Key="/file.txt")
result = control_client.delete_by_name(delete_by_name)
```

---

## Performance Considerations

### Filespace Operations
```python
# Filespace operations are lightweight metadata operations
# No data transfer involved
register = FilespaceRegisterRequest(Filespace="/backup/data")
result = control_client.register_filespace(register)  # Fast
```

### Object Operations
```python
# Object operations involve server communication but no data transfer
# Transaction overhead is minimal for single operations
delete = ObjectDeleteRequest(Filespace="/backup", Key="/file.txt")
result = control_client.delete_by_name(delete)  # Fast
```

### Batch Considerations
```python
# For multiple operations, consider grouping
filespaces = ["/backup/app1", "/backup/app2", "/backup/app3"]

for fs in filespaces:
    register = FilespaceRegisterRequest(Filespace=fs)
    control_client.register_filespace(register)
```

---

## Validation Rules

### FilespaceRegisterRequest
- `filespace` cannot be empty or whitespace-only

### FilespaceUpdateRequest
- `filespace` cannot be empty or whitespace-only
- `occupancy` must be >= 0 if provided
- `capacity` must be >= 0 if provided

### FilespaceDeleteRequest
- `filespace` cannot be empty or whitespace-only

### ObjectDeleteRequest
- `filespace` cannot be empty or whitespace-only
- `key` cannot be empty or whitespace-only
- `copy_group` must be >= 1

### ObjectDeleteByIdRequest
- `obj_id_hi` must be >= 0
- `obj_id_lo` must be >= 0

### ObjectRenameRequest
- `filespace` cannot be empty or whitespace-only
- `key` cannot be empty or whitespace-only
- `new_key` cannot be empty or whitespace-only

### ObjectUpdateRequest
- `filespace` cannot be empty or whitespace-only
- `key` cannot be empty or whitespace-only

---

## Error Scenarios

### Filespace Already Exists
```python
# Registering existing filespace is safe (idempotent)
register = FilespaceRegisterRequest(Filespace="/backup/data")
result = control_client.register_filespace(register)  # Success
result = control_client.register_filespace(register)  # Also success
```

### Filespace Not Found
```python
try:
    update = FilespaceUpdateRequest(
        Filespace="/nonexistent",
        Occupancy=1000
    )
    result = control_client.update_filespace(update)
except TSMError as e:
    print(f"Filespace not found: {e}")
```

### Object Not Found
```python
try:
    delete = ObjectDeleteRequest(
        Filespace="/backup",
        Key="/nonexistent.txt"
    )
    result = control_client.delete_by_name(delete)
except TSMError as e:
    print(f"Object not found: {e}")
```

### Invalid Object ID
```python
try:
    delete = ObjectDeleteByIdRequest(
        ObjIdHi=-1,  # Invalid (must be >= 0)
        ObjIdLo=67890
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

---

## Thread Safety

**WARNING**: ControlClient is **NOT thread-safe**. Each instance requires exclusive access to its session handle.

```python
# WRONG: Sharing client across threads
client = ControlClient(session)
thread1.start(lambda: client.delete_by_name(...))  # ❌ Undefined behavior
thread2.start(lambda: client.rename(...))          # ❌ Data corruption risk

# CORRECT: Separate clients for each thread
session1 = ClientSession()
session1.login(...)
client1 = ControlClient(session1)

session2 = ClientSession()
session2.login(...)
client2 = ControlClient(session2)

thread1.start(lambda: client1.delete_by_name(...))  # ✓ Safe
thread2.start(lambda: client2.rename(...))          # ✓ Safe
```

---

## Internal Models (Not for Direct Use)

The following internal models are used by the SDK implementation and should not be used directly:

- `FilespaceRegisterInternal`: Internal filespace registration model
- `FilespaceUpdateInternal`: Internal filespace update model
- `FilespaceDeleteInternal`: Internal filespace deletion model
- `ObjectDeleteInternal`: Internal object deletion model
- `ObjectDeleteByIdInternal`: Internal object deletion by ID model
- `ObjectRenameInternal`: Internal object rename model
- `ObjectUpdateInternal`: Internal object update model

These models handle low-level C API parameter mapping and are automatically created by the SDK.

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0