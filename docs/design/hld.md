# High-Level Design (HLD): IBM Storage Protect Python SDK

This document provides a high-level architectural overview and design specifications for the Python-based SDK wrapper for IBM Storage Protect (formerly Tivoli Storage Manager / TSM). The SDK bridges modern Python applications with the native IBM Storage Protect C client libraries.

---

## 1. System Context & Architecture

The SDK is structured as a **layered framework** that transitions from user-friendly, type-safe Python abstractions down to raw C memory and system-level dynamic library calls.

```mermaid
graph TD
    UserApp[User Python Application]
    
    subgraph "SDK High-Level Client Layer"
        Session[ClientSession]
        DataClient[DataClient]
        ControlClient[ControlClient]
        QueryClient[QueryClient]
    end
    
    subgraph "Validation & Serialization Layer"
        Models[Pydantic Data Models]
        Enums[Type-Safe Enums]
    end
    
    subgraph "Internal C-API Translation & Workflow Layer"
        SessionMgr[SessionManager]
        BackupOp[BackupOperation]
        RestoreOp[RestoreOperation]
        ObjMgmt[Delete / Rename / Update Operations]
        Helpers[Path Parsing, Structure Init, Error Checking]
    end
    
    subgraph "Low-Level ctypes Binding Layer"
        Loader[load.py - Dynamic Library Loader]
        Prototypes[prototypes.py - Function Prototypes]
        Types[platform_types.py / structs.py - C Structs & Types]
        RC[return_codes.py - Return Codes]
    end
    
    subgraph "External C Library Layer"
        CLib[dsmtca64.dll / libApiTSM64.so / libApiTSM64.a]
    end

    UserApp --> Session
    UserApp --> DataClient
    UserApp --> ControlClient
    UserApp --> QueryClient
    
    Session & DataClient & ControlClient & QueryClient --> Models
    Session & DataClient & ControlClient & QueryClient --> SessionMgr & BackupOp & RestoreOp & ObjMgmt
    
    SessionMgr & BackupOp & RestoreOp & ObjMgmt --> Helpers
    Helpers --> Prototypes
    Prototypes --> Loader
    Loader --> CLib
```

### Architectural Layers

1. **High-Level Client Layer**: The primary public-facing API. It exposes object-oriented interfaces (`ClientSession`, `DataClient`, `ControlClient`, `QueryClient`) that hide all transaction handling, paging, chunking, and memory management.
2. **Validation & Serialization Layer**: Utilizes **Pydantic (v2)** models (`data_models/`) and standard enums (`enums/`) to ensure all input arguments are validated client-side before invoking C calls. This prevents segmentation faults by catching invalid types early.
3. **Internal C-API Translation Layer**: Implements core operational workflows (`SessionManager`, `BackupOperation`, `RestoreOperation`, etc.) that translate Python models into low-level C structures and coordinate multi-step API sequences (e.g., binding management classes before starting backup transactions).
4. **Low-Level ctypes Binding Layer**: Directly maps C API signatures, structures, types, and return codes into Python. It uses python's built-in `ctypes` module to dynamically load and interface with the native dynamic link libraries.
5. **Native C Library**: The dynamic shared libraries (`dsmtca64.dll` on Windows, `libApiTSM64.so` on Linux, etc.) provided by the IBM Storage Protect client installer.

---

## 2. Key Design Patterns & Core Decisions

### 2.1. Resource Lifecycle & Context Management
To prevent resource and memory leaks of C handles on the server and client, the SDK implements the **Context Manager Pattern** (`__enter__` and `__exit__`). 
- Active sessions are automatically cleaned up when exiting the context block.
- A global registry clean-up is registered via python's `atexit` module, guaranteeing that `dsmCleanUp` is called with single-threaded execution modes when the python process exits.

### 2.2. Delegator Pattern for Data Client
The `DataClient` provides a single unified entry point for all backup and restore operations to preserve backward compatibility. Internally, it delegates logic to specialized clients (`BackupClient` and `RestoreClient`), enforcing high cohesion and single-responsibility principles.

### 2.3. Transaction-Centric Operations
Backup, delete, and rename operations are intrinsically transaction-based. The SDK wraps these operations using the C API's `dsmBeginTxn` and `dsmEndTxnEx` calls. On failure of any sub-step, it enforces a `DSM_VOTE_ABORT` vote to automatically roll back changes on the server. On success, a `DSM_VOTE_COMMIT` vote is issued.

