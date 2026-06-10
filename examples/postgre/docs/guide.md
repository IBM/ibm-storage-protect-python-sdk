# PostgreSQL Database Backup & Restore Guide

This guide demonstrates how to use the IBM Storage Protect Python SDK for PostgreSQL database backup, restore, query, and object management operations.

---

## 1. Overview

The PostgreSQL examples provide comprehensive demonstrations of:

### Backup Operations (`backup/`)
- **Single Backup** (`single.py`) - Individual file backup with streaming
- **Batch Backup** (`batch.py`) - Multiple files in optimized transactions
- **Group Backup** (`group.py`) - Related files with leader-member relationships

### Restore Operations (`restore/`)
- **Single Restore** - Full, Point-in-Time, and Partial restore
- **Batch Restore** - Multiple file restoration
- **Group Restore** - Group member restoration

### Query Operations (`query/`)
- **Single Query** (`single.py`) - Query specific backup objects
- **Batch Query** (`batch.py`) - Query multiple objects
- **Group Query** (`group.py`) - Query group members
- **List All** (`list_all.py`) - Overview of all backups

### Object Management (`object_management/`)
- **Single** (`single.py`) - Rename, update, delete single objects
- **Batch** (`batch.py`) - Manage batch objects
- **Group** (`group.py`) - Manage group objects
- **Filespace Deletion** (`delete_filespace.py`) - Delete entire filespace

### Key Features
- **4MB Streaming Chunks**: Uses generators to stream large files efficiently
- **Pre-Compressed Support**: `.tar.gz` files marked as `PreCompressed=True`
- **Memory Efficient**: Avoids loading entire files into RAM
- **JSON Logging**: Comprehensive logging for debugging and auditing

---

## 2. Configuration & Prerequisites

### Authentication
All examples use `LoginCredentials()` which reads from TSM configuration:
- Configuration files: `dsm.sys`, `dsm.opt`
- Or environment variables if configured

### Filespace
All examples use: `/postgres_bckp`

### Directory Structure
```
protect_postgre/
├── backup/              # Backup examples
│   ├── single.py       # Single file backup
│   ├── batch.py        # Batch backup (5 files)
│   └── group.py        # Group backup (leader + members)
├── restore/            # Restore examples
│   ├── single/         # Single restore (full, PIT, partial)
│   ├── batch/          # Batch restore (full, PIT, partial)
│   └── group/          # Group restore (full, PIT, partial)
├── query/              # Query examples
│   ├── single.py       # Query single object
│   ├── batch.py        # Query batch objects
│   ├── group.py        # Query group members
│   └── list_all.py     # List all backups
└── object_management/  # Object management
    ├── single.py       # Manage single object
    ├── batch.py        # Manage batch objects
    ├── group.py        # Manage group objects
    └── delete_filespace.py  # Delete filespace
```

---

## 3. Backup Examples

### 3.1. Single Backup (`backup/single.py`)

Backs up a single database file using streaming chunks.

**Usage:**
```bash
cd sp_client_sdk/examples/postgre/src/protect_postgre/backup
python single.py
```

**Key Implementation:**
```python
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest

def read_file_in_chunks(filepath, chunk_size=4*1024*1024):
    """Yield file data in 4MB chunks"""
    with open(filepath, "rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            yield block

# Session setup
creds = LoginCredentials()
sess = ClientSession()
sess.login(creds)

# Backup with streaming
file_path = "/path/to/ecommerce_db.tar.gz"
file_size = os.path.getsize(file_path)

backup_req = BackupRequest(
    Key=file_path,
    Body=read_file_in_chunks(file_path),
    Filespace="/postgres_bckp",
    SizeEstimate=file_size
)

client = DataClient(sess)
result = client.backup(backup_req)
print(f"Status: {result.status}")
sess.logout()
```

### 3.2. Batch Backup (`backup/batch.py`)

Backs up multiple database files in a single batch operation.

**Usage:**
```bash
python batch.py
```

