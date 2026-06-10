# SDK Test Cases Specification

This document provides granular test cases for verifying the correctness, reliability, and security of the IBM Storage Protect Python SDK.

---

## 1. Session & Lifecycle Management (TC-SES)

### TC-SES-01: Session Login and Logout
- **Requirement Covered**: [FR-SES-01], [FR-SES-02], [NFR-LOG-01]
- **Type**: Integration
- **Preconditions**: Storage Protect server is running and accessible. Node name is registered.
- **Inputs**:
  - `node` = `"<registered test node>"`
  - `password` = `"<test node password>"`
- **Test Steps**:
  1. Instantiate `ClientSession`.
  2. Instantiate `LoginCredentials` with the node and password.
  3. Call `session.login(credentials)`.
  4. Verify that `session.is_active` is `True` and `session.handle` is a positive integer.
  5. Check log file to confirm a `session.login.completed` event is written with correct `session_handle` and `duration_ms` metric.
  6. Call `session.logout()`.V
  7. Verify `session.is_active` becomes `False`.
- **Expected Results**: Session connects, generates valid handle, logs metrics, and disconnects cleanly.

### TC-SES-02: Session Context Manager Resource Recovery
- **Requirement Covered**: [FR-SES-03], [NFR-PF-04]
- **Type**: Integration / Robustness
- **Preconditions**: Standard connection credentials configured.
- **Inputs**: None.
- **Test Steps**:
  1. Define a block using python's `with ClientSession() as session:` statement.
  2. Within the block, log in using valid `LoginCredentials` credentials.
  3. Inside the block, raise an explicit Python `ValueError("Test Error")`.
  4. Outside the block, catch the `ValueError`.
  5. Verify that `session.is_active` is `False` and that the session has successfully triggered logout.
- **Expected Results**: The context exit block successfully handles error propagation and automatically disconnects the C API handle, freeing server allocations.

### TC-SES-03: Retrieve Server and Client Information
- **Requirement Covered**: [FR-SES-04]
- **Type**: Integration
- **Preconditions**: Valid login session established.
- **Inputs**: None.
- **Test Steps**:
  1. Call `session.get_info()`.
  2. Verify the returned model `SessionInfo` contains:
     - `server_name` (non-empty string)
     - `server_version` (positive integer)
     - `compression` (boolean value)
     - `lan_free_enabled` (boolean value)
- **Expected Results**: Returns validated Pydantic model populated with merged settings from `dsmQuerySessInfo` and `dsmQuerySessOptions`.

### TC-SES-04: Node Password Change
- **Requirement Covered**: [FR-SES-05]
- **Type**: System / Functional
- **Preconditions**: Active connection established.
- **Inputs**:
  - `current_password` = `"<current test password>"`
  - `new_password` = `"<new test password>"`
- **Test Steps**:
  1. Instantiate `PasswordChange` model.
  2. Call `session.change_password(change_request)`.
  3. Verify that the C call succeeds without raising exceptions.
  4. Call `session.logout()`.
  5. Attempt to login with `current_password` and verify `TSMAuthenticationError` is raised.
  6. Attempt to login with `new_password` and verify connection is successfully established.
- **Expected Results**: Password change applies on the server; subsequent logins are authenticated using the new credentials.

---

## 2. Data Backup & Policy Binding (TC-BK)

### TC-BK-01: Single Object Backup (Bytes & Generator Streams)
- **Requirement Covered**: [FR-BK-01], [FR-BK-02], [FR-BK-03]
- **Type**: Integration / Functional
- **Preconditions**: Active session established. Target filespace is registered.
- **Inputs**:
  - `Key` = `"/database/backup_test.bin"`
  - `Body` = `b"Test binary backup payload"`
- **Test Steps**:
  1. Instantiate `DataClient`.
  2. Create `BackupRequest` request model.
  3. Call `client.backup(backup_spec)`.
  4. Verify that `dsmBindMC` binds the object to the default domain policy.
  5. Verify that `dsmBeginTxn` initiates a transaction.
  6. Verify that `dsmSendObj` and `dsmSendData` return success.
  7. Verify that `dsmEndTxnEx` commits the transaction.
  8. Inspect return `BackupResult` model and verify `status` is `"success"`.
