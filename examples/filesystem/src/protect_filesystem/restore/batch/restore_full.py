"""
Batch Object Full Restoration for Filesystem
=============================================

Demonstrates full restoration for multiple files.
Output: <filename>_restored.json
"""

from pathlib import Path

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
    log_dir="./logs",
    log_format="json",
    console_level="INFO"
))



# Output directory for restored files
OUTPUT_DIR = Path("./restored_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Backup inventory details
FILESPACE = "/filesystem_backup"
BATCH_FILES = [
    "/path/to/data/file1.json",
    "/path/to/data/file2.json",
    "/path/to/data/file3.json",
    "/path/to/data/file4.json",
    "/path/to/data/file5.json",
]


if __name__ == "__main__":
    print("="*60)
    print("BATCH OBJECTS - FULL RESTORATION")
    print("="*60)
    
    try:
        creds = LoginCredentials()
        sess = ClientSession()
        sess.login(creds)
        
        # Create batch restore request
        restore_requests = [
            RestoreRequest(Key=file_path, Filespace=FILESPACE)
            for file_path in BATCH_FILES
        ]
        
        batch_request = BatchRestoreRequest(
            Objects=restore_requests,
            Filespace=FILESPACE
        )
        
        client = DataClient(sess)
        result = client.batch_restore(batch_request)
        
        print(f"Restoring {result.total_objects} files...")
        
        # Save each restored file
        for restore_result in result.results:
            filename = Path(restore_result.key).name
            output_file = OUTPUT_DIR / f"{filename.replace('.json', '_restored.json')}"
            
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
