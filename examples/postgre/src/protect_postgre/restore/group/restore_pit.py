"""
Group Point-in-Time (PIT) Restoration Example
==============================================

Demonstrates point-in-time restoration of an entire group backup from IBM Storage Protect.
This example restores the leader and all 5 member files from a specific backup timestamp.

Output naming convention: <file_name_TIMESTAMP_restored>
where TIMESTAMP is the backup time in format YYYYMMDD_HHMMSS

Backup Information:
- Group Leader: leader.json (Object ID: 0-9552867, backed up 2026-05-31 23:03:57)
- Group Members: 5 files (analytics_db.tar.gz, notification_db.tar.gz, orders_db.tar.gz, 
                          payment_db.tar.gz, users_db.tar.gz)
- Member Object IDs: 0-9552868 to 0-9552872
- Backup Date Range: 2026-05-31 23:03:57 to 23:04:02
- Filespace: /postgres_bckp
- Total Size: ~500 MB (5 members × ~100 MB each + leader)

Note: Group backups are atomic - all members are from the same backup session.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports


from ibm_storage_protect.session import ClientSession
from ibm_storage_protect.data_client.client import DataClient
from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.restore import GroupRestoreRequest
from ibm_storage_protect.errors.exceptions import TSMError
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger


configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/postgre/src/protect_postgre/restore/group/logs",
    log_format="json",
    console_level="INFO"
))



def restore_group_pit():
    """
    Restore entire group backup from a specific point in time.
    
    This performs a point-in-time group restoration, retrieving the versions
    of the leader and all members that existed at the specified backup timestamp.
    Group backups ensure all members are from the same backup session.
    """
    # Configuration
    FILESPACE = "/postgres_bckp"
    
    # Group Leader Object ID: 0-9552867
    LEADER_HI = 0
    LEADER_LO = 9552867
    
    # Point-in-time date: 2026-05-31 23:03:57 (leader backup time)
    PIT_DATE = datetime(2026, 5, 31, 23, 3, 57)
    timestamp_str = PIT_DATE.strftime("%Y%m%d_%H%M%S")
    
    # Output directory
    output_dir = Path("/home/onecloud-user/tsm_sample/tsm_sdk/refactored_sp/sp_client_sdk/examples/restore_dummy_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("GROUP POINT-IN-TIME RESTORATION")
    print("=" * 80)
    print(f"Filespace     : {FILESPACE}")
    print(f"Leader ID     : {LEADER_HI}-{LEADER_LO}")
    print(f"PIT Date      : {PIT_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output Dir    : {output_dir}")
    print(f"Restore Type  : Point-in-Time (group from specific backup session)")
    print("=" * 80)
    
    # Initialize session
    print("\n[1/4] Initializing session...")
    creds = LoginCredentials()
    session = ClientSession()
    
    try:
        session.login(creds)
        print("      ✓ Session established")
        
        # Create data client
        print("\n[2/4] Creating data client...")
        client = DataClient(session)
        print("      ✓ Client ready")
        
        # Create group restore request with PIT date
        print("\n[3/4] Initiating group PIT restore...")
        print(f"      Querying group members for leader {LEADER_HI}-{LEADER_LO} at {timestamp_str}...")
        
        group_request = GroupRestoreRequest(
            Filespace=FILESPACE,
            GroupLeaderObjIdHi=LEADER_HI,
            GroupLeaderObjIdLo=LEADER_LO,
            PitDate=PIT_DATE,  # Specify point-in-time date
        )
        
        # Execute group restore
        start_time = datetime.now()
        result = client.group_restore(group_request)
        
        print(f"      ✓ Group restore initiated")
        print(f"      Total objects in group: {result.total_objects}")
        print(f"      Leader + {result.total_objects - 1} member(s)")
        print(f"      Backup session: {PIT_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Write restored files to disk
        print("\n[4/4] Writing group files to disk...")
        total_bytes = 0
        leader_info = None
        member_files = []
        failed_files = []
        
        for member in result.results:
            filename = Path(member.key).name
            # Output file with naming convention: <file_name_TIMESTAMP_restored>
            base_name = Path(filename).stem
            extension = Path(filename).suffix
            output_file = output_dir / f"{base_name}_{timestamp_str}_restored{extension}"
            
            try:
                bytes_written = 0
                with open(output_file, "wb") as fh:
                    for chunk in member.body:
                        fh.write(chunk)
                        bytes_written += len(chunk)
                
                total_bytes += bytes_written
                
                if member.is_group_leader:
                    leader_info = (filename, bytes_written, output_file, member.last_modified)
                    print(f"      ✓ [LEADER] {filename}: {bytes_written:,} bytes → {output_file.name}")
                else:
                    member_files.append((filename, bytes_written, output_file, member.last_modified))
                    print(f"      ✓ [MEMBER] {filename}: {bytes_written:,} bytes → {output_file.name}")
                    
            except Exception as e:
                failed_files.append((filename, str(e)))
                print(f"      ✗ {filename}: {str(e)}")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Summary
        print("\n" + "=" * 80)
        print("GROUP PIT RESTORATION SUMMARY")
        print("=" * 80)
        print(f"Leader ID             : {LEADER_HI}-{LEADER_LO}")
        print(f"PIT Date              : {PIT_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total objects         : {result.total_objects}")
        print(f"Successfully restored : {len(member_files) + (1 if leader_info else 0)}")
        print(f"Failed                : {len(failed_files)}")
        print(f"Total bytes restored  : {total_bytes:,} ({total_bytes / (1024 * 1024):.2f} MB)")
        print(f"Duration              : {duration:.2f} seconds")
        print(f"Throughput            : {(total_bytes / (1024 * 1024)) / duration:.2f} MB/s")
        
        if leader_info:
            filename, size, output_file, last_mod = leader_info
            print(f"\n✓ Group Leader (PIT: {timestamp_str}):")
            print(f"  - {filename} ({size / (1024 * 1024):.2f} MB)")
            print(f"    Backup time: {last_mod.strftime('%Y-%m-%d %H:%M:%S') if last_mod else 'N/A'}")
            print(f"    Output: {output_file}")
        
        if member_files:
            print(f"\n✓ Group Members ({len(member_files)}) (PIT: {timestamp_str}):")
            for filename, size, output_file, last_mod in member_files:
                print(f"  - {filename} ({size / (1024 * 1024):.2f} MB)")
                print(f"    Backup time: {last_mod.strftime('%Y-%m-%d %H:%M:%S') if last_mod else 'N/A'}")
                print(f"    Output: {output_file}")
        
        if failed_files:
            print(f"\n✗ Failed files:")
            for filename, error in failed_files:
                print(f"  - {filename}: {error}")
        
        print("\n" + "=" * 80)
        print("GROUP POINT-IN-TIME RESTORATION COMPLETED")
        print("=" * 80)
        print(f"Note: All group members restored from backup session at {PIT_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      Group backups ensure atomic consistency across all members")
        
        return {
            "status": "success" if len(failed_files) == 0 else "partial",
            "leader_id": {"hi": LEADER_HI, "lo": LEADER_LO},
            "pit_date": PIT_DATE.isoformat(),
            "total_objects": result.total_objects,
            "successful": len(member_files) + (1 if leader_info else 0),
            "failed": len(failed_files),
            "total_bytes": total_bytes,
            "duration_seconds": duration,
            "output_dir": str(output_dir),
        }
        
    except TSMError as e:
        print(f"\n✗ Group restoration failed: {e.message}")
        print(f"  Error code: {e.error_code}")
        raise
    
    finally:
        session.logout()
        print("\n✓ Session closed")


if __name__ == "__main__":
    restore_group_pit()

# Made with Bob