- **Expected Results**: Data is written to Storage Protect storage pools, and stats (bytes sent) are returned.

### TC-BK-02: Enforce the 4MB Backup Chunk Guard
- **Requirement Covered**: [NFR-PERF-01], [NFR-PERF-03]
- **Type**: Unit / Boundary
- **Preconditions**: Active data client instantiated.
- **Inputs**:
  - Chunk size inside generator = `5 * 1024 * 1024` (5MB, exceeding the 4MB limit)
- **Test Steps**:
  1. Create a byte chunk generator yielding a 5MB block.
  2. Instantiate `BackupRequest` containing this body generator.
  3. Call `client.backup(backup_spec)`.
  4. Verify that `TSMDataError` is raised *before* any ctypes dynamic library call is executed.
- **Expected Results**: Client-side Pydantic validator/guard blocks execution, raising `TSMDataError` and preventing a native C-level buffer crash.

### TC-BK-03: Batch Backup (Transactional Safety)
- **Requirement Covered**: [FR-BK-04], [NFR-ERR-03]
- **Type**: Integration / Robustness
- **Preconditions**: Active session established.
- **Inputs**:
  - `Objects` = List of three `BackupRequest` models (First two valid, third has an empty key path).
- **Test Steps**:
  1. Instantiate `SPBatchBackup` with the object list.
  2. Call `client.batch_backup(batch_spec)`.
  3. Observe that the third backup item fails validation, raising an error.
  4. Verify that the SDK executes `dsmEndTxn` with vote `DSM_VOTE_ABORT` in the transaction block.
  5. Query the server for the first two objects.
  6. Verify that *neither* object exists on the server.
- **Expected Results**: A single validation failure causes the entire batch transaction to roll back atomically, leaving no orphaned states.

### TC-BK-04: Logical Group Backup (Leader-Member Relationship)
- **Requirement Covered**: [FR-BK-05]
- **Type**: System / Functional
- **Preconditions**: Active data client. Metadata JSON path config.
- **Inputs**:
  - Group Tag = `"postgresql-db-backup"`
- **Test Steps**:
  1. Call `client.create_group("postgresql-db-backup")`.
  2. Call `group.add_leader(BackupRequest(Key="/db/manifest.json", Body=b"manifest"))`.
  3. Verify that the server returns a `groupLeaderObjId` (hi/lo pair).
  4. Call `group.add_member(BackupRequest(Key="/db/data_page1.dat", Body=b"data"))`.
  5. Call `group.close()`.
  6. Read `.sp_groups.json` metadata file and verify the leader ID and group tag are successfully saved.
- **Expected Results**: Leader-member associations apply on the server and metadata state is persisted locally.

### TC-BK-05: Group Reopen, Metadata Load, and Member Modification
- **Requirement Covered**: [FR-BK-05], [FR-QY-03]
- **Type**: System / Functional
- **Preconditions**: Active data client. Existing group `.sp_groups.json` contains a valid entry.
- **Inputs**:
  - Group Tag = `"postgresql-db-backup"`
  - Member Key = `"/db/data_page2.dat"`
  - Member keys to remove = `["/db/data_page1.dat"]`
- **Test Steps**:
  1. Call `client.load_group(".sp_groups.json", "postgresql-db-backup")`.
  2. Verify that the loaded group has the correct leader ID.
  3. Call `group.reopen()`.
  4. Call `group.add_member(BackupRequest(Key="/db/data_page2.dat", Body=b"more data"))`.
  5. Call `group.close()`.
  6. Call `group.remove_members(["/db/data_page1.dat"])` to remove the member.
  7. Call `group.delete()` to destroy the group.
  8. Verify that the group metadata is removed from `.sp_groups.json`.
- **Expected Results**: Reopening, adding member, closing, query-based member removal, and group deletion succeed and cleanly update the local JSON state file.

---


## 3. Data Restore & Reassembly (TC-RS)

### TC-RS-01: Multi-Part Reassembly Ordering
- **Requirement Covered**: [FR-RS-02], [NFR-PERF-04]
- **Type**: Integration / Regression
- **Preconditions**: An object split into 3 parts exists on the server.
- **Inputs**:
  - `Key` = `"/database/split_archive.db"`
