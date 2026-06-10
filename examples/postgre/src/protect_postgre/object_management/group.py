"""
Group Object Management for PostgreSQL Backups
===============================================

Demonstrates object management operations on group-backed-up PostgreSQL database files.
Uses the high-level GroupHandle API for proper group management operations.
"""

import json
import os
from ibm_storage_protect import ClientSession, DataClient, QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.query import GroupQueryRequest
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
    Perform object management operations on group-backed-up objects.
    
    Operations performed:
    1. Load group metadata and query group members
    2. Remove some member objects from the group
    3. Delete the entire group (leader + remaining members)
    """
    
    # Initialize session
    print("="*60)
    print("GROUP OBJECT MANAGEMENT OPERATIONS")
    print("="*60)
    
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    data_client = DataClient(session)
    query_client = QueryClient(session)
    
    # Group details from group.py backup
    group_name = "database_backup_group"
    
    # Path to group metadata file
    groups_file = "/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/postgre/src/protect_postgre/backup/.sp_groups.json"
    
    try:
        # ===================================================================
        # STEP 1: LOAD GROUP AND QUERY MEMBERS
        # ===================================================================
        print("\n" + "-"*60)
        print("STEP 1: LOADING GROUP METADATA")
        print("-"*60)
        
        # Load group using DataClient
        if not os.path.exists(groups_file):
            print(f"✗ Group metadata file not found: {groups_file}")
            print("  Please run group backup first.")
            return
        
        group = data_client.load_group(groups_file, group_name)
        
        print(f"✓ Loaded group:")
        print(f"  Group Name: {group.name}")
        print(f"  Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")
        
        # Load filespace from metadata file
        with open(groups_file, 'r') as f:
            groups_data = json.load(f)
        filespace = groups_data[group_name]['filespace']
        print(f"  Filespace: {filespace}")
        
        # Query group members to see what we have
        print("\n" + "-"*60)
        print("STEP 2: QUERYING GROUP MEMBERS")
        print("-"*60)
        
        group_query = GroupQueryRequest(
            Filespace=filespace,
            GroupLeaderObjIdHi=group.leader_id['hi'],
            GroupLeaderObjIdLo=group.leader_id['lo']
        )
        
        group_results = query_client.query_group_members(group_query)
        
        if group_results.total_objects == 0:
            print("✗ No group members found. Group may have been deleted.")
            return
        
        print(f"✓ Found {group_results.total_objects} objects in group")
        
        # Separate leader and members
        leader_obj = None
        member_objects = []
        
        for obj in group_results.objects:
            if obj.is_group_leader:
                leader_obj = obj
                print(f"\n  [LEADER] {obj.key.split('/')[-1]}")
                print(f"    ID: {obj.object_id}")
            else:
                member_objects.append(obj)
        
        print(f"\n  Found {len(member_objects)} member objects:")
        for i, obj in enumerate(member_objects[:5], 1):
            print(f"    {i}. {obj.key.split('/')[-1]} (ID: {obj.object_id})")
        if len(member_objects) > 5:
            print(f"    ... and {len(member_objects) - 5} more")
        
        if not leader_obj:
            print("\n✗ Leader object not found in group results.")
            return
        
        # ===================================================================
        # OPERATION 1: REMOVE SOME MEMBERS FROM GROUP
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 1: REMOVE SOME MEMBERS FROM GROUP")
        print("-"*60)
        
        # Remove first 2 members as examples
        members_to_remove = min(2, len(member_objects))
        if members_to_remove > 0:
            keys_to_remove = [member_objects[i].key for i in range(members_to_remove)]
            
            print(f"Removing {members_to_remove} member(s) from group:")
            for key in keys_to_remove:
                print(f"  - {key.split('/')[-1]}")
            
            try:
                result = group.remove_members(keys_to_remove)
                print(f"\n✓ Remove Status: {result.message}")
                print(f"  Removed {members_to_remove} member(s)")
                remaining_members = len(member_objects) - members_to_remove
                print(f"  Remaining members: {remaining_members}")
            except TSMError as e:
                print(f"✗ Remove failed: {e}")
                remaining_members = len(member_objects)
        else:
            print("✗ No member objects to remove")
            remaining_members = 0
        
        # ===================================================================
        # OPERATION 2: DELETE ENTIRE GROUP
        # ===================================================================
        print("\n" + "-"*60)
        print("OPERATION 2: DELETE ENTIRE GROUP")
        print("-"*60)
        print(f"Note: This will delete the leader and all {remaining_members} remaining member(s)")
        
        print(f"\nDeleting group: {group.name}")
        print(f"  Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")
        
        try:
            group.delete()
            print(f"\n✓ Group deleted successfully")
            print(f"  Leader and all {remaining_members} remaining member(s) were deleted")
        except TSMError as e:
            print(f"✗ Delete failed: {e}")
            raise
        
        # ===================================================================
        # SUMMARY
        # ===================================================================
        print("\n" + "="*60)
        print("GROUP OBJECT MANAGEMENT COMPLETED SUCCESSFULLY")
        print("="*60)
        print("Operations performed:")
        print(f"  1. ✓ Queried {group_results.total_objects} objects")
        print(f"  2. ✓ Removed {members_to_remove} member(s) from group")
        print(f"  3. ✓ Deleted entire group (leader + {remaining_members} remaining member(s))")
        print(f"\nTotal objects deleted: {len(member_objects) + 1}")
        print("="*60)
        
    except TSMError as e:
        print(f"\n✗ Error during group object management: {e}")
        print(f"  Error code: {e.error_code if hasattr(e, 'error_code') else 'N/A'}")
        raise
    
    finally:
        # Logout
        session.logout()
        print("\nSession logged out.")


if __name__ == "__main__":
    main()

# Made with Bob
