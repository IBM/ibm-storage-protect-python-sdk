# Query Operation Models - Data Design

## Overview

Query operation models enable discovery and retrieval of metadata for objects, filespaces, management classes, and backup groups. These models are defined in [`data_models/query.py`](../../src/ibm_storage_protect/data_models/query.py) and used by [`QueryClient`](../../src/ibm_storage_protect/query.py).

---

## Query Client

### QueryClient

**Purpose**: Execute query operations against IBM Storage Protect server.

**Location**: [`query.py`](../../src/ibm_storage_protect/query.py:50)

**Constructor**:
```python
QueryClient(session: ClientSession)
```

**Methods**:
- [`query_object()`](../../src/ibm_storage_protect/query.py:873): Query specific backup objects
- [`query_objects()`](../../src/ibm_storage_protect/query.py:379): Query multiple backup objects
- [`list_objects()`](../../src/ibm_storage_protect/query.py:565): List objects with optional prefix filtering
- [`query_filespaces()`](../../src/ibm_storage_protect/query.py:748): Query all filespaces
- [`query_mgmt_classes()`](../../src/ibm_storage_protect/query.py:991): Query management classes
- [`query_group_members()`](../../src/ibm_storage_protect/query.py:197): Query group members by leader ID

**Example**:
```python
from ibm_storage_protect import ClientSession, QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials

session = ClientSession()
session.login(LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD")))
query_client = QueryClient(session)

# Use query operations
results = query_client.list_objects(...)
```

---

## Object Query Operations

### BackupQueryRequest (Input)

**Purpose**: Query specific backup objects by key and filespace.

**Usage**: Input to [`QueryClient.query_object()`](../../src/ibm_storage_protect/query.py:873)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `key` | `str` | Required | - | `Key` | Cannot be empty | Object key path to query |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace name |
| `obj_state` | `ObjStateEnum` | Optional | `ACTIVE` | `ObjState` | - | Object state (ACTIVE, INACTIVE, ANY) |
| `obj_type` | `ObjectType` | Optional | `FILE` | `ObjType` | - | Object type (FILE, DIRECTORY, ANY) |
| `pit_date` | `str` | Optional | `None` | `PitDate` | Format: "YYYY-MM-DD HH:MM:SS" | Point-in-time date for historical query |

**Example**:
```python
from ibm_storage_protect.data_models.query import BackupQueryRequest
from ibm_storage_protect.enums import ObjState, ObjType

# Query active file
query = BackupQueryRequest(
    Key="/data/myfile.txt",
    Filespace="/myfs",
    ObjState=ObjState.ACTIVE,
    ObjType=ObjType.FILE
)

results = query_client.query_object(query)

# Query with point-in-time
query = BackupQueryRequest(
    Key="/data/myfile.txt",
    Filespace="/myfs",
    PitDate="2026-01-15 10:30:00"
)

results = query_client.query_object(query)
```

---

### ListObjectsRequest (Input)

**Purpose**: List objects with optional prefix filtering.

**Usage**: Input to [`QueryClient.list_objects()`](../../src/ibm_storage_protect/query.py:180)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace name |
| `prefix` | `str` | Optional | `None` | `Prefix` | - | Key prefix filter (e.g., "/data/logs/") |
| `obj_state` | `ObjStateEnum` | Optional | `ACTIVE` | `ObjState` | - | Object state filter |
| `obj_type` | `ObjectType` | Optional | `ANY` | `ObjType` | - | Object type filter |
| `max_results` | `int` | Optional | `1000` | `MaxResults` | >= 1 | Maximum results to return |

**Example**:
```python
from ibm_storage_protect.data_models.query import ListObjectsRequest
from ibm_storage_protect.enums import ObjState, ObjType

# List all active files in filespace
query = ListObjectsRequest(
    Filespace="/myfs",
    ObjState=ObjState.ACTIVE,
    ObjType=ObjType.FILE,
    MaxResults=500
)

results = query_client.list_objects(query)

# List objects with prefix
query = ListObjectsRequest(
    Filespace="/myfs",
    Prefix="/data/logs/",
    MaxResults=100
)

results = query_client.list_objects(query)
```

