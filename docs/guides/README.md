# IBM Storage Protect SDK - Data Design Documentation

## Overview

This directory contains comprehensive data design specifications for the IBM Storage Protect Python SDK. The documentation is organized by functional area to provide clear reference for API consumers and implementers.

## Document Structure

### Core Documentation

- **[01_session_models.md](01_session_models.md)** - Session management and authentication models
- **[02_backup_models.md](02_backup_models.md)** - Backup operation models including single, batch, and group operations
- **[03_query_models.md](03_query_models.md)** - Query and search operation models
- **[04_restore_models.md](04_restore_models.md)** - Restore operation models
- **[05_control_management.md](05_control_management.md)** - Filespace and object management operations (register, update, delete, rename)
- **[06_group_operations.md](06_group_operations.md)** - Detailed group backup operations with real-world examples
- **[07_logging_guide.md](07_logging_guide.md)** - Comprehensive logging configuration and usage guide

### Quick Reference

- **[api_summary.md](api_summary.md)** - Quick reference table of all public API models

## Design Principles

### 1. Type Safety
All models use Pydantic for automatic validation and type checking at runtime.

### 2. Clear API Boundaries
- Public models are defined in `data_models` package
- Internal models use `_` prefix (e.g., `_BackupInternal`)
- Users should only interact with public models

### 3. Flexible Field Naming
Models support both PascalCase and snake_case field names through aliases:
```python
# Both work identically
backup = BackupRequest(Key="/path", Body=data)
backup = BackupRequest(key="/path", body=data)
```

### 4. Comprehensive Validation
- Required fields are enforced
- Optional fields have sensible defaults
- Constraints are validated (e.g., port ranges, minimum values)

### 5. Documentation
Each model includes:
- Purpose and usage context
- Field descriptions
- Type information
- Constraints and validation rules
- Code examples

## Logging

The SDK includes a comprehensive logging system that captures all operations, errors, and C API interactions. **Logging must be explicitly configured** to see detailed logs and write to files.

### Quick Start

```python
from ibm_storage_protect.logger import configure_logging, LogConfig

# Configure logging at application startup
config = LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    user_log_file="myapp_user.log",      # Custom log file names
    debug_log_file="myapp_debug.log",
    error_log_file="myapp_error.log",
    log_dir="./logs",
    log_format="text",                   # "text" or "json"
    console_level="INFO"
)
configure_logging(config)
```

### What Gets Logged

- ✅ All session operations (login, logout, password changes)
- ✅ Backup/restore operations with performance metrics
- ✅ Query operations and results
- ✅ SDK error codes (TSM-xxxx) with full context
- ✅ C API error messages (ANS1073E, etc.)
- ✅ Internal diagnostics for troubleshooting

### Log Files Created

```
./logs/
├── myapp_user.log       # Main operational log (INFO+)
├── myapp_debug.log      # Detailed diagnostics (DEBUG+)
└── myapp_error.log      # Error-only log (ERROR+)
```

### Documentation

For complete logging documentation, see:
- **[07_logging_guide.md](07_logging_guide.md)** - Quick start, configuration, and examples

## Usage Patterns

### Basic Workflow
```python
from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.logger import configure_logging

# Configure logging first (recommended)
configure_logging()

# 1. Establish session
session = ClientSession()
credentials = LoginCredentials(
    node=os.getenv("SP_NODE"),
    password=os.getenv("SP_PASSWORD"),
)
session.login(credentials)

# 2. Create client
client = DataClient(session)

# 3. Perform operations
backup = BackupRequest(key="/data/file.txt", body=b"content")
result = client.backup(backup)

# 4. Cleanup
session.logout()
```

### Group Operations Workflow
```python
from ibm_storage_protect.data_client.backup.group import GroupBackupClient
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.data_models.query import GroupQueryRequest

# Create group with automatic leader assignment
group_client = GroupBackupClient(session)
group = group_client.create_group("my-group")
group.add_member(BackupRequest(key="/data/file1.txt", body=b"content1"))
group.add_member(BackupRequest(key="/data/file2.txt", body=b"content2"))
group.close()

print(f"Group created: {group.name}")
print(f"Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")

# Reopen and modify existing group
group_loaded = group_client.load_group(".sp_groups.json", "my-group")
group_loaded.reopen()
group_loaded.add_member(BackupRequest(key="/data/file3.txt", body=b"content3"))
group_loaded.close()

# Query group contents
query_client = QueryClient(session)
query = GroupQueryRequest(
    filespace="/",
    group_leader_obj_id_hi=group.leader_id['hi'],
    group_leader_obj_id_lo=group.leader_id['lo']
)
result = query_client.query_group(query)
print(f"Total objects in group: {result.total_objects}")
```

## Model Categories

### Input Models
Models used to specify operation parameters:
- `LoginCredentials` - Authentication credentials
- `BackupRequest` - Single backup specification
- `BatchBackupRequest` - Multiple backup specification
- `GroupQueryRequest` - Group query parameters
- `RestoreRequest` - Restore specification

### Output Models
Models returned by operations:
- `SessionDetails` - Active session information
- `BackupResult` - Backup operation result
- `GroupBackupResult` - Group backup result
- `BackupQueryResult` - Query operation result
- `RestoreResult` - Restore operation result

### Metadata Models
Models containing detailed information:
- `SessionInfo` - Detailed session configuration
- `ObjectMetadata` - Complete object metadata
- `BackupStats` - Detailed backup statistics

## Internal Models (Not for Direct Use)

The following models are internal implementation details:
- `_BackupInternal` - Low-level C API parameters
- `_GroupBackupInternal` - Internal group operations
- `_QueryInternal` - Internal query parameters

These models are marked with underscore prefix and should not be used directly by SDK consumers.

## Validation Rules

### Common Constraints
- **Filespace**: Cannot be empty, defaults to "/"
- **Key**: Cannot be empty for object operations
- **Port numbers**: Must be between 1-65535
- **Object IDs**: Must be non-negative integers
- **Counts**: Must be non-negative (>= 0)
- **Body size**: Maximum 4MB per chunk (4,194,304 bytes)

### Field Requirements
- **Required**: Must be provided, no default value
- **Optional**: Has default value or can be None
- **Conditional**: Required based on other field values

## Version Compatibility

This documentation reflects SDK version 0.1.0 and is compatible with:
- IBM Storage Protect Server 8.1.x and later
- Python 3.8 and later
- Pydantic 2.x

## Contributing

When adding new models:
1. Follow existing naming conventions
2. Add comprehensive field documentation
3. Include usage examples
4. Update relevant documentation files
5. Add validation rules where appropriate

## Support

For questions or issues:
- Review the specific model documentation
- Check the examples in `/examples` directory
- Refer to the main SDK documentation
- Contact the development team

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0  
**Documentation Version**: 1.0