**Key Implementation:**
```python
from ibm_storage_protect.data_models.backup import BatchBackupRequest

# Prepare multiple files
files = [
    "/path/to/audit_db.tar.gz",
    "/path/to/employee_db.tar.gz",
    "/path/to/inventory_db.tar.gz",
    "/path/to/logs_db.tar.gz",
    "/path/to/sales_db.tar.gz"
]

# Create batch request
batch = BatchBackupRequest(
    objects=[
        BackupRequest(
            Key=file,
            Body=read_file_in_chunks(file),
            SizeEstimate=os.path.getsize(file)
        ) for file in files
    ],
    Filespace="/postgres_bckp",
    MaxPerTxn=10
)

result = client.batch_backup(batch)
```

### 3.3. Group Backup (`backup/group.py`)

Creates a group backup with leader (metadata) and members (data files).

**Usage:**
```bash
python group.py
```

**Key Implementation:**
```python
# Create group
group = client.create_group("database_backup_group", filespace="/postgres_bckp")

# Add leader (JSON metadata file)
leader_backup = BackupRequest(
    Key="/path/to/leader.json",
    Body=chunked_file_reader(leader_file),
    Filespace="/postgres_bckp",
    SizeEstimate=os.path.getsize(leader_file),
    PreCompressed=False  # JSON not compressed
)
group.add_member(leader_backup)

# Add members (.tar.gz files)
for member_file in member_files:
    member_backup = BackupRequest(
        Key=member_file,
        Body=chunked_file_reader(member_file),
        Filespace="/postgres_bckp",
        SizeEstimate=os.path.getsize(member_file),
        PreCompressed=True  # .tar.gz already compressed
    )
    group.add_member(member_backup)

# Finalize group
group.save()
group.close()

print(f"Group: {group.name}")
print(f"Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")
```

---

## 4. Restore Examples

### 4.1. Single Full Restore (`restore/single/restore_full.py`)

Restores complete file from backup.

**Usage:**
```bash
cd sp_client_sdk/examples/postgre/src/protect_postgre/restore/single
python restore_full.py
```

**Key Implementation:**
```python
from ibm_storage_protect.data_models.restore import RestoreRequest

restore_request = RestoreRequest(
    Key="/path/to/ecommerce_db.tar.gz",
    Filespace="/postgres_bckp"
)

result = client.restore(restore_request)

# Stream to file
output_file = "ecommerce_db_restored.tar.gz"
with open(output_file, "wb") as f:
    for chunk in result.body:
        f.write(chunk)
```

### 4.2. Point-in-Time Restore (`restore/single/restore_pit.py`)

Restores file from specific backup timestamp.

**Key Addition:**
```python
restore_request = RestoreRequest(
    Key="/path/to/file.tar.gz",
    Filespace="/postgres_bckp",
    PitDate="2026-05-31 22:35:04"  # Specific backup date
)
```

### 4.3. Partial Restore (`restore/single/restore_partial.py`)

Restores specific byte range from file.

**Key Addition:**
```python
restore_request = RestoreRequest(
    Key="/path/to/file.tar.gz",
    Filespace="/postgres_bckp",
    Offset=0,           # Start byte
    Length=10485760     # 10MB (10,485,760 bytes)
)
```

---

## 5. Query Examples

### 5.1. Query Single Backup (`query/single.py`)

Queries metadata for a specific backed-up file.

**Usage:**
```bash
cd sp_client_sdk/examples/postgre/src/protect_postgre/query
python single.py
```

**Key Implementation:**
```python
from ibm_storage_protect import QueryClient
from ibm_storage_protect.data_models.query import BackupQueryRequest
from ibm_storage_protect.enums import ObjState, ObjType

query = BackupQueryRequest(
    Key="/path/to/ecommerce_db.tar.gz",
    Filespace="/postgres_bckp",
    ObjState=ObjState.ACTIVE,
    ObjType=ObjType.FILE
)

result = query_client.query_object(query)

if result and result.key:
    print(f"Object ID: {result.object_id}")
    print(f"Size: {result.size:,} bytes")
    print(f"Last Modified: {result.last_modified}")
    print(f"Compressed: {result.compressed}")
```