---

### ObjectMetadata (Output)

**Purpose**: Complete metadata for a backed-up object.

**Usage**: Returned by query operations

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `key` | `str` | Required | `Key` | Object key path |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `obj_id_hi` | `int` | Required | `ObjIdHi` | High part of object ID |
| `obj_id_lo` | `int` | Required | `ObjIdLo` | Low part of object ID |
| `obj_state` | `str` | Required | `ObjState` | Object state (ACTIVE/INACTIVE) |
| `obj_type` | `str` | Required | `ObjType` | Object type (FILE/DIRECTORY) |
| `size` | `int` | Required | `Size` | Object size in bytes |
| `backup_date` | `str` | Required | `BackupDate` | Backup timestamp |
| `expiration_date` | `str` | Optional | `ExpirationDate` | Expiration timestamp |
| `owner` | `str` | Optional | `Owner` | Object owner |
| `management_class` | `str` | Optional | `ManagementClass` | Management class name |
| `compressed` | `bool` | Required | `Compressed` | Object is compressed |
| `deduplicated` | `bool` | Required | `Deduplicated` | Object is deduplicated |
| `encrypted` | `bool` | Required | `Encrypted` | Object is encrypted |
| `group_leader_obj_id` | `str` | Optional | `GroupLeaderObjId` | Group leader object ID (if member) |
| `is_group_leader` | `bool` | Required | `IsGroupLeader` | Object is a group leader |
| `media` | `str` | Optional | `Media` | Storage media type |
| `repository` | `str` | Optional | `Repository` | Storage repository |

**Example Output**:
```python
{
    "key": "/data/myfile.txt",
    "filespace": "/myfs",
    "obj_id_hi": 12345,
    "obj_id_lo": 67890,
    "obj_state": "ACTIVE",
    "obj_type": "FILE",
    "size": 1048576,
    "backup_date": "2026-05-29 09:30:00",
    "expiration_date": "2027-05-29 09:30:00",
    "owner": "root",
    "management_class": "STANDARD",
    "compressed": True,
    "deduplicated": False,
    "encrypted": False,
    "group_leader_obj_id": None,
    "is_group_leader": False,
    "media": "DISK",
    "repository": "BACKUP"
}
```

**Usage**:
```python
results = query_client.query_backup(query)
for obj in results:
    print(f"Key: {obj.key}")
    print(f"Size: {obj.size} bytes")
    print(f"Backup Date: {obj.backup_date}")
    print(f"Compressed: {obj.compressed}")
    print(f"Object ID: {obj.obj_id_hi}-{obj.obj_id_lo}")
```

---

### QueryResult (Output)

**Purpose**: Generic query result container.

**Usage**: Returned by query operations

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Query status ("success" or "failed") |
| `objects` | `List[ObjectMetadata]` | Required | `Objects` | List of matching objects |
| `total_count` | `int` | Required | `TotalCount` | Total objects found |
| `has_more` | `bool` | Required | `HasMore` | More results available |

**Example**:
```python
result = query_client.list_objects(query)
print(f"Status: {result.status}")
print(f"Found {result.total_count} objects")
print(f"More results: {result.has_more}")

for obj in result.objects:
    print(f"  - {obj.key} ({obj.size} bytes)")
```

---

## Group Query Operations

### GroupQueryRequest (Input)

**Purpose**: Query group members by leader object ID.

**Usage**: Input to [`QueryClient.query_group_members()`](../../src/ibm_storage_protect/query.py:197)

**Fields**:

| Field | Type | Required | Default | Alias | Constraints | Description |
|-------|------|----------|---------|-------|-------------|-------------|
| `group_leader_obj_id_hi` | `int` | Required | - | `GroupLeaderObjIdHi` | >= 0 | High part of group leader object ID |
| `group_leader_obj_id_lo` | `int` | Required | - | `GroupLeaderObjIdLo` | >= 0 | Low part of group leader object ID |
| `filespace` | `str` | Optional | `"/"` | `Filespace` | Cannot be empty | Filespace name |
| `include_leader` | `bool` | Optional | `True` | `IncludeLeader` | - | Include leader in results |
| `max_results` | `int` | Optional | `1000` | `MaxResults` | >= 1 | Maximum results to return |

