"""
IBM Storage Protect SDK - Logging Context Management

This module manages the thread-local context variables used to correlate logs
across operations, requests, and sessions.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_context = threading.local()


def set_log_context(
    session_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    session_handle: Optional[str] = None,
    object_key: Optional[str] = None
):
    """
    Set thread-local logging context for correlation across operations.
    """
    if session_handle:
        _context.session_handle = session_handle
        _context.correlation_id = session_handle
        _context.session_id = session_handle
    elif session_id:
        _context.session_id = session_id
        _context.session_handle = session_id
        _context.correlation_id = session_id
    elif correlation_id:
        _context.correlation_id = correlation_id
        _context.session_handle = correlation_id
        _context.session_id = correlation_id

    if object_key:
        _context.object_key = object_key
        _context.request_id = object_key
        _context.operation_id = object_key
    elif operation_id:
        _context.operation_id = operation_id
        _context.object_key = operation_id
        _context.request_id = operation_id
    elif request_id:
        _context.request_id = request_id
        _context.object_key = request_id
        _context.operation_id = request_id


def create_session_id(handle: int) -> str:
    """
    Create a unique session ID from a C API handle.
    """
    suffix = datetime.now(timezone.utc).strftime("%H%M%S")
    return f"handle_{handle}_{suffix}"


def create_operation_id(key: Optional[str] = None, operation: Optional[str] = None) -> str:
    """
    Create a unique operation ID for tracking operations.
    """
    if key:
        return key
    if operation:
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        return f"{operation}_{timestamp}"
    return str(uuid.uuid4())


def clear_log_context():
    """
    Clear all thread-local logging context.
    """
    for attr in ['correlation_id', 'request_id', 'session_id', 'operation_id',
                 'session_handle', 'object_key']:
        if hasattr(_context, attr):
            delattr(_context, attr)


def get_log_context() -> Dict[str, Optional[str]]:
    """
    Retrieve the current thread-local logging context.
    """
    return {
        'session_id': getattr(_context, 'session_id', None),
        'operation_id': getattr(_context, 'operation_id', None),
        'correlation_id': getattr(_context, 'correlation_id', None),
        'request_id': getattr(_context, 'request_id', None),
        'session_handle': getattr(_context, 'session_handle', None),
        'object_key': getattr(_context, 'object_key', None)
    }
