"""
IBM Storage Protect Client SDK - Backup Data Models

This module defines Pydantic data models for backup operations in the IBM Storage
Protect Client SDK. These models provide type-safe, validated interfaces for
single object backups, batch backups, and group backup management.

Key Responsibilities:
---------------------
1. **Request Models**: Define input structures for backup operations
2. **Result Models**: Define output structures with operation results
3. **Internal Models**: Bridge between user-facing and C API layers
4. **Validation**: Ensure data integrity through Pydantic validators
5. **Type Safety**: Provide strong typing for all backup operations

Model Categories:
-----------------
- Single Backup: BackupRequest, BackupResult, BackupRequestInternal
- Batch Backup: BatchBackupRequest, BatchBackupResult, BatchBackupInternal
- Group Backup: GroupBackupRequest, GroupBackupResult, GroupBackupInternal
- Group Operations: BeginGroupBackupRequest, ReopenGroupBackupRequest, GroupRemoveMembersRequest,
                   GroupAssignToMembersRequest, GroupDeleteRequest
- Response Models: LeaderResponse, MemberResponse, GroupOperationResult

Data Flow:
----------
1. **User Input**: User creates BackupRequest/BatchBackupRequest/GroupBackupRequest models
2. **Validation**: Pydantic validates all fields and constraints
3. **Internal Conversion**: Models converted to BackupRequestInternal for C API
4. **C API Execution**: Internal models passed to backup operations
5. **Result Mapping**: C API results mapped to BackupResult models
6. **User Output**: Validated result models returned to user

Field Naming Conventions:
-------------------------
- PascalCase: User-facing fields (Key, Body, Filespace, ManagementClass)
- snake_case: Internal fields and aliases (key, body, filespace)
- Both supported via populate_by_name configuration

Validation Rules:
-----------------
- Keys and filespaces cannot be empty strings
- Object lists must contain at least one item
- Object IDs must have both 'hi' and 'lo' components
- Size estimates and counts must be non-negative
- Group tags must be non-empty strings

Example Usage:
--------------
    # Single object backup
    backup = BackupRequest(
        Key="/data/file.txt",
        Body=b"file content",
        Filespace="/myfs",
        ManagementClass="STANDARD",
        SizeEstimate=1024
    )

    # Batch backup
    batch = BatchBackupRequest(
        Objects=[
            BackupRequest(Key="/file1.txt", Body=b"content1"),
            BackupRequest(Key="/file2.txt", Body=b"content2")
        ],
        Filespace="/myfs",
        MaxPerTxn=10
    )

    # Group backup (via client.create_group())
    group = client.create_group("my-group", filespace="/myfs")
    group.add_leader(BackupRequest(Key="/leader.json", Body=b"{}"))
    group.add_member(BackupRequest(Key="/member1.dat", Body=b"data"))
    group.close()

Notes:
------
- All models support both PascalCase and snake_case field names
- Body field accepts bytes, file-like objects, or generators
- Internal models are not intended for direct user instantiation
- Group operations require proper leader/member relationship management
- Statistics are optional and depend on server configuration

See Also:
---------
- c_api_bridge.wrappers.backup: Low-level backup operations
- data_client.client: High-level backup client interface
- data_models.restore: Restore operation data models
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods,line-too-long

import io
from typing import (
    Generator,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from ibm_storage_protect.enums import (
    MountWait as MountWaitEnum,
    ObjState as ObjStateEnum,
    ObjType as ObjectType,
   )


class BackupRequest(BaseModel):
    """
    Single object backup request model.

    Defines the parameters for backing up a single object to IBM Storage Protect.
    Supports various data sources (bytes, streams, generators) and allows control
    over compression, deduplication, and storage management.

    Attributes
    ----------
    key : str
        Object key (path) in the filespace. Must not be empty.
    body : Union[bytes, io.BufferedIOBase, Generator[bytes, None, None]]
        Object data source. Can be raw bytes, file-like object, or generator.
    filespace : str, default="/"
        Filespace name where object will be stored.
    management_class : str, optional
        Management class name for storage policy override.
    obj_type : ObjectType, default=ObjectType.FILE
        Object type (FILE, DIRECTORY, etc.).
    owner : str, optional
        Object owner name. Defaults to session owner if not specified.
    size_estimate : int, default=0
        Estimated object size in bytes for buffer allocation optimization.
    pre_compressed : bool, default=False
        If True, skip server-side compression (data already compressed).
    mount_wait : MountWaitEnum, default=MountWaitEnum.WAIT
        Whether to wait for tape mount if object goes to tape storage.
    obj_info : Union[str, bytes], optional
        Application-specific metadata (max 1024 bytes extended, 255 standard).
    disable_dedup : bool, default=False
        If True, disable server-side deduplication for this object.
    """
    key: str = Field(..., alias="Key", description="Object key path")
    body: Union[bytes, io.BufferedIOBase, Generator[bytes, None, None]] = Field(..., alias="Body", description="Object data source")
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace name")
    management_class: Optional[str] = Field(default=None, alias="ManagementClass", description="Management class name")
    obj_type: Optional[ObjectType] = Field(default=ObjectType.FILE, alias="ObjType", description="Object type")
    owner: Optional[str] = Field(default=None, alias="Owner", description="Object owner")
    size_estimate: int= Field(default=0, alias="SizeEstimate", description="Estimated object size in bytes", ge=0)
    pre_compressed: bool = Field(default=False, alias="PreCompressed", description="Data is pre-compressed")
    mount_wait: MountWaitEnum = Field(default=MountWaitEnum.WAIT, alias="MountWait", description="Wait for tape mount")
    obj_info: Optional[Union[str, bytes]] = Field(default=None, alias="ObjInfo", description="Additional object information")
    disable_dedup: bool = Field(default=False, alias="DisableDedup", description="Disable deduplication")

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "key": "/data/file.txt",
                "body": b"file content",
                "filespace": "/myfs",
                "management_class": "STANDARD"
            }
        }
class ObjectReference(BaseModel):
    key: str = Field(..., alias="Key", description="Object key path")
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace name")
    obj_state: Optional[ObjStateEnum] = Field(default=ObjStateEnum.ACTIVE, alias="ObjState", description="Object state")
    obj_type: Optional[ObjectType] = Field(default=ObjectType.FILE, alias="ObjType", description="Object type")

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        """Validate filespace is not empty."""
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        """Validate key is not empty."""
        if not v or not v.strip():
            raise ValueError("Key cannot be empty")
        return v

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "key": "/data/file.txt"
            }
        }


class BackupInternal(BaseModel):
    """
    Internal backup model for C API layer.

    Bridges user-facing BackupRequest model and low-level C API backup operations.
    Contains normalized and validated parameters ready for C API consumption.
    Not intended for direct user instantiation.

    Attributes
    ----------
    handle : int
        Session handle from dsmInitEx().
    filespace : str
        Normalized filespace name.
    high_level : str
        High-level path component (directory portion).
    low_level : str
        Low-level path component (filename portion).
    data_source : Union[bytes, io.BufferedIOBase, Generator[bytes, None, None]]
        Validated data source ready for streaming.
    obj_type : int
        Object type code (0x01 for FILE, 0x02 for DIRECTORY).
    owner : str
        Object owner name (empty string if not specified).
    management_class : str, optional
        Management class name for policy override.
    size_estimate : int
        Size estimate in bytes (minimum 1024 if not specified).
    pre_compressed : bool
        Pre-compression flag for C API.
    mount_wait : bool
        Mount wait flag for C API.
    obj_info : bytes, optional
        Object info as bytes for C API.
    disable_dedup : bool
        Deduplication disable flag for C API.

    Notes
    -----
    - Created by data_client layer from BackupRequest models
    - Key is split into high_level and low_level components
    - Enum values converted to integer codes
    - All strings converted to appropriate encodings
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    high_level: str = Field(..., description="High-level path")
    low_level: str = Field(..., description="Low-level path")
    data_source: Union[bytes, io.BufferedIOBase, Generator[bytes, None, None]] = Field(..., description="Data source")
    obj_type: int = Field(default=0x01, description="Object type code")
    owner: str = Field(default="", description="Object owner")
    management_class: Optional[str] = Field(default=None, description="Management class")
    size_estimate: int = Field(default=0, description="Size estimate", ge=0)
    pre_compressed: bool = Field(default=False, description="Pre-compressed flag")
    mount_wait: bool = Field(default=True, description="Mount wait flag")
    obj_info: Optional[bytes] = Field(default=None, description="Object info bytes")
    disable_dedup: bool = Field(default=False, description="Disable dedup flag")

    class Config:
        arbitrary_types_allowed = True


