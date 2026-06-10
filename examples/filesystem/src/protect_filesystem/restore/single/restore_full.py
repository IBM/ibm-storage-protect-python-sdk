"""
Single Object Full Restoration for Filesystem
==============================================

Demonstrates full restoration for a single file.
Output: example_restored.json
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


if __name__ == "__main__":
    print("="*60)
    print("SINGLE OBJECT - FULL RESTORATION")
    print("="*60)
    
    try:
        creds = LoginCredentials()
        sess = ClientSession()
        sess.login(creds)
        
        restore_request = RestoreRequest(
            Key=BACKUP_KEY,
            Filespace=FILESPACE
        )
        
        client = DataClient(sess)
        result = client.restore(restore_request)
        
        # Save restored file
        output_file = OUTPUT_DIR / "example_restored.json"
        print(f"Restoring to: {output_file}")
        
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
