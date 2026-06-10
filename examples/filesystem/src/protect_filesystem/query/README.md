# PostgreSQL Backup Query Scripts

This directory contains query scripts to discover and retrieve metadata for backed up PostgreSQL database files.

## Overview

These scripts demonstrate how to query different types of backups created by the backup scripts:

1. **Single Backup** - Query individual database file
2. **Batch Backup** - Query multiple database files backed up together
3. **Group Backup** - Query group leader and member files
4. **List All** - Overview of all backups in the filespace

## Scripts

### 1. single.py - Query Single Backup

Queries the `ecommerce_db.tar.gz` file that was backed up individually.

**Usage:**
```bash
python single.py
```

**What it does:**
- Queries a specific backup object by key and filespace
- Displays complete metadata including size, dates, compression status
- Shows object ID for restore operations

**Example Output:**
```
Found 1 backup(s)
Object Key: /path/to/ecommerce_db.tar.gz
Object ID: 12345-67890
Size: 10,485,760 bytes (10.00 MB)
Backup Date: 2026-06-01 02:15:30
Compressed: True
```

---

### 2. batch.py - Query Batch Backups

Queries the 5 database files backed up in a batch operation:
- audit_db.tar.gz
- employee_db.tar.gz
- inventory_db.tar.gz
- logs_db.tar.gz
- sales_db.tar.gz

**Usage:**
```bash
python batch.py
```

**What it does:**
- **Method 1**: Queries each file individually by exact key
- **Method 2**: Lists all objects using prefix filter (more efficient)
- Displays summary statistics for all batch files

**Example Output:**
```
METHOD 1: Query Each File Individually
Querying: audit_db.tar.gz
  ✓ Found
    Size: 5,242,880 bytes (5.00 MB)
    Backup Date: 2026-06-01 02:20:15

Summary: Found 5/5 files
Total Size: 26,214,400 bytes (25.00 MB)
```

---

### 3. group.py - Query Group Backup

Queries the group backup containing a leader (leader.json) and multiple member files (.tar.gz).

**Usage:**
```bash
python group.py
```

**What it does:**
- **Step 1**: Queries the leader object to get its Object ID
- **Step 2**: Uses the leader ID to query all group members
- **Step 3**: Alternative method using prefix filter
- Categorizes objects as leaders, members, or standalone

**Example Output:**
```
STEP 1: Query Leader Object
✓ Leader found
  Object ID: 12345-67890
  Is Group Leader: True

STEP 2: Query Group Members
✓ Group query successful
  Total members (including leader): 6

  Members (5):
  1. database1.tar.gz
     Size: 10,485,760 bytes (10.00 MB)
     Group Leader ID: 12345-67890
```

---

### 4. list_all.py - List All Backups

Provides a comprehensive overview of all backups in the `/postgres_bckp` filespace.

**Usage:**
```bash
python list_all.py
```

**What it does:**
- Displays filespace information (capacity, usage, last backup)
- Lists all active backup objects
- Categorizes backups by type (single, batch, group leader, group member)
- Shows summary statistics

**Example Output:**
```
STEP 1: Filespace Information
✓ Filespace: /postgres_bckp
  Used Space: 52,428,800 bytes
  Usage: 5.00%

STEP 2: All Backed Up Objects
✓ Found 11 active backup(s)

SINGLE BACKUPS (1)
• ecommerce_db.tar.gz
  Size: 10,485,760 bytes (10.00 MB)

BATCH BACKUPS (5)
• audit_db.tar.gz
  Size: 5,242,880 bytes (5.00 MB)

GROUP LEADERS (1)
• leader.json
  Is Group Leader: True

GROUP MEMBERS (4)
• database1.tar.gz
  Group Leader ID: 12345-67890

SUMMARY
Total Objects: 11
Total Storage Used: 52,428,800 bytes (50.00 MB)
```

---

## Query Models Used

All scripts use the IBM Storage Protect SDK query models:

