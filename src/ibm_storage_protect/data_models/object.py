"""
IBM Storage Protect SDK - Object Management Data Models

This module defines Pydantic data models for object management operations
in the IBM Storage Protect SDK. These models provide type-safe, validated
interfaces for deleting, renaming, and updating backed-up objects.

Object Management Operations:
------------------------------
Object management operations manipulate backed-up objects without transferring
data content. They are control path operations that modify metadata and object
properties on the server.

1. **Delete Operations**: Remove backed-up objects
   - delete_by_name: Delete using filespace and key path
   - delete_by_id: Delete using unique object ID

2. **Rename Operations**: Change object names
   - Modify high-level and/or low-level names
   - Support merge option to combine with existing objects

3. **Update Operations**: Modify object attributes
   - Change owner and/or management class
   - Selective updates via optional fields

Object Identification:
----------------------
Objects in IBM Storage Protect are identified by:
- **Filespace**: Logical container/namespace
- **Key**: Full path (split into high-level/low-level by C API)
- **Object Type**: File, directory, or other (DSM_OBJ_FILE, etc.)
- **Object ID**: Unique identifier (hi/lo pair) assigned by server

Model Categories:
-----------------
1. **Request Models**: User-facing input models with validation
   - ObjectDeleteRequest, ObjectDeleteByIdRequest, ObjectRenameRequest, ObjectUpdateRequest
   - Use capitalized field names (Filespace, Key, etc.)
   - Support both field names and aliases

2. **Internal Models**: Internal representation for C API layer
   - ObjectDeleteInternal, ObjectRenameInternal, etc.
   - Use lowercase snake_case field names
   - Include session handle and converted enum values

3. **Result Models**: Operation results returned to users
   - ObjectDeleteResult, ObjectRenameResult, etc.
   - Indicate operation status and affected objects
   - Use capitalized field names

Field Naming Convention:
------------------------
- **User-facing models**: PascalCase (Filespace, Key, NewKey)
- **Internal models**: snake_case (filespace, key, new_key)
- **Aliases**: Support both conventions via populate_by_name=True

Validation:
-----------
All models include validators to ensure:
- Filespace names are non-empty and non-whitespace
- Keys (paths) are non-empty and non-whitespace
- Object IDs are non-negative
- Copy groups are >= 1

Transaction Management:
-----------------------
Delete and rename operations are wrapped in transactions for atomicity.
Update operations don't require explicit transactions.

Example Usage:
--------------
    # Delete object by name
    delete_req = ObjectDeleteRequest(
        Filespace="/backup/data",
        Key="/path/to/file.txt",
        CopyGroup=1
    )

    # Delete object by ID
    delete_req = ObjectDeleteByIdRequest(
        ObjIdHi=12345,
        ObjIdLo=67890
    )

    # Rename object
    rename_req = ObjectRenameRequest(
        Filespace="/backup/data",
        Key="/old/path.txt",
        NewKey="/new/path.txt",
        Merge=False
    )

    # Update object attributes
    update_req = ObjectUpdateRequest(
        Filespace="/backup/data",
        Key="/path/file.txt",
        Owner="admin",
        ManagementClass="STANDARD"
    )

See Also:
---------
- control: High-level object operations
- c_api_bridge.wrappers.object: Low-level C API wrappers
- enums.ObjType: Object type enumeration
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods

from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from ibm_storage_protect.enums import ObjType as ObjectType


class ObjectDeleteRequest(BaseModel):
    """
    Request model for deleting an object by name.

    Deletes a backed-up object using its filespace and key (path). The operation
    is wrapped in a transaction for atomicity.

    Attributes:
        filespace: Name of the filespace containing the object
        key: Full path to the object (e.g., "/path/to/file.txt")
        copy_group: Copy group number (default: 1, must be >= 1)
        obj_type: Object type (default: FILE)

    Validation:
        - filespace cannot be empty or whitespace-only
        - key cannot be empty or whitespace-only
        - copy_group must be >= 1

    Example:
        >>> req = ObjectDeleteRequest(
        ...     filespace="/backup/data",
        ...     key="/documents/report.pdf"
        ... )
    """
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    key: str = Field(..., alias="Key", description="Object key path")
    copy_group: int = Field(default=1, alias="CopyGroup", description="Copy group number", ge=1)
    obj_type: Optional[ObjectType] = Field(
        default=ObjectType.FILE, alias="ObjType", description="Object type"
    )

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if not v or not v.strip():
            raise ValueError("Key cannot be empty")
        return v

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        """Pydantic configuration for ObjectDeleteRequest."""
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "key": "/data/file.txt",
                "copy_group": 1
            }
        }


class ObjectDeleteInternal(BaseModel):
    """
    Internal model for object deletion passed to C API layer.

    Attributes:
        handle: Raw session handle from dsmInitEx()
        filespace: Name of the filespace
        key: Object key path
        copy_group: Copy group number
        obj_type: Object type code (converted from enum)

    Notes:
        - Uses snake_case naming for internal consistency
        - obj_type is the integer value from ObjType enum
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    key: str = Field(..., description="Object key path")
    copy_group: int = Field(default=1, description="Copy group number", ge=1)
    obj_type: int = Field(default=0x01, description="Object type code")

    class Config:
        arbitrary_types_allowed = True


