# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods,line-too-long
"""
IBM Storage Protect SDK - Filespace Data Models

This module defines Pydantic data models for filespace management operations
in the IBM Storage Protect SDK. These models provide type-safe, validated
interfaces for filespace registration, updates, and deletion.

Filespace Lifecycle:
--------------------
1. **Registration** (FilespaceRegisterRequest): Create a new filespace
   - Required before backing up objects
   - Idempotent operation (safe to repeat)

2. **Update** (FilespaceUpdateRequest): Modify filespace attributes
   - Update capacity, occupancy, type, and info
   - Selective updates via optional fields

3. **Deletion** (FilespaceDeleteRequest): Remove filespace and all objects
   - Irreversible operation
   - Affects all repositories

Model Categories:
-----------------
1. **Request Models**: User-facing input models with validation
   - FilespaceRegisterRequest, FilespaceUpdateRequest, FilespaceDeleteRequest
   - Use capitalized field names (Filespace, Capacity, etc.)
   - Support both field names and aliases for flexibility

2. **Internal Models**: Internal representation for C API layer
   - FilespaceRegisterRequestInternal, FilespaceUpdateRequestInternal, FilespaceDeleteRequestInternal
   - Use lowercase snake_case field names
   - Include session handle for C API calls

3. **Result Models**: Operation results returned to users
   - FilespaceRegisterResult, FilespaceUpdateResult, FilespaceDeleteResult
   - Indicate operation status and affected filespace
   - Use capitalized field names for consistency

Field Naming Convention:
------------------------
- **User-facing models**: PascalCase (Filespace, Capacity, Occupancy)
- **Internal models**: snake_case (filespace, capacity, occupancy)
- **Aliases**: Support both conventions via populate_by_name=True

Validation:
-----------
All models include validators to ensure:
- Filespace names are non-empty and non-whitespace
- Numeric values (capacity, occupancy) are non-negative
- Required fields are present

Example Usage:
--------------
    # Register a filespace
    register_req = FilespaceRegisterRequest(Filespace="/backup/data")
    # or using alias
    register_req = FilespaceRegisterRequest(filespace="/backup/data")

    # Update filespace with metrics
    update_req = FilespaceUpdateRequest(
        Filespace="/backup/data",
        Occupancy=5000000000,  # 5GB used
        Capacity=10000000000,  # 10GB total
        FsInfo="Production database backup"
    )

    # Delete filespace
    delete_req = FilespaceDeleteRequest(Filespace="/backup/data")

See Also:
---------
- control: High-level filespace operations
- c_api_bridge.wrappers.filespace: Low-level C API wrappers
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods,line-too-long

from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class FilespaceRegisterRequest(BaseModel):
    """
    Request model for registering a new filespace.

    A filespace is a logical container that organizes backed-up objects,
    typically representing a filesystem, application namespace, or data source.

    Attributes:
        filespace: Name of the filespace to register (e.g., "/backup/data").
                  Must be unique and non-empty. Case-sensitive on most platforms.

    Validation:
        - filespace cannot be empty or whitespace-only

    Example:
        >>> req = FilespaceRegisterRequest(filespace="/backup/database")
    """
    filespace: str = Field(..., alias="Filespace", description="Filespace name")

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        """Pydantic configuration for FilespaceRegisterRequest."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "fs_type": "Python-SDK",
                "fs_info": "Python SDK Filespace",
                "occupancy": 100,
                "capacity": 1000
            }
        }


class FilespaceRegisterInternal(BaseModel):
    """
    Internal model for filespace registration passed to C API layer.

    This model is used internally to pass validated data to the low-level
    C API wrapper functions. It includes the session handle required for
    C API calls.

    Attributes:
        handle: Raw session handle from dsmInitEx()
        filespace: Name of the filespace to register

    Notes:
        - This model is not exposed to end users
        - Uses snake_case naming for internal consistency
        - Allows arbitrary types for C API compatibility
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")

    class Config:
        arbitrary_types_allowed = True


class FilespaceRegisterResult(BaseModel):
    """
    Result model returned after filespace registration.

    Indicates the outcome of the registration operation and the affected filespace.

    Attributes:
        Status: Operation status ("success" or error indicator)
        Filespace: Name of the registered filespace

    Example:
        >>> result = FilespaceRegisterResult(Status="success", Filespace="/backup/data")
        >>> print(f"Registered: {result.Filespace}")
    """
    status: str = Field(..., alias="Status", description="Operation status")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")

    class Config:
        """Pydantic configuration for FilespaceRegisterResult."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "filespace": "/myfs"
            }
        }