### BackupQueryRequest
Query specific objects by key:
```python
from ibm_storage_protect.data_models.query import BackupQueryRequest

query = BackupQueryRequest(
    Key="/path/to/file.tar.gz",
    Filespace="/postgres_bckp",
    ObjState=ObjState.ACTIVE,
    ObjType=ObjType.FILE
)
results = query_client.query_object(query)
```

### ListObjectsRequest
List objects with optional prefix filtering:
```python
from ibm_storage_protect.data_models.query import ListObjectsRequest

query = ListObjectsRequest(
    Filespace="/postgres_bckp",
    Prefix="/path/to/directory/",
    MaxResults=100
)
results = query_client.list_objects(query)
```

### GroupQueryRequest
Query group members by leader ID:
```python
from ibm_storage_protect.data_models.query import GroupQueryRequest

query = GroupQueryRequest(
    GroupLeaderObjIdHi=12345,
    GroupLeaderObjIdLo=67890,
    Filespace="/postgres_bckp",
    IncludeLeader=True
)
results = query_client.query_group_members(query)
```

### ListFilespacesRequest
List all filespaces:
```python
from ibm_storage_protect.data_models.query import ListFilespacesRequest

query = ListFilespacesRequest(MaxResults=100)
results = query_client.query_filespaces(query)
```

---

## Object Metadata

Each query returns `ObjectMetadata` with the following information:

- **key**: Object path
- **filespace**: Filespace name
- **obj_id_hi/obj_id_lo**: Object ID (needed for restore)
- **obj_state**: ACTIVE or INACTIVE
- **obj_type**: FILE or DIRECTORY
- **size**: Size in bytes
- **backup_date**: When backed up
- **expiration_date**: When it expires
- **compressed**: Compression status
- **deduplicated**: Deduplication status
- **encrypted**: Encryption status
- **is_group_leader**: Is this a group leader?
- **group_leader_obj_id**: Leader ID if group member
- **management_class**: Storage policy
- **media**: Storage media type
- **repository**: Storage repository

---

## Prerequisites

1. IBM Storage Protect SDK installed
2. Valid TSM credentials configured
3. Backups must exist (run backup scripts first)

## Configuration

All scripts use the default credentials from `LoginCredentials()`. Ensure your TSM configuration is set up correctly:

```python
from ibm_storage_protect.data_models.session import LoginCredentials

# Uses default configuration
creds = LoginCredentials()

# Or specify explicitly
creds = LoginCredentials(
    node="YOUR_NODE",
    password="YOUR_PASSWORD",
    server="YOUR_SERVER"
)
```

---

## Common Query Patterns

### Query by Exact Path
```python
query = BackupQueryRequest(
    Key="/exact/path/to/file.tar.gz",
    Filespace="/postgres_bckp"
)
```

### Query with Prefix Filter
```python
query = ListObjectsRequest(
    Filespace="/postgres_bckp",
    Prefix="/path/to/directory/"
)
```

### Query Historical State (Point-in-Time)
```python
query = BackupQueryRequest(
    Key="/path/to/file.tar.gz",
    Filespace="/postgres_bckp",
    PitDate="2026-01-01 00:00:00"
)
```

### Query Inactive Objects
```python
query = ListObjectsRequest(
    Filespace="/postgres_bckp",
    ObjState=ObjState.INACTIVE
)
```

---

## Error Handling

All scripts include error handling:

```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    results = query_client.query_backup(query)
    if results.total_count == 0:
        print("Object not found")
except TSMError as e:
    print(f"Query failed: {e}")
```

---

## Performance Tips

1. **Use specific queries** when you know the exact path (faster)
2. **Use prefix filtering** to narrow down results
3. **Limit MaxResults** to avoid memory issues with large result sets
4. **Query groups efficiently** by getting leader ID first

---

## Related Documentation

- [Query Models Guide](../../../docs/guides/03_query_models.md)
- [Backup Scripts](../backup/)
- [Restore Scripts](../restore/)

---

## Support

For issues or questions, refer to the main SDK documentation or contact support.