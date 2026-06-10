"""
Single Object Backup for PostgreSQL
====================================

Demonstrates backing up a single PostgreSQL database file to IBM Storage Protect.
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
    log_dir="/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/postgre/src/protect_postgre/backup/logs",
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


file_path_1 = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/audit_db.tar.gz"
file_path_2 = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/employee_db.tar.gz"
file_path_3 = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/inventory_db.tar.gz"
file_path_4 = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/logs_db.tar.gz"
file_path_5 = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/sales_db.tar.gz"
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
    Filespace="/postgres_bckp",
    MaxPerTxn=10
)

client = DataClient(sess)
result = client.batch_backup(batch)
print(result)
sess.logout()
print("success")