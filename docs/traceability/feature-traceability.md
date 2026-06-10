# Requirements Traceability Matrix (RTM)

This document provides end-to-end traceability mapping for the functional requirements of the IBM Storage Protect Python SDK, spanning from requirements definition through architectural design, implementation, and verification.

---

## 1. Feature-to-Design-to-Test Traceability Matrix

This table maps each functional requirement (defined in [features.md](../requirements/features.md)) to its design section in the High-Level Design ([hld.md](../design/hld.md)) and Low-Level Design ([lld.md](../design/lld.md)), the implementation module in `src/`, and the verification test case in the test specification ([test-cases.md](../test/test-cases.md)).

| Requirement ID | Description | Design Reference | Implementation Location | Verification Test Case |
| :--- | :--- | :--- | :--- | :--- |
| **FR-SES-01** | Session login | [hld.md: Section 3.1](../design/hld.md#31-session-lifecycle-flow)<br>[lld.md: Section 3.1](../design/lld.md#31-session-login-sequence) | [session.py](../../src/ibm_storage_protect/session.py) | [TC-SES-01](../test/test-cases.md#tc-ses-01-session-login-and-logout) |
| **FR-SES-02** | Session logout | [hld.md: Section 3.1](../design/hld.md#31-session-lifecycle-flow) | [session.py](../../src/ibm_storage_protect/session.py) | [TC-SES-01](../test/test-cases.md#tc-ses-01-session-login-and-logout) |
| **FR-SES-03** | Context Manager | [hld.md: Section 2.1](../design/hld.md#21-resource-lifecycle--context-management) | [session.py](../../src/ibm_storage_protect/session.py) | [TC-SES-02](../test/test-cases.md#tc-ses-02-session-context-manager-resource-recovery) |
| **FR-SES-04** | Session Info | [hld.md: Section 3.1](../design/hld.md#31-session-lifecycle-flow) | [session.py](../../src/ibm_storage_protect/session.py) | [TC-SES-03](../test/test-cases.md#tc-ses-03-retrieve-server-and-client-information) |
| **FR-SES-05** | Password Change | [hld.md: Section 3.1](../design/hld.md#31-session-lifecycle-flow) | [session.py](../../src/ibm_storage_protect/session.py) | [TC-SES-04](../test/test-cases.md#tc-ses-04-node-password-change) |
| **FR-BK-01** | Single Backup | [hld.md: Section 3.2](../design/hld.md#32-data-backup-flow-single-object)<br>[lld.md: Section 3.2](../design/lld.md#32-single-object-backup-sequence) | [backup.py](../../src/ibm_storage_protect/data_client/backup.py)<br>[single.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/backup/single.py) | [TC-BK-01](../test/test-cases.md#tc-bk-01-single-object-backup-bytes--generator-streams) |
| **FR-BK-02** | Policy Binding | [hld.md: Section 3.2](../design/hld.md#32-data-backup-flow-single-object) | [single.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/backup/single.py) | [TC-BK-01](../test/test-cases.md#tc-bk-01-single-object-backup-bytes--generator-streams) |
| **FR-BK-03** | Transaction backup | [hld.md: Section 2.3](../design/hld.md#23-transaction-centric-operations) | [single.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/backup/single.py) | [TC-BK-01](../test/test-cases.md#tc-bk-01-single-object-backup-bytes--generator-streams) |
| **FR-BK-04** | Batch Backup | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [batch.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/backup/batch.py) | [TC-BK-03](../test/test-cases.md#tc-bk-03-batch-backup-transactional-safety) |
| **FR-BK-05** | Group Backup | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [group.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/backup/group.py) | [TC-BK-04](../test/test-cases.md#tc-bk-04-logical-group-backup-leader-member-relationship) |
| **FR-RS-01** | Restore | [hld.md: Section 3.3](../design/hld.md#33-data-restore-flow-single-object)<br>[lld.md: Section 3.3](../design/lld.md#33-single-object-restore-sequence) | [restore.py](../../src/ibm_storage_protect/data_client/restore.py)<br>[single.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/restore/single.py) | [TC-RS-01](../test/test-cases.md#tc-rs-01-multi-part-reassembly-ordering) |
| **FR-RS-02** | Part Sorting | [hld.md: Section 3.3](../design/hld.md#33-data-restore-flow-single-object) | [single.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/restore/single.py) | [TC-RS-01](../test/test-cases.md#tc-rs-01-multi-part-reassembly-ordering) |
| **FR-RS-03** | Partial Restore | [lld.md: Section 3.3](../design/lld.md#33-single-object-restore-sequence) | [single.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/restore/single.py) | [TC-RS-02](../test/test-cases.md#tc-rs-02-partial-object-restore-por) |
| **FR-RS-04** | Streaming Generator | [lld.md: Section 3.3](../design/lld.md#33-single-object-restore-sequence) | [single.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/restore/single.py) | [TC-RS-01](../test/test-cases.md#tc-rs-01-multi-part-reassembly-ordering) |
| **FR-RS-05** | Batch Restore | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [batch.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/restore/batch.py) | [TC-RS-02](../test/test-cases.md#tc-rs-02-partial-object-restore-por) |
| **FR-RS-06** | Group Restore | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [group.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/restore/group.py) | [TC-RS-02](../test/test-cases.md#tc-rs-02-partial-object-restore-por) |
| **FR-CT-01** | Filespace Register | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [control.py](../../src/ibm_storage_protect/control.py) | [TC-CT-01](../test/test-cases.md#tc-ct-01-idempotent-filespace-registration) |
| **FR-CT-02** | Filespace Update | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [control.py](../../src/ibm_storage_protect/control.py) | [TC-CT-01](../test/test-cases.md#tc-ct-01-idempotent-filespace-registration) |
| **FR-CT-03** | Filespace Delete | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [control.py](../../src/ibm_storage_protect/control.py) | [TC-BK-03](../test/test-cases.md#tc-bk-03-batch-backup-transactional-safety) |
| **FR-CT-04** | Name Deletion | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [object.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/object.py) | [TC-BK-03](../test/test-cases.md#tc-bk-03-batch-backup-transactional-safety) |
| **FR-CT-05** | ID Deletion | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [object.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/object.py) | [TC-BK-03](../test/test-cases.md#tc-bk-03-batch-backup-transactional-safety) |
| **FR-CT-06** | Object Rename | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [object.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/object.py) | [TC-CT-02](../test/test-cases.md#tc-ct-02-object-renaming-and-version-merging) |
| **FR-CT-07** | Attribute Update | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [object.py](../../src/ibm_storage_protect/c_api_bridge/wrappers/object.py) | [TC-CT-02](../test/test-cases.md#tc-ct-02-object-renaming-and-version-merging) |
| **FR-QY-01** | List Objects | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [query.py](../../src/ibm_storage_protect/query.py) | [TC-QY-01](../test/test-cases.md#tc-qy-01-wildcard-queries-and-object-listing) |
| **FR-QY-02** | Backup Query | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [query.py](../../src/ibm_storage_protect/query.py) | [TC-QY-01](../test/test-cases.md#tc-qy-01-wildcard-queries-and-object-listing) |
| **FR-QY-03** | Group Query | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [query.py](../../src/ibm_storage_protect/query.py) | [TC-BK-05](../test/test-cases.md#tc-bk-05-group-reopen-metadata-load-and-member-modification) |
| **FR-QY-04** | Filespace Query | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [query.py](../../src/ibm_storage_protect/query.py) | [TC-QY-02](../test/test-cases.md#tc-qy-02-filespace-and-management-class-policy-queries) |
| **FR-QY-05** | Mgmt Class Query | [lld.md: Section 1](../design/lld.md#1-module-and-file-architecture) | [query.py](../../src/ibm_storage_protect/query.py) | [TC-QY-02](../test/test-cases.md#tc-qy-02-filespace-and-management-class-policy-queries) |

### 🔍 Verification Gaps
> [!NOTE]
> All functional requirements are fully modeled in the architectural design, fully implemented in the SDK python wrappers, and fully covered (100% trace coverage) in the verification test suite. There are no gaps between features, designs, implementation, and test suites.

---

## 2. Feature-to-Examples Mapping Matrix

This table maps the SDK functional features to user-facing integration example scripts located under the `examples/` directory:
*   **Filesystem Protect Example**: [fs_backup.py](../../examples/filesystem/src/protect_filesystem/fs_backup.py) / [fs_restore.py](../../examples/filesystem/src/protect_filesystem/fs_restore.py)
*   **PostgreSQL Backup Example**: [postgres_backup.py](../../examples/postgre/src/protect_postgre/postgres_backup.py) / [postgres_restore.py](../../examples/postgre/src/protect_postgre/postgres_restore.py)

| Feature ID | Description | Filesystem Example | PostgreSQL Example | Status |
| :--- | :--- | :--- | :--- | :---: |
| **FR-SES-01** | Session login | `fs_backup.py`, `fs_restore.py` | `postgres_backup.py`, `postgres_restore.py` | Covered |
| **FR-SES-02** | Session logout | `fs_backup.py`, `fs_restore.py` | `postgres_backup.py`, `postgres_restore.py` | Covered |
| **FR-SES-03** | Context Manager | - | `postgres_backup.py`, `postgres_restore.py` | Covered |
| **FR-SES-04** | Session Info | - | - | **GAP** |
| **FR-SES-05** | Password Change | - | - | **GAP** |
| **FR-BK-01** | Single Backup | - | `postgres_backup.py` | Covered |
| **FR-BK-02** | Policy Binding | `fs_backup.py` (default) | `postgres_backup.py` (default) | Covered |
| **FR-BK-03** | Transaction backup | - | `postgres_backup.py` | Covered |
| **FR-BK-04** | Batch Backup | - | - | **GAP** |
| **FR-BK-05** | Group Backup | `fs_backup.py` (parallel) | - | Covered |
| **FR-RS-01** | Restore | - | `postgres_restore.py` | Covered |
| **FR-RS-02** | Part Sorting | - | `postgres_restore.py` (implicit) | Covered |
| **FR-RS-03** | Partial Restore | - | - | **GAP** |
| **FR-RS-04** | Streaming Restore | - | `postgres_restore.py` | Covered |
| **FR-RS-05** | Batch Restore | - | - | **GAP** |
| **FR-RS-06** | Group Restore | `fs_restore.py` (parallel) | - | Covered |
| **FR-CT-01** | Filespace Register | `fs_backup.py` | `postgres_backup.py` | Covered |
| **FR-CT-02** | Filespace Update | - | - | **GAP** |
| **FR-CT-03** | Filespace Delete | - | - | **GAP** |
| **FR-CT-04** | Name Deletion | - | - | **GAP** |
| **FR-CT-05** | ID Deletion | - | - | **GAP** |
| **FR-CT-06** | Object Rename | - | - | **GAP** |
| **FR-CT-07** | Attribute Update | - | - | **GAP** |
| **FR-QY-01** | List Objects | - | - | **GAP** |
| **FR-QY-02** | Backup Query | `fs_restore.py` (implicit) | `postgres_restore.py` (implicit) | Covered |
| **FR-QY-03** | Group Query | `fs_restore.py` | - | Covered |
| **FR-QY-04** | Filespace Query | - | - | **GAP** |
| **FR-QY-05** | Mgmt Class Query | - | - | **GAP** |

### 🔍 Identified Example Gaps
> [!WARNING]
> While the test suite fully verifies all features, several advanced features are not showcased in user-facing integration example scripts. The following gaps should be addressed by adding sample scripts to the `examples/` directory:
> 1.  **Session & Password Metadata (`FR-SES-04`, `FR-SES-05`)**: No examples show how to query session compression options or programmatically cycle passwords.
> 2.  **Batch Actions (`FR-BK-04`, `FR-RS-05`)**: No examples demonstrate backing up or restoring lists of files in single transaction batches (outside group backup APIs).
> 3.  **Partial / PIT Restore (`FR-RS-03`)**: No database examples show Point-In-Time restores or retrieving subsets of page tables.
> 4.  **Filespace & Object Management (`FR-CT-02`, `FR-CT-03`, `FR-CT-04`, `FR-CT-05`, `FR-CT-06`, `FR-CT-07`)**: There are no administration script examples demonstrating deleting backup versions, renaming directories, updates, or updating copy policies.
> 5.  **Standalone Queries (`FR-QY-01`, `FR-QY-04`, `FR-QY-05`)**: No examples show wildcards, registered filespace metrics listings, or management class domain lookups.
