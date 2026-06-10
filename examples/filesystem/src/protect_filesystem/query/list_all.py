"""
List All Filesystem Backups
=============================

List all backed up files in the /filesystem_backup filespace.
This provides an overview of all backups regardless of how they were created.
"""

import json
import os
from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.query import QueryClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.query import ListObjectsRequest, QueryFilespacesRequest, GroupQueryRequest
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


def list_all_backups():
    """List all filesystem backups in the filespace"""
    
    # Initialize session
    creds = LoginCredentials()
    session = ClientSession()
    session.login(creds)
    query_client = QueryClient(session)
    
    filespace = "/filesystem_backup"
    
    print("="*70)
    print("LIST ALL FILESYSTEM BACKUPS")
    print("="*70)
    
    # Step 1: Check filespace information
    print("\nSTEP 1: Filespace Information")
    print("-"*70)
    
    try:
        fs_query = QueryFilespacesRequest(FsPattern="*")
        fs_results = query_client.query_filespaces(fs_query)
        
        postgres_fs = None
        for fs in fs_results.filespaces:
            if fs.get('Name') == filespace:
                postgres_fs = fs
                break
        
        if postgres_fs:
            print(f"✓ Filespace: {postgres_fs.get('Name')}")
            print(f"  Type: {postgres_fs.get('Type')}")
            print(f"  Capacity: {postgres_fs.get('Capacity', 0):,} bytes")
            print(f"  Occupancy: {postgres_fs.get('Occupancy', 0):,} bytes")
            capacity = postgres_fs.get('Capacity', 0)
            occupancy = postgres_fs.get('Occupancy', 0)
            used_pct = (occupancy / capacity * 100) if capacity > 0 else 0
            print(f"  Usage: {used_pct:.2f}%")
        else:
            print(f"⚠ Filespace '{filespace}' not found")
            print("  No backups exist in this filespace yet")
    
    except TSMError as e:
        print(f"✗ Failed to query filespace: {e}")
    
    # Step 2: List all objects in the filespace
    print("\n" + "="*70)
    print("STEP 2: All Backed Up Objects")
    print("-"*70)
    
    try:
        query = ListObjectsRequest(
            Filespace=filespace,
            ObjState=ObjState.ACTIVE,
            ObjType=ObjType.FILE,
            MaxResults=1000
        )
        
        results = query_client.list_objects(query)
        
        print(f"\n✓ Found {results.key_count} active backup(s)")
        
        if results.key_count > 0:
            # Categorize objects
            single_backups = []
            batch_backups = []
            group_leaders = []
            group_members = []
            
            for obj in results.contents:
                filename = obj.get('Key', '').split('/')[-1]
                key = obj.get('Key', '')
                
                if obj.get('IsGroupLeader', False):
                    group_leaders.append((filename, obj))
                elif obj.get('GroupLeaderObjId'):
                    group_members.append((filename, obj))
                elif '/data/' in key and not obj.get('IsGroupLeader', False) and not obj.get('GroupLeaderObjId'):
                    batch_backups.append((filename, obj))
                else:
                    # Fallback categorization
                    if filename.endswith('.json'):
                        group_leaders.append((filename, obj))
                    else:
                        single_backups.append((filename, obj))
            
            # Display Single Backups
            if single_backups:
                print(f"\n{'='*70}")
                print(f"SINGLE BACKUPS ({len(single_backups)})")
                print("="*70)
                
                total_size = 0
                for filename, obj in single_backups:
                    size = obj.get('Size', 0)
                    total_size += size
                    print(f"\n• {filename}")
                    print(f"  Key: {obj.get('Key')}")
                    print(f"  Object ID: {obj.get('ObjectId')}")
                    print(f"  Size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
                    print(f"  Last Modified: {obj.get('LastModified')}")
                    print(f"  Expiration: {obj.get('ExpiryDate')}")
                    print(f"  Compressed: {obj.get('Compressed')}")
                    print(f"  Deduplicated: {obj.get('Deduplicated')}")
                    print(f"  Management Class: {obj.get('ManagementClass')}")
                
                print(f"\nTotal Size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
            
            # Display Batch Backups
            if batch_backups:
                print(f"\n{'='*70}")
                print(f"BATCH BACKUPS ({len(batch_backups)})")
                print("="*70)
                
                total_size = 0
                for filename, obj in batch_backups:
                    size = obj.get('Size', 0)
                    total_size += size
                    print(f"\n• {filename}")
                    print(f"  Key: {obj.get('Key')}")
                    print(f"  Object ID: {obj.get('ObjectId')}")
                    print(f"  Size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
                    print(f"  Last Modified: {obj.get('LastModified')}")
                    print(f"  Compressed: {obj.get('Compressed')}")
                
                print(f"\nTotal Size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
            
            # Display Group Leaders
            if group_leaders:
                print(f"\n{'='*70}")
                print(f"GROUP LEADERS ({len(group_leaders)})")
                print("="*70)
                
                for filename, obj in group_leaders:
                    print(f"\n• {filename}")
                    print(f"  Key: {obj.get('Key')}")
                    print(f"  Object ID: {obj.get('ObjectId')}")
                    print(f"  Size: {obj.get('Size', 0):,} bytes")
                    print(f"  Last Modified: {obj.get('LastModified')}")
                    print(f"  Is Group Leader: {obj.get('IsGroupLeader')}")
            
            # Display Group Members
            if group_members:
                print(f"\n{'='*70}")
                print(f"GROUP MEMBERS ({len(group_members)})")
                print("="*70)
                
                total_size = 0
                for filename, obj in group_members:
                    size = obj.get('Size', 0)
                    total_size += size
                    print(f"\n• {filename}")
                    print(f"  Key: {obj.get('Key')}")
                    print(f"  Object ID: {obj.get('ObjectId')}")
                    print(f"  Size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
                    print(f"  Last Modified: {obj.get('LastModified')}")
                    print(f"  Group Leader ID: {obj.get('GroupLeaderObjId')}")
                    print(f"  Compressed: {obj.get('Compressed')}")
                
                print(f"\nTotal Size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
            
            # Summary
            print(f"\n{'='*70}")
            print("SUMMARY")
            print("="*70)
            print(f"Total Objects: {results.key_count}")
            print(f"  Single Backups: {len(single_backups)}")
            print(f"  Batch Backups: {len(batch_backups)}")
            print(f"  Group Leaders: {len(group_leaders)}")
            print(f"  Group Members: {len(group_members)}")
            
            total_all_size = sum(obj.get('Size', 0) for _, obj in single_backups + batch_backups + group_leaders + group_members)
            print(f"\nTotal Storage Used: {total_all_size:,} bytes ({total_all_size / (1024*1024):.2f} MB)")
            
            if results.key_count >= results.max_keys:
                print("\n⚠ More results may be available (increase MaxKeys to see all)")
        else:
            print("\nNo backups found in this filespace")
        
        # Step 3: Query Group Details (if group exists)
        print("\n" + "="*70)
        print("STEP 3: Group Backup Details")
        print("-"*70)
        
        groups_file = "./backup/.sp_groups.json"
        
        if os.path.exists(groups_file):
            try:
                with open(groups_file, 'r') as f:
                    groups_data = json.load(f)
                
                if groups_data:
                    print(f"\n✓ Found {len(groups_data)} saved group(s)")
                    
                    for group_name, group_info in groups_data.items():
                        print(f"\n  Group: {group_name}")
                        print(f"    Filespace: {group_info['filespace']}")
                        print(f"    Leader ID: {group_info['leader_id']['hi']}-{group_info['leader_id']['lo']}")
                        print(f"    Created: {group_info['created_at']}")
                        
                        # Query the actual group members
                        try:
                            group_query = GroupQueryRequest(
                                GroupLeaderObjIdHi=group_info['leader_id']['hi'],
                                GroupLeaderObjIdLo=group_info['leader_id']['lo'],
                                Filespace=group_info['filespace']
                            )
                            
                            group_results = query_client.query_group_members(group_query)
                            
                            print(f"    Total Members: {group_results.total_objects}")
                            
                            if group_results.objects:
                                leader_found = False
                                member_count = 0
                                total_group_size = 0
                                
                                for obj in group_results.objects:
                                    total_group_size += obj.size
                                    if obj.is_group_leader:
                                        leader_found = True
                                    else:
                                        member_count += 1
                                
                                print(f"    Leader: {'Yes' if leader_found else 'No'}")
                                print(f"    Members: {member_count}")
                                print(f"    Total Size: {total_group_size:,} bytes ({total_group_size / (1024*1024):.2f} MB)")
                        
                        except TSMError as e:
                            print(f"    ✗ Failed to query group: {e}")
                else:
                    print("\n  No groups found in metadata file")
            
            except json.JSONDecodeError as e:
                print(f"\n✗ Failed to parse group metadata: {e}")
        else:
            print("\n  No group metadata file found")
            print("  Run group backup script to create groups")
    
    except TSMError as e:
        print(f"\n✗ Query failed: {e}")
    
    finally:
        session.logout()
        print("\n" + "="*70)
        print("Query operation completed.")


if __name__ == "__main__":
    list_all_backups()

# Made with Bob
