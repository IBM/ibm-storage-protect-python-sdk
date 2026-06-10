"""
IBM Storage Protect Client API Function Prototypes

This module defines function prototypes (signatures) for IBM Storage Protect Client API
functions using ctypes to specify return types and argument types.

Function Categories: Session Management, Transaction Control, Data Operations, Query
Operations, Object Management, Filespace Management, Group Operations, Buffer Management.

Return Types: Most functions return dsInt16_t (return code). 0 = success, non-zero = error.

Reference: https://www.ibm.com/docs/en/SSEQVQ_8.2.0/pdf/b_api_using.pdf
"""

import ctypes

# pylint: disable=wildcard-import,unused-wildcard-import,line-too-long
from .load import lib          # lib = ctypes.CDLL(...), already loaded
from .platform_types import *        # base types: dsInt16_t, dsUint32_t, dsBool_t, etc.
from .structs import *        # structs/enums: dsmObjName, DataBlk, ObjAttr, etc.


# =============================================================================
# Data Retrieval Functions
# =============================================================================

# --- dsmBeginGetData ---------------------------------------------------------
# Initiates retrieval of one or more backup objects
# Args: session_handle, mount_wait, get_type, get_list
lib.dsmBeginGetData.restype = dsInt16_t
lib.dsmBeginGetData.argtypes = [dsUint32_t, dsBool_t, dsmGetType, ctypes.POINTER(dsmGetList)]

# =============================================================================
# Query Functions
# =============================================================================

# --- dsmBeginQuery -----------------------------------------------------------
# Starts a query operation (backup, filespace, management class, groups, etc.)
# Args: session_handle, query_type, query_buffer
# Note: dsmQueryBuff is void*, query_buffer contains query-specific data
lib.dsmBeginQuery.restype = dsInt16_t
lib.dsmBeginQuery.argtypes = [dsUint32_t, dsmQueryType, ctypes.c_void_p]

# =============================================================================
# Transaction Control Functions
# =============================================================================

# --- dsmBeginTxn -------------------------------------------------------------
# Begins a transaction for backup/restore operations
# Args: session_handle
lib.dsmBeginTxn.restype = dsInt16_t
lib.dsmBeginTxn.argtypes = [dsUint32_t]

# =============================================================================
# Management Class Functions
# =============================================================================

# --- dsmBindMC ---------------------------------------------------------------
# Binds an object to a management class to determine retention policy
# Args: session_handle, obj_name, send_type, mc_bind_key
lib.dsmBindMC.restype = dsInt16_t
lib.dsmBindMC.argtypes = [dsUint32_t, ctypes.POINTER(dsmObjName), dsmSendType, ctypes.POINTER(mcBindKey)]

# --- dsmChangePW -------------------------------------------------------------
lib.dsmChangePW.restype = dsInt16_t
lib.dsmChangePW.argtypes = [dsUint32_t, ctypes.c_char_p, ctypes.c_char_p]

# --- dsmCleanUp --------------------------------------------------------------
lib.dsmCleanUp.restype = dsInt16_t
lib.dsmCleanUp.argtypes = [dsBool_t]

# --- dsmDeleteAccess ---------------------------------------------------------
lib.dsmDeleteAccess.restype = dsInt16_t
lib.dsmDeleteAccess.argtypes = [dsUint32_t, dsUint32_t]

# --- dsmDeleteObj ------------------------------------------------------------
lib.dsmDeleteObj.restype = dsInt16_t
lib.dsmDeleteObj.argtypes = [dsUint32_t, dsmDelType, dsmDelInfo]

# --- dsmDeleteFS -------------------------------------------------------------
lib.dsmDeleteFS.restype = dsInt16_t
lib.dsmDeleteFS.argtypes = [dsUint32_t, ctypes.c_char_p, dsUint8_t]

