# IBM Storage Protect — Python SDK

This repository contains a Python SDK that provides a safe, type-checked, and Pythonic wrapper around the native IBM Storage Protect (formerly TSM) C client libraries. The SDK exposes high-level session, data (backup/restore), query, and control APIs that handle transactions, chunking, error mapping, and logging for you.

Key repository components:

- `src/ibm_storage_protect/` — SDK implementation (clients, models, low-level ctypes bindings).
- `docs/` — Guides, design docs (HLD / LLD), examples and reference material.
- `examples/` — Integration examples (filesystem, postgre, group backup flows).

## Features

- High-level clients: `ClientSession`, `DataClient`, `ControlClient`, `QueryClient`.
- Pydantic (v2) models for type-safe input validation and aliases for C-style PascalCase and Pythonic snake_case.
- Safe dynamic loading of platform-specific IBM Storage Protect C libraries (override with `IBM_SP_API_LIB`).
- Streaming-friendly backup and restore flows with enforced chunk size limits (4MB backup chunks; 1MB restore buffer).
- Transactional group backups with leader/member semantics and local metadata persistence (`.sp_groups.json`).
- Rich exception mapping from native C return codes to Python `TSMError` subclasses with retry hints.
- Structured, configurable logging (text and JSON outputs) with session/operation correlation IDs.

## Supported Platforms

- Linux

## Prerequisites

Before using this SDK, ensure the following components are installed and configured:

### IBM Storage Protect Client API (BA Client)

- **Version**: 8.1.x and higher
- **Installation**: The IBM Storage Protect Client API binary must be installed on the machine where the SDK will be used
- **Library**: The native client library (libApiTSM64.so) must be accessible to the SDK

### IBM Storage Protect Server Ecosystem

- **Version**: IBM Storage Protect Server 8.1.x and higher
- **Purpose**: Required to perform backup, restore, query, and control operations
- **Configuration**: The server must be properly configured and accessible from the client machine

## Requirements

- Python 3.10+
- Pydantic v2
- The IBM Storage Protect Client API libraries (libApiTSM64.so)

Note: The SDK uses `ctypes` to load the native client library; make sure the native client is installed on the host, or set `IBM_SP_API_LIB` to the library absolute path.

## Installation

### From Wheel File

If you have the pre-built wheel file (e.g., `ibm_storage_protect_sdk-1.0.0-py3-none-any.whl`):

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install ibm_storage_protect_sdk-1.0.0-py3-none-any.whl
```

### From Source

Install the package and development requirements in a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## Environment

To override the dynamic library path (highest precedence):

```bash
export DSMI_DIR=/opt/tivoli/tsm/client/api/bin64
export DSMI_CONFIG=/opt/tivoli/tsm/client/api/bin64/dsm.opt
export DSMI_LOG=/tmp
export LD_LIBRARY_PATH=/opt/tivoli/tsm/client/api/bin64:$LD_LIBRARY_PATH
export IBM_SP_API_LIB=/opt/tivoli/tsm/client/api/bin64/libApiTSM64.so
```

## Creating Your First Application

After installing the SDK from the wheel file, follow these steps to create a simple backup and restore application:

### Step 1: Set Up Environment Variables

Before running your application, configure the required environment variables:

```bash
export DSMI_DIR=/opt/tivoli/tsm/client/api/bin64
export DSMI_CONFIG=/opt/tivoli/tsm/client/api/bin64/dsm.opt
export DSMI_LOG=/tmp
export LD_LIBRARY_PATH=/opt/tivoli/tsm/client/api/bin64:$LD_LIBRARY_PATH
export IBM_SP_API_LIB=/opt/tivoli/tsm/client/api/bin64/libApiTSM64.so

# Set your credentials
export SP_NODE=your_node_name
export SP_PASSWORD=your_password
```

### Step 2: Create Your Application File

Create a new Python file (e.g., `my_backup_app.py`) with the following code:

```python
#!/usr/bin/env python3
"""
Simple IBM Storage Protect Backup and Restore Application
"""

import os
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.data_models.restore import RestoreRequest
from ibm_storage_protect.logger.config import configure_logging, LogConfig


def main():
    # Step 1: Configure logging
    configure_logging(LogConfig(
        enable_user_log=True,
        enable_error_log=True,
        log_dir="./logs",
        console_level="INFO"
    ))
    
    # Step 2: Set up credentials
    credentials = LoginCredentials(
        node=os.getenv("SP_NODE"),
        password=os.getenv("SP_PASSWORD"),
    )
    
    # Step 3: Create session and login
    with ClientSession() as session:
        print("Logging in to IBM Storage Protect...")
        session.login(credentials)
        print("Login successful!")
        
        # Initialize data client
        data_client = DataClient(session)
        
        # Step 4: Perform a single backup
        print("\n--- Performing Backup ---")
        backup_spec = BackupRequest(
            Key="/myapp/data/config.txt",
            Body=b"This is my application configuration data",
            Filespace="/"
        )
        
        backup_result = data_client.backup(backup_spec)
        print(f"Backup Status: {backup_result.Status}")
        print(f"Backed up object: {backup_result.Key}")
        
        # Step 5: Perform a single restore
        print("\n--- Performing Restore ---")
        restore_spec = RestoreRequest(
            Key="/myapp/data/config.txt",
            Filespace="/"
        )
        
        restore_result = data_client.restore(restore_spec)
        
        # Write restored data to a file
        restored_data = b""
        for chunk in restore_result.Body:
            restored_data += chunk
        
        output_file = "./restored_config.txt"
        with open(output_file, "wb") as f:
            f.write(restored_data)
        
        print(f"Restore Status: {restore_result.Status}")
        print(f"Restored object: {restore_result.Key}")
        print(f"Data written to: {output_file}")
        print(f"Restored content: {restored_data.decode('utf-8')}")
        
        print("\n--- Application completed successfully! ---")


