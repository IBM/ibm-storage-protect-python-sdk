"""
IBM Storage Protect SDK - Query Data Models

This module defines Pydantic data models for query operations in the IBM Storage
Protect SDK. These models provide type-safe request/response structures with
automatic validation, serialization, and documentation.

Model Categories:
-----------------
1. **Request Models**: User-facing models for query requests
   - GroupQueryRequest, BackupQueryRequest, ListObjectsRequest, etc.

2. **Internal Models**: Internal models for C API translation
   - GroupQueryRequestInternal, BackupQueryRequestInternal, etc.

3. **Response Models**: Models for query results
   - GroupQueryRequestResult, BackupQueryRequestResult, etc.

4. **Metadata Models**: Models for object metadata
   - ObjectMetadata, QueryObjectResult

Key Features:
-------------
- **Automatic Validation**: Pydantic validates all fields on instantiation
- **Type Safety**: Full type hints for IDE support and type checking
- **Flexible Aliases**: Support both snake_case and PascalCase field names
- **JSON Schema**: Auto-generated schemas for API documentation
- **Examples**: Built-in examples for each model

Design Patterns:
----------------
- Request models use PascalCase for user-facing API consistency
- Internal models use snake_case for C API compatibility
- All models support both naming conventions via aliases
- Validators ensure data integrity (non-empty strings, valid ranges)

Usage Pattern:
--------------
    from ibm_storage_protect.data_models.query import ListObjectsRequest

    # Create request with validation
    request = ListObjectsRequest(
        Filespace="/myfs",
        Prefix="/backup",
        MaxKeys=100
    )

    # Alternative: use snake_case
    request = ListObjectsRequest(
        filespace="/myfs",
        prefix="/backup",
        max_keys=100
    )

    # Pass to query client
    result = query_client.list_objects(request)

Reference:
----------
Pydantic Documentation: https://docs.pydantic.dev/
IBM Storage Protect API: https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods,line-too-long

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from ibm_storage_protect.enums import (
    ObjState as ObjStateEnum,
    ObjType as ObjTypeEnum,
)


class GroupQueryRequest(BaseModel):
    """
    Request model for querying group backup members.

    This model represents a request to query all objects belonging to a specific
    group backup, identified by the group leader's object ID. Group backups allow
    multiple related objects to be backed up together as a logical unit.

    Attributes
    ----------
    filespace : str
        The filespace name containing the group. Must be non-empty.
    group_leader_obj_id_hi : int
        High 32 bits of the group leader's object ID. Must be >= 0.
    group_leader_obj_id_lo : int
        Low 32 bits of the group leader's object ID. Must be >= 0.
    owner : str, optional
        Owner name filter for multi-owner configurations. None matches all owners.
    obj_type : ObjTypeEnum, optional
        Object type filter (default: ObjTypeEnum.ANY).
        Options: FILE, DIRECTORY, ANY

    Notes
    -----
    - Both hi and lo components are required to identify the group leader
    - A group ID of (0, 0) is considered invalid
    - The query performs a full filespace scan to find all group members

    Example
    -------
    >>> from ibm_storage_protect.data_models.query import GroupQueryRequest
    >>>
    >>> request = GroupQueryRequest(
    ...     filespace="/myfs",
    ...     group_leader_obj_id_hi=12345,
    ...     group_leader_obj_id_lo=67890
    ... )
    """
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    group_leader_obj_id_hi: int = Field(..., alias="GroupLeaderObjIdHi", description="Group leader object ID high part", ge=0)
    group_leader_obj_id_lo: int = Field(..., alias="GroupLeaderObjIdLo", description="Group leader object ID low part", ge=0)
    owner: Optional[str] = Field(default=None, alias="Owner", description="Object owner")
    obj_type: Optional[ObjTypeEnum] = Field(default=ObjTypeEnum.ANY, alias="ObjType", description="Object type")

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "group_leader_obj_id_hi": 12345,
                "group_leader_obj_id_lo": 67890
            }
        }


class GroupQueryInternal(BaseModel):
    """
    Internal model for group query C API translation.

    This model is used internally to translate user-facing GroupQueryRequest requests
    into parameters suitable for the C API layer. It uses snake_case naming and
    includes the session handle.

    Attributes
    ----------
    handle : int
        The session handle from dsmInitEx().
    filespace : str
        The filespace name containing the group.
    leader_hi : int
        High 32 bits of the group leader's object ID.
    leader_lo : int
        Low 32 bits of the group leader's object ID.
    owner : str
        Owner name filter (empty string matches all).
    obj_type : int
        Object type code (0xFF = DSM_OBJ_ANY_TYPE).

    Notes
    -----
    - This model is not intended for direct user instantiation
    - Used internally by QueryClient
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    leader_hi: int = Field(..., description="Group leader object ID high part", ge=0)
    leader_lo: int = Field(..., description="Group leader object ID low part", ge=0)
    owner: str = Field(default="", description="Object owner")
    obj_type: int = Field(default=0xFF, description="Object type code")

    class Config:
        arbitrary_types_allowed = True


