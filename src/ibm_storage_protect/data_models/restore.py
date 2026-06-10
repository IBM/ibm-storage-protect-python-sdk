"""
IBM Storage Protect Client SDK - Restore Data Models

This module defines Pydantic data models for restore operations in the IBM Storage
Protect Client SDK. These models provide type-safe, validated interfaces for
single object restores, batch restores, and group restore operations.

Key Responsibilities:
---------------------
1. **Request Models**: Define input structures for restore operations
2. **Result Models**: Define output structures with restored data streams
3. **Validation**: Ensure data integrity through Pydantic validators
4. **Type Safety**: Provide strong typing for all restore operations
5. **Streaming Support**: Enable memory-efficient data retrieval via generators

Model Categories:
-----------------
- Single Restore: RestoreRequest, RestoreResult
- Batch Restore: BatchRestoreRequest, BatchRestoreResult
- Group Restore: GroupRestoreRequest, GroupRestoreMemberResult, GroupRestoreResult

Restore Types Supported:
------------------------
- Full Object Restore: Retrieve entire backed-up object
- Partial Object Restore: Retrieve specific byte range (offset/length)
- Point-in-Time Restore: Retrieve historical version by date
- Batch Restore: Retrieve multiple objects efficiently
- Group Restore: Retrieve all members of a group backup

Data Flow:
----------
1. **User Input**: User creates RestoreRequest/BatchRestoreRequest/GroupRestoreRequest models
2. **Validation**: Pydantic validates all fields and constraints
3. **Query Phase**: System queries for object IDs and metadata
4. **C API Execution**: dsmBeginGetData() initiates restore operation
5. **Data Streaming**: dsmGetObj()/dsmGetData() stream data chunks
6. **Result Mapping**: Data and metadata mapped to RestoreResult models
7. **User Output**: Generator yields data chunks for memory-efficient processing

Field Naming Conventions:
-------------------------
- PascalCase: User-facing fields (Key, Filespace, ObjState, PitDate)
- snake_case: Internal fields and aliases (key, filespace, obj_state)
- Both supported via populate_by_name configuration

Validation Rules:
-----------------
- Keys cannot be empty strings
- Offset and Length must be non-negative
- Object lists must contain at least one item
- Point-in-time dates must be valid datetime objects

Performance Considerations:
---------------------------
- Body generators enable streaming without loading entire object into memory
- Batch restores reduce API overhead for multiple objects
- Partial restores minimize data transfer for large objects
- Chunk size affects memory usage (default: 1MB)

Example Usage:
--------------
    # Single object restore
    restore = RestoreRequest(
        Key="/data/file.txt",
        Filespace="/myfs",
        ObjState=ObjStateEnum.ACTIVE
    )
    result = client.restore(restore)
    with open("restored_file.txt", "wb") as f:
        for chunk in result.Body:
            f.write(chunk)

    # Partial restore (first 1MB)
    partial = RestoreRequest(
        Key="/data/large_file.bin",
        Filespace="/myfs",
        Offset=0,
        Length=1024*1024
    )

    # Batch restore
    batch = BatchRestoreRequest(
        Objects=[
            RestoreRequest(Key="/file1.txt"),
            RestoreRequest(Key="/file2.txt")
        ],
        Filespace="/myfs"
    )

    # Group restore
    group = GroupRestoreRequest(
        Filespace="/myfs",
        GroupLeaderObjIdHi=0,
        GroupLeaderObjIdLo=8251150
    )
    result = client.group_restore(group)
    for member in result.results:
        print(f"Restoring {member.Key}")
        for chunk in member.Body:
            process(chunk)

Notes:
------
- All models support both PascalCase and snake_case field names
- Body field is always a generator for memory efficiency
- Partial restores require Offset and/or Length parameters
- Point-in-time restores retrieve historical versions
- Group restores automatically retrieve all members

See Also:
---------
- c_api_bridge.wrappers.restore: Low-level restore operations
- data_client.client: High-level restore client interface
- data_models.backup: Backup operation data models
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods,line-too-long

from datetime import datetime
from typing import (
    Generator,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from ibm_storage_protect.enums import (
    MountWait as MountWaitEnum,
    ObjState as ObjStateEnum,
    ObjType as ObjTypeEnum,
)


class RestoreRequest(BaseModel):
    """
    Single object restore request model.

    Defines the parameters for restoring a single object from IBM Storage Protect.
    Supports full and partial object restore, point-in-time restore, and various
    object state filters.

    Attributes
    ----------
    key : str
        Object key (path) to restore. Must not be empty.
    filespace : str, default="/"
        Filespace name where object is stored.
    obj_state : ObjStateEnum, default=ObjStateEnum.ACTIVE
        Object state filter (ACTIVE, INACTIVE, ANY_MATCH).
    obj_type : ObjTypeEnum, default=ObjTypeEnum.FILE
        Object type filter (FILE, DIRECTORY, etc.).
    pit_date : datetime, optional
        Point-in-time date for historical restore. None for latest version.
    mount_wait : MountWaitEnum, default=MountWaitEnum.WAIT
        Whether to wait for tape mount if object is on tape.
    offset : int, default=0
        Starting byte offset for partial restore (0 for full restore).
    length : int, default=0
        Number of bytes to restore (0 for full restore from offset to end).
    owner : str, optional
        Object owner name for multi-owner configurations.
    """
    key: str = Field(..., alias="Key", description="Object key path")
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace name")
    obj_state: Optional[ObjStateEnum] = Field(
        default=ObjStateEnum.ACTIVE, alias="ObjState", description="Object state"
    )
    obj_type: Optional[ObjTypeEnum] = Field(
        default=ObjTypeEnum.FILE, alias="ObjType", description="Object type"
    )
    pit_date: Optional[datetime] = Field(
        default=None, alias="PitDate", description="Point-in-time restore date"
    )
    mount_wait: MountWaitEnum = Field(
        default=MountWaitEnum.WAIT, alias="MountWait", description="Wait for tape mount"
    )
    offset: int = Field(default=0, alias="Offset", description="Partial restore offset", ge=0)
    length: int = Field(default=0, alias="Length", description="Partial restore length", ge=0)
    owner: Optional[str] = Field(default=None, alias="Owner", description="Object owner")

    @field_validator("key")
    @classmethod
    def validate_key(cls, value):
        if not value or not value.strip("/"):
            raise ValueError("Key must not be empty")
        return value

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "key": "/data/file.txt",
                "filespace": "/myfs",
                "obj_state": ObjStateEnum.ACTIVE,
                "obj_type": ObjTypeEnum.FILE,
                "offset": 0,
                "length": 0,
            }
        }


class RestoreResult(BaseModel):
    key: str = Field(..., alias="Key", description="Object key path")
    body: Generator[bytes, None, None] = Field(
        ..., alias="Body", description="Restored object data stream"
    )
    last_modified: Optional[datetime] = Field(
        default=None, alias="LastModified", description="Object last modified time"
    )
    object_id: str = Field(default="", alias="ObjectId", description="Object identifier")
    media_class: str = Field(default="", alias="MediaClass", description="Media class")
    management_class: str = Field(
        default="", alias="ManagementClass", description="Management class"
    )

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True


class BatchRestoreRequest(BaseModel):
    objects: List[RestoreRequest] = Field(
        ..., alias="Objects", description="List of objects to restore", min_items=1
    )
    filespace: str = Field(
        default="/", alias="Filespace", description="Default filespace for all objects"
    )

    @field_validator("objects")
    @classmethod
    def validate_objects(cls, value):
        """Validate objects list is not empty."""
        if not value:
            raise ValueError("objects list cannot be empty")
        return value

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "objects": [
                    {"key": "/data/file1.txt"},
                    {"key": "/data/file2.txt", "offset": 0, "length": 0},
                ],
                "filespace": "/myfs",
            }
        }


class BatchRestoreResult(BaseModel):
    results: List[RestoreResult] = Field(..., alias="Results", description="Restored objects")
    total_objects: int = Field(
        ..., alias="TotalObjects", description="Total objects restored", ge=0
    )

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True


class GroupRestoreRequest(BaseModel):
    filespace: str = Field(default="/", alias="Filespace", description="Filespace name")
    group_leader_obj_id_hi: int = Field(
        ..., alias="GroupLeaderObjIdHi", description="Group leader object id high part", ge=0
    )
    group_leader_obj_id_lo: int = Field(
        ..., alias="GroupLeaderObjIdLo", description="Group leader object id low part", ge=0
    )
    owner: Optional[str] = Field(default=None, alias="Owner", description="Object owner")
    obj_type: Optional[ObjTypeEnum] = Field(default=ObjTypeEnum.FILE, alias="ObjType", description="Object type")
    mount_wait: MountWaitEnum = Field(
        default=MountWaitEnum.WAIT, alias="MountWait", description="Wait for tape mount"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "group_leader_obj_id_hi": 12345,
                "group_leader_obj_id_lo": 67890,
            }
        }


class GroupRestoreMemberResult(BaseModel):
    key: str = Field(..., alias="Key", description="Object key path")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    body: Generator[bytes, None, None] = Field(..., alias="Body", description="Restored object data stream")
    is_group_leader: bool = Field(default=False, alias="IsGroupLeader", description="Whether this object is the group leader")
    last_modified: Optional[datetime] = Field(default=None, alias="LastModified", description="Object last modified time")
    object_id: str = Field(default="", alias="ObjectId", description="Object identifier")
    media_class: str = Field(default="", alias="MediaClass", description="Media class")
    management_class: str = Field(default="", alias="ManagementClass", description="Management class")

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True


class GroupRestoreResult(BaseModel):
    results: List[GroupRestoreMemberResult] = Field(..., alias="Results", description="Restored group members")
    total_objects: int = Field(..., alias="TotalObjects", description="Total objects restored", ge=0)

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