if __name__ == "__main__":
    main()
```

### Step 3: Run Your Application

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run the application
python my_backup_app.py
```

### Expected Output

```
Logging in to IBM Storage Protect...
Login successful!

--- Performing Backup ---
Backup Status: Success
Backed up object: /myapp/data/config.txt

--- Performing Restore ---
Restore Status: Success
Restored object: /myapp/data/config.txt
Data written to: ./restored_config.txt
Restored content: This is my application configuration data

--- Application completed successfully! ---
```

### Next Steps

Once you have the basic backup and restore working:

1. **Backup files from disk**: Read file contents and backup using `open()` and file streams
2. **Handle larger files**: Use generators to stream data in chunks (4MB for backup, 1MB for restore)
3. **Add error handling**: Wrap operations in try-except blocks to handle `TSMError` exceptions
4. **Query backed up objects**: Use `QueryClient` to list and search for backed up data
5. **Batch operations**: Use `batch_backup()` and `batch_restore()` for multiple files
6. **Group operations**: Use transactional group backups for related files that must succeed or fail together

## Quick Start

Example: configure logging, open a session, and run a simple backup.

```python
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.logger.config import configure_logging, LogConfig

configure_logging(LogConfig(
    enable_user_log=True,
    enable_error_log=True,
    log_dir="./logs",
    console_level="INFO"
))

credentials = LoginCredentials(
    node=os.getenv("SP_NODE"),
    password=os.getenv("SP_PASSWORD"),
)

with ClientSession() as session:
    session.login(credentials)
    data_client = DataClient(session)

    backup_spec = BackupRequest(
        Key="/app/config/settings.conf",
        Body=b"configuration contents",
    )

    result = data_client.backup(backup_spec)
    print("Backup status:", result.Status)
```

## Usage Notes & Best Practices

- Always call `configure_logging()` at application startup to enable structured logs and file rotation.
- Use `ClientSession` as a context manager (`with` statement) to ensure `logout()` is called and C handles are released.
- For large files, stream data using a generator yielding chunks <= 4MB for backups.
- Restores return a generator that yields 1MB chunks — write them to disk incrementally rather than collecting into memory.
- Use `batch_backup` and `batch_restore` for high-throughput multi-object operations, and `create_group()` for transactional group backups.
- Do not share a `ControlClient` instance across threads; create per-thread instances tied to an active session.

## API Overview

- Session & authentication: `ClientSession`, `LoginCredentials`, `PasswordChange` — see `src/ibm_storage_protect/session.py`.
- Data operations (backup/restore/group): `DataClient`, `BackupClient`, `RestoreClient`, `GroupHandle` — see `src/ibm_storage_protect/data_client/`.
- Query operations: QueryClient in `src/ibm_storage_protect/query.py` and models in `src/ibm_storage_protect/data_models/query.py`.
- Control operations (filespace & metadata): ControlClient in `src/ibm_storage_protect/control.py` and models in `src/ibm_storage_protect/data_models/filespace.py` and `object.py`.
- Errors: `TSMError` subclasses and mapping logic under `src/ibm_storage_protect/errors/`.

Refer to the in-repo design guides for operational details and examples:

- Guides: [docs/guides](docs/guides/README.md)
- High-level design: [docs/design/hld.md](docs/design/hld.md)
- Low-level design: [docs/design/lld.md](docs/design/lld.md)

## Examples

Explore runnable integration examples in the `examples/` folder:

- `examples/filesystem/` — filesystem protect example and integration tests.
- `examples/postgre/` — PostgreSQL backup/restore integration example.

Quick snippet: streaming restore to disk

```python
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.data_models.restore import RestoreRequest

with ClientSession() as session:
    session.login(credentials)
    client = DataClient(session)

    spec = RestoreRequest(Key="/db/large_database.db", Filespace="/")
    result = client.restore(spec)

    with open("/tmp/recovered.db", "wb") as out:
        for chunk in result.Body:
            out.write(chunk)

    print("Restore complete")
```

## Tests & Mocking

The SDK includes a built-in Mock C API that allows running the entire test suite immediately without installing native C libraries on your machine.

### Running Tests with the Mock C API
By default, the SDK dynamically detects `pytest` and loads the Mock C API instead of the native libraries. To run all unit and integration tests under the mock:
```bash
pytest
```

