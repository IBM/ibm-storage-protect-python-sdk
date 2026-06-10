# Filesystem Backup & Restore Guide

This guide explains how to use the IBM Storage Protect Python SDK to back up files
and directories using various strategies including single file backup, batch backup,
and group backup with parallel upload and download for maximum throughput.

---

## 1. Overview & Objectives

The IBM Storage Protect SDK provides multiple strategies for backing up filesystem data:

- **Single File Backup**: Back up individual files independently
- **Batch Backup**: Back up multiple files in a single transaction
- **Group Backup**: Back up related files as a logical unit with a leader/member model

When protecting a set of related files (application data, configuration directories,
log archives, etc.), the **group backup** feature provides:

- **Atomic commit**: All files in a directory are committed together as one group
  transaction. Either all succeed or none are visible to restore.
- **Single restore handle**: The entire set is recovered with one `SPGroupRestore`
  call that takes only the group leader object ID — no per-file bookkeeping required.
- **Leader / member model**: The first file uploaded becomes the *group leader*
  (the anchor object whose ID identifies the group). Every subsequent file is a
  *group member* linked to that leader.

The example scripts extend this foundation with **parallel transfers** using Python's
`concurrent.futures.ThreadPoolExecutor`, so large directories upload and download
significantly faster than sequential implementations.

Key SDK constraints addressed by the implementation:

- **4 MB chunk limit** [NFR-PERF-01]: The native C library's `dsmSendData` call
  cannot transmit more than 4 MB per buffer. `read_file_in_chunks()` wraps every
  file in a generator that yields at most 4 MB per iteration, keeping memory usage
  constant regardless of file size.
- **Streaming restores** [NFR-PERF-02]: `group_restore()` returns each member's
  body as a generator. `_write_member()` consumes the generator chunk-by-chunk
  and writes directly to disk without buffering the entire file in RAM.

---

## 2. Prerequisites & Configuration

### 2.1. Environment Variables

Both scripts read credentials and tuning parameters from environment variables so
that secrets are never hard-coded in source files.

| Variable | Default | Description |
|----------|---------|-------------|
| `SP_NODE` | _none_ | Registered node name |
| `SP_PASSWORD` | _none_ | Node password |
| `SP_FILESPACE` | `/` | Target / source filespace on the server |
| `SP_GROUP_NAME` | `fs-backup-<timestamp>` | Logical group tag (backup only) |
| `SP_MAX_WORKERS` | `4` | Parallel upload / download thread count |

**Windows PowerShell:**
```powershell
$env:SP_NODE     = "MY-NODE"
$env:SP_PASSWORD = "MySecurePassword"
```

**Linux / macOS:**
```bash
export SP_NODE="MY-NODE"
export SP_PASSWORD="MySecurePassword"
```

### 2.2. PYTHONPATH

Run all scripts from the repository root with both `src` directories on the path:

**Windows PowerShell:**
```powershell
$env:PYTHONPATH = "src;examples/filesystem/src"
```

**Linux / macOS:**
```bash
export PYTHONPATH="src:examples/filesystem/src"
```

### 2.3. Shared C Library

The SDK delegates all IBM Storage Protect wire-protocol operations to a platform
native shared library. Follow the [Getting Started Guide](../../../docs/guides/01_introduction.md)
to configure the library path for your platform (`IBM_SP_API_LIB` environment
variable or system linker path).

---

## 3. Backup Strategies

### 3.1. Single File Backup

Use [`backup/single.py`](../src/protect_filesystem/backup/single.py) to back up individual files:

```python
file_path = "/path/to/data/example.json"
filespace = "/filesystem_backup"

bckp = BackupRequest(
    key=file_path,
    body=read_file_in_chunks(file_path),
    filespace=filespace,
    SizeEstimate=file_size
)
client = DataClient(sess)
result = client.backup(bckp)
```

### 3.2. Batch Backup

Use [`backup/batch.py`](../src/protect_filesystem/backup/batch.py) to back up multiple files in one transaction:

```python
batch = BatchBackupRequest(
    objects=[
        BackupRequest(Key=file_path_1, Body=read_file_in_chunks(file_path_1), SizeEstimate=file_size_1),
        BackupRequest(Key=file_path_2, Body=read_file_in_chunks(file_path_2), SizeEstimate=file_size_2),
        # ... more files
    ],
    Filespace="/filesystem_backup",
    MaxPerTxn=10
)
result = client.batch_backup(batch)
```

### 3.3. Group Backup

### 3.1. How It Works

`backup_directory()` implements the following workflow:

1. **Scan**: `collect_files()` calls `Path.rglob("*")` recursively and returns a
   deterministically sorted list of every regular file under the source directory.
   Sorting ensures the same file always becomes the leader across repeated runs.

2. **Session**: A `ClientSession` is created and authenticated with `LoginCredentials`.
   Any `TSMError` at login causes an immediate exit with code 1.

3. **Group creation**: `client.create_group(group_name, filespace=SP_FILESPACE)`
   opens a `GroupHandle` — a stateful context object that tracks the leader ID
   and orchestrates the underlying C API calls.

4. **Leader upload (synchronous)**: The first file is uploaded via
   `group.add_leader(BackupRequest(...))`. This step **must** complete before members
   can be submitted because the leader's object ID becomes the group's identifier.
   If the leader upload fails, the function exits immediately.

5. **Member uploads (parallel)**: All remaining files are dispatched as independent
   tasks to a `ThreadPoolExecutor`. Each task calls `group.add_member(BackupRequest(...))`.
   The SDK's internal locking guarantees thread safety. Failures are recorded in the
   results list but do not abort other uploads.

6. **Commit**: `group.close()` flushes the transaction and makes the group visible
   to restore queries.

7. **Summary**: Leader ID (`hi`-`lo`), file count, and duration are printed and
   returned as a dictionary. **Record the Leader ID — it is required for restore.**

### 3.2. Script Execution

```bash
python src/protect_filesystem/fs_backup.py <source_directory> [group_name]
```

**Example:**
```bash
python src/protect_filesystem/fs_backup.py /var/app/data nightly-app-backup
```

If `group_name` is omitted, one is generated from the current timestamp:
```
fs-backup-20240523-014500
```

### 3.3. Key Code Snippet

```python
from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest

# 1. Authenticate
session = ClientSession()
session.login(
    LoginCredentials(
        node=os.getenv("SP_NODE"),
        password=os.getenv("SP_PASSWORD"),
    )
)
client = DataClient(session)

# 2. Create group handle
group = client.create_group("filesystem-backup-group", filespace="/filesystem_backup")

# 3. Add leader (first / anchor file)
group.add_leader(BackupRequest(
    key="config.json",
    body=read_file_in_chunks("/var/app/data/config.json"),
    size_estimate=2048,
))

# 4. Add members (remaining files)
group.add_member(BackupRequest(
    key="data/records.csv",
    body=read_file_in_chunks("/var/app/data/data/records.csv"),
    size_estimate=512000,
))

# 5. Commit
group.close()
print(f"Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")

session.logout()
```

### 3.4. Backup Key Design

`build_backup_key()` derives a POSIX relative path from each file's absolute path:

```python
def build_backup_key(file_path: Path, source_root: Path) -> str:
    return file_path.relative_to(source_root).as_posix()
```

For example, if `source_root` is `/var/app/data`:

| Absolute path | Backup key |
|---------------|------------|
| `/var/app/data/config.json` | `config.json` |
| `/var/app/data/logs/app.log` | `logs/app.log` |
| `/var/app/data/sub/a/b.bin` | `sub/a/b.bin` |

Using POSIX separators ensures keys are identical on both Windows and Linux,
making backups portable across operating systems.

### 3.5. Chunked File Reader

```python
_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB – native C API hard limit per send call

def read_file_in_chunks(filepath: str, chunk_size: int = _CHUNK_SIZE):
    with open(filepath, "rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            yield block
```