**Example**:
```python
from ibm_storage_protect.data_models.query import GroupQueryRequest

# Query group members
query = GroupQueryRequest(
    GroupLeaderObjIdHi=12345,
    GroupLeaderObjIdLo=67890,
    Filespace="/myfs",
    IncludeLeader=True,
    MaxResults=500
)

results = query_client.query_group_members(query)

# Process results
print(f"Group has {results.total_count} members")
for member in results.objects:
    if member.is_group_leader:
        print(f"Leader: {member.key}")
    else:
        print(f"Member: {member.key}")
```

---

### GroupQueryResult (Output)

**Purpose**: Result of group query operation.

**Usage**: Returned by [`QueryClient.query_group_members()`](../../src/ibm_storage_protect/query.py:197)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Query status |
| `group_leader_obj_id` | `str` | Required | `GroupLeaderObjId` | Group leader object ID (formatted as hi-lo) |
| `filespace` | `str` | Required | `Filespace` | Filespace name |
| `leader` | `ObjectMetadata` | Optional | `Leader` | Leader object metadata |
| `members` | `List[ObjectMetadata]` | Required | `Members` | Member objects metadata |
| `total_count` | `int` | Required | `TotalCount` | Total members (including leader if requested) |
| `has_more` | `bool` | Required | `HasMore` | More results available |

---

## Filespace Query Operations

### ListFilespacesRequest (Input)

**Purpose**: List all filespaces for the current node.

**Usage**: Input to [`QueryClient.query_filespaces()`](../../src/ibm_storage_protect/query.py:748)

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `max_results` | `int` | Optional | `1000` | `MaxResults` | Maximum results to return (>= 1) |

**Example**:
```python
from ibm_storage_protect.data_models.query import ListFilespacesRequest

query = ListFilespacesRequest(MaxResults=100)
results = query_client.query_filespaces(query)

for fs in results.filespaces:
    print(f"Filespace: {fs.name}")
    print(f"  Capacity: {fs.capacity} bytes")
    print(f"  Used: {fs.used_space} bytes")
```

---

### FilespaceMetadata (Output)

**Purpose**: Metadata for a filespace.

**Usage**: Part of filespace query results

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `name` | `str` | Required | `Name` | Filespace name |
| `fsid` | `int` | Required | `FsId` | Filespace ID |
| `capacity` | `int` | Required | `Capacity` | Total capacity in bytes |
| `used_space` | `int` | Required | `UsedSpace` | Used space in bytes |
| `backup_date` | `str` | Required | `BackupDate` | Last backup timestamp |
| `platform` | `str` | Optional | `Platform` | Platform type |
| `is_unicode` | `bool` | Required | `IsUnicode` | Unicode support enabled |

---

### FilespaceQueryResult (Output)

**Purpose**: Result of filespace query operation.

**Usage**: Returned by [`QueryClient.query_filespaces()`](../../src/ibm_storage_protect/query.py:748)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Query status |
| `filespaces` | `List[FilespaceMetadata]` | Required | `Filespaces` | List of filespaces |
| `total_count` | `int` | Required | `TotalCount` | Total filespaces found |

---

## Management Class Query Operations

### ListManagementClassesRequest (Input)

**Purpose**: List management classes available on the server.

**Usage**: Input to [`QueryClient.query_mgmt_classes()`](../../src/ibm_storage_protect/query.py:991)

**Fields**:

| Field | Type | Required | Default | Alias | Description |
|-------|------|----------|---------|-------|-------------|
| `max_results` | `int` | Optional | `1000` | `MaxResults` | Maximum results to return (>= 1) |

