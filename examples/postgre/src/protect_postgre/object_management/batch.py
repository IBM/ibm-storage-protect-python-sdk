"""
Batch Object Management for PostgreSQL Backups
===============================================

Demonstrates object management operations on batch-backed-up PostgreSQL database files.
Performs rename, update, and delete operations on multiple objects efficiently.
"""

from ibm_storage_protect import ClientSession, ControlClient, QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.object import (
    ObjectRenameRequest,
    ObjectUpdateRequest,
    ObjectDeleteByIdRequest
)
from ibm_storage_protect.data_models.query import BackupQueryRequest
from ibm_storage_protect.enums import ObjType
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger

configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/postgre/src/protect_postgre/object_management/logs",
    log_format="json",
    console_level="INFO"
))


def main():
    """
    Perform object management operations on batch-backed-up objects.
    
    Operations performed:
    1. Query batch objects to get their IDs
    2. Rename selected objects
    3. Update attributes on all objects
    4. Delete all batch objects by ID
    """
    
    # Initialize session
    print("="*60)
    print("BATCH OBJECT MANAGEMENT OPERATIONS")
    print("="*60)
    
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    control_client = ControlClient(session)
    query_client = QueryClient(session)
    
    # Batch details from batch.py backup
    filespace = "/postgres_bckp"
    
    # Object keys from batch backup
    batch_keys = [
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/audit_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/employee_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/inventory_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/logs_db.tar.gz",
        "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/batch_backup_dummy_data/sales_db.tar.gz"
    ]
    
    try:
        # ===================================================================
        # STEP 1: QUERY BATCH OBJECTS TO GET THEIR IDs
        # ===================================================================
        print("\n" + "-"*60)
        print("STEP 1: QUERYING BATCH OBJECTS")
        print("-"*60)
        
        batch_objects = []
        
        print(f"Querying {len(batch_keys)} batch objects...")
        for key in batch_keys:
            query = BackupQueryRequest(
                Filespace=filespace,
                Key=key
            )
            results = query_client.query_objects(query)
            
            if results.total_objects > 0:
                obj = results.objects[0]
                batch_objects.append(obj)
                print(f"  ✓ Found: {obj['Key'].split('/')[-1]}")
                print(f"    ID: {obj['ObjectId']}")
            else:
                print(f"  ✗ Not found: {key.split('/')[-1]}")
        
        if len(batch_objects) == 0:
            print("\n✗ No batch objects found. Please run batch backup first.")
            return
        
        print(f"\n✓ Successfully queried {len(batch_objects)}/{len(batch_keys)} objects")
        
        # ===================================================================
        # OPERATION 1: RENAME SELECTED OBJECTS
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 1: RENAME SELECTED OBJECTS")
        print("-"*60)
        
        # Rename first 2 objects as examples
        rename_count = min(2, len(batch_objects))
        print(f"Renaming {rename_count} objects...")
        
        renamed_objects = []
        for i in range(rename_count):
            obj = batch_objects[i]
            original_key = obj['Key']
            new_key = original_key.replace(".tar.gz", "_renamed.tar.gz")
            
            print(f"\n  Object {i+1}:")
            print(f"    Original: {original_key.split('/')[-1]}")
            print(f"    New: {new_key.split('/')[-1]}")
            
            try:
                rename_request = ObjectRenameRequest(
                    Filespace=filespace,
                    Key=original_key,
                    NewKey=new_key,
                    Merge=False,
                    ObjType=ObjType.FILE
                )
                
                rename_result = control_client.rename(rename_request)
                print(f"    ✓ Status: {rename_result.status}")
                
                # Update object key for subsequent operations
                obj['Key'] = new_key
                renamed_objects.append(obj)
                
            except TSMError as e:
                print(f"    ✗ Failed: {e}")
        
        print(f"\n✓ Renamed {len(renamed_objects)}/{rename_count} objects")
        
        # ===================================================================
        # OPERATION 2: UPDATE ALL OBJECT ATTRIBUTES
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 2: UPDATE ALL OBJECT ATTRIBUTES")
        print("-"*60)
        
        print(f"Updating attributes for {len(batch_objects)} objects...")
        print("  Setting owner: postgres_batch_admin")
        print("  Setting management class: STANDARD")
        
        updated_count = 0
        for obj in batch_objects:
            try:
                update_request = ObjectUpdateRequest(
                    Filespace=filespace,
                    Key=obj['Key'],
                    Owner="postgres_batch_admin",
                    ManagementClass="STANDARD",
                    ObjType=ObjType.FILE
                )
                
                update_result = control_client.update(update_request)
                if update_result.status == "success":
                    updated_count += 1
                    print(f"  ✓ Updated: {obj['Key'].split('/')[-1]}")
                    
            except TSMError as e:
                print(f"  ✗ Failed to update {obj['Key'].split('/')[-1]}: {e}")
        
        print(f"\n✓ Updated {updated_count}/{len(batch_objects)} objects")
        
        # ===================================================================
        # OPERATION 3: DELETE ALL BATCH OBJECTS BY ID
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 3: DELETE ALL BATCH OBJECTS BY ID")
        print("-"*60)
        
        print(f"Deleting {len(batch_objects)} batch objects...")
        
        deleted_count = 0
        for obj in batch_objects:
            try:
                # Extract hi and lo from ObjectIdRaw dictionary
                obj_id_raw = obj.get('ObjectIdRaw', {})
                delete_request = ObjectDeleteByIdRequest(
                    ObjIdHi=obj_id_raw.get('hi', 0),
                    ObjIdLo=obj_id_raw.get('lo', 0)
                )
                
                delete_result = control_client.delete_by_id(delete_request)
                if delete_result.status == "success":
                    deleted_count += 1
                    print(f"  ✓ Deleted: {obj['Key'].split('/')[-1]}")
                    print(f"    ID: {delete_result.obj_id_hi}-{delete_result.obj_id_lo}")
                    
            except TSMError as e:
                print(f"  ✗ Failed to delete {obj['Key'].split('/')[-1]}: {e}")
        
        print(f"\n✓ Deleted {deleted_count}/{len(batch_objects)} objects")
        
        # ===================================================================
        # SUMMARY
        # ===================================================================
        print("\n" + "="*60)
        print("BATCH OBJECT MANAGEMENT COMPLETED SUCCESSFULLY")
        print("="*60)
        print("Operations performed:")
        print(f"  1. ✓ Queried {len(batch_objects)} objects")
        print(f"  2. ✓ Renamed {len(renamed_objects)} objects")
        print(f"  3. ✓ Updated {updated_count} objects")
        print(f"  4. ✓ Deleted {deleted_count} objects")
        print("="*60)
        
    except TSMError as e:
        print(f"\n✗ Error during batch object management: {e}")
        print(f"  Error code: {e.error_code if hasattr(e, 'error_code') else 'N/A'}")
        raise
    
    finally:
        # Logout
        session.logout()
        print("\nSession logged out.")


if __name__ == "__main__":
    main()

# Made with Bob
