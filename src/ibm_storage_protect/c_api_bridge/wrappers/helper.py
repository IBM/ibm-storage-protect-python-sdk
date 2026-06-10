"""
IBM Storage Protect Client API - Internal Helper Functions

This module provides low-level utility functions for the IBM Storage Protect
Client API wrapper layer. These functions handle common operations such as error
checking, data conversion, structure initialization, and input validation.

Key Responsibilities:
---------------------
1. **Error Handling**: Convert Client API return codes to Python exceptions
2. **Data Conversion**: Transform between Python and C data types
3. **Input Validation**: Validate and normalize user inputs
4. **Structure Management**: Initialize and manage C structures safely
5. **Path Parsing**: Parse and normalize object keys and paths

Supported Operations:
---------------------
- Backup and restore operations
- Query operations (filespaces, objects, management classes)
- Session management
- Group backup/restore operations

Note: Archive and retrieve operations are not currently supported.

Thread Safety:
--------------
All functions in this module are thread-safe and stateless. They can be called
concurrently from multiple threads without synchronization.

Client API Integration:
-----------------------
These helpers abstract the complexity of ctypes and Client API interactions,
providing a cleaner Python interface for higher-level operations.

Reference:
----------
IBM Storage Protect Client API Documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
"""

from ctypes import (
    byref,
    c_uint32,
    memset,
    sizeof,
    create_string_buffer
)
from datetime import datetime
from enum import Enum
from typing import (
    Tuple,
    Optional,
    List,
    Generator,
    Any,
    Type
)
import logging

from ibm_storage_protect.c_api_bridge.c_api.structs import (
    DSM_MAX_RC_MSG_LENGTH,
    dsmDate
)
from ibm_storage_protect.c_api_bridge.c_api.return_codes import DSM_RC_OK
from ibm_storage_protect.c_api_bridge.c_api.load import lib
from ibm_storage_protect.errors.mapper import _map_internal_error
from ibm_storage_protect.enums import MountWait

_logger = logging.getLogger('ibm_storage_protect.c_api.helper')


def _rc_msg(handle: int, rc: int) -> str:
    """
    Retrieve the human-readable error message for a Client API return code.

    Calls the IBM Storage Protect Client API function dsmRCMsg() to obtain a
    descriptive error message corresponding to the given return code. This
    provides context for debugging and error reporting.

    Parameters
    ----------
    handle : int
        The session handle obtained from dsmInitEx(). Used to retrieve
        session-specific error messages.
    rc : int
        The return code from a Client API function call (e.g., DSM_RC_OK,
        DSM_RC_ABORT_NO_MATCH, etc.).

    Returns
    -------
    str
        A human-readable error message describing the return code. If the
        message contains non-UTF-8 characters, they are replaced with the
        Unicode replacement character (U+FFFD).

    Notes
    -----
    - The message buffer is limited to DSM_MAX_RC_MSG_LENGTH bytes
    - Messages are decoded with error='replace' to handle encoding issues
    - This function does not raise exceptions; it always returns a string

    Client API Reference
    --------------------
    dsmRCMsg() - Retrieve return code message

    Example
    -------
    >>> msg = _rc_msg(handle, 2200)
    >>> print(msg)
    'ANS2200E (RC2200) No objects found matching query criteria'
    """
    buf = create_string_buffer(DSM_MAX_RC_MSG_LENGTH)
    lib.dsmRCMsg(handle, rc, buf)
    return buf.value.decode(errors="replace")


