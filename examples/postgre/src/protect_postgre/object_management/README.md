# Object Management Examples for PostgreSQL Backups

This directory contains examples demonstrating object management operations on backed-up PostgreSQL database files in IBM Storage Protect.

## Overview

Object management operations manipulate backed-up objects without transferring data content. These operations include renaming, updating attributes, and deleting objects.

## Prerequisites

Before running these examples, you must first run the backup examples to create objects:
- `../backup/single.py` - Creates a single backed-up object
- `../backup/group.py` - Creates group-backed-up objects (leader + members)
- `../backup/batch.py` - Creates batch-backed-up objects

## Examples

### 1. Single Object Management (`single.py`)

Demonstrates object management on a single backed-up PostgreSQL database file.

**Operations:**
- Rename object (change object path)
- Update object attributes (owner, management class)
- Delete object by name

**Usage:**
```bash
cd sp_client_sdk/examples/postgre/src/protect_postgre/object_management
python single.py
```

**Expected Output:**
```
============================================================
SINGLE OBJECT MANAGEMENT OPERATIONS
============================================================

------------------------------------------------------------
OPERATION 1: RENAME OBJECT
------------------------------------------------------------
Original key: /home/.../ecommerce_db.tar.gz
New key: /home/.../ecommerce_db_renamed.tar.gz

✓ Rename Status: success
  Filespace: /postgres_bckp
  Old Key: /home/.../ecommerce_db.tar.gz
  New Key: /home/.../ecommerce_db_renamed.tar.gz

------------------------------------------------------------
OPERATION 2: UPDATE OBJECT ATTRIBUTES
------------------------------------------------------------
Updating object: /home/.../ecommerce_db_renamed.tar.gz
Setting owner: postgres_admin
Setting management class: STANDARD

✓ Update Status: success
  Filespace: /postgres_bckp
  Key: /home/.../ecommerce_db_renamed.tar.gz

------------------------------------------------------------
OPERATION 3: DELETE OBJECT
------------------------------------------------------------
Deleting object: /home/.../ecommerce_db_renamed.tar.gz
From filespace: /postgres_bckp

✓ Delete Status: success
  Filespace: /postgres_bckp
  Key: /home/.../ecommerce_db_renamed.tar.gz

============================================================
OBJECT MANAGEMENT COMPLETED SUCCESSFULLY
============================================================
```

---

### 2. Group Object Management (`group.py`)

Demonstrates object management on group-backed-up PostgreSQL database files.

**Operations:**
- Query group objects to get their IDs
- Rename leader object
- Update attributes on member objects
- Delete leader by ID
- Delete all member objects by ID

**Usage:**
```bash
python group.py
```

**Expected Output:**
```
============================================================
GROUP OBJECT MANAGEMENT OPERATIONS
============================================================

------------------------------------------------------------
STEP 1: QUERYING GROUP OBJECTS
------------------------------------------------------------

Querying leader object: /home/.../leader.json
✓ Found leader object:
  Object ID: 12345-67890
  Key: /home/.../leader.json

Querying all objects in filespace: /postgres_bckp
✓ Found 11 total objects in filespace
✓ Identified 10 member objects
  1. analytics_db.tar.gz (ID: 12346-67891)
  2. notification_db.tar.gz (ID: 12347-67892)
  3. orders_db.tar.gz (ID: 12348-67893)
  ... and 7 more

------------------------------------------------------------
OPERATION 1: RENAME LEADER OBJECT
------------------------------------------------------------
✓ Rename Status: success

------------------------------------------------------------
OPERATION 2: UPDATE MEMBER OBJECT ATTRIBUTES
------------------------------------------------------------
✓ Updated 10/10 member objects

------------------------------------------------------------
OPERATION 3: DELETE LEADER OBJECT BY ID
------------------------------------------------------------
✓ Delete Status: success

------------------------------------------------------------
OPERATION 4: DELETE ALL MEMBER OBJECTS BY ID
------------------------------------------------------------
✓ Deleted 10/10 member objects

============================================================
GROUP OBJECT MANAGEMENT COMPLETED SUCCESSFULLY
============================================================
```

---

### 3. Batch Object Management (`batch.py`)

Demonstrates object management on batch-backed-up PostgreSQL database files.

**Operations:**
- Query batch objects to get their IDs
- Rename selected objects
- Update attributes on all objects
- Delete all batch objects by ID

**Usage:**
```bash
python batch.py
```