### 2.4. Error Translation Mapping
Low-level integer return codes (RCs) returned by the C library are translated into python exceptions using a dedicated mapping registry (`errors/mapper.py`). 
- Maps C return codes (e.g., `2021`, `-50`, `137`) to structured python exception types (e.g., `TSMConnectionError`, `TSMAuthenticationError`).
- Injects rich metadata, including:
  - Standardized SDK error codes (e.g., `TSM-1102` for network errors)
  - Severity classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - Intelligent **retry suggestions** (e.g., indicating whether an error is transient and specifying a recommended cooldown delay).

### 2.5. Structured Logging & Context Correlation
All client layers generate structured, machine-readable logs containing:
- Unique session IDs (`session_id` correlated with the C handle)
- Unique operation IDs (`operation_id`)
- Duration metrics (`duration_ms` calculated using `time.perf_counter()`)
- Granular step events (e.g., `query.list_objects.started`, `c_api.dsmGetObj.call`, `query.list_objects.completed`)

---

## 3. High-Level Data Flows

### 3.1. Session Lifecycle Flow

The session lifecycle manages initialization, options configuration, active status validation, password modification, and graceful termination.

```mermaid
sequenceDiagram
    autonumber
    participant App as Python Application
    participant CS as ClientSession
    participant SM as SessionManager
    participant C_API as C API (prototypes)
    participant Lib as Dynamic Shared Library

    App->>+CS: with ClientSession() as session
    CS->>+SM: Initialize SessionManager
    SM-->>-CS: SM Instance
    CS-->>App: session
    
    App->>+CS: session.login(LoginCredentials)
    CS->>+SM: SM.login()
    SM->>+C_API: dsmInitEx(handle, init_in, init_out)
    C_API->>+Lib: Initialize connection & authenticate
    Lib-->>-C_API: Return code (RC) & handle
    C_API-->>-SM: rc, handle
    Note over SM: Map RC. Handle password<br>expiration (RC 2030 / 52)
    SM-->>-CS: handle
    CS->>CS: Generate session_id for logging
    CS-->>-App: SPSession Model

    App->>+CS: session.get_info()
    CS->>+SM: SM.get_session_info()
    SM->>+C_API: dsmQuerySessInfo(handle, info)
    C_API-->>-SM: rc, info_struct
    SM->>+C_API: dsmQuerySessOptions(handle, opt)
    C_API-->>-SM: rc, opt_struct
    SM-->>-CS: merged session info dict
    CS-->>-App: SessionDetails Model

    App->>+CS: session.logout()
    CS->>+SM: SM.logout()
    SM->>+C_API: dsmTerminate(handle)
    C_API-->>-SM: void
    SM-->>-CS: clean state
    CS-->>-App: session inactive
```

---

### 3.2. Data Backup Flow (Single Object)

Backing up a single object requires binding to a management class policy, beginning a server transaction, sending object headers, streaming data in chunks up to 4MB, ending the object transmission, and committing the transaction.

```mermaid
sequenceDiagram
    autonumber
    participant Client as DataClient / BackupClient
    participant Op as BackupOperation
    participant C_API as C API (prototypes)

    Client->>+Op: execute()
    
    Note over Op: Step 1: Bind MC Policy
    Op->>+C_API: dsmBindMC(handle, obj_name, send_type, mc_bind_key)
    C_API-->>-Op: rc, mc_bind_key
    Note over Op: Validate copy group & target destination
    
    Note over Op: Step 2: Begin Transaction
    Op->>+C_API: dsmBeginTxn(handle)
    C_API-->>-Op: rc (Set txn_active = True)
    
    Note over Op: Step 3: Send Object Header
    Op->>+C_API: dsmSendObj(handle, send_type, name, attr, NULL)
    C_API-->>-Op: rc
    
    Note over Op: Step 4: Stream Data Chunks (<= 4MB)
    loop for each chunk in data_source
        Op->>+C_API: dsmSendData(handle, data_blk)
        C_API-->>-Op: rc
    end
    
    Note over Op: Step 5: End Object Send
    Op->>+C_API: dsmEndSendObjEx(end_in, end_out)
    C_API-->>-Op: rc, stats
    
    Note over Op: Step 6: Commit Transaction
    Op->>+C_API: dsmEndTxnEx(ein, eout)
    C_API-->>-Op: rc (Set txn_active = False)
    
    Op-->>-Client: BackupResult Model
```