class ObjectDeleteResult(BaseModel):
    """
    Result model returned after object deletion by name.

    Attributes:
        Status: Operation status ("success" or error indicator)
        Filespace: Name of the filespace
        Key: Path of the deleted object

    Example:
        >>> result = ObjectDeleteResult(
        ...     Status="success",
        ...     Filespace="/backup/data",
        ...     Key="/documents/report.pdf"
        ... )
    """
    status: str = Field(..., alias="Status", description="Operation status")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    key: str = Field(..., alias="Key", description="Object key path")

    class Config:
        """Pydantic configuration for ObjectDeleteResult."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "filespace": "/myfs",
                "key": "/data/file.txt"
            }
        }


class ObjectDeleteByIdRequest(BaseModel):
    """
    Request model for deleting an object by its unique ID.

    More efficient than delete by name when the object ID is known.
    The operation is wrapped in a transaction for atomicity.

    Attributes:
        obj_id_hi: High 32 bits of the object ID (must be >= 0)
        obj_id_lo: Low 32 bits of the object ID (must be >= 0)

    Example:
        >>> req = ObjectDeleteByIdRequest(
        ...     obj_id_hi=12345,
        ...     obj_id_lo=67890
        ... )
    """
    obj_id_hi: int = Field(..., alias="ObjIdHi", description="Object ID high part", ge=0)
    obj_id_lo: int = Field(..., alias="ObjIdLo", description="Object ID low part", ge=0)

    class Config:
        """Pydantic configuration for ObjectDeleteByIdRequest."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "obj_id_hi": 12345,
                "obj_id_lo": 67890
            }
        }


class ObjectDeleteByIdInternal(BaseModel):
    """
    Internal model for object deletion by ID passed to C API layer.

    Attributes:
        handle: Raw session handle from dsmInitEx()
        obj_id_hi: High 32 bits of object ID
        obj_id_lo: Low 32 bits of object ID
    """
    handle: int = Field(..., description="Session handle")
    obj_id_hi: int = Field(..., description="Object ID high part", ge=0)
    obj_id_lo: int = Field(..., description="Object ID low part", ge=0)

    class Config:
        arbitrary_types_allowed = True


class ObjectDeleteByIdResult(BaseModel):
    """
    Result model returned after object deletion by ID.

    Attributes:
        Status: Operation status ("success" or error indicator)
        ObjIdHi: High 32 bits of the deleted object's ID
        ObjIdLo: Low 32 bits of the deleted object's ID

    Example:
        >>> result = ObjectDeleteByIdResult(
        ...     Status="success",
        ...     ObjIdHi=12345,
        ...     ObjIdLo=67890
        ... )
    """
    status: str = Field(..., alias="Status", description="Operation status")
    obj_id_hi: int = Field(..., alias="ObjIdHi", description="Object ID high part")
    obj_id_lo: int = Field(..., alias="ObjIdLo", description="Object ID low part")

    class Config:
        """Pydantic configuration for ObjectDeleteByIdResult."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "obj_id_hi": 12345,
                "obj_id_lo": 67890
            }
        }


class ObjectRenameRequest(BaseModel):
    """
    Request model for renaming an object.

    Changes an object's high-level and/or low-level names. The operation
    is wrapped in a transaction for atomicity.

    Attributes:
        filespace: Name of the filespace containing the object
        key: Current full path to the object
        new_key: New full path for the object
        merge: If True, merge with existing object at NewKey (default: False)
        obj_type: Object type (default: FILE)

    Validation:
        - filespace cannot be empty or whitespace-only
        - key cannot be empty or whitespace-only
        - new_key cannot be empty or whitespace-only

    Example:
        >>> req = ObjectRenameRequest(
        ...     filespace="/backup/data",
        ...     key="/old/path.txt",
        ...     new_key="/new/path.txt",
        ...     merge=False
        ... )
    """
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    key: str = Field(..., alias="Key", description="Current object key path")
    new_key: str = Field(..., alias="NewKey", description="New object key path")
    merge: bool = Field(default=False, alias="Merge", description="Merge with existing object")
    obj_type: Optional[ObjectType] = Field(
        default=ObjectType.FILE, alias="ObjType", description="Object type"
    )

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if not v or not v.strip():
            raise ValueError("Key cannot be empty")
        return v

    @field_validator('new_key')
    @classmethod
    def validate_new_key(cls, v):
        if not v or not v.strip():
            raise ValueError("NewKey cannot be empty")
        return v

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        """Pydantic configuration for ObjectRenameRequest."""
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "key": "/data/old_file.txt",
                "new_key": "/data/new_file.txt",
                "merge": False
            }
        }


class ObjectRenameInternal(BaseModel):
    """
    Internal model for object rename passed to C API layer.

    Attributes:
        handle: Raw session handle from dsmInitEx()
        filespace: Name of the filespace
        key: Current object key path
        new_key: New object key path
        merge: Whether to merge with existing object
        obj_type: Object type code (converted from enum)
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    key: str = Field(..., description="Current object key path")
    new_key: str = Field(..., description="New object key path")
    merge: bool = Field(default=False, description="Merge with existing object")
    obj_type: int = Field(default=0x01, description="Object type code")

    class Config:
        arbitrary_types_allowed = True


