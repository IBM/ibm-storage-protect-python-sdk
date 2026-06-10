"""
IBM Storage Protect Client API Version and Release Information

This module contains version, release, and build information for the IBM Storage Protect
Client API. These constants are used throughout the API bindings to ensure compatibility
between the client application and the IBM Storage Protect server.

Version Information:
--------------------
The API version follows a four-part numbering scheme:
- COMMON_VERSION: Major version number (e.g., 8)
- COMMON_RELEASE: Release number (e.g., 2)
- COMMON_LEVEL: Level/minor version (e.g., 1)
- COMMON_SUBLEVEL: Sub-level/patch version (e.g., 0)

Current Version: 8.2.1.0 (IBM Storage Protect)

Product Names:
--------------
The product has evolved through several names over its history:
- DFDSM (Distributed File Data Storage Manager) - Original name
- ADSM (ADSTAR Distributed Storage Manager) - Early commercial name
- TSM (Tivoli Storage Manager) - Long-standing name
- ITSM/IBM Storage Protect - Current name

Build History:
--------------
The COMMON_BUILD constants track the evolution of the product through various
releases from TSM 5.1.0 through IBM Storage Protect 8.2.1. Each build number
corresponds to a specific release version.

VRL (Version Release Level) Constants:
---------------------------------------
VRL constants provide numeric identifiers for specific versions, useful for
version comparison and compatibility checks. Format: VRL_XYZ where X.Y.Z is
the version number (e.g., VRL_821 = 821 for version 8.2.1).

Platform Strings:
-----------------
Platform-specific identifiers for TDP (Tivoli Data Protection) products:
- TDP4VE: TDP for VMware
- TDP4HYPERV: TDP for Hyper-V

Usage:
------
These constants are primarily used in:
1. dsmapitd.py - To set DSM_API_VERSION, DSM_API_RELEASE, DSM_API_LEVEL
2. API initialization - To verify client/server compatibility
3. Feature detection - To determine available functionality based on version

Example:
--------
    from .release import COMMON_VERSION, COMMON_RELEASE, COMMON_LEVEL

    # Used in dsmApiVersion structure during dsmInit()
    api_version.version = COMMON_VERSION
    api_version.release = COMMON_RELEASE
    api_version.level = COMMON_LEVEL

Reference:
----------
For version compatibility information, see:
https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
"""

# =============================================================================
# Current Version Information
# =============================================================================

# Version components for IBM Storage Protect 8.2.1.0
COMMON_VERSION     =    8  # Major version
COMMON_RELEASE     =    2  # Release number
COMMON_LEVEL       =    1  # Level (minor version)
COMMON_SUBLEVEL     =   0  # Sub-level (patch version)
COMMON_DRIVER        =  ""  # Driver/build identifier (empty for release builds)

# Full version string
COMMON_VERSIONTXT ="8.2.1.0"

# Copyright and product information
SHIPYEARTXT  =""  # Ship year (text format)
SHIPYEARTXTW ="2026"  # Ship year (wide text format)
TSMPRODTXT  ="IBM Storage Protect"  # Product name

# Version components as strings (for display purposes)
COMMON_VERSION_STR  =  "8"
COMMON_RELEASE_STR  =  "2"
COMMON_LEVEL_STR    =  "1"
COMMON_SUBLEVEL_STR =  "0"
COMMON_DRIVER_STR   =  ""

# =============================================================================
# Product Name Definitions
# =============================================================================

# Product name evolution constants
COMMON_NAME_DFDSM    =  1  # Distributed File Data Storage Manager (original)
COMMON_NAME_ADSM     =  2  # ADSTAR Distributed Storage Manager
COMMON_NAME_TSM      =  3  # Tivoli Storage Manager
COMMON_NAME_ITSM     =  4  # IBM Storage Protect (current)
COMMON_NAME          =  COMMON_NAME_ITSM  # Current product name identifier

# =============================================================================
# Build History Constants
# =============================================================================

