# Logging Guide

## Overview

The IBM Storage Protect Python SDK includes a comprehensive logging system that captures all operations, errors, and C API interactions. This guide provides configuration and usage documentation for the logging system implemented in [`logger/`](../../src/ibm_storage_protect/logger/).

---

## Quick Start

### Enable Logging in Your Application

```python
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger

# Configure logging at application startup
configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="./logs",
    log_format="text",
    console_level="INFO"
))

# Get a logger for your application (optional)
logger = get_logger('my_app')
logger.info("Application started")
```

### What You Get

After configuration, the SDK automatically logs:
- ✅ Session operations (login, logout, password changes)
- ✅ Backup/restore operations with metrics
- ✅ Query operations and results
- ✅ All errors with SDK error codes (TSM-xxxx)
- ✅ C API error messages (ANS1073E, etc.)
- ✅ Performance metrics and timing

### Log Files Created

**Default file names:**
```
./logs/
├── ibm_sp_user.log          # Main operational log (INFO+)
├── ibm_sp_error.log         # Error-only log (ERROR+)
├── ibm_sp_debug.log         # Detailed diagnostics (DEBUG+, if enabled)
└── ibm_sp_internal_api.log  # C API calls (DEBUG+, if enabled)
```

**Custom file names:**
```
./logs/
├── myapp_user.log           # Custom user log
├── myapp_error.log          # Custom error log
├── myapp_debug.log          # Custom debug log
└── myapp_api.log            # Custom internal API log
```

**With rotation:**
```
./logs/
├── myapp_user.log           # Current log
├── myapp_user.log.1         # Previous backup
├── myapp_user.log.2         # Older backup
└── myapp_user.log.3         # Oldest backup
```

---

## Core Concepts

### Logger Hierarchy

The SDK uses a hierarchical logger structure:

```
ibm_storage_protect                    # Root logger
├── ibm_storage_protect.session        # Session operations
├── ibm_storage_protect.data_client    # Backup/restore operations
├── ibm_storage_protect.query          # Query operations
├── ibm_storage_protect.control        # Control operations
├── ibm_storage_protect.errors         # Error handling
│   └── ibm_storage_protect.errors.mapper  # C API error mapping
└── ibm_storage_protect.c_api_bridge   # Low-level C API calls
```

### Log Levels

| Level | Purpose | When to Use |
|-------|---------|-------------|
| **DEBUG** | Detailed diagnostics | Development, troubleshooting C API issues |
| **INFO** | Normal operations | Production monitoring, operation tracking |
| **WARNING** | Recoverable issues | Retryable errors, degraded performance |
| **ERROR** | Operation failures | Non-retryable errors, authentication failures |
| **CRITICAL** | System failures | Unrecoverable errors, data corruption |

**Recommendation**: Use `INFO` for production, `DEBUG` for development.

---

## Configuration Options

### LogConfig Class

**Location**: [`logger/config.py`](../../src/ibm_storage_protect/logger/config.py:17)

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_user_log` | `bool` | `True` | Enable main operational log |
| `enable_debug_log` | `bool` | `False` | Enable detailed diagnostics log |
| `enable_error_log` | `bool` | `True` | Enable error-only log |
| `enable_internal_api_log` | `bool` | `False` | Enable C API boundary log |
| `user_log_file` | `str` | `"ibm_sp_user.log"` | User log filename |
| `debug_log_file` | `str` | `"ibm_sp_debug.log"` | Debug log filename |
| `error_log_file` | `str` | `"ibm_sp_error.log"` | Error log filename |
| `internal_api_log_file` | `str` | `"ibm_sp_internal_api.log"` | Internal API log filename |
| `log_dir` | `str` | `"logs"` | Log directory path |
| `max_bytes` | `int` | `10485760` (10MB) | Max bytes per log file |
| `backup_count` | `int` | `5` | Number of backup files to keep |
| `log_format` | `str` | `"text"` | Log format ("text" or "json") |
| `console_output` | `bool` | `True` | Enable console output |
| `console_level` | `str` | `"INFO"` | Console log level |
| `internal_api_log_level` | `str` | `"DEBUG"` | Internal API log level |

### Basic Configuration

```python
from ibm_storage_protect.logger import configure_logging, LogConfig

