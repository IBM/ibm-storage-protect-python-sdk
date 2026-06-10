"""
Filespace Deletion for PostgreSQL Backups
==========================================

Demonstrates complete filespace deletion, which removes the filespace and ALL
objects within it from IBM Storage Protect. This is the final cleanup operation
after all object management operations are complete.

⚠️ WARNING: This operation is IRREVERSIBLE and deletes ALL objects within the
filespace from all repositories (backup and archive).
"""

from ibm_storage_protect import ClientSession, ControlClient, QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.filespace import FilespaceDeleteRequest
from ibm_storage_protect.data_models.query import BackupQueryRequest
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
    Delete the entire PostgreSQL backup filespace.
    
    This operation:
    1. Queries remaining objects in the filespace (if any)
    2. Deletes the entire filespace and all its objects
    
    ⚠️ WARNING: This is a destructive operation that cannot be undone!
    """
    
    # Initialize session
    print("="*60)
    print("FILESPACE DELETION OPERATION")
    print("="*60)
    print("\n⚠️  WARNING: This will delete the ENTIRE filespace and")
    print("   ALL objects within it. This operation is IRREVERSIBLE!")
    print("="*60)
    
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    control_client = ControlClient(session)
    query_client = QueryClient(session)
    
    # Filespace used in all backup examples
    filespace = "/postgres_bckp"
    
    try:
        # ===================================================================
        # STEP 1: QUERY REMAINING OBJECTS (OPTIONAL - FOR INFORMATION)
        # ===================================================================
        print("\n" + "-"*60)
        print("STEP 1: CHECKING FILESPACE CONTENTS")
        print("-"*60)
        
        print(f"Querying objects in filespace: {filespace}")
        
        try:
            query = BackupQueryRequest(
                Filespace=filespace,
                Key="*"
            )
            results = query_client.query_objects(query)
            
            if results.total_objects > 0:
                print(f"\n⚠️  Found {results.total_objects} objects in filespace:")
                
                # Show first 10 objects
                display_count = min(10, results.total_objects)
                for i, obj in enumerate(results.objects[:display_count], 1):
                    print(f"  {i}. {obj['Key'].split('/')[-1]}")
                    print(f"     ID: {obj['ObjectId']}")
                    print(f"     Size: {obj.get('Size', 0)} bytes")
                
                if results.total_objects > display_count:
                    print(f"  ... and {results.total_objects - display_count} more objects")
                
                print(f"\n⚠️  All {results.total_objects} objects will be PERMANENTLY DELETED!")
            else:
                print(f"✓ No objects found in filespace (already cleaned up)")
                
        except TSMError as e:
            print(f"Note: Could not query filespace contents: {e}")
            print("Proceeding with deletion anyway...")
        
        # ===================================================================
        # STEP 2: DELETE FILESPACE
        # ===================================================================
        print("\n" + "-"*60)
        print("STEP 2: DELETING FILESPACE")
        print("-"*60)
        
        print(f"\nDeleting filespace: {filespace}")
        print("This will remove:")
        print("  - The filespace itself")
        print("  - ALL objects within the filespace")
        print("  - ALL backup copies")
        print("  - ALL archive copies")
        
        delete_request = FilespaceDeleteRequest(
            Filespace=filespace
        )
        
        print("\nExecuting deletion...")
        delete_result = control_client.delete_filespace(delete_request)
        
        print(f"\n✓ Deletion Status: {delete_result.status}")
        print(f"  Filespace: {delete_result.filespace}")
        
        # ===================================================================
        # STEP 3: VERIFY DELETION (OPTIONAL)
        # ===================================================================
        print("\n" + "-"*60)
        print("STEP 3: VERIFYING DELETION")
        print("-"*60)
        
        try:
            verify_query = BackupQueryRequest(
                Filespace=filespace,
                Key="*"
            )
            verify_results = query_client.query_objects(verify_query)
            
            if verify_results.total_objects == 0:
                print(f"✓ Verification successful: No objects remain in filespace")
            else:
                print(f"⚠️  Warning: {verify_results.total_objects} objects still found")
                print("   This may indicate a partial deletion or timing issue")
                
        except TSMError as e:
            # Expected if filespace no longer exists
            print(f"✓ Filespace appears to be completely removed")
        
        # ===================================================================
        # SUMMARY
        # ===================================================================
        print("\n" + "="*60)
        print("FILESPACE DELETION COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Deleted filespace: {filespace}")
        print("All objects and metadata have been permanently removed.")
        print("="*60)
        
    except TSMError as e:
        print(f"\n✗ Error during filespace deletion: {e}")
        print(f"  Error code: {e.error_code if hasattr(e, 'error_code') else 'N/A'}")
        
        # Provide helpful error messages
        if "not found" in str(e).lower():
            print("\nNote: Filespace may have already been deleted.")
        elif "in use" in str(e).lower():
            print("\nNote: Filespace may be in use. Try again later.")
        
        raise
    
    finally:
        # Logout
        session.logout()
        print("\nSession logged out.")


if __name__ == "__main__":
    # Prompt for confirmation before running
    print("\n" + "="*60)
    print("FILESPACE DELETION SCRIPT")
    print("="*60)
    print("\nThis script will PERMANENTLY DELETE the filespace:")
    print("  /postgres_bckp")
    print("\nAnd ALL objects within it, including:")
    print("  - Single backup objects")
    print("  - Group backup objects (leader and members)")
    print("  - Batch backup objects")
    print("\n⚠️  THIS OPERATION CANNOT BE UNDONE!")
    print("="*60)
    
    response = input("\nType 'DELETE' to confirm deletion: ")
    
    if response == "DELETE":
        print("\nProceeding with deletion...\n")
        main()
    else:
        print("\nDeletion cancelled. No changes made.")

# Made with Bob