class BackupResult(BaseModel):
    """
    Single object backup operation result.

    Contains the outcome and statistics from a backup operation.
    Returned by DataClient.backup() method.

    Attributes
    ----------
    status : str
        Operation status ("success" or "failed").
    filespace : str
        Filespace where object was backed up.
    high_level : str
        High-level path component of backed up object.
    low_level : str
        Low-level path component of backed up object.
    stats : dict, optional
        Backup statistics including bytes sent, compression, deduplication.

    Notes
    -----
    - Stats dictionary structure depends on server configuration
    - Common stats: total_bytes_sent, compressed, deduplicated
    - Group backups include group_leader_obj_id in stats
    """
    status: str = Field(..., alias="Status", description="Operation status")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    high_level: str = Field(..., alias="HighLevel", description="High-level path")
    low_level: str = Field(..., alias="LowLevel", description="Low-level path")
    stats: Optional[dict] = Field(default=None, alias="Stats", description="Backup statistics")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "filespace": "/myfs",
                "high_level": "/data",
                "low_level": "file.txt",
                "stats": {
                    "total_bytes_sent": 1024,
                    "compressed": True,
                    "deduplicated": False
                }
            }
        }


class BatchBackupRequest(BaseModel):
    objects: List[BackupRequest] = Field(..., alias="Objects", description="List of objects to backup", min_items=1)
    filespace: str = Field(default="/", alias="Filespace", description="Filespace for all objects")
    max_per_txn: int = Field(default=1, alias="MaxPerTxn", description="Maximum objects per transaction", ge=1)

    @field_validator('objects')
    @classmethod
    def validate_objects(cls, v):
        """Validate objects list is not empty."""
        if not v:
            raise ValueError("objects list cannot be empty")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "objects": [
                    {"key": "/data/file1.txt", "body": b"content1"},
                    {"key": "/data/file2.txt", "body": b"content2"}
                ],
                "filespace": "/myfs",
                "max_per_txn": 10
            }
        }


