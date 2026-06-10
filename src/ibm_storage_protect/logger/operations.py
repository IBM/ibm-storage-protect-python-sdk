"""
IBM Storage Protect SDK - Logging Operations Context Manager

This module implements telemetry tracing context manager wrappers for SDK calls.
"""

import contextlib
import logging
import time
from typing import Any, Dict, Optional
from .context import set_log_context


@contextlib.contextmanager
def log_operation(
    logger: logging.Logger,
    operation_name: str,
    session: Any,
    filespace: Optional[str] = None,
    object_key: Optional[str] = None,
    context_details: Optional[Dict[str, Any]] = None,
    handle: Optional[Any] = None
) -> Any:
    """
    Context manager to wrap SDK operations with standard structured logging.
    """
    # pylint: disable=import-outside-toplevel
    from ibm_storage_protect.errors.exceptions import TSMError

    session_handle = getattr(session, '_session_id', None)
    if not session_handle and hasattr(session, '_session'):
        # pylint: disable=protected-access
        session_handle = getattr(session._session, '_session_id', None)

    start_time = time.perf_counter()
    set_log_context(session_handle=session_handle, object_key=object_key)

    result_data = {
        "context": context_details.copy() if context_details else {},
        "metrics": {}
    }

    start_extra = {
        'event_type': f'{operation_name}.started',
        'operation': operation_name,
        'session_handle': session_handle,
        'object_key': object_key,
        'status': 'started',
        'context': result_data["context"]
    }
    if filespace is not None:
        start_extra['filespace'] = filespace
    if handle is not None:
        start_extra['handle'] = handle

    logger.info("Starting %s: %s", operation_name, object_key or "", extra=start_extra)

    try:
        yield result_data

        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
        result_data["metrics"]["duration_ms"] = duration_ms

        success_extra = {
            'event_type': f'{operation_name}.completed',
            'operation': operation_name,
            'session_handle': session_handle,
            'object_key': object_key,
            'duration_ms': duration_ms,
            'status': 'success',
            'context': result_data["context"],
            'metrics': result_data["metrics"]
        }
        if filespace is not None:
            success_extra['filespace'] = filespace
        if handle is not None:
            success_extra['handle'] = handle

        logger.info("%s completed: %s", operation_name.capitalize(), object_key or "", extra=success_extra)

    except TSMError as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
        fail_extra = {
            'event_type': f'{operation_name}.failed',
            'operation': operation_name,
            'session_handle': session_handle,
            'object_key': object_key,
            'duration_ms': duration_ms,
            'status': 'failed',
            'context': result_data["context"],
            'error': e.to_dict(),
            'metrics': {'duration_ms': duration_ms}
        }
        if filespace is not None:
            fail_extra['filespace'] = filespace
        if handle is not None:
            fail_extra['handle'] = handle

        logger.error("%s failed: %s", operation_name.capitalize(), object_key or "", extra=fail_extra, exc_info=True)
        raise

    except Exception as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
        err_extra = {
            'event_type': f'{operation_name}.error',
            'operation': operation_name,
            'session_handle': session_handle,
            'object_key': object_key,
            'duration_ms': duration_ms,
            'status': 'error',
            'context': result_data["context"],
            'error': {
                'message': str(e),
                'error_type': type(e).__name__
            },
            'metrics': {'duration_ms': duration_ms}
        }
        if filespace is not None:
            err_extra['filespace'] = filespace
        if handle is not None:
            err_extra['handle'] = handle

        logger.error("Unexpected error during %s: %s", operation_name, object_key or "", extra=err_extra, exc_info=True)
        raise