# Using LogConfig class for advanced control
config = LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    enable_internal_api_log=False,
    user_log_file="app_user.log",
    debug_log_file="app_debug.log",
    error_log_file="app_error.log",
    internal_api_log_file="app_internal_api.log",
    log_dir="./logs",
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5,
    log_format="text",
    console_output=True,
    console_level="INFO"
)

configure_logging(config)
```

### Production Configuration

```python
configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=False,         # Disable debug in production
    enable_error_log=True,
    log_dir="/var/log/myapp",
    log_format="json",              # Machine-readable format
    console_level="WARNING",        # Minimal console output
    max_bytes=50*1024*1024,         # 50MB per file
    backup_count=10                 # Keep more backups
))
```

### Development Configuration

```python
configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,          # Enable detailed diagnostics
    enable_error_log=True,
    enable_internal_api_log=True,   # Enable C API logging
    log_dir="./logs",
    log_format="text",              # Human-readable
    console_level="DEBUG",          # Verbose console output
    internal_api_log_level="DEBUG"  # Capture all C API calls
))
```

---

## Log Formats

### Text Format (Human-Readable)

```
2026-05-29 09:15:30,123 - ibm_storage_protect.session - INFO - Session login started | event=session.login.started | op=login | node=MYNODE
2026-05-29 09:15:30,456 - ibm_storage_protect.session - INFO - Session login completed | event=session.login.completed | session=handle_12345_101530
2026-05-29 09:15:31,789 - ibm_storage_protect.errors.mapper - ERROR - C API error mapped to SDK error | event=error.mapped | c_code=2200 | error_code=TSM-2200
```

### JSON Format (Machine-Readable)

```json
{
  "timestamp": "2026-05-29T09:15:30.123Z",
  "level": "INFO",
  "logger": "ibm_storage_protect.session",
  "message": "Session login started",
  "event_type": "session.login.started",
  "operation": "login",
  "context": {
    "node": "MYNODE"
  }
}
```

---

## Common Use Cases

### 1. Debugging Failed Operations

```python
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger

# Enable detailed logging
configure_logging(LogConfig(
    enable_debug_log=True,
    enable_internal_api_log=True,
    console_level="DEBUG"
))

logger = get_logger('my_app')

try:
    # Your operation
    session.login(credentials)
except Exception as e:
    logger.error(
        "Operation failed",
        extra={
            "event_type": "operation.failed",
            "error": str(e)
        },
        exc_info=True  # Include stack trace
    )
    raise
```

**Check logs**: `./logs/ibm_sp_debug.log` for C API details

### 2. Monitoring Production Systems

```python
# Production configuration with JSON format
configure_logging(LogConfig(
    log_format="json",
    console_level="WARNING",
    enable_error_log=True
))

# Logs are now machine-readable for log aggregation tools
# Monitor: ./logs/ibm_sp_error.log for failures
```

### 3. Troubleshooting C API Errors

```python
# Enable internal API logging
configure_logging(LogConfig(
    enable_internal_api_log=True,
    internal_api_log_level="DEBUG"
))

# All C API calls and return codes are logged
# Check: ./logs/ibm_sp_internal_api.log
```

### 4. Application-Level Logging

```python
from ibm_storage_protect.logger import get_logger

# Get a logger for your application
logger = get_logger('my_app')

# Log with structured context
logger.info(
    "Backup batch started",
    extra={
        "event_type": "batch.started",
        "context": {
            "file_count": 100,
            "total_size_mb": 1024
        }
    }
)