**Example**:
```python
from ibm_storage_protect.data_models.query import ListManagementClassesRequest

query = ListManagementClassesRequest(MaxResults=50)
results = query_client.query_mgmt_classes(query)

for mc in results.management_classes:
    print(f"Management Class: {mc.name}")
    print(f"  Description: {mc.description}")
    print(f"  Retention: {mc.retention_days} days")
```

---

### ManagementClassMetadata (Output)

**Purpose**: Metadata for a management class.

**Usage**: Part of management class query results

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `name` | `str` | Required | `Name` | Management class name |
| `description` | `str` | Optional | `Description` | Management class description |
| `retention_days` | `int` | Required | `RetentionDays` | Retention period in days |
| `serialization` | `str` | Optional | `Serialization` | Serialization setting |
| `compression` | `bool` | Required | `Compression` | Compression enabled |
| `deduplication` | `bool` | Required | `Deduplication` | Deduplication enabled |
| `encryption` | `bool` | Required | `Encryption` | Encryption enabled |

---

### ManagementClassQueryResult (Output)

**Purpose**: Result of management class query operation.

**Usage**: Returned by [`QueryClient.query_mgmt_classes()`](../../src/ibm_storage_protect/query.py:991)

**Fields**:

| Field | Type | Required | Alias | Description |
|-------|------|----------|-------|-------------|
| `status` | `str` | Required | `Status` | Query status |
| `management_classes` | `List[ManagementClassMetadata]` | Required | `ManagementClasses` | List of management classes |
| `total_count` | `int` | Required | `TotalCount` | Total management classes found |

---

## Complete Workflow Examples

### Query Specific Object
```python
from ibm_storage_protect import ClientSession, QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.query import BackupQueryRequest
from ibm_storage_protect.enums import ObjState

# Setup
session = ClientSession()
session.login(LoginCredentials(node=os.getenv("SP_NODE"), password=os.getenv("SP_PASSWORD")))
query_client = QueryClient(session)

# Query object
query = BackupQueryRequest(
    Key="/data/important.txt",
    Filespace="/myfs",
    ObjState=ObjState.ACTIVE
)

results = query_client.query_object(query)

if results.total_count > 0:
    obj = results.objects[0]
    print(f"Found: {obj.key}")
    print(f"Size: {obj.size} bytes")
    print(f"Backup Date: {obj.backup_date}")
    print(f"Compressed: {obj.compressed}")
else:
    print("Object not found")

# Cleanup
session.logout()
```

### List Objects with Prefix
```python
from ibm_storage_protect.data_models.query import ListObjectsRequest

# List all log files
query = ListObjectsRequest(
    Filespace="/logs",
    Prefix="/var/log/",
    MaxResults=100
)

results = query_client.list_objects(query)

print(f"Found {results.total_count} log files")
for obj in results.objects:
    print(f"  {obj.key}: {obj.size} bytes, backed up {obj.backup_date}")

if results.has_more:
    print("More results available (increase MaxResults)")
```

### Query Group Members
```python
from ibm_storage_protect.data_models.query import GroupQueryRequest

# Query group by leader ID
query = GroupQueryRequest(
    GroupLeaderObjIdHi=12345,
    GroupLeaderObjIdLo=67890,
    Filespace="/myfs",
    IncludeLeader=True
)

results = query_client.query_group_members(query)

print(f"Group: {results.group_leader_obj_id}")
print(f"Total members: {results.total_count}")

if results.leader:
    print(f"Leader: {results.leader.key} ({results.leader.size} bytes)")

print("Members:")
for member in results.members:
    print(f"  - {member.key} ({member.size} bytes)")
```

### List All Filespaces
```python
from ibm_storage_protect.data_models.query import ListFilespacesRequest

query = ListFilespacesRequest()
results = query_client.query_filespaces(query)

print(f"Found {results.total_count} filespaces:")
for fs in results.filespaces:
    used_pct = (fs.used_space / fs.capacity * 100) if fs.capacity > 0 else 0
    print(f"  {fs.name}:")
    print(f"    Capacity: {fs.capacity:,} bytes")
    print(f"    Used: {fs.used_space:,} bytes ({used_pct:.1f}%)")
    print(f"    Last Backup: {fs.backup_date}")
```