# Build identifiers for version tracking and compatibility
# Each constant represents a specific product release
COMMON_BUILD_TSM_510 = 1   # TSM 5.1.0
COMMON_BUILD_TSM_511 = 2   # TSM 5.1.1
COMMON_BUILD_TSM_515 = 3   # TSM 5.1.5
COMMON_BUILD_TSM_516 = 4   # TSM 5.1.6
COMMON_BUILD_TSM_520 = 5   # TSM 5.2.0
COMMON_BUILD_TSM_522 = 6   # TSM 5.2.2
COMMON_BUILD_TSM_517 = 7   # TSM 5.1.7
COMMON_BUILD_TSM_523 = 8   # TSM 5.2.3
COMMON_BUILD_TSM_530 = 9   # TSM 5.3.0
COMMON_BUILD_TSM_524 = 10  # TSM 5.2.4
COMMON_BUILD_TSM_532 = 11  # TSM 5.3.2
COMMON_BUILD_TSM_533 = 12  # TSM 5.3.3
COMMON_BUILD_TSM_525 = 13  # TSM 5.2.5
COMMON_BUILD_TSM_534 = 14  # TSM 5.3.4
COMMON_BUILD_TSM_540 = 15  # TSM 5.4.0
COMMON_BUILD_TSM_535 = 16  # TSM 5.3.5
COMMON_BUILD_TSM_541 = 17  # TSM 5.4.1
COMMON_BUILD_TSM_550 = 18  # TSM 5.5.0
COMMON_BUILD_TSM_542 = 19  # TSM 5.4.2
COMMON_BUILD_TSM_551 = 20  # TSM 5.5.1
COMMON_BUILD_TSM_610 = 21  # TSM 6.1.0
COMMON_BUILD_TSM_552 = 22  # TSM 5.5.2
COMMON_BUILD_TSM_611 = 23  # TSM 6.1.1
COMMON_BUILD_TSM_543 = 24  # TSM 5.4.3
COMMON_BUILD_TSM_620 = 25  # TSM 6.2.0
COMMON_BUILD_TSM_612 = 26  # TSM 6.1.2
COMMON_BUILD_TSM_553 = 27  # TSM 5.5.3
COMMON_BUILD_TSM_613 = 28  # TSM 6.1.3
COMMON_BUILD_TSM_621 = 29  # TSM 6.2.1
COMMON_BUILD_TSM_622 = 30  # TSM 6.2.2
COMMON_BUILD_TSM_614 = 31  # TSM 6.1.4
COMMON_BUILD_TSM_623 = 32  # TSM 6.2.3
COMMON_BUILD_TSM_630 = 33  # TSM 6.3.0
COMMON_BUILD_TSM_615 = 34  # TSM 6.1.5
COMMON_BUILD_TSM_624 = 35  # TSM 6.2.4
COMMON_BUILD_TSM_631 = 36  # TSM 6.3.1
COMMON_BUILD_TSM_640 = 37  # TSM 6.4.0
COMMON_BUILD_TSM_710 = 38  # TSM 7.1.0
COMMON_BUILD_TSM_625 = 39  # TSM 6.2.5
COMMON_BUILD_TSM_641 = 40  # TSM 6.4.1
COMMON_BUILD_TSM_711 = 41  # TSM 7.1.1
COMMON_BUILD_TSM_712 = 42  # TSM 7.1.2
COMMON_BUILD_TSM_713 = 43  # TSM 7.1.3
COMMON_BUILD_TSM_714 = 44  # TSM 7.1.4
COMMON_BUILD_TSM_720 = 45  # TSM 7.2.0
COMMON_BUILD_TSM_721 = 46  # TSM 7.2.1
COMMON_BUILD_TSM_642 = 47  # TSM 6.4.2
COMMON_BUILD_TSM_643 = 48  # TSM 6.4.3
COMMON_BUILD_TSM_715 = 49  # TSM 7.1.5
COMMON_BUILD_TSM_716 = 50  # TSM 7.1.6
COMMON_BUILD_TSM_810 = 51  # IBM Storage Protect 8.1.0
COMMON_BUILD_TSM_811 = 52  # IBM Storage Protect 8.1.1
COMMON_BUILD_TSM_812 = 53  # IBM Storage Protect 8.1.2
COMMON_BUILD_TSM_718 = 54  # TSM 7.1.8
COMMON_BUILD_TSM_814 = 55  # IBM Storage Protect 8.1.4
COMMON_BUILD_TSM_816 = 56  # IBM Storage Protect 8.1.6
COMMON_BUILD_TSM_817 = 57  # IBM Storage Protect 8.1.7
COMMON_BUILD_TSM_818 = 58  # IBM Storage Protect 8.1.8
COMMON_BUILD_TSM_819 = 59  # IBM Storage Protect 8.1.9
COMMON_BUILD_TSM_8110 = 60  # IBM Storage Protect 8.1.10
COMMON_BUILD_TSM_8111 = 61  # IBM Storage Protect 8.1.11
COMMON_BUILD_TSM_8112 = 62  # IBM Storage Protect 8.1.12
COMMON_BUILD_TSM_8113 = 63  # IBM Storage Protect 8.1.13
COMMON_BUILD_TSM_8114 = 64  # IBM Storage Protect 8.1.14
COMMON_BUILD_TSM_8115 = 65  # IBM Storage Protect 8.1.15
COMMON_BUILD_TSM_8117 = 66  # IBM Storage Protect 8.1.17
COMMON_BUILD_TSM_8119 = 67  # IBM Storage Protect 8.1.19
COMMON_BUILD_TSM_8120 = 68  # IBM Storage Protect 8.1.20
COMMON_BUILD_TSM_8121 = 69  # IBM Storage Protect 8.1.21
COMMON_BUILD_TSM_8122 = 70  # IBM Storage Protect 8.1.22
COMMON_BUILD_TSM_8123 = 71  # IBM Storage Protect 8.1.23
COMMON_BUILD_TSM_8124 = 72  # IBM Storage Protect 8.1.24
COMMON_BUILD_TSM_8125 = 73  # IBM Storage Protect 8.1.25
COMMON_BUILD_TSM_8126 = 74  # IBM Storage Protect 8.1.26
COMMON_BUILD_TSM_8127 = 75  # IBM Storage Protect 8.1.27
COMMON_BUILD_TSM_820 = 76  # IBM Storage Protect 8.2.0
COMMON_BUILD_TSM_821 = 77  # IBM Storage Protect 8.2.1 (current)

