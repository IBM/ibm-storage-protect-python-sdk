"""
IBM Storage Protect Client API - Batch Backup Operations

This module provides Python wrappers for IBM Storage Protect batch backup operations,
enabling efficient data protection through multi-object backups using the IBM Storage
Protect Client API.

Key Responsibilities:
---------------------
1. **Batch Backup**: Efficiently back up multiple objects in transactions
2. **Transaction Optimization**: Group objects to reduce transaction overhead
3. **Atomic Operations**: Ensure all-or-nothing backup for each batch
4. **Error Recovery**: Automatic transaction abort on failures

Batch Backup Workflow:
----------------------
1. **Group Objects**: Divide objects into batches based on max_per_txn
2. **Begin Transaction**: Start transaction for each batch
3. **Send Objects**: Back up all objects in batch within transaction
4. **Commit Transaction**: Complete batch backup atomically
5. **Error Handling**: Abort transaction on any failure

Thread Safety:
--------------
Batch operations are NOT thread-safe when using the same session handle.
Each thread should maintain its own session handle for concurrent operations.

Performance Considerations:
---------------------------
- Use batch operations for multiple small objects (reduces transaction overhead)
- Adjust max_per_txn based on object sizes and network conditions
- Larger batches reduce overhead but increase rollback cost on failure
- Recommended: 10-50 objects per transaction for small files

Client API Integration:
-----------------------
This module uses BackupOperation for individual object backups within
a shared transaction context, optimizing the backup workflow.

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
Chapters: "Backup Operations", "Transaction Management"

Example Usage:
--------------
    # Batch backup
    batch_op = BatchBackupOperation(
        session=session,
        objects=[obj1, obj2, obj3],
        filespace="/myfs",
        max_per_txn=10
    )
    results = batch_op.execute()
"""

from typing import Optional

# pylint: disable=protected-access,too-many-arguments,too-many-positional-arguments


from ibm_storage_protect.c_api_bridge.c_api.structs import DSM_OBJ_FILE
from ibm_storage_protect.logger import get_logger
from ibm_storage_protect.c_api_bridge.wrappers.helper import parse_key, get_session_owner
from .single import BackupOperation

_logger = get_logger(__name__)