class ObjectMetadata(BaseModel):
    """
    Complete object metadata from IBM Storage Protect query operations.

    This model represents comprehensive metadata for a backed-up object, including
    identification, size, dates, state, storage information, and group backup details.
    It is returned by various query operations and provides all information needed
    for object management and restore operations.

    Attributes
    ----------
    key : str
        Full object path (e.g., "backup/data/file.txt").
    filespace : str
        Filespace name containing the object.
    high_level : str
        High-level path component (directory path).
    low_level : str
        Low-level path component (filename).
    size : int
        Object size in bytes (>= 0).
    last_modified : datetime, optional
        Last modification timestamp. None if not available.
    expiry_date : datetime, optional
        Expiration date for the object. None if not set.
    object_id : str
        Unique object identifier in "hi-lo" format (e.g., "12345-67890").
    object_id_raw : Dict[str, int]
        Raw object ID components with 'hi' and 'lo' keys.
    state : str
        Object state: "active" or "inactive".
    media_class : str
        Storage media class: "DISK", "TAPE", or hex code.
    management_class : str
        Management class name governing retention and storage.
    owner : str
        Object owner name.
    compressed : bool
        True if object is compressed.
    deduplicated : bool
        True if object is client-side deduplicated.
    copy_group : int
        Copy group number (>= 0).
    group_leader_obj_id : str
        Group leader object ID in "hi-lo" format.
    group_leader_obj_id_raw : Dict[str, int]
        Raw group leader ID with 'hi' and 'lo' keys.
    is_group_leader : bool
        True if this object is a group leader.
    is_open_group : bool
        True if the group is still open for additions.
    """
    key: str = Field(..., alias="Key", description="Full object path")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    high_level: str = Field("", alias="HighLevel", description="High-level path component")
    low_level: str = Field("", alias="LowLevel", description="Low-level path component")
    size: int = Field(..., alias="Size", description="Object size in bytes", ge=0)
    last_modified: Optional[datetime] = Field(None, alias="LastModified", description="Last modification timestamp")
    expiry_date: Optional[datetime] = Field(None, alias="ExpiryDate", description="Expiration date")
    object_id: str = Field("", alias="ObjectId", description="Unique object identifier")
    object_id_raw: Dict[str, int] = Field(default_factory=dict, alias="ObjectIdRaw", description="Raw object ID components")
    state: str = Field("active", alias="State", description="Object state (active/inactive)")
    media_class: str = Field("DISK", alias="MediaClass", description="Storage media class")
    management_class: str = Field("STANDARD", alias="ManagementClass", description="Management class name")
    owner: str = Field("", alias="Owner", description="Object owner")
    compressed: bool = Field(False, alias="Compressed", description="Whether object is compressed")
    deduplicated: bool = Field(False, alias="Deduplicated", description="Whether object is deduplicated")
    copy_group: int = Field(1, alias="CopyGroup", description="Copy group number", ge=0)
    group_leader_obj_id: str = Field("", alias="GroupLeaderObjId", description="Group leader object ID")
    group_leader_obj_id_raw: Dict[str, int] = Field(default_factory=dict, alias="GroupLeaderObjIdRaw", description="Raw group leader ID")
    is_group_leader: bool = Field(False, alias="IsGroupLeader", description="True if this is the group leader")
    is_open_group: bool = Field(False, alias="IsOpenGroup", description="True if group is still open")

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "key": "db/main.db",
                "filespace": "/",
                "size": 1024,
                "object_id": "0-8251150",
                "is_group_leader": True
            }
        }


class GroupQueryResult(BaseModel):
    objects: List[ObjectMetadata] = Field(..., alias="Objects", description="Group member objects with full metadata")
    total_objects: int = Field(..., alias="TotalObjects", description="Total objects in group", ge=0)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "objects": [
                    {"key": "/data/leader.txt", "is_group_leader": True, "size": 1024},
                    {"key": "/data/member1.txt", "is_group_leader": False, "size": 2048}
                ],
                "total_objects": 2
            }
        }