# Current build identifier
COMMON_BUILD = COMMON_BUILD_TSM_821

# =============================================================================
# Version Release Level (VRL) Constants
# =============================================================================

# Numeric version identifiers for version comparison
# Format: VRL_XYZ where X.Y.Z is the version number
VRL_712 = 712    # Version 7.1.2
VRL_713 = 713    # Version 7.1.3
VRL_714 = 714    # Version 7.1.4
VRL_715 = 715    # Version 7.1.5
VRL_716 = 716    # Version 7.1.6
VRL_718 = 718    # Version 7.1.8
VRL_810 = 810    # Version 8.1.0
VRL_811 = 811    # Version 8.1.1
VRL_812 = 812    # Version 8.1.2
VRL_814 = 814    # Version 8.1.4
VRL_816 = 816    # Version 8.1.6
VRL_817 = 817    # Version 8.1.7
VRL_818 = 818    # Version 8.1.8
VRL_819 = 819    # Version 8.1.9
VRL_8110 = 8110  # Version 8.1.10
VRL_8111 = 8111  # Version 8.1.11
VRL_8112 = 8112  # Version 8.1.12
VRL_8113 = 8113  # Version 8.1.13
VRL_8114 = 8114  # Version 8.1.14
VRL_8115 = 8115  # Version 8.1.15
VRL_8117 = 8117  # Version 8.1.17
VRL_8119 = 8119  # Version 8.1.19
VRL_8120 = 8120  # Version 8.1.20
VRL_8121 = 8121  # Version 8.1.21
VRL_8122 = 8122  # Version 8.1.22
VRL_8123 = 8123  # Version 8.1.23
VRL_8124 = 8124  # Version 8.1.24
VRL_8125 = 8125  # Version 8.1.25
VRL_8126 = 8126  # Version 8.1.26
VRL_8127 = 8127  # Version 8.1.27
VRL_820 = 820    # Version 8.2.0
VRL_821 = 821    # Version 8.2.1 (current)

# =============================================================================
# Platform-Specific Product Strings
# =============================================================================

# TDP (Tivoli Data Protection) for VMware platform identifiers
TDP4VE_PLATFORM_STRING_MBCS = "TDP VMware"  # Multi-byte character set
TDP4VE_PLATFORM_STRING = "TDP VMware"       # Standard string

# TDP for Hyper-V platform identifiers
TDP4HYPERV_PLATFORM_STRING_MBCS = "TDP HyperV"  # Multi-byte character set
TDP4HYPERV_PLATFORM_STRING = "TDP HyperV"       # Standard string

# Made with Bob
