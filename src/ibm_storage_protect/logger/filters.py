"""
IBM Storage Protect SDK - Logging Filters & Sanitization

This module defines standard logging filters and utility functions to sanitize
sensitive data and route low-level C API bridge messages to separate diagnostics logs.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict
from .context import _context


def _sanitize_value(key: str, value: Any) -> Any:
    """
    Check if a value should be sanitized based on its key name.
    """
    sensitive_keys = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'key',
        'credential', 'auth', 'authorization', 'api_key'
    }

    key_lower = key.lower()
    if any(sensitive in key_lower for sensitive in sensitive_keys):
        return '***REDACTED***'

    return value


def sanitize_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a dictionary by redacting sensitive values.
    """
    if not isinstance(context, dict):
        return context

    return {k: _sanitize_value(k, v) for k, v in context.items()}


class SafeExtraFilter(logging.Filter):
    """
    Logging filter that enriches log records with context and sanitizes sensitive data.
    """

    def __init__(self, include_internal_details: bool = False, include_exception_traces: bool = True):
        super().__init__()
        self.include_internal_details = include_internal_details
        self.include_exception_traces = include_exception_traces

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'timestamp'):
            record.timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
        if not hasattr(record, 'perf_ns'):
            record.perf_ns = time.perf_counter_ns()

        if not hasattr(record, 'session_handle'):
            record.session_handle = getattr(_context, 'session_handle', None)

        if not hasattr(record, 'object_key'):
            record.object_key = getattr(_context, 'object_key', None)

        if not hasattr(record, 'correlation_id'):
            record.correlation_id = getattr(_context, 'correlation_id', None)

        if not hasattr(record, 'request_id'):
            record.request_id = getattr(_context, 'request_id', None)

        context = getattr(record, 'context', None)
        if isinstance(context, dict):
            record.context = sanitize_context(context)

        error = getattr(record, 'error', None)
        if isinstance(error, dict):
            record.error = sanitize_context(error)

        if not self.include_internal_details:
            for attr in ('internal', 'c_error_code', 'c_api_message', 'function', 'pathname', 'filename', 'module'):
                if hasattr(record, attr):
                    delattr(record, attr)

        if not self.include_exception_traces:
            record.exc_info = None
            record.stack_info = None
        return True


class ExcludeCApiBridgeFilter(logging.Filter):
    """
    Filter that excludes log records from the c_api_bridge module.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "c_api_bridge" not in record.name


class IncludeCApiBridgeFilter(logging.Filter):
    """
    Filter that includes only log records from the c_api_bridge module.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "c_api_bridge" in record.name