# SDK operations are automatically logged
client.backup(backup_spec)  # Logged internally

logger.info(
    "Backup batch completed",
    extra={
        "event_type": "batch.completed",
        "metrics": {
            "duration_ms": 45000,
            "files_processed": 100
        }
    }
)
```

---

## Integration with Error Handling

The logging system is tightly integrated with the SDK error handling system. All SDK exceptions include structured error information that is automatically logged.

```python
from ibm_storage_protect.errors.exceptions import TSMError

try:
    session.login(credentials)
except TSMError as error:
    # Error is automatically logged by SDK
    # You can add application context
    logger.error(
        "Login failed in production workflow",
        extra={
            "event_type": "workflow.failed",
            "error": error.to_dict(),  # Structured error info
            "context": {
                "workflow": "nightly_backup",
                "retry_count": 3
            }
        }
    )
    raise
```

**Error object includes**:
- `error_code`: SDK error code (e.g., TSM-2102)
- `error_name`: Error name (e.g., PASSWORD_EXPIRED)
- `category`: Error category (e.g., AUTHENTICATION)
- `severity`: Severity level (e.g., HIGH)
- `retry_recommended`: Whether retry is suggested
- `retry_after`: Recommended retry delay in seconds
- `message`: Full error message including C API messages

---

## Troubleshooting

### No Logs Appearing

**Problem**: Running application but no log files created.

**Solution**: Ensure you call `configure_logging()` at application startup:

```python
from ibm_storage_protect.logger import configure_logging

# Must be called before using SDK
configure_logging()

# Now use SDK
from ibm_storage_protect import ClientSession
session = ClientSession()
```

### C API Messages Not Showing

**Problem**: Seeing "unknown C API error" instead of actual messages.

**Solution**: Enable debug logging to capture C API details:

```python
configure_logging(LogConfig(
    enable_debug_log=True,
    enable_internal_api_log=True
))
```

Check `./logs/ibm_sp_debug.log` and `./logs/ibm_sp_internal_api.log`.

### Too Many Log Files

**Problem**: Log directory filling up with rotated files.

**Solution**: Adjust rotation settings:

```python
configure_logging(LogConfig(
    max_bytes=50*1024*1024,  # Larger files (50MB)
    backup_count=3           # Fewer backups
))
```

### Logs Too Verbose

**Problem**: Too much output in production.

**Solution**: Adjust log levels:

```python
configure_logging(LogConfig(
    console_level="WARNING",     # Only warnings on console
    enable_debug_log=False,      # Disable debug log
    enable_internal_api_log=False  # Disable C API log
))
```

---

## Best Practices

### 1. Configure Early

Always configure logging at the start of your application:

```python
# At the top of your main script/module
from ibm_storage_protect.logger import configure_logging

configure_logging()  # Configure before any SDK operations
```

### 2. Use Appropriate Levels

- **Development**: `DEBUG` level with all logs enabled
- **Staging**: `INFO` level with error log
- **Production**: `INFO` or `WARNING` level, JSON format

### 3. Use Structured Logging

Prefer structured context over string formatting:

```python
# Good: Structured context
logger.info(
    "Backup completed",
    extra={
        "event_type": "backup.completed",
        "metrics": {
            "files": 100,
            "bytes": 1024000
        }
    }
)

# Avoid: String formatting
logger.info(f"Backup completed: 100 files, 1024000 bytes")
```

### 4. Don't Log Sensitive Data

The SDK automatically sanitizes passwords, but be careful with:
- Custom credentials
- API keys
- Personal data
- File contents

### 5. Monitor Error Logs

Set up monitoring for the error log:

```bash
# Monitor error log in real-time
tail -f ./logs/ibm_sp_error.log