class ObjectRenameResult(BaseModel):
    """
    Result model returned after object rename.

    Attributes:
        Status: Operation status ("success" or error indicator)
        Filespace: Name of the filespace
        OldKey: Original path of the object
        NewKey: New path of the object

    Example:
        >>> result = ObjectRenameResult(
        ...     Status="success",
        ...     Filespace="/backup/data",
        ...     OldKey="/old/path.txt",
        ...     NewKey="/new/path.txt"
        ... )
    """
    status: str = Field(..., alias="Status", description="Operation status")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    old_key: str = Field(..., alias="OldKey", description="Old object key path")
    new_key: str = Field(..., alias="NewKey", description="New object key path")

    class Config:
        """Pydantic configuration for ObjectRenameResult."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "filespace": "/myfs",
                "old_key": "/data/old_file.txt",
                "new_key": "/data/new_file.txt"
            }
        }


class ObjectUpdateRequest(BaseModel):
    """
    Request model for updating object attributes.

    Modifies an object's owner and/or management class without transferring
    data. Only provided fields are updated.

    Attributes:
        filespace: Name of the filespace containing the object
        key: Full path to the object
        owner: Optional new owner
        management_class: Optional new management class
        obj_type: Object type (default: FILE)

    Validation:
        - filespace cannot be empty or whitespace-only
        - key cannot be empty or whitespace-only

    Example:
        >>> req = ObjectUpdateRequest(
        ...     filespace="/backup/data",
        ...     key="/path/file.txt",
        ...     owner="admin",
        ...     management_class="STANDARD"
        ... )
    """
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    key: str = Field(..., alias="Key", description="Object key path")
    owner: Optional[str] = Field(default=None, alias="Owner", description="New owner")
    management_class: Optional[str] = Field(
        default=None, alias="ManagementClass", description="New management class"
    )
    obj_type: Optional[ObjectType] = Field(
        default=ObjectType.FILE, alias="ObjType", description="Object type"
    )

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if not v or not v.strip():
            raise ValueError("Key cannot be empty")
        return v

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        """Pydantic configuration for ObjectUpdateRequest."""
        arbitrary_types_allowed = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "key": "/data/file.txt",
                "owner": "newowner",
                "management_class": "STANDARD"
            }
        }


class ObjectUpdateInternal(BaseModel):
    """
    Internal model for object update passed to C API layer.

    Attributes:
        handle: Raw session handle from dsmInitEx()
        filespace: Name of the filespace
        key: Object key path
        owner: Optional new owner
        management_class: Optional new management class
        obj_type: Object type code (converted from enum)
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    key: str = Field(..., description="Object key path")
    owner: Optional[str] = Field(default=None, description="New owner")
    management_class: Optional[str] = Field(default=None, description="New management class")
    obj_type: int = Field(default=0x01, description="Object type code")

    class Config:
        arbitrary_types_allowed = True


class ObjectUpdateResult(BaseModel):
    """
    Result model returned after object update.

    Attributes:
        Status: Operation status ("success" or error indicator)
        Filespace: Name of the filespace
        Key: Path of the updated object

    Example:
        >>> result = ObjectUpdateResult(
        ...     Status="success",
        ...     Filespace="/backup/data",
        ...     Key="/path/file.txt"
        ... )
    """
    status: str = Field(..., alias="Status", description="Operation status")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    key: str = Field(..., alias="Key", description="Object key path")

    class Config:
        """Pydantic configuration for ObjectUpdateResult."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "filespace": "/myfs",
                "key": "/data/file.txt"
            }
        }