### List Management Classes
```python
from ibm_storage_protect.data_models.query import ListManagementClassesRequest

query = ListManagementClassesRequest()
results = query_client.query_mgmt_classes(query)

print(f"Available management classes ({results.total_count}):")
for mc in results.management_classes:
    print(f"  {mc.name}:")
    print(f"    Retention: {mc.retention_days} days")
    print(f"    Compression: {mc.compression}")
    print(f"    Deduplication: {mc.deduplication}")
    print(f"    Encryption: {mc.encryption}")
```

---

## Best Practices

### 1. Use Appropriate Filters
```python
# Narrow down results with filters
query = ListObjectsRequest(
    Filespace="/myfs",
    Prefix="/data/2026/",  # Only 2026 data
    ObjState=ObjState.ACTIVE,  # Only active objects
    MaxResults=500
)
```

### 2. Handle Pagination
```python
# Check for more results
results = query_client.list_objects(query)
if results.has_more:
    print(f"Showing {len(results.objects)} of {results.total_count} total")
    print("Increase MaxResults to see more")
```

### 3. Point-in-Time Queries
```python
# Query historical state
query = BackupQueryRequest(
    Key="/data/file.txt",
    Filespace="/myfs",
    PitDate="2026-01-01 00:00:00"  # State at specific time
)
```

### 4. Error Handling
```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    results = query_client.query_object(query)
    if results.status != "success":
        print(f"Query warning: {results.status}")
except TSMError as e:
    print(f"Query failed: {e}")
```

---

## Performance Considerations

### Limit Result Sets
```python
# Use MaxResults to limit memory usage
query = ListObjectsRequest(
    Filespace="/large-fs",
    MaxResults=100  # Limit to 100 objects
)
```

### Use Prefix Filtering
```python
# Prefix filtering is more efficient than post-processing
query = ListObjectsRequest(
    Filespace="/myfs",
    Prefix="/data/logs/2026/"  # Server-side filtering
)
# Better than:
# query = ListObjectsRequest(Filespace="/myfs")
# filtered = [obj for obj in results.objects if obj.key.startswith("/data/logs/2026/")]
```

### Specific Queries vs. List Operations
```python
# Use query_object for specific objects (faster)
query = BackupQueryRequest(Key="/data/specific.txt", Filespace="/myfs")
results = query_client.query_object(query)

# Use list_objects for browsing (slower for large sets)
query = ListObjectsRequest(Filespace="/myfs")
results = query_client.list_objects(query)
```

---

## Validation Rules

### BackupQueryRequest
- `key` cannot be empty
- `filespace` cannot be empty (defaults to "/")
- `pit_date` must be in format "YYYY-MM-DD HH:MM:SS" if provided

### ListObjectsRequest
- `filespace` cannot be empty (defaults to "/")
- `max_results` must be >= 1

### GroupQueryRequest
- `group_leader_obj_id_hi` must be >= 0
- `group_leader_obj_id_lo` must be >= 0
- `filespace` cannot be empty (defaults to "/")
- `max_results` must be >= 1

---

## Error Scenarios

### Object Not Found
```python
query = BackupQueryRequest(Key="/nonexistent.txt", Filespace="/myfs")
results = query_client.query_object(query)

if results.total_count == 0:
    print("Object not found")
```

### Invalid Date Format
```python
try:
    query = BackupQueryRequest(
        Key="/data/file.txt",
        PitDate="invalid-date"  # Wrong format
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

### Query Failure
```python
try:
    results = query_client.list_objects(query)
except TSMError as e:
    print(f"Query failed: {e}")
    # Handle error
```

---

## Internal Models (Not for Direct Use)

The following internal models are used by the SDK implementation and should not be used directly:

- `BackupQueryInternal`: Internal query model for C API layer
- `ListObjectsInternal`: Internal list model for C API layer
- `GroupQueryInternal`: Internal group query model for C API layer

These models handle low-level C API parameter mapping and are automatically created by the SDK.

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0