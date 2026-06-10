# PostgreSQL Restoration Examples

This directory contains comprehensive restoration examples for IBM Storage Protect, demonstrating three restoration modes (Single, Batch, Group) with three restoration types each (Full, Point-in-Time, Partial).

## Directory Structure

```
restore/
├── single/              # Single object restoration examples
│   ├── restore_full.py      # Full restoration
│   ├── restore_pit.py       # Point-in-Time restoration
│   └── restore_partial.py   # Partial (byte-range) restoration
├── batch/               # Batch restoration examples
│   ├── restore_full.py      # Full restoration for multiple files
│   ├── restore_pit.py       # Point-in-Time restoration for multiple files
│   └── restore_partial.py   # Partial restoration for multiple files
└── group/               # Group restoration examples
    ├── restore_full.py      # Full restoration for group members
    ├── restore_pit.py       # Point-in-Time restoration for group members
    └── restore_partial.py   # Partial restoration for group members
```

## Restoration Types

### 1. Full Restoration
Complete file recovery with output naming convention: `<filename>_restored.tar.gz`

**Example:**
- Input: `ecommerce_db.tar.gz`
- Output: `ecommerce_db_restored.tar.gz`

### 2. Point-in-Time (PIT) Restoration
Recovery from specific backup timestamp with output naming convention: `<filename>_TIMESTAMP_restored.tar.gz`

**Example:**
- Input: `ecommerce_db.tar.gz` (backed up 2026-05-31 22:35:04)
- Output: `ecommerce_db_20260531223504_restored.tar.gz`

### 3. Partial Restoration
Byte-range recovery with output naming convention: `<filename>_STARTBYTE_ENDBYTE_restored.tar.gz`

**Example:**
- Input: `ecommerce_db.tar.gz` (first 10 MB)
- Output: `ecommerce_db_0_10485760_restored.tar.gz`

## Backup Inventory

The examples restore from the following backed-up files:

### Single Backup
- **File:** `ecommerce_db.tar.gz`
- **Object ID:** 0-9552854
- **Backup Time:** 2026-05-31 22:35:04
- **Size:** ~100 MB

### Batch Backups (5 files)
- **Files:** `audit_db.tar.gz`, `employee_db.tar.gz`, `inventory_db.tar.gz`, `logs_db.tar.gz`, `sales_db.tar.gz`
- **Object IDs:** 0-9552861 to 0-9552865
- **Backup Time:** 2026-05-31 22:43:58
- **Size:** ~100 MB each

### Group Backups (1 leader + 5 members)
- **Leader:** `leader.json` (Object ID: 0-9552867, Backup Time: 2026-05-31 23:03:57)
- **Members:** `analytics_db.tar.gz`, `notification_db.tar.gz`, `orders_db.tar.gz`, `payment_db.tar.gz`, `users_db.tar.gz`
- **Object IDs:** 0-9552868 to 0-9552872
- **Backup Time:** 2026-05-31 23:03:57 to 23:04:02
- **Size:** ~100 MB each

## Output Directory

All restored files are saved to:
```
/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/restore_dummy_data
```

## Usage

### Running Individual Examples

```bash
# Single restoration examples
cd sp_client_sdk/examples/postgre
uv run src/protect_postgre/restore/single/restore_full.py
uv run src/protect_postgre/restore/single/restore_pit.py
uv run src/protect_postgre/restore/single/restore_partial.py

# Batch restoration examples
uv run src/protect_postgre/restore/batch/restore_full.py
uv run src/protect_postgre/restore/batch/restore_pit.py
uv run src/protect_postgre/restore/batch/restore_partial.py

# Group restoration examples
uv run src/protect_postgre/restore/group/restore_full.py
uv run src/protect_postgre/restore/group/restore_pit.py
uv run src/protect_postgre/restore/group/restore_partial.py
```

### Running All Restorations

```bash
# Run all restoration examples
cd sp_client_sdk/examples/postgre
uv run run_all_restores.py
```

## Key Features

### Single Restoration
- Restores individual objects by key
- Supports full, PIT, and partial restoration
- Memory-efficient streaming for large files

### Batch Restoration
- Restores multiple objects in optimized transactions
- Reduces API overhead for multiple files
- All files restored with same restoration type

### Group Restoration
- Restores all members of a group backup
- Maintains leader-member relationships
- Automatically handles group metadata

## Technical Details

### Filespace
All backups are stored in filespace: `/postgres_bckp`

### Object Type
All objects are of type: `API:Python-SDK`

### Compression
- `.tar.gz` files are pre-compressed
- JSON files (group leaders) are not compressed

### Progress Tracking
Each restoration script provides:
- Real-time progress updates
- Bytes written count
- Object ID information
- Last modified timestamp

### Error Handling
All scripts include comprehensive error handling:
- TSM API errors are caught and reported
- Failed restorations raise exceptions
- Detailed error messages for troubleshooting

## Notes

- Ensure IBM Storage Protect server is accessible before running examples
- Valid credentials must be configured in the environment
- Output directory is automatically created if it doesn't exist
- Partial restorations default to first 10 MB of each file
- PIT restorations use the original backup timestamps

## Related Files

- **Core Implementation:** `sp_client_sdk/src/ibm_storage_protect/c_api_bridge/wrappers/restore/`
- **Data Models:** `sp_client_sdk/src/ibm_storage_protect/data_models/restore.py`
- **Backup Examples:** `sp_client_sdk/examples/postgre/src/protect_postgre/backup/`
- **Query Examples:** `sp_client_sdk/examples/postgre/src/protect_postgre/query/`