class BackupQueryRequest(BaseModel):
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    key: str = Field(..., alias="Key", description="Object key path")
    obj_state: Optional[ObjStateEnum] = Field(default=ObjStateEnum.ACTIVE, alias="ObjState", description="Object state")
    obj_type: Optional[ObjTypeEnum] = Field(default=ObjTypeEnum.FILE, alias="ObjType", description="Object type")
    pit_date: Optional[datetime] = Field(default=None, alias="PitDate", description="Point-in-time date")
    owner: Optional[str] = Field(default=None, alias="Owner", description="Object owner")

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if not v or not v.strip():
            raise ValueError("Key cannot be empty")
        return v

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "key": "/data/file.txt",
                "obj_state": ObjStateEnum.ACTIVE
            }
        }


class BackupQueryInternal(BaseModel):
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    key: str = Field(..., description="Object key path")
    obj_state: int = Field(default=1, description="Object state code")
    obj_type: int = Field(default=0x01, description="Object type code")
    pit_date: Optional[datetime] = Field(default=None, description="Point-in-time date")
    owner: str = Field(default="", description="Object owner")

    class Config:
        arbitrary_types_allowed = True


class BackupQueryResult(BaseModel):
    objects: List[Dict[str, Any]] = Field(..., alias="Objects", description="Query results")
    total_objects: int = Field(..., alias="TotalObjects", description="Total objects found", ge=0)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "objects": [
                    {"Key": "/data/file.txt", "Size": 1024, "LastModified": "2024-01-01T00:00:00"}
                ],
                "total_objects": 1
            }
        }


class ListObjectsRequest(BaseModel):

    prefix: str = Field(default="", alias="Prefix", description="Object key prefix")
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace name")
    max_keys: Optional[int] = Field(default=1000, alias="MaxKeys", description="Maximum keys to return", ge=1, le=10000)
    obj_state: Optional[ObjStateEnum] = Field(default=ObjStateEnum.ACTIVE, alias="ObjState", description="Object state")
    obj_type: Optional[ObjTypeEnum] = Field(default=ObjTypeEnum.FILE, alias="ObjType", description="Object type")
    pit_date: Optional[datetime] = Field(default=None, alias="PitDate", description="Point-in-time date")

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "prefix": "/data",
                "max_keys": 1000
            }
        }


class ListObjectsInternal(BaseModel):
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    prefix: str = Field(default="", description="Object key prefix")
    max_keys: int = Field(default=1000, description="Maximum keys to return", ge=1)
    obj_state: int = Field(default=1, description="Object state code")
    obj_type: int = Field(default=0x01, description="Object type code")
    pit_date: Optional[datetime] = Field(default=None, description="Point-in-time date")

    class Config:
        arbitrary_types_allowed = True


class ListObjectsResult(BaseModel):
    name: str = Field(..., alias="Name", description="Filespace name")
    prefix: str = Field(..., alias="Prefix", description="Prefix used")
    contents: List[Dict[str, Any]] = Field(..., alias="Contents", description="Object list")
    key_count: int = Field(..., alias="KeyCount", description="Number of keys returned", ge=0)
    max_keys: int = Field(..., alias="MaxKeys", description="Maximum keys requested", ge=1)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "/myfs",
                "prefix": "/data",
                "contents": [
                    {"key": "/data/file1.txt", "size": 1024},
                    {"key": "/data/file2.txt", "size": 2048}
                ],
                "key_count": 2,
                "max_keys": 1000
            }
        }


class QueryFilespacesRequest(BaseModel):
    fs_pattern: str = Field(default="*", alias="FsPattern", description="Filespace name pattern")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "fs_pattern": "*"
            }
        }


class QueryFilespacesInternal(BaseModel):
    handle: int = Field(..., description="Session handle")
    fs_pattern: str = Field(default="*", description="Filespace name pattern")

    class Config:
        arbitrary_types_allowed = True


class QueryFilespacesResult(BaseModel):
    filespaces: List[Dict[str, Any]] = Field(..., alias="Filespaces", description="Filespace list")
    total_filespaces: int = Field(..., alias="TotalFilespaces", description="Total filespaces found", ge=0)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespaces": [
                    {"Name": "/myfs", "Type": "Python-SDK", "Occupancy": 100, "Capacity": 1000}
                ],
                "total_filespaces": 1
            }
        }


class QueryObjectRequest(BaseModel):
    key: str = Field(..., alias="Key", description="Object key path")
    filespace: Optional[str] = Field(default="/", alias="Filespace", description="Filespace name")
    obj_state: Optional[ObjStateEnum] = Field(default=ObjStateEnum.ACTIVE, alias="ObjState", description="Object state")
    obj_type: Optional[ObjTypeEnum] = Field(default=ObjTypeEnum.FILE, alias="ObjType", description="Object type")

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
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