The generator is passed directly as the `body=` argument of `BackupRequest`. The SDK
feeds the C library one chunk at a time, so peak heap usage is bounded by
`chunk_size` regardless of the actual file size.

---

## 4. Restore Strategies

### 4.1. Single File Restore

Use [`restore/single/restore_full.py`](../src/protect_filesystem/restore/single/restore_full.py) for full restoration:

```python
restore_request = RestoreRequest(
    Key="/path/to/data/example.json",
    Filespace="/filesystem_backup"
)
result = client.restore(restore_request)
```

For partial restoration, use [`restore/single/restore_partial.py`](../src/protect_filesystem/restore/single/restore_partial.py).
For point-in-time restoration, use [`restore/single/restore_pit.py`](../src/protect_filesystem/restore/single/restore_pit.py).

### 4.2. Batch Restore

Use [`restore/batch/restore_full.py`](../src/protect_filesystem/restore/batch/restore_full.py) to restore multiple files:

```python
batch_request = BatchRestoreRequest(
    Objects=[
        RestoreRequest(Key=file_path, Filespace=filespace)
        for file_path in batch_files
    ],
    Filespace=filespace
)
result = client.batch_restore(batch_request)
```

### 4.3. Group Restore

### 4.1. How It Works

`restore_group()` implements the following workflow:

1. **Session**: Same authentication pattern as backup.

2. **Group restore request**: An `SPGroupRestore` model is constructed with the
   leader object ID components (`group_leader_obj_id_hi`, `group_leader_obj_id_lo`)
   and the filespace. A single `client.group_restore(group_request)` call triggers
   the SDK to query the group, retrieve the leader and all member metadata, and
   return a stream for each object's data.

3. **Parallel writes**: All member results (including the leader) are dispatched to
   a `ThreadPoolExecutor`. Each worker calls `_write_member()`, which:
   - Derives the output path as `dest_root / member.Key`.
   - Creates intermediate directories with `parents=True, exist_ok=True`.
   - Streams `member.Body` chunk-by-chunk to an open binary file handle.

4. **Summary**: Total bytes written, success / failure counts, and duration are
   printed and returned.

### 4.2. Script Execution

```bash
python src/protect_filesystem/fs_restore.py <leader_hi> <leader_lo> <dest_directory>
```

The `leader_hi` and `leader_lo` values are the two integers printed in the backup
summary line `Leader ID : <hi>-<lo>`.

**Example** (restoring the backup from Section 3.2):
```bash
python src/protect_filesystem/fs_restore.py 0 9011210 /var/app/restored
```

### 4.3. Key Code Snippet

```python
from ibm_storage_protect.data_models.restore import SPGroupRestore

# Build restore request using the leader object ID from the backup summary
group_request = SPGroupRestore(
    filespace="/",
    group_leader_obj_id_hi=0,
    group_leader_obj_id_lo=9011210,
)

# Execute — returns all members including the leader
group_result = client.group_restore(group_request)

# Stream each member to disk
from pathlib import Path
dest_root = Path("/var/app/restored")
for member in group_result.results:
    role = "LEADER" if member.IsGroupLeader else "MEMBER"
    dest_path = dest_root / member.Key
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as fh:
        for chunk in member.Body:   # generator – streams in SDK-sized buffers
            fh.write(chunk)
    print(f"  [{role}] {member.Key}")
```

### 4.4. Directory Tree Reconstruction

The restore script writes each member to `dest_root / member.Key`. Because backup
keys are relative POSIX paths (see Section 3.4), the original directory structure
is fully recreated under `dest_root`:

```
/var/app/restored/
  config.json
  data/
    records.csv
  logs/
    app.log
```

`Path.mkdir(parents=True, exist_ok=True)` creates all intermediate directories
automatically, so no pre-creation of the destination tree is required.

---

## 5. Parallelism Model

### 5.1. Why Leaders Must Be Uploaded First

The IBM Storage Protect group API assigns the leader's object ID as the group
identifier at the moment `add_leader()` is called. All subsequent `add_member()`
calls reference this ID internally. Therefore:

