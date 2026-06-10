"""
Query Group Filesystem Backup
===============================

Query metadata for a group backup containing a leader and multiple member files.
This script queries the filesystem_backup_group using the saved leader ID.
"""

import json
import os
from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.query import GroupQueryRequest
from ibm_storage_protect.enums import ObjState, ObjType
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


def query_group_backup():
    """Query the group backup using saved leader ID"""
    
    # Initialize session
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    query_client = QueryClient(session)
    
    # Path to the saved group metadata
    groups_file = "./backup/.sp_groups.json"
    
    print("="*70)
    print("QUERY GROUP FILESYSTEM BACKUP")
    print("="*70)
    
    # Step 1: Load the saved group leader ID
    print("\nSTEP 1: Load Saved Group Leader ID")
    print("-"*70)
    
    try:
        if not os.path.exists(groups_file):
            print(f"\n✗ Group metadata file not found: {groups_file}")
            print("  Please run the group backup script first to create the group.")
            session.logout()
            return
        
        with open(groups_file, 'r') as f:
            groups_data = json.load(f)
        
        group_name = "filesystem_backup_group"
        if group_name not in groups_data:
            print(f"\n✗ Group '{group_name}' not found in metadata file")
            session.logout()
            return
        
        group_info = groups_data[group_name]
        leader_id = group_info['leader_id']
        filespace = group_info['filespace']
        
        print(f"\n✓ Group metadata loaded")
        print(f"  Group Name: {group_name}")
        print(f"  Filespace: {filespace}")
        print(f"  Leader ID (hi): {leader_id['hi']}")
        print(f"  Leader ID (lo): {leader_id['lo']}")
        print(f"  Created At: {group_info['created_at']}")
        
        # Step 2: Query all group members using the leader ID
        print("\n" + "="*70)
        print("STEP 2: Query All Group Members")
        print("-"*70)
        
        group_query = GroupQueryRequest(
            GroupLeaderObjIdHi=leader_id['hi'],
            GroupLeaderObjIdLo=leader_id['lo'],
            Filespace=filespace
        )
        
        group_results = query_client.query_group_members(group_query)
        
        print(f"\n✓ Group query successful")
        print(f"  Total objects in group: {group_results.total_objects}")
        
        if group_results.objects:
            print(f"\n  Group Objects ({len(group_results.objects)}):")
            print("  " + "-"*66)
            
            total_size = 0
            leader_count = 0
            member_count = 0
            
            for idx, obj in enumerate(group_results.objects, 1):
                filename = obj.key.split('/')[-1]
                total_size += obj.size
                
                if obj.is_group_leader:
                    leader_count += 1
                    role = "LEADER"
                else:
                    member_count += 1
                    role = "MEMBER"
                
                print(f"\n  {idx}. {filename} [{role}]")
                print(f"     Key: {obj.key}")
                print(f"     Object ID: {obj.object_id}")
                print(f"     Size: {obj.size:,} bytes ({obj.size / (1024*1024):.2f} MB)")
                print(f"     Last Modified: {obj.last_modified}")
                print(f"     State: {obj.state}")
                print(f"     Compressed: {obj.compressed}")
                print(f"     Deduplicated: {obj.deduplicated}")
                print(f"     Management Class: {obj.management_class}")
                if obj.group_leader_obj_id:
                    print(f"     Group Leader ID: {obj.group_leader_obj_id}")
            
            print("\n  " + "-"*66)
            print(f"  Summary:")
            print(f"    Total Objects: {len(group_results.objects)}")
            print(f"    Leaders: {leader_count}")
            print(f"    Members: {member_count}")
            print(f"    Total Size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
        else:
            print("\n  No objects found in group")
        
        # Additional Info
        print("\n" + "="*70)
        print("NOTES")
        print("-"*70)
        print("• Group queries require the leader's Object ID (hi and lo components)")
        print("• The leader ID is saved during group backup in .sp_groups.json")
        print("• query_group_members() returns ALL objects including the leader")
        print("• You cannot query the leader separately - use group query instead")
    
    except TSMError as e:
        print(f"\n✗ Query failed: {e}")
    except json.JSONDecodeError as e:
        print(f"\n✗ Failed to parse group metadata file: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
    
    finally:
        session.logout()
        print("\n" + "="*70)
        print("Query operation completed.")


if __name__ == "__main__":
    query_group_backup()

# Made with Bob