class QueryObjectInternal(BaseModel):
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    key: str = Field(..., description="Object key path")
    obj_state: int = Field(default=1, description="Object state code")
    obj_type: int = Field(default=0x01, description="Object type code")

    class Config:
        arbitrary_types_allowed = True


class QueryObjectResult(BaseModel):
    """Single object query result with full metadata"""
    key: str = Field(..., alias="Key", description="Full object path")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    high_level: str = Field("", alias="HighLevel", description="High-level path component")
    low_level: str = Field("", alias="LowLevel", description="Low-level path component")
    size: int = Field(..., alias="Size", description="Object size in bytes", ge=0)
    last_modified: Optional[datetime] = Field(None, alias="LastModified", description="Last modification timestamp")
    expiry_date: Optional[datetime] = Field(None, alias="ExpiryDate", description="Expiration date")
    object_id: str = Field("", alias="ObjectId", description="Unique object identifier")
    object_id_raw: Dict[str, int] = Field(default_factory=dict, alias="ObjectIdRaw", description="Raw object ID components")
    state: str = Field("active", alias="State", description="Object state (active/inactive)")
    media_class: str = Field("DISK", alias="MediaClass", description="Storage media class")
    management_class: str = Field("STANDARD", alias="ManagementClass", description="Management class name")
    owner: str = Field("", alias="Owner", description="Object owner")
    compressed: bool = Field(False, alias="Compressed", description="Whether object is compressed")
    deduplicated: bool = Field(False, alias="Deduplicated", description="Whether object is deduplicated")
    copy_group: int = Field(1, alias="CopyGroup", description="Copy group number", ge=0)
    group_leader_obj_id: str = Field("", alias="GroupLeaderObjId", description="Group leader object ID")
    group_leader_obj_id_raw: Dict[str, int] = Field(default_factory=dict, alias="GroupLeaderObjIdRaw", description="Raw group leader ID")
    is_group_leader: bool = Field(False, alias="IsGroupLeader", description="True if this is the group leader")
    is_open_group: bool = Field(False, alias="IsOpenGroup", description="True if group is still open")

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "key": "data/file.txt",
                "size": 1024,
                "last_modified": "2024-01-01T00:00:00",
                "state": "active"
            }
        }


class QueryMgmtClassesRequest(BaseModel):
    """
    Request model for querying management class definitions.

    Retrieves management class information including backup and archive policies.

    Attributes
    ----------
    mc_name : str, optional
        Management class name pattern (default: "" = all classes).
    detail : bool
        Include detailed copy group information (default: True).

    Notes
    -----
    - When detail=True, includes BackupCG and ArchiveCG dictionaries
    - When detail=False, only includes Name and Description

    Example
    -------
    >>> from ibm_storage_protect.data_models.query import QueryMgmtClassesRequest
    >>>
    >>> request = QueryMgmtClassesRequest(detail=True)
    """
    mc_name: Optional[str] = Field(default="", alias="McName", description="Management class name pattern")
    detail: bool = Field(default=True, alias="Detail", description="Include detailed information")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "mc_name": "",
                "detail": True
            }
        }


class QueryMgmtClassesInternal(BaseModel):
    """
    Internal model for management class query C API translation.

    Attributes
    ----------
    handle : int
        Session handle.
    mc_name : str
        Management class name pattern.
    detail : bool
        Include detailed information.
    """
    handle: int = Field(..., description="Session handle")
    mc_name: str = Field(default="", description="Management class name pattern")
    detail: bool = Field(default=True, description="Include detailed information")

    class Config:
        arbitrary_types_allowed = True


class QueryMgmtClassesResult(BaseModel):
    """
    Response model for management class query operations.

    Contains management class definitions and policies.

    Attributes
    ----------
    management_classes : List[Dict[str, Any]]
        List of management class dictionaries.
    total_classes : int
        Total number of classes found (>= 0).

    Example
    -------
    >>> result = query_client.query_mgmt_classes(request)
    >>> for mc in result.management_classes:
    ...     print(f"{mc['Name']}: {mc['Description']}")
    """
    management_classes: List[Dict[str, Any]] = Field(..., alias="ManagementClasses", description="Management class list")
    total_classes: int = Field(..., alias="TotalClasses", description="Total classes found", ge=0)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "management_classes": [
                    {"Name": "STANDARD", "Description": "Standard management class"}
                ],
                "total_classes": 1
            }
        }