class BatchBackupOperation:
    """
    Batch backup operation handler for multiple objects.

    Efficiently backs up multiple objects by grouping them into transactions,
    reducing overhead compared to individual backups. Optimizes performance
    for scenarios with many small objects.

    Attributes
    ----------
    session : Session
        The active IBM Storage Protect session.
    objects : list
        List of object dictionaries to back up.
    filespace : str
        The filespace name for all objects.
    max_per_txn : int
        Maximum objects per transaction (default: 1).

    Notes
    -----
    - Groups objects into transactions for efficiency
    - Each transaction is atomic (all-or-nothing)
    - Failed transactions are automatically aborted
    - Suitable for backing up many small objects

    Example
    -------
    >>> batch_op = BatchBackupOperation(
    ...     session=session,
    ...     objects=[obj1, obj2, obj3],
    ...     filespace="/myfs",
    ...     max_per_txn=10
    ... )
    >>> results = batch_op.execute()
    """

    def __init__(
        self,
        session,
        objects,
        filespace,
        max_per_txn=1,
        session_handle: Optional[str] = None,
        object_key: Optional[str] = None
    ):
        """
        Initialize the batch backup operation.

        Parameters
        ----------
        session : Session
            The active IBM Storage Protect session wrapper.
        objects : list
            List of dictionaries representing objects to back up (must contain "Key" and "Body").
        filespace : str
            The destination filespace name for all objects in the batch.
        max_per_txn : int, optional
            Maximum number of backup operations grouped within a single transaction (default: 1).
        session_handle : str, optional
            Correlation ID for session logging.
        object_key : str, optional
            Correlation ID for object logging.
        """
        self.session = session
        self.objects = objects
        self.filespace = filespace
        self.max_per_txn = max(1, max_per_txn)
        self.session_handle = session_handle
        self.object_key = object_key

    def execute(self):
        """
        Execute batch backup operation for all objects.

        Processes objects in batches, creating transactions for each batch
        and backing up all objects within each transaction.

        Returns
        -------
        list
            List of backup results, one per object.
        """
        _logger.info(
            "Executing batch backup operation",
            extra={
                'event_type': 'c_api.backup.batch.execute.started',
                'filespace': self.filespace,
                'object_count': len(self.objects),
                'max_per_txn': self.max_per_txn,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        results = []
        for i in range(0, len(self.objects), self.max_per_txn):
            batch = self.objects[i:i + self.max_per_txn]
            _logger.debug(
                "Processing batch backup chunk",
                extra={
                    'event_type': 'c_api.backup.batch.chunk.started',
                    'batch_start': i,
                    'batch_size': len(batch),
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                }
            )
            results.extend(self._run_batch(batch))
        _logger.info(
            "Batch backup operation completed",
            extra={
                'event_type': 'c_api.backup.batch.execute.completed',
                'filespace': self.filespace,
                'result_count': len(results),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        return results

    def _run_batch(self, batch):
        """
        Run a single batch of objects within one transaction.

        Parameters
        ----------
        batch : list
            List of objects to back up in this transaction.

        Returns
        -------
        list
            List of backup results for objects in this batch.
        """
        _logger.debug(
            "Running batch backup transaction",
            extra={
                'event_type': 'c_api.backup.batch.run.started',
                'batch_size': len(batch),
                'filespace': self.filespace,
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        def _empty_data():
            """
            Create an empty generator for transaction initialization.

            This generator is used to initialize a transaction without sending data,
            allowing the transaction context to be established for batch operations.

            Yields
            ------
            None
                Never yields any data (empty generator).
            """
            yield from ()

        txn_op = BackupOperation(
            session=self.session,
            filespace=self.filespace,
            high_level="/",
            low_level="/",
            data_source=_empty_data(),
            session_handle=self.session_handle,
            object_key=self.object_key,
        )
        txn_op._begin_transaction()
        results = []
        try:
            for obj in batch:
                _logger.debug(
                    "Sending object within batch transaction",
                    extra={
                        'event_type': 'c_api.backup.batch.object.started',
                        'key': obj["Key"],
                        'session_handle': self.session_handle,
                        'object_key': self.object_key
                    }
                )
                op = self._make_op(obj)
                op.send_within_txn()
                results.append({
                    "status": "success",
                    "filespace": self.filespace,
                    "Key": obj["Key"],
                    "stats": op.get_stats(),
                })
            txn_op._commit_transaction()
        except Exception:
            _logger.error(
                "Batch backup transaction failed",
                extra={
                    'event_type': 'c_api.backup.batch.run.failed',
                    'filespace': self.filespace,
                    'session_handle': self.session_handle,
                    'object_key': self.object_key
                },
                exc_info=True
            )
            txn_op._abort_transaction()
            raise
        _logger.debug(
            "Batch backup transaction completed",
            extra={
                'event_type': 'c_api.backup.batch.run.completed',
                'result_count': len(results),
                'session_handle': self.session_handle,
                'object_key': self.object_key
            }
        )
        return results

    def _make_op(self, obj):
        """
        Create a BackupOperation instance for an object.

        Parameters
        ----------
        obj : dict
            Object dictionary with Key, Body, and optional attributes.

        Returns
        -------
        BackupOperation
            Configured backup operation for the object.
        """
        hl, ll = parse_key(obj["Key"])
        return BackupOperation(
            session=self.session,
            filespace=self.filespace,
            high_level=hl,
            low_level=ll,
            data_source=obj["Body"],
            obj_type=obj.get("ObjType", DSM_OBJ_FILE),
            owner=obj.get("Owner", get_session_owner(self.session)),
            management_class=obj.get("ManagementClass"),
            size_estimate=obj.get("SizeEstimate", 1024),
            pre_compressed=obj.get("PreCompressed", False),
            mount_wait=obj.get("MountWait", True),
            obj_info=obj.get("ObjInfo"),
            disable_dedup=obj.get("DisableDedup", False),
            session_handle=self.session_handle,
            object_key=self.object_key,
        )
