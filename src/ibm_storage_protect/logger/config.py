"""
IBM Storage Protect SDK - Logging Configuration

This module defines the log configuration classes, logger instantiation helpers,
and dynamic log level controls.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from .filters import SafeExtraFilter, ExcludeCApiBridgeFilter, IncludeCApiBridgeFilter
from .formatters import StructuredFormatter, TextFormatter


class LogConfig:
    """
    Configuration class for logging setup.
    """

    def __init__(
        self,
        enable_user_log: bool = True,
        enable_debug_log: bool = False,
        enable_error_log: bool = True,
        enable_internal_api_log: bool = False,
        user_log_file: str = "ibm_sp_user.log",
        debug_log_file: str = "ibm_sp_debug.log",
        error_log_file: str = "ibm_sp_error.log",
        internal_api_log_file: str = "ibm_sp_internal_api.log",
        log_dir: str = "logs",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        log_format: str = "text",
        console_output: bool = True,
        console_level: str = "INFO",
        internal_api_log_level: str = "DEBUG"
    ):
        self.enable_user_log = enable_user_log
        self.enable_debug_log = enable_debug_log
        self.enable_error_log = enable_error_log
        self.enable_internal_api_log = enable_internal_api_log
        self.user_log_file = user_log_file
        self.debug_log_file = debug_log_file
        self.error_log_file = error_log_file
        self.internal_api_log_file = internal_api_log_file
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.log_format = log_format.lower()
        self.console_output = console_output
        self.console_level = console_level.upper()
        self.internal_api_log_level = internal_api_log_level.upper()

        Path(log_dir).mkdir(parents=True, exist_ok=True)


def configure_logging(config: Optional[LogConfig] = None) -> None:
    """
    Configure the logging system with the specified configuration.
    """
    if config is None:
        config = LogConfig()

    root_logger = logging.getLogger("ibm_storage_protect")
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    if config.log_format == "json":
        formatter = StructuredFormatter()
    else:
        formatter = TextFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    if config.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.console_level))
        console_handler.addFilter(SafeExtraFilter(include_internal_details=False))
        console_handler.addFilter(ExcludeCApiBridgeFilter())
        console_handler.setFormatter(
            TextFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                use_colors=True
            )
        )
        root_logger.addHandler(console_handler)

    if config.enable_user_log:
        user_handler = RotatingFileHandler(
            Path(config.log_dir) / config.user_log_file,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count
        )
        user_handler.setLevel(logging.INFO)
        user_handler.addFilter(SafeExtraFilter(include_internal_details=False))
        user_handler.addFilter(ExcludeCApiBridgeFilter())
        user_handler.setFormatter(formatter)
        root_logger.addHandler(user_handler)

    if config.enable_debug_log:
        debug_handler = RotatingFileHandler(
            Path(config.log_dir) / config.debug_log_file,
            maxBytes=config.max_bytes * 5,
            backupCount=config.backup_count * 2
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.addFilter(SafeExtraFilter(include_internal_details=True))
        debug_handler.setFormatter(formatter)
        root_logger.addHandler(debug_handler)

    if config.enable_error_log:
        error_handler = RotatingFileHandler(
            Path(config.log_dir) / config.error_log_file,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.addFilter(SafeExtraFilter(include_internal_details=True))
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    if config.enable_internal_api_log:
        internal_api_handler = RotatingFileHandler(
            Path(config.log_dir) / config.internal_api_log_file,
            maxBytes=config.max_bytes * 5,
            backupCount=config.backup_count * 2
        )
        internal_api_handler.setLevel(getattr(logging, config.internal_api_log_level))
        internal_api_handler.addFilter(SafeExtraFilter(include_internal_details=True))
        internal_api_handler.addFilter(IncludeCApiBridgeFilter())
        internal_api_handler.setFormatter(formatter)
        root_logger.addHandler(internal_api_handler)

    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.
    """
    if not name.startswith('ibm_storage_protect'):
        name = f'ibm_storage_protect.{name}'
    return logging.getLogger(name)


def set_sdk_log_level(level: str) -> None:
    """
    Dynamically adjust the log level for all active SDK handlers and the root logger.
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    root_logger = logging.getLogger("ibm_storage_protect")
    root_logger.setLevel(numeric_level)
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)


# Initialize default stream logger
_root_logger = logging.getLogger('ibm_storage_protect')
if not _root_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.addFilter(SafeExtraFilter(include_internal_details=False))
    _handler.addFilter(ExcludeCApiBridgeFilter())
    _handler.setFormatter(TextFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    _root_logger.addHandler(_handler)
    _root_logger.setLevel(logging.WARNING)
    _root_logger.propagate = False