# Alert on critical errors
grep "CRITICAL" ./logs/ibm_sp_error.log | mail -s "Critical Error" admin@example.com
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""
Example: IBM Storage Protect SDK with Logging
"""
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.errors.exceptions import TSMError

# Configure logging first
configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="./logs",
    log_format="text",
    console_level="INFO",
    max_bytes=10*1024*1024,
    backup_count=5
))

# Get application logger
logger = get_logger('backup_app')

def main():
    logger.info("Application started", extra={"event_type": "app.started"})
    
    session = None
    try:
        # Create session
        session = ClientSession()
        credentials = LoginCredentials(
            node=os.getenv("SP_NODE"),
            password=os.getenv("SP_PASSWORD"),
            owner=os.getenv("SP_OWNER"),
            server=os.getenv("SP_SERVER")
        )
        
        # Login (automatically logged by SDK)
        session.login(credentials)
        logger.info(
            "Session established",
            extra={
                "event_type": "session.established",
                "context": {
                    "node": credentials.node
                }
            }
        )
        
        # Create data client
        client = DataClient(session)
        
        # Backup file (automatically logged by SDK)
        backup = BackupRequest(
            Key="/data/important.txt",
            Body=b"Important data content"
        )
        backup_result = client.backup(backup)
        
        logger.info(
            "Backup successful",
            extra={
                "event_type": "backup.success",
                "metrics": {
                    "bytes": len(backup.body)
                }
            }
        )
        
    except TSMError as error:
        logger.error(
            "SDK operation failed",
            extra={
                "event_type": "operation.failed",
                "error": error.to_dict()
            },
            exc_info=True
        )
        return 1
        
    except Exception as error:
        logger.critical(
            "Unexpected error",
            extra={
                "event_type": "app.error",
                "error": str(error)
            },
            exc_info=True
        )
        return 1
        
    finally:
        if session:
            try:
                session.logout()
                logger.info("Session closed", extra={"event_type": "session.closed"})
            except Exception as e:
                logger.error(
                    "Logout failed",
                    extra={
                        "event_type": "cleanup.failed",
                        "error": str(e)
                    }
                )
    
    logger.info("Application completed", extra={"event_type": "app.completed"})
    return 0

if __name__ == "__main__":
    exit(main())
```

---

## API Reference

### Functions

#### [`configure_logging(config=None)`](../../src/ibm_storage_protect/logger/config.py:59)
Configure the logging system with the specified configuration.

**Parameters**: `config` (LogConfig, optional) - Configuration object. If None, uses defaults.

---

#### [`get_logger(name)`](../../src/ibm_storage_protect/logger/config.py:139)
Get a logger instance for the specified module.

**Parameters**: `name` (str) - Logger name. Automatically prefixed with 'ibm_storage_protect.' if not already.

**Returns**: logging.Logger

---

#### [`set_sdk_log_level(level)`](../../src/ibm_storage_protect/logger/config.py:148)
Dynamically adjust the log level for all active SDK handlers.

**Parameters**: `level` (str) - Log level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

---

### Context Management

#### [`set_log_context(**kwargs)`](../../src/ibm_storage_protect/logger/context.py)
Set thread-local logging context.

#### [`clear_log_context()`](../../src/ibm_storage_protect/logger/context.py)
Clear thread-local logging context.

#### [`get_log_context()`](../../src/ibm_storage_protect/logger/context.py)
Get current thread-local logging context.

---

## Summary

**Key Points**:
1. ✅ Configure logging at application startup with `configure_logging()`
2. ✅ SDK automatically logs all operations, errors, and C API interactions
3. ✅ Use appropriate log levels: DEBUG (dev), INFO (prod), WARNING (issues)
4. ✅ Enable error log for quick failure review
5. ✅ Use JSON format for production log aggregation

**Default Behavior Without Configuration**:
- Console output at WARNING level only
- No log files created
- Limited diagnostic information

**With Configuration**:
- Full operational logs with C API messages
- Automatic log rotation
- Structured error information
- Performance metrics

---

**Last Updated**: 2026-05-29  
**SDK Version**: 0.1.0