class BatchBackupInternal(BaseModel):
    """
    Internal batch backup model for C API layer.

    Bridges user-facing BatchBackupRequest model and low-level C API batch operations.
    Not intended for direct user instantiation.

    Attributes
    ----------
    handle : int
        Session handle from dsmInitEx().
    objects : List[dict]
        List of internal object dictionaries ready for C API.
    filespace : str
        Filespace name for all objects.
    max_per_txn : int
        Maximum objects per transaction.
    """
    handle: int = Field(..., description="Session handle")
    objects: List[dict] = Field(..., description="Internal object list")
    filespace: str = Field(..., description="Filespace name")
    max_per_txn: int = Field(default=1, description="Max per transaction", ge=1)

    class Config:
        arbitrary_types_allowed = True


class BatchBackupResult(BaseModel):
    """
    Batch backup operation result.

    Contains overall status and individual results for each object in the batch.
    Returned by DataClient.batch_backup() method.

    Attributes
    ----------
    status : str
        Overall operation status ("success" or "partial" or "failed").
    results : List[dict]
        Individual results for each object with status and stats.
    total_objects : int
        Total number of objects processed.
    successful : int
        Number of successfully backed up objects.
    failed : int
        Number of failed backup attempts.

    Notes
    -----
    - Status is "success" only if all objects succeed
    - Status is "partial" if some objects succeed and some fail
    - Status is "failed" if all objects fail
    - Each result dict contains: Key, status, stats (if successful)
    """
    status: str = Field(..., alias="Status", description="Overall status")
    results: List[dict] = Field(..., alias="Results", description="Individual object results")
    total_objects: int = Field(..., alias="TotalObjects", description="Total objects processed", ge=0)
    successful: int = Field(..., alias="Successful", description="Successful backups", ge=0)
    failed: int = Field(..., alias="Failed", description="Failed backups", ge=0)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "results": [
                    {"Key": "/data/file1.txt", "status": "success"},
                    {"Key": "/data/file2.txt", "status": "success"}
                ],
                "total_objects": 2,
                "successful": 2,
                "failed": 0
            }
        }


class GroupBackupRequest(BaseModel):
    group_tag: str = Field(..., alias="GroupTag", description="Unique group identifier")
    leader: BackupRequest = Field(..., alias="Leader", description="Group leader object (required)")
    members: Optional[List[BackupRequest]] = Field(default=None, alias="Members", description="Group member objects (optional)")
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace for group")

    @field_validator('group_tag')
    @classmethod
    def validate_group_tag(cls, v):
        if not v or not v.strip():
            raise ValueError("GroupTag cannot be empty")
        return v

    @field_validator('leader')
    @classmethod
    def validate_leader(cls, v):
        if not v:
            raise ValueError("Leader is required")
        return v

    class Config:
        populate_by_name = True  # Allow both PascalCase and snake_case
        json_schema_extra = {
            "example": {
                "group_tag": "backup-group-001",
                "leader": {"key": "/data/leader.txt", "body": b"leader content"},
                "members": [
                    {"key": "/data/member1.txt", "body": b"member1 content"},
                    {"key": "/data/member2.txt", "body": b"member2 content"}
                ],
                "filespace": "/myfs"
            }
        }


