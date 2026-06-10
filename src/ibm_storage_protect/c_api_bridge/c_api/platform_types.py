"""
IBM Storage Protect Client API Platform-Specific Type Definitions

This module defines platform-specific base types and structures used throughout
the IBM Storage Protect Client API. These types provide a consistent interface
across different platforms (AIX, Linux, Windows) while mapping to the appropriate
native C types.

Platform Detection:
-------------------
- DS_MACOS: macOS platform identifier (18)
- DS_UNIX: Unix/Linux platform identifier (12)
- DS_AIX: AIX platform identifier (same as DS_UNIX)

Base Type Definitions:
----------------------
The module defines fundamental integer types that map to C types:
- dsInt8_t, dsUint8_t: 8-bit signed/unsigned integers
- dsInt16_t, dsUint16_t: 16-bit signed/unsigned integers
- dsInt32_t, dsUint32_t: 32-bit signed/unsigned integers
- dsInt64_t, dsUint64_t: 64-bit signed/unsigned integers
- dsLong_t, dsULong_t: Platform-specific long integers

Character and String Types:
---------------------------
- dsChar_t: Character type (c_char for non-Unicode)
- dsString_t: String pointer type (c_char_p for non-Unicode)

Note: Unicode support can be enabled by modifying these definitions.

Boolean Type:
-------------
- dsmBool_t: Boolean type (integer-based)
- dsmTrue: Boolean true value (1)
- dsmFalse: Boolean false value (0)

Backward Compatibility:
-----------------------
The module provides aliases for older naming conventions:
- bool_t, bTrue, bFalse: Legacy boolean types
- dsBool_t: Alias for dsmBool_t

Special Structures:
-------------------
- dsUint160_t: 160-bit unsigned integer structure (5 x 32-bit components)
  Used for large numeric values like restore order identifiers

- dsStruct64_t: 64-bit structure with high/low 32-bit components
  Used for representing 64-bit values on platforms without native 64-bit support
  Components: hi (high 32 bits), lo (low 32 bits)

Usage:
------
These types are imported by dsmapitd.py and used throughout the API bindings
to ensure type consistency and platform compatibility.

Example:
--------
    from .dsmapips import dsUint32_t, dsStruct64_t, dsmBool_t

    # Define a structure using platform-specific types
    class MyStruct(ctypes.Structure):
        _fields_ = [
            ("count", dsUint32_t),
            ("size", dsStruct64_t),
            ("enabled", dsmBool_t),
        ]

Reference:
----------
For more information about IBM Storage Protect data types, see:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
"""

import ctypes

# =============================================================================
# Platform Identifiers
# =============================================================================

DS_MACOS = 18  # macOS platform identifier
DS_UNIX = 12   # Unix/Linux platform identifier
DS_AIX = DS_UNIX  # AIX uses the same identifier as Unix

# =============================================================================
# Base Integer Type Definitions
# =============================================================================
# These types map to standard C integer types via ctypes

dsInt8_t = ctypes.c_int8      # 8-bit signed integer (-128 to 127)
dsUint8_t = ctypes.c_uint8    # 8-bit unsigned integer (0 to 255)
dsInt16_t = ctypes.c_int16    # 16-bit signed integer (-32,768 to 32,767)
dsUint16_t = ctypes.c_uint16  # 16-bit unsigned integer (0 to 65,535)
dsInt32_t = ctypes.c_int32    # 32-bit signed integer
dsUint32_t = ctypes.c_uint32  # 32-bit unsigned integer
dsULong_t = ctypes.c_ulong    # Platform-specific unsigned long
dsLong_t = ctypes.c_long      # Platform-specific signed long

# =============================================================================
# Character and String Types
# =============================================================================
# Defining the dsChar_t and dsString_t for non-Unicode
# Update these definitions if Unicode support is required

dsChar_t = ctypes.c_char      # Single character type
dsString_t = ctypes.c_char_p  # Null-terminated string pointer

# =============================================================================
# 160-bit Unsigned Integer Structure
# =============================================================================
# Used for very large numeric values, particularly restore order identifiers

class dsUint160_t(ctypes.Structure):
    """
    160-bit unsigned integer structure.

    Composed of five 32-bit unsigned integers to represent a 160-bit value.
    Used primarily for restore order extended values in query responses.

    Fields:
        top: Most significant 32 bits
        hi_hi: Second most significant 32 bits
        hi_lo: Middle 32 bits
        lo_hi: Second least significant 32 bits
        lo_lo: Least significant 32 bits
    """
    _fields_ = [
        ("top", dsUint32_t),      # Bits 128-159 (most significant)
        ("hi_hi", dsUint32_t),    # Bits 96-127
        ("hi_lo", dsUint32_t),    # Bits 64-95
        ("lo_hi", dsUint32_t),    # Bits 32-63
        ("lo_lo", dsUint32_t)     # Bits 0-31 (least significant)
    ]

# =============================================================================
# Boolean Type Definitions
# =============================================================================

dsmBool_t = ctypes.c_int  # Boolean type (integer-based)
dsmFalse = 0x00           # Boolean false value
dsmTrue = 0x01            # Boolean true value

# =============================================================================
# Backward Compatibility Aliases
# =============================================================================
# These aliases maintain compatibility with older code

dsUint8_t = ctypes.c_uint8    # Redundant definition for compatibility
dsInt8_t = ctypes.c_int8      # Redundant definition for compatibility
dsUint16_t = ctypes.c_uint16  # Redundant definition for compatibility
dsInt16_t = ctypes.c_int16    # Redundant definition for compatibility
dsUint32_t = ctypes.c_uint32  # Redundant definition for compatibility
dsInt32_t = ctypes.c_int32    # Redundant definition for compatibility
dsBool_t = dsmBool_t          # Legacy boolean type alias
bool_t = dsBool_t             # Even older boolean type alias
bTrue = dsmTrue               # Legacy true value
bFalse = dsmFalse             # Legacy false value

# =============================================================================
# 64-bit Integer Types
# =============================================================================

dsInt64_t = ctypes.c_long     # 64-bit signed integer (platform-dependent)
dsUint64_t = ctypes.c_ulong   # 64-bit unsigned integer (platform-dependent)

# =============================================================================
# 64-bit Structure for Cross-Platform Compatibility
# =============================================================================

class dsStruct64_t(ctypes.Structure):
    """
    64-bit value represented as a structure with high and low 32-bit components.

    This structure is used to represent 64-bit values on platforms that may not
    have native 64-bit integer support, or where explicit control over the
    high and low 32-bit components is needed.

    Fields:
        hi: High-order 32 bits (bits 32-63)
        lo: Low-order 32 bits (bits 0-31)

    Usage:
        This structure is commonly used for:
        - Object IDs (ObjID)
        - File sizes (sizeEstimate)
        - Byte counts (totalBytesSent, totalBytesRecv)
        - Offsets (partialObjOffset, partialObjLength)

    Example:
        # Create a 64-bit value from high and low components
        obj_id = dsStruct64_t()
        obj_id.hi = 0x00000001
        obj_id.lo = 0x23456789
        # Represents: 0x0000000123456789
    """
    _fields_ = [
        ("hi", dsUint32_t),  # High-order 32 bits
        ("lo", dsUint32_t)   # Low-order 32 bits
    ]

# Made with Bob