- **Test Steps**:
  1. Call `client.restore(RestoreRequest(Key="/database/split_archive.db"))`.
  2. Verify that the query returns 3 metadata parts.
  3. Verify that the translation layer sorts them using `restoreOrder` (`top`, `hi_hi`, `hi_lo`, `lo_hi`, `lo_lo`).
  4. Verify that the ctypes reference anchoring keeps structures alive during streaming.
  5. Stream the chunks and verify that the reassembled byte array matches the original un-split backup.
- **Expected Results**: Parts are retrieved and sorted correctly, producing an undamaged sequential file stream.

### TC-RS-02: Partial Object Restore (POR)
- **Requirement Covered**: [FR-RS-03]
- **Type**: Functional / Boundary
- **Preconditions**: A 10MB test file has been backed up.
- **Inputs**:
  - `Offset` = `4 * 1024 * 1024` (4MB mark)
  - `Length` = `1024 * 1024` (1MB size)
- **Test Steps**:
  1. Instantiate `RestoreRequest` passing `Offset` and `Length` parameter.
  2. Call `client.restore(restore_spec)`.
  3. Stream the output data into a byte string.
  4. Verify the length of the string is exactly 1MB.
  5. Compare the byte content against the original file's 4MB-to-5MB offset range.
- **Expected Results**: POR executes `dsmGetList` with POR version and returns exactly the requested sub-range bytes.

### TC-RS-03: Point-in-Time (PIT) Restore
- **Requirement Covered**: [FR-RS-03], [FR-RS-04]
- **Type**: Functional / Boundary
- **Preconditions**: Active connection. Historical versions of a file exist on the server.
- **Inputs**:
  - `Key` = `"/database/backup_test.bin"`
  - `PitDate` = `datetime.now() - timedelta(days=7)`
- **Test Steps**:
  1. Instantiate `RestoreRequest` with `Key`, `Filespace`, and `PitDate`.
  2. Call `client.restore(restore_spec)`.
  3. Verify that the C API receives a populated `dsmDate` structure matching the `PitDate`.
  4. Stream the output data into a byte string.
  5. Verify the restored data matches the state of the file 7 days ago.
- **Expected Results**: Restore proceeds successfully using `PitDate` to target historical file versions.

---


## 4. Namespace Control & Object Management (TC-CT)

### TC-CT-01: Idempotent Filespace Registration
- **Requirement Covered**: [FR-CT-01], [FR-CT-02]
- **Type**: Integration
- **Preconditions**: ControlClient initialized.
- **Inputs**:
  - `Filespace` = `"/myfs"`
- **Test Steps**:
  1. Call `control_client.register_filespace(SPFilespaceRegister(Filespace="/myfs"))`.
  2. Verify status returned is `"success"`.
  3. Call `control_client.register_filespace(SPFilespaceRegister(Filespace="/myfs"))` a second time.
  4. Verify that no exception is raised and status is still `"success"`.
  5. Call `control_client.update_filespace(SPFilespaceUpdate(Filespace="/myfs", Occupancy=5000))` and verify it succeeds.
- **Expected Results**: Second registration call resolves gracefully (idempotent), allowing safe subsequent metadata modifications.

### TC-CT-02: Object Renaming and Version Merging
- **Requirement Covered**: [FR-CT-06]
- **Type**: Functional / Transactional
- **Preconditions**: Backups exist for `/myfs/old_name.txt` and `/myfs/new_name.txt`.
- **Inputs**:
  - `Key` = `"/myfs/old_name.txt"`
  - `NewKey` = `"/myfs/new_name.txt"`
  - `Merge` = `True`
- **Test Steps**:
  1. Call `control_client.rename(SPObjectRename(Key="/myfs/old_name.txt", NewKey="/myfs/new_name.txt", Merge=True))`.
  2. Verify that the operation returns success.
  3. Query `/myfs/new_name.txt` using a backup query showing active and inactive versions.
  4. Verify that versions of `old_name.txt` have been successfully consolidated into the history of `new_name.txt`.
- **Expected Results**: Objects merge successfully on the server namespace, preserving version histories.

## 5. Queries & Search Patterns (TC-QY)