def validate_chunks(body):
    """
    Validate and normalize data chunks for backup operations.

    Ensures that data provided for backup operations meets the IBM Storage
    Protect Client API requirements: chunks must be bytes/bytearray and not
    exceed 4MB in size. This function acts as a generator that validates and
    yields chunks in the correct format.

    Parameters
    ----------
    body : bytes, bytearray, or Generator[bytes, None, None]
        The data to be backed up. Can be:
        - bytes or bytearray: Single chunk of data (must be ≤ 4MB)
        - Generator: Yields bytes/bytearray chunks (each ≤ 4MB)

    Yields
    ------
    bytes
        Validated data chunks ready for transmission to the Client API.

    Raises
    ------
    ValueError
        If a single bytes/bytearray exceeds 4MB, or if any generator chunk
        exceeds 4MB.
    TypeError
        If body is a file handle (use generator instead), or if generator
        yields non-bytes data.

    Notes
    -----
    - The 4MB limit is imposed by the IBM Storage Protect Client API buffer size
    - File handles are explicitly rejected to prevent resource leaks
    - Generators are the recommended approach for large files

    Example
    -------
    >>> # Small data - direct bytes
    >>> for chunk in validate_chunks(b"small data"):
    ...     send_to_api(chunk)

    >>> # Large file - use generator
    >>> def read_file(path):
    ...     with open(path, 'rb') as f:
    ...         while chunk := f.read(256 * 1024):  # 256KB chunks
    ...             yield chunk
    >>> for chunk in validate_chunks(read_file('/path/to/file')):
    ...     send_to_api(chunk)
    """
    max_chunk_size = 4 * 1024 * 1024

    if isinstance(body, (bytes, bytearray)):
        if len(body) > max_chunk_size:
            raise ValueError(
                f"Body is {len(body)} bytes — exceeds 4MB. "
                "Use a generator to chunk it."
            )
        def _gen_bytes():
            yield bytes(body) if isinstance(body, bytearray) else body
        return _gen_bytes()

    if hasattr(body, 'read'):
        raise TypeError(
            "File handles are not accepted. Pass bytes or a generator.\n"
            "  def read_chunks(path):\n"
            "      with open(path, 'rb') as f:\n"
            "          while chunk := f.read(256*1024):\n"
            "              yield chunk"
        )

    def _gen_chunks():
        for chunk in body:
            if not isinstance(chunk, (bytes, bytearray)):
                raise TypeError(
                    f"Generator must yield bytes, got {type(chunk).__name__}"
                )
            if len(chunk) > max_chunk_size:
                raise ValueError(
                    f"Chunk size {len(chunk)} exceeds 4MB. "
                    "Reduce generator chunk size."
                )
            yield bytes(chunk) if isinstance(chunk, bytearray) else chunk
    return _gen_chunks()


def parse_key(key: str) -> tuple:
    """
    Parse an object key into high-level (HL) and low-level (LL) components.

    IBM Storage Protect organizes objects using a two-level naming hierarchy:
    - High-level (HL): Directory path or namespace
    - Low-level (LL): Object name or filename

    This function splits a full object key into these components, following
    the IBM Storage Protect naming conventions.

    Parameters
    ----------
    key : str
        The full object key to parse (e.g., "/path/to/object.txt").
        Leading slash is optional and will be added if missing.

    Returns
    -------
    tuple[str, str]
        A tuple of (high_level, low_level) strings:
        - high_level: Directory path (e.g., "/path/to")
        - low_level: Object name (e.g., "/object.txt")

    Raises
    ------
    ValueError
        If the key is empty or contains only slashes.

    Notes
    -----
    - Keys are normalized to start with '/'
    - Root-level objects have HL="/" and LL="/objectname"
    - The LL component always includes a leading slash

    Client API Reference
    --------------------
    dsmObjName structure: hl and ll fields

    Example
    -------
    >>> parse_key("/backup/database/data.db")
    ('/backup/database', '/data.db')
    >>> parse_key("config.json")
    ('/', '/config.json')

    >>> parse_key("/")
    ValueError: Key must not be empty
    """
    if not key or not key.strip("/"):
        raise ValueError("Key must not be empty")
    if not key.startswith('/'):
        key = '/' + key

    last_slash = key.rfind('/')

    if last_slash <= 0:
        return "/", key
    high_level = key[:last_slash] if last_slash > 1 else "/"
    low_level = key[last_slash:]

    return high_level, low_level