class GroupBackupInternal(BaseModel):
    """
    Internal C-API-ready representation of a group backup request.

    This model stores the normalized values passed down from the data client layer:
    session handle, effective filespace, encoded group tag, and the prepared member
    dictionaries derived from [`BackupRequest`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:98)
    objects.

    Notes
    -----
    - [`group_tag`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:508)
      is stored as bytes because the lower layer expects encoded values.
    - [`members`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:509)
      contains already transformed dictionaries, similar to the structure produced
      by [`DataClient._prepare_backup_dict()`](sp-client-sdk/src/ibm_storage_protect/data_client/client.py:2181).
    - Not intended for direct user instantiation.
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    group_tag: bytes = Field(..., description="Group tag bytes")
    members: List[dict] = Field(..., description="Internal member list")

    class Config:
        arbitrary_types_allowed = True


class LeaderResponse(BaseModel):
    """
    Result details for the leader object of a group backup.

    This nested response appears inside
    [`GroupBackupResult`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:545)
    and represents the special leader object that anchors the group.

    Notes
    -----
    - [`stats`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:517)
      contains the per-object backup statistics returned for the leader.
    - [`metadata`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:518)
      can include extra leader-specific details when the lower layer provides them.
    """
    key: str = Field(..., alias="Key", description="Leader object key")
    stats: dict = Field(..., description="Backup statistics")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")

    class Config:
        populate_by_name = True  # Allow both 'key' and 'Key'
        json_schema_extra = {
            "example": {
                "key": "/db/metadata.json",
                "stats": {"total_bytes_sent": 1024, "compressed": True},
                "metadata": {}
            }
        }


class MemberResponse(BaseModel):
    """
    Result details for a non-leader member object in a group backup.

    This nested response appears in
    [`GroupBackupResult.members`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:552).

    Notes
    -----
    - [`key`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:532)
      identifies the member object within the group.
    - [`stats`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:533)
      contains the per-member backup statistics produced by the operation.
    """
    key: str = Field(..., alias="Key", description="Member object key")
    stats: dict = Field(..., description="Backup statistics")

    class Config:
        populate_by_name = True  # Allow both 'key' and 'Key'
        json_schema_extra = {
            "example": {
                "key": "/db/table1.dat",
                "stats": {"total_bytes_sent": 2048, "compressed": True}
            }
        }


class GroupBackupResult(BaseModel):
    status: str = Field(..., description="Operation status")
    group_tag: str = Field(..., alias="GroupTag", description="Group tag")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    group_leader_obj_id: str = Field(..., alias="GroupLeaderObjId", description="Group leader object ID (formatted as hi-lo)")
    group_leader_obj_id_raw: dict = Field(..., alias="GroupLeaderObjIdRaw", description="Raw group leader object ID with hi/lo parts")
    leader: LeaderResponse = Field(..., alias="Leader", description="Leader object details")
    members: List[MemberResponse] = Field(default_factory=list, alias="Members", description="Member objects")
    total_objects: int = Field(..., alias="TotalObjects", description="Total objects in group", ge=1)
    duration_ms: float = Field(..., alias="DurationMs", description="Operation duration in milliseconds")

    class Config:
        populate_by_name = True  # Allow both snake_case and PascalCase
        json_schema_extra = {
            "example": {
                "status": "success",
                "group_tag": "backup-group-001",
                "filespace": "/myfs",
                "group_leader_obj_id": "0-8251150",
                "group_leader_obj_id_raw": {"hi": 0, "lo": 8251150},
                "leader": {"key": "/data/leader.txt", "stats": {}},
                "members": [{"key": "/data/member1.txt", "stats": {}}],
                "total_objects": 2,
                "duration_ms": 1234.56
            }
        }


class BeginGroupBackupRequest(BaseModel):
    group_tag: str = Field(..., alias="GroupTag", description="Unique group identifier")
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace for group")

    @field_validator('group_tag')
    @classmethod
    def validate_group_tag(cls, v):
        if not v or not v.strip():
            raise ValueError("GroupTag cannot be empty")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "group_tag": "my-backup-group",
                "filespace": "/myfs"
            }
        }


class ReopenGroupBackupRequest(BaseModel):
    group_tag: str = Field(..., alias="GroupTag", description="Group identifier to reopen")
    group_leader_obj_id_hi: int = Field(..., alias="GroupLeaderObjIdHi", description="High part of group leader object ID", ge=0)
    group_leader_obj_id_lo: int = Field(..., alias="GroupLeaderObjIdLo", description="Low part of group leader object ID", ge=0)
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace for group")

    @field_validator('group_tag')
    @classmethod
    def validate_group_tag(cls, v):
        if not v or not v.strip():
            raise ValueError("GroupTag cannot be empty")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "group_tag": "existing-backup-group",
                "group_leader_obj_id_hi": 0,
                "group_leader_obj_id_lo": 8251150,
                "filespace": "/"
            }
        }


class RemoveMemberResponse(BaseModel):
    """
    Response model for removing members from a backup group.

    This summarizes the outcome of a member-removal operation.

    Notes
    -----
    - [`removed_count`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:712)
      indicates how many requested members were removed from the group.
    - [`removed_keys`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:713)
      lists the detached object keys when available from the operation result.
    - [`duration_ms`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:714)
      records elapsed execution time.
    """
    status: str = Field(..., alias="Status", description="Operation status")
    group_tag: str = Field(..., alias="GroupTag", description="Group identifier")
    removed_count: int = Field(..., alias="RemovedCount", description="Number of members removed", ge=0)
    removed_keys: List[str] = Field(..., alias="RemovedKeys", description="Keys of removed objects")
    duration_ms: float = Field(..., alias="DurationMs", description="Operation duration in milliseconds")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "group_tag": "my-backup-group",
                "removed_count": 2,
                "removed_keys": ["/db/old-file1.dat", "/db/old-file2.dat"],
                "duration_ms": 567.89
            }
        }


class AssignMemberResponse(BaseModel):
    """
    Response model for assigning members to a backup group.

    This summarizes the outcome of a group member assignment request.

    Notes
    -----
    - [`assigned_count`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:732)
      reports how many member object IDs were successfully associated with the group.
    - [`assigned_keys`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:733)
      provides the corresponding object keys when available.
    - [`duration_ms`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:734)
      captures the total client-side operation duration.
    """
    status: str = Field(..., alias="Status", description="Operation status")
    group_tag: str = Field(..., alias="GroupTag", description="Group identifier")
    assigned_count: int = Field(..., alias="AssignedCount", description="Number of members assigned", ge=0)
    assigned_keys: List[str] = Field(..., alias="AssignedKeys", description="Keys of assigned objects")
    duration_ms: float = Field(..., alias="DurationMs", description="Operation duration in milliseconds")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "group_tag": "target-backup-group",
                "assigned_count": 2,
                "assigned_keys": ["/db/archive1.dat", "/db/archive2.dat"],
                "duration_ms": 456.78
            }
        }


class DeleteGroupResponse(BaseModel):
    """
    Response model for backup group deletion.

    This captures the high-level outcome returned by the group delete flow after
    the specified group leader and associated group definition are removed.

    Notes
    -----
    - [`group_tag`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:751)
      identifies the deleted group.
    - [`leader_key`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:752)
      provides the object key of the deleted leader entry for traceability.
    - [`duration_ms`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:753)
      records elapsed execution time reported by the client layer.
    """
    status: str = Field(..., alias="Status", description="Operation status")
    group_tag: str = Field(..., alias="GroupTag", description="Deleted group tag")
    leader_key: str = Field(..., alias="LeaderKey", description="Deleted leader key")
    duration_ms: float = Field(..., alias="DurationMs", description="Operation duration in milliseconds")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "group_tag": "old-backup-group",
                "leader_key": "/backups/manifest.json",
                "duration_ms": 345.67
            }
        }


class GroupRemoveMembersRequest(BaseModel):
    group_tag: str = Field(..., alias="GroupTag", description="Group identifier")
    group_leader_obj_id_hi: int = Field(..., alias="GroupLeaderObjIdHi", description="High part of leader object ID", ge=0)
    group_leader_obj_id_lo: int = Field(..., alias="GroupLeaderObjIdLo", description="Low part of leader object ID", ge=0)
    member_obj_ids: List[dict] = Field(..., alias="MemberObjIds", description="List of member object IDs to remove", min_items=1)
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace for group")

    @field_validator('member_obj_ids')
    @classmethod
    def validate_member_obj_ids(cls, v):
        if not v:
            raise ValueError("MemberObjIds cannot be empty")
        for obj_id in v:
            if 'hi' not in obj_id or 'lo' not in obj_id:
                raise ValueError("Each object ID must have 'hi' and 'lo' fields")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "group_tag": "my-backup-group",
                "group_leader_obj_id_hi": 0,
                "group_leader_obj_id_lo": 8251150,
                "member_obj_ids": [
                    {"hi": 0, "lo": 8251151},
                    {"hi": 0, "lo": 8251152}
                ],
                "filespace": "/"
            }
        }


class GroupAssignToMembersRequest(BaseModel):
    group_tag: str = Field(..., alias="GroupTag", description="Group identifier")
    group_leader_obj_id_hi: int = Field(..., alias="GroupLeaderObjIdHi", description="High part of target group leader object ID", ge=0)
    group_leader_obj_id_lo: int = Field(..., alias="GroupLeaderObjIdLo", description="Low part of target group leader object ID", ge=0)
    member_obj_ids: List[dict] = Field(..., alias="MemberObjIds", description="List of member object IDs to assign to the group", min_items=1)
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace for group")

    @field_validator('member_obj_ids')
    @classmethod
    def validate_member_obj_ids(cls, v):
        if not v:
            raise ValueError("MemberObjIds cannot be empty")
        for obj_id in v:
            if 'hi' not in obj_id or 'lo' not in obj_id:
                raise ValueError("Each object ID must have 'hi' and 'lo' fields")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "group_tag": "target-backup-group",
                "group_leader_obj_id_hi": 0,
                "group_leader_obj_id_lo": 8251150,
                "member_obj_ids": [
                    {"hi": 0, "lo": 8251151},
                    {"hi": 0, "lo": 8251152}
                ],
                "filespace": "/"
            }
        }


class GroupDeleteRequest(BaseModel):
    group_tag: str = Field(..., alias="GroupTag", description="Group identifier to delete")
    group_leader_obj_id_hi: int = Field(..., alias="GroupLeaderObjIdHi", description="High part of leader object ID", ge=0)
    group_leader_obj_id_lo: int = Field(..., alias="GroupLeaderObjIdLo", description="Low part of leader object ID", ge=0)
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace for group")

    @field_validator('group_tag')
    @classmethod
    def validate_group_tag(cls, v):
        if not v or not v.strip():
            raise ValueError("GroupTag cannot be empty")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "group_tag": "old-backup-group",
                "group_leader_obj_id_hi": 0,
                "group_leader_obj_id_lo": 8251150,
                "filespace": "/"
            }
        }


class GroupOperationResult(BaseModel):
    """
    Generic response model for group-management operations.

    This lightweight result container is suitable for operations in
    [`client.py`](sp-client-sdk/src/ibm_storage_protect/data_client/client.py)
    that primarily return a completion status plus an optional human-readable
    message rather than object-level details.

    Notes
    -----
    - [`status`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:955)
      typically reflects success or failure of the requested operation.
    - [`message`](sp-client-sdk/src/ibm_storage_protect/data_models/backup.py:956)
      can carry additional context from the client or lower API layers.
    """
    status: str = Field(..., alias="Status", description="Operation status")
    message: Optional[str] = Field(default=None, alias="Message", description="Optional message")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully"
            }
        }


class BackupStats(BaseModel):
    """
    Statistics for backup operations.

    Tracks data transfer metrics including compression and deduplication.
    """
    total_bytes_sent: int = Field(..., alias="TotalBytesSent", description="Total bytes sent", ge=0)
    compressed: bool = Field(..., alias="Compressed", description="Object was compressed")
    compressed_size: int = Field(default=0, alias="CompressedSize", description="Compressed size", ge=0)
    deduplicated: bool = Field(..., alias="Deduplicated", description="Object was deduplicated")
    dedup_size: int = Field(default=0, alias="DedupSize", description="Deduplicated size", ge=0)
    group_leader_obj_id: Optional[str] = Field(default=None, alias="GroupLeaderObjId", description="Group leader object ID")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "total_bytes_sent": 1048576,
                "compressed": True,
                "compressed_size": 524288,
                "deduplicated": False,
                "dedup_size": 0,
                "GroupLeaderObjId": None
            }
        }
