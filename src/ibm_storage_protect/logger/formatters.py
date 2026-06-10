"""
IBM Storage Protect SDK - Log Formatters

This module provides log formatters for JSON (structured) and colored text formats.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

_LEVEL_COLORS = {
    'DEBUG': '\033[36m',
    'INFO': '\033[32m',
    'WARNING': '\033[33m',
    'ERROR': '\033[31m',
    'CRITICAL': '\033[35m',
}
_RESET_COLOR = '\033[0m'


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': getattr(record, 'timestamp', datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        event_type = getattr(record, 'event_type', None)
        operation = getattr(record, 'operation', None)
        operation_id = getattr(record, 'operation_id', None)
        correlation_id = getattr(record, 'correlation_id', None)
        request_id = getattr(record, 'request_id', None)
        session_handle = getattr(record, 'session_handle', None)
        object_key = getattr(record, 'object_key', None)
        status = getattr(record, 'status', None)
        duration_ms = getattr(record, 'duration_ms', None)
        context = getattr(record, 'context', None)
        metrics = getattr(record, 'metrics', None)
        error = getattr(record, 'error', None)
        internal = getattr(record, 'internal', None)

        if event_type is not None:
            log_data['event_type'] = event_type
        if operation is not None:
            log_data['operation'] = operation
        if operation_id is not None:
            log_data['operation_id'] = operation_id
        if session_handle is not None:
            log_data['session_handle'] = session_handle
        elif correlation_id is not None:
            log_data['correlation_id'] = correlation_id
        if object_key is not None:
            log_data['object_key'] = object_key
        elif request_id is not None:
            log_data['request_id'] = request_id
        if status is not None:
            log_data['status'] = status
        if duration_ms is not None:
            log_data['duration_ms'] = duration_ms
        if context is not None:
            log_data['context'] = context
        if metrics is not None:
            log_data['metrics'] = metrics
        if error is not None:
            log_data['error'] = error
        if internal is not None:
            log_data['internal'] = internal

        c_error_code = getattr(record, 'c_error_code', None)
        if c_error_code is not None:
            internal_data = cast(Dict[str, Any], log_data.setdefault('internal', {}))
            internal_data['c_error_code'] = c_error_code
        c_api_message = getattr(record, 'c_api_message', None)
        if c_api_message is not None:
            internal_data = cast(Dict[str, Any], log_data.setdefault('internal', {}))
            internal_data['c_api_message'] = c_api_message
        sdk_error_code = getattr(record, 'sdk_error_code', None)
        if sdk_error_code is not None:
            error_data = cast(Dict[str, Any], log_data.setdefault('error', {}))
            error_data['sdk_error_code'] = sdk_error_code

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Human-readable text formatter with optional color coding.
    """

    def __init__(self, fmt: Optional[str] = None, use_colors: bool = False):
        super().__init__(fmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, 'timestamp'):
            record.timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
        base_msg = super().format(record)

        extras = []
        event_type = getattr(record, 'event_type', None)
        operation = getattr(record, 'operation', None)
        sdk_error_code = getattr(record, 'sdk_error_code', None)
        c_error_code = getattr(record, 'c_error_code', None)
        category = getattr(record, 'category', None)
        retry_recommended = getattr(record, 'retry_recommended', None)
        session_handle = getattr(record, 'session_handle', None)
        object_key = getattr(record, 'object_key', None)
        correlation_id = getattr(record, 'correlation_id', None)
        request_id = getattr(record, 'request_id', None)
        status = getattr(record, 'status', None)
        duration_ms = getattr(record, 'duration_ms', None)

        if event_type is not None:
            extras.append(f"event={event_type}")
        if operation is not None:
            extras.append(f"op={operation}")
        if sdk_error_code is not None:
            extras.append(f"error_code={sdk_error_code}")
        if c_error_code is not None:
            extras.append(f"c_code={c_error_code}")
        if category is not None:
            extras.append(f"category={category}")
        if retry_recommended is not None:
            extras.append(f"retry={retry_recommended}")
        if session_handle is not None:
            extras.append(f"session={session_handle}")
        elif correlation_id is not None:
            extras.append(f"correlation_id={correlation_id}")
        if object_key is not None:
            extras.append(f"key={object_key}")
        elif request_id is not None:
            extras.append(f"request_id={request_id}")
        if status is not None:
            extras.append(f"status={status}")
        if duration_ms is not None:
            extras.append(f"duration_ms={duration_ms}")

        if extras:
            base_msg = f"{base_msg} | {' | '.join(extras)}"

        if self.use_colors:
            color = _LEVEL_COLORS.get(record.levelname, '')
            if color:
                return f"{color}{base_msg}{_RESET_COLOR}"
        return base_msg