def prefix_to_hl_ll(prefix: str) -> Tuple[str, str]:
    """
    Convert a prefix string into high-level and low-level wildcard patterns.

    Transforms a user-provided prefix into IBM Storage Protect query patterns
    with wildcards. This enables prefix-based object listing and searching.
    The function intelligently determines whether the prefix represents a
    directory path or a partial filename.

    Parameters
    ----------
    prefix : str
        The prefix to convert (e.g., "/backup/logs" or "/data/file").
        Empty string matches all objects.

    Returns
    -------
    Tuple[str, str]
        A tuple of (high_level_pattern, low_level_pattern):
        - For directory prefixes: ("/path*", "/*")
        - For file prefixes: ("/path", "/file*")
        - For empty prefix: ("/*", "/*")

    Notes
    -----
    - Trailing slashes indicate directory prefixes
    - Segments with dots are treated as filenames
    - Segments without dots are treated as directories
    - Wildcards (*) enable pattern matching in queries

    Algorithm
    ---------
    1. Empty prefix → match everything: ("/*", "/*")
    2. Ends with "/" → directory: ("/path", "/*")
    3. Last segment has "." → file: ("/path", "/file*")
    4. Last segment no "." → directory: ("/path*", "/*")

    Example
    -------
    >>> prefix_to_hl_ll("/backup/logs")
    ('/backup/logs*', '/*')

    >>> prefix_to_hl_ll("/backup/data.db")
    ('/backup', '/data.db*')

    >>> prefix_to_hl_ll("/backup/")
    ('/backup', '/*')

    >>> prefix_to_hl_ll("")
    ('/*', '/*')
    """
    if not prefix:
        return "/*", "/*"
    if not prefix.startswith("/"):
        prefix = "/" + prefix

    if prefix.endswith("/"):
        return prefix.rstrip("/") or "/", "/*"
    last_slash   = prefix.rfind("/")
    last_segment = prefix[last_slash + 1:]

    if "." in last_segment:
        # Treat as filename prefix
        hl = prefix[:last_slash] if last_slash > 0 else "/"
        ll = prefix[last_slash:]
        return hl, ll + "*"

    # Treat as directory prefix
    return prefix + "*", "/*"


def key_to_hl_ll(key: str) -> Tuple[str, str]:
    """
    Convert an object key into high-level and low-level components for queries.

    Similar to parse_key() but designed specifically for query operations.
    Handles edge cases like root-level objects and ensures proper formatting
    for IBM Storage Protect query structures.

    Parameters
    ----------
    key : str
        The object key to convert. Leading slash is optional.

    Returns
    -------
    Tuple[str, str]
        A tuple of (high_level, low_level) for query operations:
        - high_level: Directory path with leading slash
        - low_level: Object name with leading slash

    Notes
    -----
    - Empty keys return ("/", "/*") to match all objects
    - Root-level objects have HL="/"
    - Both components always start with "/"

    Example
    -------
    >>> key_to_hl_ll("backup/data/file.txt")
    ('/backup/data', '/file.txt')

    >>> key_to_hl_ll("/config.json")
    ('/', '/config.json')

    >>> key_to_hl_ll("")
    ('/', '/*')
    """
    key = key[1:] if key.startswith("/") else key
    if not key:
        return "/", "/*"
    parts = key.rsplit("/", 1)
    if len(parts) == 2:
        return "/" + parts[0], "/" + parts[1]
    return "/", "/" + parts[0]


def unwrap_handle(handle) -> int:
    """
    Extract the integer value from a session handle.

    Session handles can be either c_uint32 ctypes objects or plain integers.
    This function normalizes them to plain Python integers for consistent
    usage across the codebase.

    Parameters
    ----------
    handle : c_uint32 or int
        The session handle to unwrap.

    Returns
    -------
    int
        The integer value of the handle.

    Example
    -------
    >>> handle = c_uint32(12345)
    >>> unwrap_handle(handle)
    12345

    >>> unwrap_handle(67890)
    67890
    """
    if isinstance(handle, c_uint32):
        return handle.value
    return int(handle)


def decode_field(raw) -> str:
    """
    Decode a C string field to a Python string.

    Client API structures often contain fixed-size character arrays that may be
    null-padded. This function safely decodes them to Python strings,
    removing null bytes and handling encoding errors gracefully.

    Parameters
    ----------
    raw : bytes, bytearray, or ctypes array
        The raw C string data to decode.

    Returns
    -------
    str
        The decoded string with null padding removed. Non-UTF-8 characters
        are replaced with the Unicode replacement character (U+FFFD).

    Notes
    -----
    - Null bytes (\\x00) are stripped from the end
    - UTF-8 decoding errors are handled with 'replace' strategy
    - Works with both bytes and ctypes character arrays

    Example
    -------
    >>> decode_field(b"Hello\\x00\\x00\\x00")
    'Hello'

    >>> decode_field(b"\\xff\\xfeInvalid")
    '��Invalid'
    """
    if isinstance(raw, (bytes, bytearray)):
        return raw.rstrip(b"\x00").decode("utf-8", errors="replace")
    return bytes(raw).rstrip(b"\x00").decode("utf-8", errors="replace")