- The leader upload is always **synchronous** and **sequential**.
- Members can be submitted **in any order** and **concurrently** after the leader
  is established.

### 5.2. Thread Pool Sizing

```python
SP_MAX_WORKERS = int(os.getenv("SP_MAX_WORKERS", "4"))
```

`ThreadPoolExecutor(max_workers=SP_MAX_WORKERS)` creates a fixed-size pool.

**Tuning guidance:**

| Scenario | Suggested workers |
|----------|------------------|
| Spinning-disk source, 1 Gbps LAN | 2–4 |
| SSD source, 10 Gbps LAN | 4–8 |
| Network is the bottleneck (< 100 Mbps) | 1–2 |
| Many small files (< 1 MB each) | 8–16 |

Setting workers above the available CPU cores or network bandwidth will not
improve throughput and may introduce contention.

### 5.3. Thread Safety

The SDK's `GroupHandle.add_member()` acquires an internal lock before delegating
to the C API layer, making concurrent calls safe. Each `_upload_member()` call
also creates its own file handle and `BackupRequest` instance, so there is no shared
mutable state between threads.

---

## 6. Error Handling

### 6.1. Authentication Failures

Both scripts catch `TSMError` at login and exit with code 1:

```python
try:
    session.login(LoginCredentials(node=SP_NODE, password=SP_PASSWORD))
except TSMError as exc:
    print(f"✗ Authentication failed: {exc.message}")
    sys.exit(1)
```

Check `SP_NODE`, `SP_PASSWORD`, and that the node is registered and not locked
on the server (error code `TSM-2101` / `TSM-2103`).

### 6.2. Leader Upload Failure

If the leader upload fails, the backup cannot continue — there is no leader ID
to associate members with. The script logs the error and exits immediately:

```python
if not leader_result[1]:
    print(f"  ✗ Leader upload failed: {leader_result[2]}")
    session.logout()
    sys.exit(1)
```

### 6.3. Member Upload Failures

Individual member failures are **non-fatal**. `_upload_member()` catches all
exceptions and returns a `(key, False, error_message)` tuple. The summary
reports `failed` > 0 but the group is still closed and partially committed.

To identify which members failed, inspect the console output for lines prefixed
with `✗ [MEMBER]`.

### 6.4. Group Restore Failures

A `TSMError` from `client.group_restore()` causes an immediate exit. Common
causes:

| Error code | Cause |
|------------|-------|
| `TSM-4101` | Leader object ID not found — wrong `hi`/`lo` values |
| `TSM-4110` | Filespace mismatch — `SP_FILESPACE` differs from backup |
| `TSM-1101` | Network error during restore stream |

### 6.5. Partial Restore Failures

If a member's `Body` generator raises during disk write (e.g., disk full), only
that member is counted as failed. All other members complete normally. Re-run the
restore script; it will overwrite already-written files safely since it uses `"wb"`.

---

## 7. Advanced Patterns

### 7.1. Restoring a Subset of Files

To restore only specific members, filter `group_result.results` before writing:

```python
group_result = client.group_restore(group_request)

# Restore only files under the "logs/" prefix
for member in group_result.results:
    if member.Key.startswith("logs/"):
        dest_path = dest_root / member.Key
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as fh:
            for chunk in member.Body:
                fh.write(chunk)
```

> **Note:** Even when restoring a subset you must still consume or discard
> the `Body` generator for *every* member returned by `group_restore()` to
> allow the SDK to release its internal buffers correctly.

### 7.2. Incremental Backup (Re-opening a Group)

After a group is closed and its leader ID recorded, you can add more members
in a later session using `reopen()`:

```python
# Load group from previously persisted metadata
group = client.load_group(".sp_groups.json", "nightly-app-backup")

# Reopen the existing group transaction
group.reopen()

# Add newly created or changed files
group.add_member(BackupRequest(
    key="data/new_records.csv",
    body=read_file_in_chunks("/var/app/data/data/new_records.csv"),
    size_estimate=204800,
))

group.close()
```

