"""
Single Object Backup for Filesystem
====================================

Demonstrates backing up a single file to IBM Storage Protect.
Uses streaming chunks to handle large files efficiently.
"""

import os
import sys
import time
from pathlib import Path
from typing import Generator

from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger

configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="./logs",
    log_format="json",
    console_level="INFO"
))

_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunks


def read_file_in_chunks(filepath: str, chunk_size: int = _CHUNK_SIZE) -> Generator[bytes, None, None]:
    """
    Yield file data in chunks to avoid loading entire file into memory.
    
    Parameters
    ----------
    filepath : str
        Path to file to read
    chunk_size : int
        Maximum bytes per chunk (must be <= 4MB)
        
    Yields
    ------
    bytes
        File data chunks
    """
    with open(filepath, "rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            yield block

creds = LoginCredentials()
sess = ClientSession()
sess.login(creds)
file_path = "/path/to/data/example.json"
file_size = os.path.getsize(file_path)
bckp = BackupRequest(
    key = file_path,
    body = read_file_in_chunks(file_path),
    filespace = "/filesystem_backup",
    SizeEstimate = file_size
)
client = DataClient(sess)
result = client.backup(bckp)
print(f"Status: {result.status}")
print(f"Path: {result.filespace}{result.high_level}/{result.low_level}")
if result.stats:
    print(f"Bytes sent: {result.stats['total_bytes_sent']}")
    print(f"Compressed: {result.stats['compressed']}")
sess.logout()
print("success")