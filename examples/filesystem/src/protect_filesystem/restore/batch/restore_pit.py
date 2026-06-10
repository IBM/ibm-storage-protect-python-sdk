"""
Batch Object Point-in-Time Restoration for PostgreSQL
======================================================

Demonstrates point-in-time restoration for multiple PostgreSQL database files.
Output: <filename>_20260531224358_restored.tar.gz
"""

from pathlib import Path
from datetime import datetime

from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.restore import RestoreRequest, BatchRestoreRequest
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger


configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/postgre/src/protect_postgre/restore/batch/logs",
    log_format="json",
    console_level="INFO"
))



# Output directory for restored files
OUTPUT_DIR = Path("/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/restore_dummy_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Backup inventory details
FILESPACE = "/postgres_bckp"
BACKUP_TIMESTAMP = datetime(2026, 5, 31, 22, 43, 58)
BATCH_FILES = [
    "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/audit_db.tar.gz",
    "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/employee_db.tar.gz",
    "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/inventory_db.tar.gz",
    "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/logs_db.tar.gz",
    "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/sales_db.tar.gz",
]


if __name__ == "__main__":
    print("="*60)
    print("BATCH OBJECTS - POINT-IN-TIME RESTORATION")
    print("="*60)
    
    try:
        creds = LoginCredentials()
        sess = ClientSession()
        sess.login(creds)
        
        # Create batch restore request with PIT date
        restore_requests = [
            RestoreRequest(Key=file_path, Filespace=FILESPACE, PitDate=BACKUP_TIMESTAMP)
            for file_path in BATCH_FILES
        ]
        
        batch_request = BatchRestoreRequest(
            Objects=restore_requests,
            Filespace=FILESPACE
        )
        
        client = DataClient(sess)
        result = client.batch_restore(batch_request)
        
        timestamp_str = BACKUP_TIMESTAMP.strftime("%Y%m%d%H%M%S")
        print(f"Restoring {result.total_objects} files from PIT: {BACKUP_TIMESTAMP}")
        
        # Save each restored file with timestamp
        for restore_result in result.results:
            filename = Path(restore_result.key).name
            base_name = filename.replace('.tar.gz', '')
            output_file = OUTPUT_DIR / f"{base_name}_{timestamp_str}_restored.tar.gz"
            
            print(f"\n  Restoring: {filename}")
            print(f"  Output: {output_file}")
            
            bytes_written = 0
            with open(output_file, "wb") as f:
                for chunk in restore_result.body:
                    f.write(chunk)
                    bytes_written += len(chunk)
            
            print(f"  ✓ Bytes written: {bytes_written:,}")
            print(f"  Object ID: {restore_result.object_id}")
        
        print(f"\n✓ All {result.total_objects} files restored successfully")
        
        sess.logout()
        print("="*60)
        
    except TSMError as e:
        print(f"\n✗ Restoration failed: {e}")
        raise

# Made with Bob