### 5.2. Query Batch Backups (`query/batch.py`)

Queries multiple backed-up files using two methods.

**Usage:**
```bash
python batch.py
```

**Method 1 - Individual Queries:**
```python
for file_path in batch_files:
    query = BackupQueryRequest(
        Key=file_path,
        Filespace="/postgres_bckp"
    )
    result = query_client.query_object(query)
```

**Method 2 - Prefix Filter (More Efficient):**
```python
from ibm_storage_protect.data_models.query import ListObjectsRequest

query = ListObjectsRequest(
    Filespace="/postgres_bckp",
    Prefix="/path/to/batch_directory/",
    MaxResults=100
)

results = query_client.list_objects(query)
```

### 5.3. Query Group Backup (`query/group.py`)

Queries group leader and all members.

**Usage:**
```bash
python group.py
```

**Key Implementation:**
```python
# Step 1: Query leader to get its ID
leader_query = BackupQueryRequest(
    Key="/path/to/leader.json",
    Filespace="/postgres_bckp"
)
leader_result = query_client.query_object(leader_query)

# Step 2: Query all group members using leader ID
from ibm_storage_protect.data_models.query import GroupQueryRequest

group_query = GroupQueryRequest(
    GroupLeaderObjIdHi=leader_result.obj_id_hi,
    GroupLeaderObjIdLo=leader_result.obj_id_lo,
    Filespace="/postgres_bckp",
    IncludeLeader=True
)

members = query_client.query_group_members(group_query)
```

---

## 6. Object Management Examples

### 6.1. Single Object Management (`object_management/single.py`)

Demonstrates rename, update, and delete operations.

**Usage:**
```bash
cd sp_client_sdk/examples/postgre/src/protect_postgre/object_management
python single.py
```

**Operations:**

**Rename:**
```python
from ibm_storage_protect import ControlClient
from ibm_storage_protect.data_models.object import ObjectRenameRequest

rename_request = ObjectRenameRequest(
    Filespace="/postgres_bckp",
    Key="/path/to/ecommerce_db.tar.gz",
    NewKey="/path/to/ecommerce_db_renamed.tar.gz",
    Merge=False
)

result = control_client.rename(rename_request)
```

**Update Attributes:**
```python
from ibm_storage_protect.data_models.object import ObjectUpdateRequest

update_request = ObjectUpdateRequest(
    Filespace="/postgres_bckp",
    Key="/path/to/ecommerce_db_renamed.tar.gz",
    Owner="postgres_admin",
    ManagementClass="STANDARD"
)

result = control_client.update(update_request)
```

**Delete:**
```python
from ibm_storage_protect.data_models.object import ObjectDeleteRequest

delete_request = ObjectDeleteRequest(
    Filespace="/postgres_bckp",
    Key="/path/to/ecommerce_db_renamed.tar.gz",
    CopyGroup=1
)

result = control_client.delete_by_name(delete_request)
```

### 6.2. Filespace Deletion (`object_management/delete_filespace.py`)

⚠️ **WARNING**: Permanently deletes entire filespace and ALL objects.

**Usage:**
```bash
python delete_filespace.py
```

**Implementation:**
```python
from ibm_storage_protect.data_models.filespace import FilespaceDeleteRequest

delete_request = FilespaceDeleteRequest(
    Filespace="/postgres_bckp"
)

result = control_client.delete_filespace(delete_request)
```

---

## 7. Best Practices

### Memory Management
- Always use generators for large files (>100MB)
- Use 4MB chunks for backup streaming
- Process restore chunks incrementally

### Compression
- Set `PreCompressed=True` for `.tar.gz` files
- Let SDK compress plain text files (SQL dumps)

### Error Handling
```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    result = client.backup(backup_req)
except TSMError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.error_code}")
```

### Logging
```python
from ibm_storage_protect.logger import configure_logging, LogConfig

configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="./logs",
    log_format="json",
    console_level="INFO"
))
```

---

## 8. Related Documentation

