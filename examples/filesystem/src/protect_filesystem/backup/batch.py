"""
Batch Backup for Filesystem
============================

Demonstrates backing up multiple files to IBM Storage Protect in a batch operation.
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
from ibm_storage_protect.data_models.backup import BackupRequest,BatchBackupRequest
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

# Get a logger for your application (optional)
logger = get_logger('my_app')
logger.info("Application started")

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


file_path_1 = "/path/to/data/file1.json"
file_path_2 = "/path/to/data/file2.json"
file_path_3 = "/path/to/data/file3.json"
file_path_4 = "/path/to/data/file4.json"
file_path_5 = "/path/to/data/file5.json"
file_size_1 = os.path.getsize(file_path_1)
file_size_2 = os.path.getsize(file_path_2)
file_size_3 = os.path.getsize(file_path_3)
file_size_4 = os.path.getsize(file_path_4)
file_size_5 = os.path.getsize(file_path_5)
batch = BatchBackupRequest(
    objects=[
        BackupRequest(Key=file_path_1, Body=read_file_in_chunks(file_path_1),SizeEstimate = file_size_1),
        BackupRequest(Key=file_path_2, Body=read_file_in_chunks(file_path_2),SizeEstimate = file_size_2),
        BackupRequest(Key=file_path_3, Body=read_file_in_chunks(file_path_3),SizeEstimate = file_size_3),
        BackupRequest(Key=file_path_4, Body=read_file_in_chunks(file_path_4),SizeEstimate = file_size_4),
        BackupRequest(Key=file_path_5, Body=read_file_in_chunks(file_path_5),SizeEstimate = file_size_5),
        
    ],
    Filespace="/filesystem_backup",
    MaxPerTxn=10
)

client = DataClient(sess)
result = client.batch_backup(batch)
print(result)
sess.logout()
print("success")