# --- dsmEndGetData -----------------------------------------------------------
lib.dsmEndGetData.restype = dsInt16_t
lib.dsmEndGetData.argtypes = [dsUint32_t]

# --- dsmEndGetDataEx ---------------------------------------------------------
lib.dsmEndGetDataEx.restype = dsInt16_t
lib.dsmEndGetDataEx.argtypes = [ctypes.POINTER(dsmEndGetDataExIn_t), ctypes.POINTER(dsmEndGetDataExOut_t)]

# --- dsmEndGetObj ------------------------------------------------------------
lib.dsmEndGetObj.restype = dsInt16_t
lib.dsmEndGetObj.argtypes = [dsUint32_t]

# --- dsmEndQuery -------------------------------------------------------------
lib.dsmEndQuery.restype = dsInt16_t
lib.dsmEndQuery.argtypes = [dsUint32_t]

# --- dsmEndSendObj -----------------------------------------------------------
lib.dsmEndSendObj.restype = dsInt16_t
lib.dsmEndSendObj.argtypes = [dsUint32_t]

# --- dsmEndSendObjEx ---------------------------------------------------------
lib.dsmEndSendObjEx.restype = dsInt16_t
lib.dsmEndSendObjEx.argtypes = [ctypes.POINTER(dsmEndSendObjExIn_t), ctypes.POINTER(dsmEndSendObjExOut_t)]

# --- dsmEndTxnEx -------------------------------------------------------------
lib.dsmEndTxnEx.restype = dsInt16_t
lib.dsmEndTxnEx.argtypes = [ctypes.POINTER(dsmEndTxnExIn_t), ctypes.POINTER(dsmEndTxnExOut_t)]

# --- dsmEndTxn ---------------------------------------------------------------
lib.dsmEndTxn.restype = dsInt16_t
lib.dsmEndTxn.argtypes = [dsUint32_t, dsUint8_t, ctypes.POINTER(dsUint16_t)]

# --- dsmGetData --------------------------------------------------------------
lib.dsmGetData.restype = dsInt16_t
lib.dsmGetData.argtypes = [dsUint32_t, ctypes.POINTER(DataBlk)]

# --- dsmGetBufferData --------------------------------------------------------
lib.dsmGetBufferData.restype = dsInt16_t
lib.dsmGetBufferData.argtypes = [ctypes.POINTER(getBufferDataIn_t), ctypes.POINTER(getBufferDataOut_t)]

# --- dsmGetNextQObj ----------------------------------------------------------
lib.dsmGetNextQObj.restype = dsInt16_t
lib.dsmGetNextQObj.argtypes = [dsUint32_t, ctypes.POINTER(DataBlk)]

# --- dsmGetObj ---------------------------------------------------------------
lib.dsmGetObj.restype = dsInt16_t
lib.dsmGetObj.argtypes = [dsUint32_t, ctypes.POINTER(ObjID), ctypes.POINTER(DataBlk)]

# =============================================================================
# Group Management Functions
# =============================================================================

# --- dsmGroupHandler ---------------------------------------------------------
# Manage backup groups (begin, open, close, add, assign, remove members)
# Args: group_handler_in, group_handler_out
# Returns: DSM_RC_SUCCESSFUL on success, error code otherwise
# Note: Groups allow coordinated backup/restore of related objects
lib.dsmGroupHandler.restype = dsInt16_t
lib.dsmGroupHandler.argtypes = [ctypes.POINTER(dsmGroupHandlerIn_t), ctypes.POINTER(dsmGroupHandlerOut_t)]


# =============================================================================
# Session Initialization Functions
# =============================================================================