def size64(s) -> int:
    """
    Convert a dsStruct64_t structure to a Python integer.

    IBM Storage Protect uses dsStruct64_t structures to represent 64-bit
    integers, split into high and low 32-bit components. This function
    reconstructs the full 64-bit value.

    Parameters
    ----------
    s : dsStruct64_t
        A structure with 'hi' and 'lo' fields representing the high and
        low 32 bits of a 64-bit integer.

    Returns
    -------
    int
        The reconstructed 64-bit integer value.

    Notes
    -----
    - Formula: (hi << 32) | lo
    - Handles sizes up to 2^64-1 bytes (16 exabytes)
    - Used for file sizes, capacities, and occupancies

    Client API Reference
    --------------------
    dsStruct64_t structure in structs.py

    Example
    -------
    >>> size_struct = dsStruct64_t()
    >>> size_struct.hi = 1
    >>> size_struct.lo = 0
    >>> size64(size_struct)
    4294967296  # 4GB
    """
    return (int(s.hi) << 32) | int(s.lo)


def check_rc(handle: int, rc: int, operation: Optional[str] = None) -> None:
    """
    Check a Client API return code and raise an exception if it indicates an error.

    This is the primary error handling function for all Client API operations.
    It converts Client API return codes into appropriate Python exceptions with
    descriptive error messages.

    Parameters
    ----------
    handle : int
        The session handle for retrieving error messages.
    rc : int
        The return code from a Client API function call.
    operation : str, optional
        A description of the operation that was attempted, used to provide
        context in error messages (e.g., "dsmBeginQuery(qtBackup)").

    Raises
    ------
    Various SDK exceptions
        Raises an appropriate exception based on the return code. The specific
        exception type is determined by _map_internal_error().

    Notes
    -----
    - DSM_RC_OK (0) does not raise an exception
    - All other return codes are treated as errors
    - Error messages are retrieved from the Client API when possible
    - Structured logging is used to record error details

    Example
    -------
    >>> rc = lib.dsmBeginQuery(handle, qtBackup, byref(qry))
    >>> check_rc(handle, rc, "dsmBeginQuery(qtBackup)")
    # Raises exception if rc != DSM_RC_OK
    """
    if rc != DSM_RC_OK:
        try:
            c_api_message = _rc_msg(handle, rc)
            if not c_api_message or not c_api_message.strip():
                c_api_message = f"Client API error {rc} (no message available)"
        except (OSError, RuntimeError, ValueError) as e:
            c_api_message = (
                f"Client API error {rc} (message retrieval failed: {str(e)})"
            )
            _logger.warning(
                "Failed to retrieve Client API message for RC %d",
                rc,
                extra={
                    'event_type': 'client_api.message_retrieval_failed',
                    'error_code': rc,
                    'error': str(e)
                }
            )

        if operation:
            context = f"{operation}: {c_api_message}"
        else:
            context = c_api_message

        _logger.debug(
            "Client API error detected: RC=%d",
            rc,
            extra={
                'event_type': 'client_api.error',
                'error_code': rc,
                'api_message': c_api_message,
                'operation': operation,
                'handle': handle
            }
        )

        error = _map_internal_error(rc, context=context)

        raise error


