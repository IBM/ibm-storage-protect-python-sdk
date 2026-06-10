"""
Single Object Point-in-Time Restoration for PostgreSQL
=======================================================

Demonstrates point-in-time restoration for a single PostgreSQL database file.
Output: ecommerce_db_20260531223504_restored.tar.gz
"""

from pathlib import Path
from datetime import datetime

from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.restore import RestoreRequest
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger


configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/postgre/src/protect_postgre/restore/single/logs",
    log_format="json",
    console_level="INFO"
))



# Output directory for restored files
OUTPUT_DIR = Path("/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/restore_dummy_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Backup inventory details
FILESPACE = "/postgres_bckp"
BACKUP_KEY = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/normal_backup_dummy_data/ecommerce_db.tar.gz"
BACKUP_TIMESTAMP = datetime(2026, 5, 31, 22, 35, 4)


if __name__ == "__main__":
    print("="*60)
    print("SINGLE OBJECT - POINT-IN-TIME RESTORATION")
    print("="*60)
    
    try:
        creds = LoginCredentials()
        sess = ClientSession()
        sess.login(creds)
        
        restore_request = RestoreRequest(
            Key=BACKUP_KEY,
            Filespace=FILESPACE,
            PitDate=BACKUP_TIMESTAMP
        )
        
        client = DataClient(sess)
        result = client.restore(restore_request)
        
        # Save restored file with timestamp
        timestamp_str = BACKUP_TIMESTAMP.strftime("%Y%m%d%H%M%S")
        output_file = OUTPUT_DIR / f"ecommerce_db_{timestamp_str}_restored.tar.gz"
        print(f"Restoring to: {output_file}")
        print(f"PIT Date: {BACKUP_TIMESTAMP}")
        
        bytes_written = 0
        with open(output_file, "wb") as f:
            for chunk in result.body:
                f.write(chunk)
                bytes_written += len(chunk)
        
        print(f"✓ Restoration completed")
        print(f"  Bytes written: {bytes_written:,}")
        print(f"  Object ID: {result.object_id}")
        print(f"  Last Modified: {result.last_modified}")
        
        sess.logout()
        print("="*60)
        
    except TSMError as e:
        print(f"\n✗ Restoration failed: {e}")
        raise

# Made with Bob