# --- dsmInit -----------------------------------------------------------------
# Initialize a session with the IBM Storage Protect server (basic version)
# Args: session_handle_ptr, api_version, app_type, config_file, options,
#       node_name, owner_name, password
# Returns: DSM_RC_SUCCESSFUL on success, error code otherwise
lib.dsmInit.restype = dsInt16_t
lib.dsmInit.argtypes = [
    ctypes.POINTER(dsUint32_t),      # OUT: session handle
    ctypes.POINTER(dsmApiVersion),   # IN: API version
    ctypes.c_char_p,                 # IN: application type
    ctypes.c_char_p,                 # IN: config file path
    ctypes.c_char_p,                 # IN: options
    ctypes.c_char_p,                 # IN: node name
    ctypes.c_char_p,                 # IN: owner name
    ctypes.c_char_p                  # IN: password
]

# --- dsmInitEx ---------------------------------------------------------------
# Initialize a session with extended parameters (preferred method)
# Args: session_handle_ptr, init_in, init_out
# Returns: DSM_RC_SUCCESSFUL on success, error code otherwise
lib.dsmInitEx.restype = dsInt16_t
lib.dsmInitEx.argtypes = [ctypes.POINTER(dsUint32_t), ctypes.POINTER(dsmInitExIn_t), ctypes.POINTER(dsmInitExOut_t)]

# --- dsmLogEvent -------------------------------------------------------------
lib.dsmLogEvent.restype = dsInt16_t
lib.dsmLogEvent.argtypes = [dsUint32_t, ctypes.POINTER(logInfo)]

# --- dsmLogEventEx -----------------------------------------------------------
lib.dsmLogEventEx.restype = dsInt16_t
lib.dsmLogEventEx.argtypes = [dsUint32_t, ctypes.POINTER(dsmLogExIn_t), ctypes.POINTER(dsmLogExOut_t)]

# --- dsmQueryAccess ----------------------------------------------------------
# qryRespAccessData ** => POINTER(POINTER(qryRespAccessData))
lib.dsmQueryAccess.restype = dsInt16_t
lib.dsmQueryAccess.argtypes = [dsUint32_t, ctypes.POINTER(ctypes.POINTER(qryRespAccessData)), ctypes.POINTER(dsUint16_t)]

# --- dsmQueryApiVersion ------------------------------------------------------
lib.dsmQueryApiVersion.restype = None
lib.dsmQueryApiVersion.argtypes = [ctypes.POINTER(dsmApiVersion)]

# --- dsmQueryApiVersionEx ----------------------------------------------------
lib.dsmQueryApiVersionEx.restype = None
lib.dsmQueryApiVersionEx.argtypes = [ctypes.POINTER(dsmApiVersionEx)]

# --- dsmQueryCliOptions ------------------------------------------------------
lib.dsmQueryCliOptions.restype = dsInt16_t
lib.dsmQueryCliOptions.argtypes = [ctypes.POINTER(optStruct)]

# --- dsmQuerySessInfo --------------------------------------------------------
lib.dsmQuerySessInfo.restype = dsInt16_t
lib.dsmQuerySessInfo.argtypes = [dsUint32_t, ctypes.POINTER(ApiSessInfo)]

# --- dsmQuerySessOptions -----------------------------------------------------
lib.dsmQuerySessOptions.restype = dsInt16_t
lib.dsmQuerySessOptions.argtypes = [dsUint32_t, ctypes.POINTER(optStruct)]

# --- dsmRCMsg ----------------------------------------------------------------
lib.dsmRCMsg.restype = dsInt16_t
lib.dsmRCMsg.argtypes = [dsUint32_t, dsInt16_t, ctypes.c_char_p]

# --- dsmRegisterFS -----------------------------------------------------------
lib.dsmRegisterFS.restype = dsInt16_t
lib.dsmRegisterFS.argtypes = [dsUint32_t, ctypes.POINTER(regFSData)]

# --- dsmReleaseBuffer --------------------------------------------------------
lib.dsmReleaseBuffer.restype = dsInt16_t
lib.dsmReleaseBuffer.argtypes = [ctypes.POINTER(releaseBufferIn_t), ctypes.POINTER(releaseBufferOut_t)]