- [Session Models](../../docs/guides/01_session_models.md)
- [Backup Models](../../docs/guides/02_backup_models.md)
- [Query Models](../../docs/guides/03_query_models.md)
- [Restore Models](../../docs/guides/04_restore_models.md)
- [Control Management](../../docs/guides/05_control_management.md)
- [Group Operations](../../docs/guides/06_group_operations.md)
- [Logging Guide](../../docs/guides/07_logging_guide.md)

---

## 5. Piping Directly with Postgres Utilities

To optimize storage operations further, you can avoid temporary disk files by piping `pg_dump` stdout directly to the Storage Protect SDK backup request, and streaming the restore body directly back to `pg_restore` or `psql` stdin.

### 5.1. Direct Streaming Backup of `pg_dump` Output
You can create a generator that runs the `pg_dump` process and yields its stdout chunks dynamically:

```python
import subprocess
from ibm_storage_protect.data_models.backup import BackupRequest

def pg_dump_generator(dbname, username, chunk_size=4 * 1024 * 1024):
    cmd = ["pg_dump", "-Fp", "-d", dbname, "-U", username]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        process.stdout.close()
        process.wait()

# Prepare backup model
backup_data = BackupRequest(
    Key="/postgres/logical/testdb.sql",
    Body=pg_dump_generator("testdb", "postgres"),
    SizeEstimate=1024 * 1024 * 100,  # 100MB estimate
    PreCompressed=False  # Let the SDK compress plain SQL text
)
```

### 5.2. Direct Streaming Restore to `psql` Stdin
Similarly, write restored stream chunks directly into the stdin of a database restore sub-process:

```python
import subprocess
from ibm_storage_protect.data_models.restore import RestoreRequest

restore_request = RestoreRequest(Key="/postgres/logical/testdb.sql")
result = client.restore(restore_request)

# Pipe output straight to psql interpreter
cmd = ["psql", "-d", "testdb", "-U", "postgres"]
process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    for chunk in result.Body:
        process.stdin.write(chunk)
finally:
    process.stdin.close()
    process.wait()
```


---

## 9. Advanced: Direct PostgreSQL Integration

For production use, you can integrate directly with PostgreSQL utilities.

### 9.1. Streaming `pg_dump` Output

Create a generator that pipes `pg_dump` output directly to backup:

```python
import subprocess
from ibm_storage_protect.data_models.backup import BackupRequest

def pg_dump_generator(dbname, username, chunk_size=4*1024*1024):
    """Stream pg_dump output in 4MB chunks"""
    cmd = ["pg_dump", "-Fp", "-d", dbname, "-U", username]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        process.stdout.close()
        process.wait()

# Backup directly from pg_dump
backup_req = BackupRequest(
    Key="/postgres/logical/testdb.sql",
    Body=pg_dump_generator("testdb", "postgres"),
    Filespace="/postgres_bckp",
    SizeEstimate=100*1024*1024,  # 100MB estimate
    PreCompressed=False  # Let SDK compress SQL text
)

result = client.backup(backup_req)
```

### 9.2. Streaming Restore to `psql`

Pipe restored data directly to `psql` for database restoration:

```python
import subprocess
from ibm_storage_protect.data_models.restore import RestoreRequest

restore_req = RestoreRequest(
    Key="/postgres/logical/testdb.sql",
    Filespace="/postgres_bckp"
)

result = client.restore(restore_req)

# Pipe to psql
cmd = ["psql", "-d", "testdb", "-U", "postgres"]
process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    for chunk in result.body:
        process.stdin.write(chunk)
finally:
    process.stdin.close()
    process.wait()
```

---

## 10. Summary

The PostgreSQL examples demonstrate:

✅ **Backup Operations**: Single, batch, and group backups with streaming  
✅ **Restore Operations**: Full, point-in-time, and partial restores  
✅ **Query Operations**: Object discovery and metadata retrieval  
✅ **Object Management**: Rename, update, delete operations  
✅ **Memory Efficiency**: Generator-based streaming for large files  
✅ **Logging**: Comprehensive JSON logging for debugging  

For detailed API documentation, see the [guides](../../docs/guides/) directory.