---

### 3.3. Data Restore Flow (Single Object)

Restoring an object requires query metadata lookup to locate the specific Object IDs, ordering parts sequentially, initiating retrieval, streaming chunks (default 1MB buffer) via a generator, and closing the retrieval session.

```mermaid
sequenceDiagram
    autonumber
    participant Client as DataClient / RestoreClient
    participant Op as RestoreOperation
    participant Q as Query Layer
    participant C_API as C API (prototypes)

    Client->>+Op: execute()
    
    Note over Op: Step 1: Query Metadata
    Op->>+Q: query_objects(filespace, key, obj_state)
    Q-->>-Op: list of object parts metadata
    
    Note over Op: Step 2: Sort Parts
    Note over Op: Sort parts by restoreOrder (top, hi_hi, hi_lo, lo_hi, lo_lo)
    
    Note over Op: Step 3: Begin GetData
    Op->>+C_API: dsmBeginGetData(handle, mount_wait, gtBackup, get_list)
    C_API-->>-Op: rc
    
    Note over Op: Step 4: Stream Object Parts as Generator
    loop for each part in sorted parts
        Op->>+C_API: dsmGetObj(handle, obj_id, data_blk)
        C_API-->>-Op: rc, first chunk
        Op-->>Client: Yield chunk
        loop while rc == DSM_RC_MORE_DATA
            Op->>+C_API: dsmGetData(handle, data_blk)
            C_API-->>-Op: rc, subsequent chunk
            Op-->>Client: Yield chunk
        end
        Op->>+C_API: dsmEndGetObj(handle)
        C_API-->>-Op: rc
    end
    
    Note over Op: Step 5: End GetData
    Op->>+C_API: dsmEndGetDataEx(end_in, end_out)
    C_API-->>-Op: rc
    
    Op-->>-Client: RestoreResult Model (with Body generator)
```

---

## 4. Cross-Platform Library Loading Design

Because IBM Storage Protect client binaries are native C libraries, the SDK supports dynamic platform-specific dynamic link library loading via `ctypes.CDLL`. 

### Search Sequence & Path Priority

```mermaid
flowchart TD
    START([Module Import]) --> ENV{IBM_SP_API_LIB\nenvironment variable\nset?}
    ENV -->|Yes| LOAD_ENV[Load from IBM_SP_API_LIB path]
    ENV -->|No| PLAT{Detect\nsys.platform}

    PLAT -->|win32| WIN[Try dsmtca64.dll\nor C:/Program Files/Tivoli/TSM/api/bin64/dsmtca64.dll]
    PLAT -->|aix| AIX[Try /usr/lib/libApiTSM64.a\nor /opt/tivoli/tsm/.../libApiTSM64.a]
    PLAT -->|linux / unix| LNX[Try libtsmapi64.so\nor /opt/tivoli/tsm/.../libApiTSM64.so\nor /usr/lib/libtsmapi64.so]

    LOAD_ENV --> LOADED{Load\nSucceeded?}
    WIN --> LOADED
    AIX --> LOADED
    LNX --> LOADED

    LOADED -->|Yes| REGISTER[Register atexit dsmCleanUp\nlib variable assigned]
    LOADED -->|No| NULL[lib = None\nLog diagnostic warning\nRaise on first C call]

    REGISTER --> READY([SDK Ready])
    NULL --> DEGRADED([SDK Degraded\nNo native ops possible])
```

1. **Environment Variable Override**: If `IBM_SP_API_LIB` is specified, it holds the absolute highest precedence.
2. **Platform Default Paths**:
   - **AIX**: Archive container format (`/usr/lib/libApiTSM64.a`, `/opt/tivoli/tsm/client/api/bin64/libApiTSM64.a`).
   - **Windows**: DLL dynamic library format (`dsmtca64.dll` in working directory or default path `C:\Program Files\Tivoli\TSM\api\bin64\dsmtca64.dll`).
   - **Linux / Unix**: Shared object format (`libtsmapi64.so`, `/opt/tivoli/tsm/client/api/bin64/libApiTSM64.so`, `/usr/lib/libtsmapi64.so`, `/usr/lib64/libtsmapi64.so`).

If loading fails for all possible paths, the library variable `lib` is set to `None`, and diagnostic logs are generated to assist the administrator in installing client dynamic libraries or configuring environment paths.
