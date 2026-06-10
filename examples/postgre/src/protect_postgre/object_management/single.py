"""
Single Object Management for PostgreSQL Backups
================================================

Demonstrates object management operations (rename, update, delete) on a single
backed-up PostgreSQL database file in IBM Storage Protect.
"""

from ibm_storage_protect import ClientSession, ControlClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.object import (
    ObjectRenameRequest,
    ObjectUpdateRequest,
    ObjectDeleteRequest
)
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
    Perform object management operations on a single backed-up object.
    
    Operations performed:
    1. Rename the backed-up object
    2. Update object attributes (owner, management class)
    3. Delete the object
    """
    
    # Initialize session
    print("="*60)
    print("SINGLE OBJECT MANAGEMENT OPERATIONS")
    print("="*60)
    
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    control_client = ControlClient(session)
    
    # Object details from single.py backup
    filespace = "/postgres_bckp"
    original_key = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/normal_backup_dummy_data/ecommerce_db.tar.gz"
    
    try:
        # ===================================================================
        # OPERATION 1: RENAME OBJECT
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 1: RENAME OBJECT")
        print("-"*60)
        
        new_key = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/dummy_data/normal_backup_dummy_data/ecommerce_db_renamed.tar.gz"
        
        print(f"Original key: {original_key}")
        print(f"New key: {new_key}")
        
        rename_request = ObjectRenameRequest(
            Filespace=filespace,
            Key=original_key,
            NewKey=new_key,
            Merge=False,
            ObjType=ObjType.FILE
        )
        
        rename_result = control_client.rename(rename_request)
        print(f"\n✓ Rename Status: {rename_result.status}")
        print(f"  Filespace: {rename_result.filespace}")
        print(f"  Old Key: {rename_result.old_key}")
        print(f"  New Key: {rename_result.new_key}")
        
        # Update key reference for subsequent operations
        current_key = new_key
        
        # ===================================================================
        # OPERATION 2: UPDATE OBJECT ATTRIBUTES
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 2: UPDATE OBJECT ATTRIBUTES")
        print("-"*60)
        
        print(f"Updating object: {current_key}")
        print("Setting owner: postgres_admin")
        print("Setting management class: STANDARD")
        
        update_request = ObjectUpdateRequest(
            Filespace=filespace,
            Key=current_key,
            Owner="postgres_admin",
            ManagementClass="STANDARD",
            ObjType=ObjType.FILE
        )
        
        update_result = control_client.update(update_request)
        print(f"\n✓ Update Status: {update_result.status}")
        print(f"  Filespace: {update_result.filespace}")
        print(f"  Key: {update_result.key}")
        
        # ===================================================================
        # OPERATION 3: DELETE OBJECT
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 3: DELETE OBJECT")
        print("-"*60)
        
        print(f"Deleting object: {current_key}")
        print(f"From filespace: {filespace}")
        
        delete_request = ObjectDeleteRequest(
            Filespace=filespace,
            Key=current_key,
            CopyGroup=1,
            ObjType=ObjType.FILE
        )
        
        delete_result = control_client.delete_by_name(delete_request)
        print(f"\n✓ Delete Status: {delete_result.status}")
        print(f"  Filespace: {delete_result.filespace}")
        print(f"  Key: {delete_result.key}")
        
        # ===================================================================
        # SUMMARY
        # ===================================================================
        print("\n" + "="*60)
        print("OBJECT MANAGEMENT COMPLETED SUCCESSFULLY")
        print("="*60)
        print("Operations performed:")
        print("  1. ✓ Renamed object")
        print("  2. ✓ Updated object attributes")
        print("  3. ✓ Deleted object")
        print("="*60)
        
    except TSMError as e:
        print(f"\n✗ Error during object management: {e}")
        print(f"  Error code: {e.error_code if hasattr(e, 'error_code') else 'N/A'}")
        raise
    
    finally:
        # Logout
        session.logout()
        print("\nSession logged out.")


if __name__ == "__main__":
    main()

# Made with Bob
