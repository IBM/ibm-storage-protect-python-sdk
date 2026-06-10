"""
Single Object Point-in-Time Restoration for Filesystem
=======================================================

Demonstrates point-in-time restoration for a single file.
Output: example_20260531223504_restored.json
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
    log_dir="./logs",
    log_format="json",
    console_level="INFO"
))



# Output directory for restored files
OUTPUT_DIR = Path("./restored_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Backup inventory details
FILESPACE = "/filesystem_backup"
BACKUP_KEY = "/path/to/data/example.json"
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
        output_file = OUTPUT_DIR / f"example_{timestamp_str}_restored.json"
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