class FilespaceUpdateRequest(BaseModel):
    """
    Request model for updating filespace attributes.

    Allows selective updates to filespace metadata. Only provided fields
    are updated; others remain unchanged on the server.

    Attributes:
        filespace: Name of the filespace to update (required)
        fs_type: Optional filespace type string (e.g., "Python-SDK", "PostgreSQL")
        fs_info: Optional descriptive information about the filespace
        occupancy: Optional current storage usage in bytes (must be >= 0)
        capacity: Optional total storage capacity in bytes (must be >= 0)

    Validation:
        - filespace cannot be empty or whitespace-only
        - occupancy and capacity must be non-negative if provided

    Example:
        >>> req = FilespaceUpdateRequest(
        ...     filespace="/backup/data",
        ...     occupancy=5000000000,  # 5GB
        ...     capacity=10000000000   # 10GB
        ... )
    """
    filespace: str = Field(..., alias="Filespace", description="Filespace name")
    fs_type: Optional[str] = Field(default=None, alias="FsType", description="Filespace type")
    fs_info: Optional[str] = Field(default=None, alias="FsInfo", description="Filespace information")
    occupancy: Optional[int] = Field(default=None, alias="Occupancy", description="Filespace occupancy", ge=0)
    capacity: Optional[int] = Field(default=None, alias="Capacity", description="Filespace capacity", ge=0)

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        """Pydantic configuration for FilespaceUpdateRequest."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs",
                "fs_info": "Updated filespace info",
                "occupancy": 200,
                "capacity": 2000
            }
        }


class FilespaceUpdateInternal(BaseModel):
    """
    Internal model for filespace updates passed to C API layer.

    Attributes:
        handle: Raw session handle from dsmInitEx()
        filespace: Name of the filespace to update
        fs_type: Optional filespace type
        fs_info: Optional filespace information
        occupancy: Optional current usage in bytes
        capacity: Optional total capacity in bytes

    Notes:
        - Uses snake_case naming for internal consistency
        - Allows arbitrary types for C API compatibility
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")
    fs_type: Optional[str] = Field(default=None, description="Filespace type")
    fs_info: Optional[str] = Field(default=None, description="Filespace information")
    occupancy: Optional[int] = Field(default=None, description="Filespace occupancy", ge=0)
    capacity: Optional[int] = Field(default=None, description="Filespace capacity", ge=0)

    class Config:
        arbitrary_types_allowed = True


class FilespaceUpdateResult(BaseModel):
    """
    Result model returned after filespace update.

    Attributes:
        Status: Operation status ("success" or error indicator)
        Filespace: Name of the updated filespace

    Example:
        >>> result = FilespaceUpdateResult(Status="success", Filespace="/backup/data")
    """
    status: str = Field(..., alias="Status", description="Operation status")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")

    class Config:
        """Pydantic configuration for FilespaceUpdateResult."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "filespace": "/myfs"
            }
        }


class FilespaceDeleteRequest(BaseModel):
    """
    Request model for deleting a filespace.

    WARNING: This operation is irreversible and deletes ALL objects
    within the filespace from all repositories (backup and archive).

    Attributes:
        filespace: Name of the filespace to delete

    Validation:
        - filespace cannot be empty or whitespace-only

    Example:
        >>> req = FilespaceDeleteRequest(filespace="/backup/old_data")
    """
    filespace: str = Field(..., alias="Filespace", description="Filespace name")

    @field_validator('filespace')
    @classmethod
    def validate_filespace(cls, v):
        if not v or not v.strip():
            raise ValueError("Filespace cannot be empty")
        return v

    class Config:
        """Pydantic configuration for FilespaceDeleteRequest."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "filespace": "/myfs"
            }
        }


class FilespaceDeleteInternal(BaseModel):
    """
    Internal model for filespace deletion passed to C API layer.

    Attributes:
        handle: Raw session handle from dsmInitEx()
        filespace: Name of the filespace to delete

    Notes:
        - Uses snake_case naming for internal consistency
        - Allows arbitrary types for C API compatibility
    """
    handle: int = Field(..., description="Session handle")
    filespace: str = Field(..., description="Filespace name")

    class Config:
        arbitrary_types_allowed = True


class FilespaceDeleteResult(BaseModel):
    """
    Result model returned after filespace deletion.

    Attributes:
        Status: Operation status ("success" or error indicator)
        Filespace: Name of the deleted filespace

    Example:
        >>> result = FilespaceDeleteResult(Status="success", Filespace="/backup/data")
    """
    status: str = Field(..., alias="Status", description="Operation status")
    filespace: str = Field(..., alias="Filespace", description="Filespace name")

    class Config:
        """Pydantic configuration for FilespaceDeleteResult."""
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "filespace": "/myfs"
            }
        }
