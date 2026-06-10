"""
Query Single PostgreSQL Backup
================================

Query metadata for a single backed up PostgreSQL database file.
This script queries the ecommerce_db.tar.gz file that was backed up.
"""

from ibm_storage_protect import ClientSession, QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.query import BackupQueryRequest
from ibm_storage_protect.enums import ObjState, ObjType
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger

configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/postgre/src/protect_postgre/query/logs",
    log_format="json",
    console_level="INFO"
))


def query_single_backup():
    """Query the single ecommerce_db.tar.gz backup"""
    
    # Initialize session
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    query_client = QueryClient(session)
    
    # File that was backed up
    file_path = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/normal_backup_dummy_data/ecommerce_db.tar.gz"
    filespace = "/postgres_bckp"
    
    print("="*70)
    print("QUERY SINGLE POSTGRESQL BACKUP")
    print("="*70)
    print(f"\nQuerying file: {file_path}")
    print(f"Filespace: {filespace}")
    
    try:
        # Query the specific backup object
        query = BackupQueryRequest(
            Key=file_path,
            Filespace=filespace,
            ObjState=ObjState.ACTIVE,
            ObjType=ObjType.FILE
        )
        
        result = query_client.query_object(query)
        
        if result and result.key:
            print(f"\n✓ Found backup")
            print("\n" + "-"*70)
            
            print(f"Object Key: {result.key}")
            print(f"Filespace: {result.filespace}")
            print(f"Object ID: {result.object_id}")
            print(f"State: {result.state}")
            print(f"Size: {result.size:,} bytes ({result.size / (1024*1024):.2f} MB)")
            print(f"Last Modified: {result.last_modified}")
            print(f"Expiration Date: {result.expiry_date}")
            print(f"Owner: {result.owner}")
            print(f"Management Class: {result.management_class}")
            print(f"Compressed: {result.compressed}")
            print(f"Deduplicated: {result.deduplicated}")
            print(f"Media Class: {result.media_class}")
            print(f"Copy Group: {result.copy_group}")
            
            if result.is_group_leader:
                print(f"Group Leader: Yes")
            elif result.group_leader_obj_id:
                print(f"Group Member: Yes (Leader ID: {result.group_leader_obj_id})")
            else:
                print(f"Group Member: No")
            
            print("-"*70)
        else:
            print("\n✗ No backup found for this file")
            print("  The file may not have been backed up yet or may have expired.")
    
    except TSMError as e:
        print(f"\n✗ Query failed: {e}")
    
    finally:
        session.logout()
        print("\nQuery operation completed.")


if __name__ == "__main__":
    query_single_backup()

# Made with Bob