**Expected Output:**
```
============================================================
BATCH OBJECT MANAGEMENT OPERATIONS
============================================================

------------------------------------------------------------
STEP 1: QUERYING BATCH OBJECTS
------------------------------------------------------------
Querying 5 batch objects...
  ✓ Found: audit_db.tar.gz
    ID: 12350-67895
  ✓ Found: employee_db.tar.gz
    ID: 12351-67896
  ✓ Found: inventory_db.tar.gz
    ID: 12352-67897
  ✓ Found: logs_db.tar.gz
    ID: 12353-67898
  ✓ Found: sales_db.tar.gz
    ID: 12354-67899

✓ Successfully queried 5/5 objects

------------------------------------------------------------
OPERATION 1: RENAME SELECTED OBJECTS
------------------------------------------------------------
✓ Renamed 2/2 objects

------------------------------------------------------------
OPERATION 2: UPDATE ALL OBJECT ATTRIBUTES
------------------------------------------------------------
✓ Updated 5/5 objects

------------------------------------------------------------
OPERATION 3: DELETE ALL BATCH OBJECTS BY ID
------------------------------------------------------------
✓ Deleted 5/5 objects

============================================================
BATCH OBJECT MANAGEMENT COMPLETED SUCCESSFULLY
============================================================
```

---

### 4. Filespace Deletion (`delete_filespace.py`)

Deletes the entire PostgreSQL backup filespace and ALL objects within it.

**⚠️ WARNING:** This operation is **IRREVERSIBLE** and deletes **ALL objects** within the filespace from **all repositories** (backup and archive).

**Operations:**
- Query remaining objects in filespace
- Delete entire filespace and all objects
- Verify deletion

**Usage:**
```bash
python delete_filespace.py
```

**Interactive Prompt:**
```
============================================================
FILESPACE DELETION SCRIPT
============================================================

This script will PERMANENTLY DELETE the filespace:
  /postgres_bckp

And ALL objects within it, including:
  - Single backup objects
  - Group backup objects (leader and members)
  - Batch backup objects

⚠️  THIS OPERATION CANNOT BE UNDONE!
============================================================

Type 'DELETE' to confirm deletion: DELETE

Proceeding with deletion...
```

**Expected Output:**
```
============================================================
FILESPACE DELETION OPERATION
============================================================

⚠️  WARNING: This will delete the ENTIRE filespace and
   ALL objects within it. This operation is IRREVERSIBLE!
============================================================

------------------------------------------------------------
STEP 1: CHECKING FILESPACE CONTENTS
------------------------------------------------------------
Querying objects in filespace: /postgres_bckp

⚠️  Found 16 objects in filespace:
  1. ecommerce_db.tar.gz
     ID: 12345-67890
     Size: 10485760 bytes
  ... and 15 more objects

⚠️  All 16 objects will be PERMANENTLY DELETED!

------------------------------------------------------------
STEP 2: DELETING FILESPACE
------------------------------------------------------------

Deleting filespace: /postgres_bckp
This will remove:
  - The filespace itself
  - ALL objects within the filespace
  - ALL backup copies
  - ALL archive copies

Executing deletion...

✓ Deletion Status: success
  Filespace: /postgres_bckp

------------------------------------------------------------
STEP 3: VERIFYING DELETION
------------------------------------------------------------
✓ Verification successful: No objects remain in filespace

============================================================
FILESPACE DELETION COMPLETED SUCCESSFULLY
============================================================
Deleted filespace: /postgres_bckp
All objects and metadata have been permanently removed.
============================================================
```

---

## Execution Order

For a complete demonstration of object management operations:

1. **Run Backups** (create objects):
   ```bash
   cd ../backup
   python single.py
   python group.py
   python batch.py
   ```

2. **Run Object Management** (manipulate objects):
   ```bash
   cd ../object_management
   python single.py
   python group.py
   python batch.py
   ```

3. **Final Cleanup** (delete filespace):
   ```bash
   python delete_filespace.py
   ```

## Key Concepts

### Object Deletion Methods

1. **Delete by Name** (`delete_by_name`):
   - Uses filespace and key path
   - Suitable when object path is known
   - Example: Delete `/postgres_bckp/database.tar.gz`

2. **Delete by ID** (`delete_by_id`):
   - Uses object ID (high and low parts)
   - More efficient when ID is known
   - Requires querying object first to get ID

### Object Attributes

Objects can have the following attributes updated:
- **Owner**: Object owner identifier
- **Management Class**: Storage policy class

### Filespace Operations

- **Register**: Create new filespace (idempotent)
- **Update**: Modify filespace attributes
- **Delete**: Remove filespace and ALL objects (irreversible)

## Error Handling

All examples include comprehensive error handling:

```python
try:
    result = control_client.delete_by_name(delete_request)
    if result.status != "success":
        print(f"Warning: {result.status}")
except TSMError as e:
    print(f"Error: {e}")
    print(f"Error code: {e.error_code}")
```

## Best Practices

1. **Always Query First**: Get object IDs before deletion
2. **Verify Operations**: Check status of each operation
3. **Use Transactions**: Operations are automatically wrapped in transactions
4. **Handle Errors**: Implement proper error handling
5. **Confirm Deletions**: Use interactive prompts for destructive operations

## Related Documentation

- [Control Management Guide](../../../docs/guides/05_control_management.md)
- [Query Examples](../query/README.md)
- [Backup Examples](../backup/README.md)

## Notes

- All operations require an active session with valid credentials
- Object management operations do not transfer data content
- Deletion operations are irreversible - use with caution
- The filespace `/postgres_bckp` is used consistently across all examples