### Running Tests with Real C API Libraries
To verify behavior against actual native C client libraries and TSM server configurations:
1. Set the environment variable `SP_USE_MOCK_C_API=0` (or `false`) to disable the mock.
2. Specify the path to the native client library with the `IBM_SP_API_LIB` environment variable (if not located in standard search paths).

**Example:**
```bash
SP_USE_MOCK_C_API=0 IBM_SP_API_LIB=/usr/lib/libtsmapi64.so pytest
```

## Contributing

Contributions are welcome. To maintain a safe, type-safe, and production-grade library, we enforce strict coding, diagnostic, and testing standards. 

Please review the **[Contribution Guidelines](docs/contrib/README.md)** before submitting any changes, which detail:
- **[Coding Standards & ctypes Safety](docs/contrib/coding_standards.md)**: Coding style, project layout, spec-driven development, and memory safety rules for raw C-API structures.
- **[Diagnostics & Troubleshooting Standards](docs/contrib/diagnostic_standards.md)**: Error translations, mapper configurations, structured logging levels, and FFDC capture.
- **[Testing & Verification Standards](docs/contrib/testing_standards.md)**: Mock unit tests, fixture cleanups, traceability matrices, and target coverage percentages.

## Support

### Best-Effort Support Model

This SDK is provided and maintained on a **best-effort basis**. While we strive to ensure quality and reliability, please note the following:

- **Community-Driven Development**: This is an open-source project that relies on community contributions and feedback to evolve and improve.
- **No Guaranteed SLA**: There are no formal service-level agreements (SLAs) or guaranteed response times for issues, feature requests, or bug fixes.
- **Volunteer Maintenance**: Updates, enhancements, and bug fixes are implemented as time and resources permit by the maintainers and community contributors.

### How to Get Help

We encourage users to actively participate in improving this SDK through the following channels:

#### 1. GitHub Issues

For bug reports, feature requests, or general questions:

- **Create a GitHub Issue**: Visit our [Issues page](https://github.com/IBM/storage-protect-python-sdk/issues) and open a new issue with:
  - A clear, descriptive title
  - Detailed description of the problem or feature request
  - Steps to reproduce (for bugs)
  - Environment details (Python version, OS, IBM Storage Protect client version)
  - Relevant code snippets or error messages
  - Expected vs. actual behavior

**Best Practices for Issues**:
- Search existing issues first to avoid duplicates
- Use appropriate labels (bug, enhancement, question, documentation)
- Provide minimal reproducible examples when reporting bugs
- Include relevant log outputs (sanitize sensitive information)

#### 2. Pull Requests

We actively welcome and encourage community contributions:

- **Submit Pull Requests**: If you've identified a bug fix, documentation improvement, or new feature:
  - Fork the repository
  - Create a feature branch (`git checkout -b feature/your-feature-name`)
  - Make your changes following our [Contribution Guidelines](docs/contrib/README.md)
  - Ensure all tests pass and add new tests for your changes
  - Submit a pull request with a clear description of the changes
  - Reference any related issues in your PR description

**Pull Request Guidelines**:
- Follow the coding standards outlined in [docs/contrib/coding_standards.md](docs/contrib/coding_standards.md)
- Adhere to testing standards in [docs/contrib/testing_standards.md](docs/contrib/testing_standards.md)
- Update documentation to reflect your changes
- Ensure backward compatibility unless explicitly discussed
- Be responsive to review feedback and questions

#### 3. IBM Support Channels

For enterprise users with IBM support contracts or those requiring official IBM assistance:

- **IBM Support Portal**: If you have an active IBM support agreement, you can open a support case through the [IBM Support Portal](https://www.ibm.com/mysupport/)
- **IBM Storage Protect Documentation**: Refer to the official [IBM Storage Protect documentation](https://www.ibm.com/docs/en/storage-protect) for product-specific guidance
- **IBM Community Forums**: Engage with the broader IBM Storage Protect community through [IBM Community](https://community.ibm.com/)

**When to Use IBM Support**:
- Critical production issues requiring immediate attention
- Questions about IBM Storage Protect server configuration or policies
- Licensing and entitlement questions
- Issues with the underlying IBM Storage Protect C API libraries
- Enterprise-level architectural guidance

**Note**: IBM Support channels are primarily for IBM Storage Protect product support. For SDK-specific issues, GitHub Issues and Pull Requests are the preferred channels.

### Response Expectations

- **GitHub Issues**: Community members and maintainers will respond as time permits. Complex issues may take longer to investigate and resolve.
- **Pull Requests**: We aim to review PRs within a reasonable timeframe, but response times may vary based on maintainer availability and PR complexity.
- **IBM Support**: Response times are governed by your support contract SLA.

### Contributing to Support

You can help improve support for everyone:

- **Answer Questions**: Help other users by responding to GitHub issues
- **Improve Documentation**: Submit PRs to clarify or expand documentation
- **Share Examples**: Contribute real-world usage examples to the `examples/` directory
- **Report Issues**: Even if you can't fix a bug, reporting it helps the community
- **Test Pre-releases**: Help validate new features and bug fixes before release

## License

This project includes a `LICENSE` file in the repository root. Review it for the license terms.

---