def dsm_date_to_datetime(d: dsmDate) -> Optional[datetime]:
    """
    Convert a dsmDate structure to a Python datetime object.

    IBM Storage Protect uses dsmDate structures to represent dates and times.
    This function converts them to Python datetime objects for easier
    manipulation and formatting.

    Parameters
    ----------
    d : dsmDate
        A dsmDate structure with year, month, day, hour, minute, and second fields.

    Returns
    -------
    datetime or None
        A Python datetime object, or None if the date is invalid (year == 0).

    Notes
    -----
    - A year value of 0 indicates an unset or invalid date
    - Month and day are clamped to minimum value of 1 to handle edge cases
    - ValueError and OverflowError are caught and return None

    Client API Reference
    --------------------
    dsmDate structure in structs.py

    Example
    -------
    >>> date_struct = dsmDate()
    >>> date_struct.year = 2024
    >>> date_struct.month = 5
    >>> date_struct.day = 11
    >>> date_struct.hour = 14
    >>> date_struct.minute = 30
    >>> date_struct.second = 0
    >>> dsm_date_to_datetime(date_struct)
    datetime.datetime(2024, 5, 11, 14, 30, 0)
    """
    try:
        if d.year == 0:
            return None
        return datetime(
            year=d.year,
            month=max(1, d.month),
            day=max(1, d.day),
            hour=d.hour,
            minute=d.minute,
            second=d.second,
        )
    except (ValueError, OverflowError):
        return None

def datetime_to_dsm_date(dt: Optional[datetime]) -> dsmDate:
    """
    Convert a Python datetime object to a dsmDate structure.

    This is the inverse of dsm_date_to_datetime(), converting Python datetime
    objects to the IBM Storage Protect dsmDate format for use in Client API calls.

    Parameters
    ----------
    dt : datetime or None
        A Python datetime object to convert, or None to create an unset date.

    Returns
    -------
    dsmDate
        A dsmDate structure with fields populated from the datetime, or all
        fields set to 0 if dt is None.

    Notes
    -----
    - None is represented as a dsmDate with year=0
    - All datetime components are directly mapped to dsmDate fields
    - No validation is performed; assumes datetime is valid

    Client API Reference
    --------------------
    dsmDate structure in structs.py

    Example
    -------
    >>> from datetime import datetime
    >>> dt = datetime(2024, 5, 11, 14, 30, 0)
    >>> dsm_date = datetime_to_dsm_date(dt)
    >>> dsm_date.year
    2024

    >>> null_date = datetime_to_dsm_date(None)
    >>> null_date.year
    0
    """
    d = dsmDate()
    if dt is None:
        d.year   = 0
        d.month  = 0
        d.day    = 0
        d.hour   = 0
        d.minute = 0
        d.second = 0
        return d
    d.year   = dt.year
    d.month  = dt.month
    d.day    = dt.day
    d.hour   = dt.hour
    d.minute = dt.minute
    d.second = dt.second
    return d


def iter_chunks(chunks: List[bytes]) -> Generator[bytes, None, None]:
    """
    Create a generator that yields bytes chunks from a list.

    Simple utility to convert a list of bytes chunks into a generator.
    Used primarily in restore operations to provide a consistent interface
    for streaming data.

    Parameters
    ----------
    chunks : List[bytes]
        A list of bytes chunks to yield.

    Yields
    ------
    bytes
        Each chunk from the input list.

    Example
    -------
    >>> chunks = [b"chunk1", b"chunk2", b"chunk3"]
    >>> for chunk in iter_chunks(chunks):
    ...     process(chunk)
    """
    yield from chunks


def init_struct(struct_type, version=None):
    """
    Initialize a Client API structure with zero-filled memory.

    Safely creates and initializes a ctypes structure for use with the
    IBM Storage Protect Client API. All memory is zeroed out, and the
    structure version field is set if provided.

    Parameters
    ----------
    struct_type : ctypes.Structure class
        The ctypes structure class to instantiate (e.g., dsmObjName, DataBlk).
    version : int, optional
        The structure version constant to set in the stVersion field.
        If None, the version field is left as 0.

    Returns
    -------
    struct_type instance
        A zero-initialized instance of the structure with version set.

    Notes
    -----
    - Zero-initialization prevents undefined behavior from uninitialized memory
    - Version fields are critical for Client API compatibility
    - Always use this function instead of direct structure instantiation

    Example
    -------
    >>> obj_name = init_struct(dsmObjName)
    >>> data_blk = init_struct(DataBlk, DataBlkVersion)
    >>> data_blk.stVersion == DataBlkVersion
    True
    """
    obj = struct_type()
    memset(byref(obj), 0, sizeof(struct_type))
    if version is not None:
        obj.stVersion = version
    return obj