### 7.3. Programmatic Integration (Library Mode)

Both scripts expose their core logic as importable functions, so they can be
embedded in larger orchestration workflows:

```python
from protect_filesystem.fs_backup import backup_directory
from protect_filesystem.fs_restore import restore_group

# Backup returns a summary dict
summary = backup_directory("/var/app/data", group_name="ci-build-42")
leader_hi = summary["leader_id"].get("hi", 0)
leader_lo = summary["leader_id"].get("lo", 0)

# … time passes, data is needed …

# Restore using the persisted leader ID
restore_summary = restore_group(leader_hi, leader_lo, "/var/app/recovered")
print(f"Restored {restore_summary['total_objects']} objects, "
      f"{restore_summary['total_bytes']:,} bytes total.")
```

### 7.4. Querying a Group After Backup

To inspect group membership without performing a restore, use `QueryClient`:

```python
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.data_models.query import GroupQueryRequest

query_client = QueryClient(session)

group_query = GroupQueryRequest(
    Filespace="/",
    GroupLeaderObjIdHi=str(leader_hi),
    GroupLeaderObjIdLo=str(leader_lo),
)

result = query_client.query_group_members(group_query)
print(f"Group contains {result.total_objects} object(s):")
for obj in result.objects:
    role = "LEADER" if obj.IsGroupLeader else "MEMBER"
    print(f"  [{role}] {obj.Key}")
```

---

## 8. Design Notes

### 8.1. Why Sort Files Before Backup?

`collect_files()` sorts results with Python's default lexicographic ordering.
This ensures:
- The **same file always becomes the leader** across multiple runs of the same
  directory, making behaviour predictable.
- **Backup keys are stable**: identical directory contents always produce the
  same key-to-file mapping.

### 8.2. POSIX Keys on Windows

`Path.relative_to(...).as_posix()` forces forward slashes on all platforms.
This is intentional: IBM Storage Protect stores and retrieves keys as opaque
strings, and POSIX separators make cross-platform restores unambiguous.

### 8.3. Leader ID Persistence

After `group.close()`, `group.leader_id` is a dict `{"hi": int, "lo": int}`.
Persist these two integers to restore the group in future sessions. The
simplest storage is a plain text or JSON file alongside your backup manifest:

```json
{
  "group_name": "nightly-app-backup",
  "leader_hi": 0,
  "leader_lo": 9011210,
  "backed_up_at": "2024-05-23T01:45:00Z"
}
```

### 8.4. Memory Budget

With default settings (`SP_MAX_WORKERS=4`, `chunk_size=4 MiB`):

- **Backup**: Peak heap ≈ `4 workers × 4 MiB = 16 MiB` for in-flight chunks,
  plus Python object overhead. File content is never fully loaded into RAM.
- **Restore**: Peak heap ≈ `4 workers × (SDK buffer size)` for in-flight
  restore buffers. Actual buffer size is controlled server-side (typically 1 MiB).

---

## 9. SDK API Quick Reference

| SDK symbol | Module | Purpose |
|-----------|--------|---------|
| `ClientSession` | `session` | Manages login / logout lifecycle |
| `LoginCredentials` | `data_models.session` | Authentication credential model |
| `DataClient` | `data_client.client` | Unified backup + restore facade |
| `GroupHandle` | `data_client.backup` | Stateful group transaction context |
| `BackupRequest` | `data_models.backup` | Single-object backup request |
| `SPGroupRestore` | `data_models.restore` | Group restore request by leader ID |
| `SPGroupRestoreResult` | `data_models.restore` | Group restore result (leader + members) |
| `QueryClient` | `query` | Group / object query interface |
| `GroupQueryRequest` | `data_models.query` | Group membership query model |
| `TSMError` | `errors.exceptions` | Base SDK exception class |
| `SDKErrorCode` | `errors.error_codes` | Enumeration of all error codes |

For full API documentation, see the [SDK reference](../../../docs/).
