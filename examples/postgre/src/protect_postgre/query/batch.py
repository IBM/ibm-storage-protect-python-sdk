"""
Query Batch PostgreSQL Backups
================================

Query metadata for multiple PostgreSQL database files that were backed up in a batch.
This script queries the 5 database files: audit_db, employee_db, inventory_db, logs_db, sales_db.
"""

from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.query import BackupQueryRequest, ListObjectsRequest
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


def query_batch_backups():
    """Query all batch backed up database files"""
    
    # Initialize session
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    query_client = QueryClient(session)
    
    # Files that were backed up in batch
    batch_files = [
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/audit_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/employee_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/inventory_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/logs_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/sales_db.tar.gz"
    ]
    filespace = "/postgres_bckp"
    
    print("="*70)
    print("QUERY BATCH POSTGRESQL BACKUPS")
    print("="*70)
    print(f"\nFilespace: {filespace}")
    print(f"Total files to query: {len(batch_files)}")
    
    # Method 1: Query each file individually
    print("\n" + "="*70)
    print("METHOD 1: Query Each File Individually")
    print("="*70)
    
    total_found = 0
    total_size = 0
    
    for file_path in batch_files:
        print(f"\nQuerying: {file_path.split('/')[-1]}")
        
        try:
            query = BackupQueryRequest(
                Key=file_path,
                Filespace=filespace,
                ObjState=ObjState.ACTIVE,
                ObjType=ObjType.FILE
            )
            
            result = query_client.query_object(query)
            
            if result and result.key:
                total_found += 1
                total_size += result.size
                
                print(f"  ✓ Found")
                print(f"    Object ID: {result.object_id}")
                print(f"    Size: {result.size:,} bytes ({result.size / (1024*1024):.2f} MB)")
                print(f"    Last Modified: {result.last_modified}")
                print(f"    Compressed: {result.compressed}")
                print(f"    Management Class: {result.management_class}")
            else:
                print(f"  ✗ Not found")
        
        except TSMError as e:
            print(f"  ✗ Query failed: {e}")
    
    print(f"\n{'='*70}")
    print(f"Summary: Found {total_found}/{len(batch_files)} files")
    print(f"Total Size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
    
    # Method 2: List all objects with prefix filter
    print("\n" + "="*70)
    print("METHOD 2: List Objects with Prefix Filter")
    print("="*70)
    
    try:
        # Use prefix to filter batch backup directory
        prefix = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/"
        
        query = ListObjectsRequest(
            Filespace=filespace,
            Prefix=prefix,
            ObjState=ObjState.ACTIVE,
            ObjType=ObjType.FILE,
            MaxResults=100
        )
        
        results = query_client.list_objects(query)
        
        print(f"\nFound {results.key_count} objects with prefix: {prefix}")
        
        if results.key_count > 0:
            print("\n" + "-"*70)
            total_batch_size = 0
            
            for obj in results.contents:
                filename = obj.get('Key', '').split('/')[-1]
                size = obj.get('Size', 0)
                total_batch_size += size
                
                print(f"\nFile: {filename}")
                print(f"  Key: {obj.get('Key')}")
                print(f"  Object ID: {obj.get('ObjectId')}")
                print(f"  Size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
                print(f"  Last Modified: {obj.get('LastModified')}")
                print(f"  State: {obj.get('State')}")
                print(f"  Compressed: {obj.get('Compressed')}")
                print(f"  Deduplicated: {obj.get('Deduplicated')}")
                print(f"  Management Class: {obj.get('ManagementClass')}")
            
            print("\n" + "-"*70)
            print(f"Total Size: {total_batch_size:,} bytes ({total_batch_size / (1024*1024):.2f} MB)")
            
            if results.key_count >= results.max_keys:
                print("\n⚠ More results may be available (increase MaxKeys to see all)")
    
    except TSMError as e:
        print(f"\n✗ List query failed: {e}")
    
    finally:
        session.logout()
        print("\n" + "="*70)
        print("Query operation completed.")


if __name__ == "__main__":
    query_batch_backups()

# Made with Bob