# --- dsmRenameObj ------------------------------------------------------------
lib.dsmRenameObj.restype = dsInt16_t
lib.dsmRenameObj.argtypes = [ctypes.POINTER(dsmRenameIn_t), ctypes.POINTER(dsmRenameOut_t)]

# --- dsmRequestBuffer --------------------------------------------------------
lib.dsmRequestBuffer.restype = dsInt16_t
lib.dsmRequestBuffer.argtypes = [ctypes.POINTER(requestBufferIn_t), ctypes.POINTER(requestBufferOut_t)]

# --- dsmRetentionEvent -------------------------------------------------------
lib.dsmRetentionEvent.restype = dsInt16_t
lib.dsmRetentionEvent.argtypes = [ctypes.POINTER(dsmRetentionEventIn_t), ctypes.POINTER(dsmRetentionEventOut_t)]

# --- dsmSendBufferData -------------------------------------------------------
lib.dsmSendBufferData.restype = dsInt16_t
lib.dsmSendBufferData.argtypes = [ctypes.POINTER(sendBufferDataIn_t), ctypes.POINTER(sendBufferDataOut_t)]

# --- dsmSendData -------------------------------------------------------------
lib.dsmSendData.restype = dsInt16_t
lib.dsmSendData.argtypes = [dsUint32_t, ctypes.POINTER(DataBlk)]

# =============================================================================
# Data Send Functions
# =============================================================================

# --- dsmSendObj --------------------------------------------------------------
# Send an object to the server (initiates backup operation)
# Args: session_handle, send_type, send_buff, obj_name, obj_attr, data_blk
# Note: send_buff is reserved (pass NULL/None)
# Returns: DSM_RC_SUCCESSFUL on success, error code otherwise
lib.dsmSendObj.restype = dsInt16_t
lib.dsmSendObj.argtypes = [
    dsUint32_t,                      # IN: session handle
    dsmSendType,                     # IN: send type (stBackup, etc.)
    ctypes.c_void_p,                 # IN: reserved (pass None)
    ctypes.POINTER(dsmObjName),      # IN: object name
    ctypes.POINTER(ObjAttr),         # IN: object attributes
    ctypes.POINTER(DataBlk),         # IN/OUT: data block for first chunk
]

# --- dsmSetAccess ------------------------------------------------------------
lib.dsmSetAccess.restype = dsInt16_t
lib.dsmSetAccess.argtypes = [dsUint32_t, dsmAccessType, ctypes.POINTER(dsmObjName), ctypes.c_char_p, ctypes.c_char_p]

# --- dsmSetUp ----------------------------------------------------------------
lib.dsmSetUp.restype = dsInt16_t
lib.dsmSetUp.argtypes = [dsBool_t, ctypes.POINTER(envSetUp)]

# --- dsmTerminate ------------------------------------------------------------
lib.dsmTerminate.restype = dsInt16_t
lib.dsmTerminate.argtypes = [dsUint32_t]

# --- dsmUpdateFS -------------------------------------------------------------
lib.dsmUpdateFS.restype = dsInt16_t
lib.dsmUpdateFS.argtypes = [dsUint32_t, ctypes.c_char_p, ctypes.POINTER(dsmFSUpd), dsUint32_t]

# --- dsmUpdateObj ------------------------------------------------------------
lib.dsmUpdateObj.restype = dsInt16_t
lib.dsmUpdateObj.argtypes = [
    dsUint32_t, dsmSendType, ctypes.c_void_p,
    ctypes.POINTER(dsmObjName),
    ctypes.POINTER(ObjAttr),
    dsUint32_t,
]

# --- dsmUpdateObjEx ----------------------------------------------------------
lib.dsmUpdateObjEx.restype = dsInt16_t
lib.dsmUpdateObjEx.argtypes = [ctypes.POINTER(dsmUpdateObjExIn_t), ctypes.POINTER(dsmUpdateObjExOut_t)]
