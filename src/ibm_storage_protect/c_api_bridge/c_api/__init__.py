"""
IBM Storage Protect Client API Python Bindings Package

This package provides Python bindings for the IBM Storage Protect (formerly Tivoli Storage Manager)
Client API library. It enables Python applications to interact with IBM Storage Protect servers for
backup, restore, and query operations.

Package Structure:
------------------
- platform_types.py: Platform-specific base type definitions and structures
- structs.py: Type definitions, constants, enums, and data structures used by the API
- prototypes.py: Function prototypes and signatures for all Client API functions
- return_codes.py: Return codes and error constants returned by API functions
- load.py: Dynamic library loading logic for platform-specific API libraries
- release.py: Version and release information for the API

Usage:
------
This package is typically imported by higher-level abstraction layers and should not be
used directly by end-user applications. The Client API bindings provide low-level access to
IBM Storage Protect functionality.

Reference:
----------
For detailed API documentation, refer to the IBM Storage Protect API documentation:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf

This documentation describes all functions, structures, and usage patterns for the
IBM Storage Protect Client API.

Note:
-----
The IBM Storage Protect API library must be installed on the system for these bindings
to function properly. The library path can be customized using the IBM_SP_API_LIB
environment variable.
"""