def extract_enum_value(enum_or_value: Any, enum_class: Type[Enum], default: Any = None) -> int:
    """
    Extract the integer value from an enum or pass through an integer.

    Provides flexible handling of parameters that can be either enum instances
    or raw integer values. This allows the SDK to accept both high-level enums
    and low-level integer constants.

    Parameters
    ----------
    enum_or_value : Enum, int, or None
        An enum instance, integer value, or None.
    enum_class : Enum class
        The expected enum class for type checking.
    default : int, optional
        The default value to return if enum_or_value is None.

    Returns
    -------
    int or default
        The integer value of the enum, the passed integer, or the default.

    Example
    -------
    >>> from enums import ObjectType
    >>> extract_enum_value(ObjectType.FILE, ObjectType)
    1

    >>> extract_enum_value(1, ObjectType)
    1

    >>> extract_enum_value(None, ObjectType, default=0)
    0
    """
    if enum_or_value is None:
        return default
    return enum_or_value.value if isinstance(enum_or_value, enum_class) else enum_or_value


def extract_mount_wait(mount_wait):
    """
    Convert a MountWait enum to a boolean value.

    The Client API uses boolean values for mount wait parameters, while the
    SDK provides a MountWait enum for clarity. This function converts between
    the two representations.

    Parameters
    ----------
    mount_wait : MountWait, bool, or other
        A MountWait enum value, boolean, or other value.

    Returns
    -------
    bool
        True if mount_wait is MountWait.WAIT, otherwise returns the value
        as-is (typically a boolean).

    Notes
    -----
    - MountWait.WAIT → True (wait for tape mount)
    - MountWait.NO_WAIT → False (fail if tape mount needed)
    - Boolean values are passed through unchanged

    Example
    -------
    >>> from enums import MountWait
    >>> extract_mount_wait(MountWait.WAIT)
    True

    >>> extract_mount_wait(MountWait.NO_WAIT)
    False

    >>> extract_mount_wait(True)
    True
    """
    return (
        mount_wait == MountWait.WAIT
        if isinstance(mount_wait, MountWait)
        else mount_wait
    )


def encode_obj_info(obj_info):
    """
    Encode object information string to bytes for Client API.

    Object information (objInfo) is an optional descriptive field that can
    be attached to backed-up objects. This function ensures it's properly
    encoded as UTF-8 bytes for the Client API.

    Parameters
    ----------
    obj_info : str, bytes, or None
        The object information to encode. Can be:
        - str: Will be encoded to UTF-8 bytes
        - bytes: Passed through unchanged
        - None: Returns None

    Returns
    -------
    bytes or None
        UTF-8 encoded bytes, or None if input was None.

    Raises
    ------
    TypeError
        If obj_info is not str, bytes, or None.

    Notes
    -----
    - Maximum length is typically 255 bytes (Client API limit)
    - Used for application-specific metadata
    - Not indexed or searchable by the server

    Example
    -------
    >>> encode_obj_info("Database backup metadata")
    b'Database backup metadata'

    >>> encode_obj_info(b"Already bytes")
    b'Already bytes'

    >>> encode_obj_info(None)
    None
    """
    if obj_info is None:
        return None
    if isinstance(obj_info, str):
        return obj_info.encode('utf-8')
    if isinstance(obj_info, bytes):
        return obj_info
    raise TypeError(f"ObjInfo must be str or bytes, got {type(obj_info)}")

def get_session_owner(session) -> str:
    """
    Get the owner name from a session object.

    This helper function safely retrieves the owner name from different types
    of session objects, handling both client instances (which have _get_owner()
    method) and SessionManager instances (which have owner attribute).

    Parameters
    ----------
    session : object
        Session object (can be BatchBackupClient, GroupBackupClient, 
        SessionManager, or any other session type)

    Returns
    -------
    str
        Owner name from session, or empty string if not available

    Notes
    -----
    - Checks for _get_owner() method first (client instances)
    - Falls back to owner attribute (SessionManager instances)
    - Returns empty string if neither is available

    Example
    -------
    >>> owner = get_session_owner(batch_client)
    'backup_admin'

    >>> owner = get_session_owner(session_manager)
    'admin'
    """
    # Check if session has _get_owner method (client instances)
    if hasattr(session, '_get_owner'):
        return session._get_owner()
    # Check if session has owner attribute directly (SessionManager)
    if hasattr(session, 'owner'):
        return session.owner or ""
    return ""