### TC-QY-01: Wildcard Queries and Object Listing
- **Requirement Covered**: [FR-QY-01], [FR-QY-02]
- **Type**: Integration / Functional
- **Preconditions**: Objects exist under the filespace.
- **Inputs**:
  - `Filespace` = `"/sdk_flow_fs"`
  - `Prefix` = `"/database/backup"`
  - `MaxKeys` = 10
- **Test Steps**:
  1. Call `query_client.list_objects(SPListObjects(Filespace="/sdk_flow_fs", Prefix="/database/backup", MaxKeys=10))`.
  2. Verify that the returned result contains matching keys up to the maximum count limit.
  3. Call `query_client.execute_backup_query(BackupQueryRequest(Filespace="/sdk_flow_fs", Key="/database/backup*", ObjState=ObjState.ACTIVE))` with wildcard patterns.
  4. Verify the search results return correctly filtered metadata.
- **Expected Results**: Object listing and backup queries correctly filter results using wildcards, prefixes, and page limits.

### TC-QY-02: Filespace and Management Class Policy Queries
- **Requirement Covered**: [FR-QY-04], [FR-QY-05]
- **Type**: Integration
- **Preconditions**: Active connection. Filespaces registered and management classes defined.
- **Inputs**:
  - `FsPattern` = `"/sdk_flow_fs"`
  - `ClassPattern` = `"*"`
- **Test Steps**:
  1. Call `query_client.query_filespaces(SPQueryFilespaces(FsPattern="/sdk_flow_fs"))`.
  2. Verify that filespace statistics (capacity, occupancy) are returned.
  3. Call `query_client.query_mgmt_classes(SPQueryMgmtClasses(ClassPattern="*"))`.
  4. Verify that returned classes match server policies.
- **Expected Results**: Statistics and policy metadata are successfully retrieved and converted to validated Python models.

---

## 6. robust Exception Mapping & Security (TC-NFR)


### TC-NFR-01: Exception Mapping & Retry Properties
- **Requirement Covered**: [NFR-ERR-01], [NFR-ERR-02]
- **Type**: Unit / Mock
- **Preconditions**: Mock dynamic library that returns `2021` (`DSM_RC_COMM_ERROR`).
- **Inputs**: None.
- **Test Steps**:
  1. Trigger an operation (e.g. login) that hits the mock library returning code `2021`.
  2. Catch the raised exception.
  3. Verify that the raised exception class is `TSMConnectionError`.
  4. Verify that `e.error_code.value` is `"TSM-1102"`.
  5. Verify that `e.is_retryable` is `True` and `e.retry_after` equals `30`.
- **Expected Results**: C codes are correctly mapped to rich Python exceptions with retry attributes.

### TC-NFR-02: Credential Sanitization
- **Requirement Covered**: [NFR-SEC-01]
- **Type**: Unit / Security
- **Preconditions**: Structured JSON logging enabled.
- **Inputs**:
  - `node` = `"<test node>"`
  - `password` = `"<test password>"`
- **Test Steps**:
  1. Instantiate `LoginCredentials` with these credentials.
  2. Trigger `session.login(creds)`.
  3. Read the output JSON log records (e.g., `ibm_sp_user.log`).
  4. Verify that the word `"MySecretPassword123!"` does not appear anywhere in the logs.
  5. Deliberately trigger a password error to raise `TSMAuthenticationError`.
  6. Serialize the exception using `e.to_dict()` or `str(e)` and verify the password is not present.
- **Expected Results**: Passwords are completely omitted/sanitized from log records and exception strings.

### TC-NFR-03: Thread Isolation (Concurrency Guards)
- **Requirement Covered**: [NFR-THR-01]
- **Type**: Unit / Concurrency
- **Preconditions**: Session handle active.
- **Inputs**: None.
- **Test Steps**:
  1. Create a `ClientSession` and log in on Thread A.
  2. Instantiate a `DataClient` on Thread A using the session handle.
  3. Spawn Thread B.
  4. From Thread B, invoke `client.backup(backup_spec)`.
  5. Verify that Thread B catches a `ValueError` or thread boundary exception.
- **Expected Results**: Client raises exception indicating cross-thread session access violation, protecting against native memory corruption.
