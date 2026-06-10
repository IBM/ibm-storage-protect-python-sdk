from ibm_storage_protect.data_models.session import LoginCredentials
from ibm_storage_protect.data_models.backup import BackupRequest
from ibm_storage_protect import ClientSession, DataClient
from ibm_storage_protect.enums import ObjType, MountWait
import os
import glob
from ibm_storage_protect.logger import configure_logging, LogConfig, get_logger
configure_logging(LogConfig(
    enable_user_log=True,
    enable_debug_log=True,
    enable_error_log=True,
    log_dir="./logs",
    log_format="json",
    console_level="INFO"
))

# Get a logger for your application (optional)
logger = get_logger('my_app')
logger.info("Application started")
# Initialize session and client
creds = LoginCredentials()
session = ClientSession()
session.login(creds)
client = DataClient(session)

# CORRECT: Backup large file with chunked generator
# WRONG: Don't load entire large file into memory
def chunked_file_reader(filepath, chunk_size=4 * 1024 * 1024):  # 4MB chunks
    """Read file in 4MB chunks to avoid RAM overload"""
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

# Base directory for group backup dummy data
base_dir = "/path/to/data/group_backup"

# Leader file (metadata)
leader_file = os.path.join(base_dir, "metadata.json")

# Find all member files
member_files = glob.glob(os.path.join(base_dir, "*.json"))
# Exclude the leader file from members
member_files = [f for f in member_files if f != leader_file]

print("="*60)
print("GROUP BACKUP OPERATION")
print("="*60)
print(f"\nLeader file: {os.path.basename(leader_file)}")
print(f"Member files found: {len(member_files)}")
for member_file in member_files:
    print(f"  - {os.path.basename(member_file)}")

# Create group with a unique name and filespace
group_name = "filesystem_backup_group"
filespace = "/filesystem_backup"
print(f"\nCreating group: {group_name}")
print(f"Filespace: {filespace}")
group = client.create_group(group_name, filespace=filespace)

# Add leader (leader.json file)
leader_size = os.path.getsize(leader_file)
print(f"\nAdding leader: {os.path.basename(leader_file)} ({leader_size} bytes)")

leader_backup = BackupRequest(
    Key=leader_file,
    Body=chunked_file_reader(leader_file),
    Filespace=filespace,
    SizeEstimate=leader_size,  # REQUIRED: Actual file size
    PreCompressed=False,  # JSON is not compressed
    ObjType=ObjType.FILE,
    MountWait=MountWait.SKIP
)

# First member added becomes the leader automatically
group.add_member(leader_backup)
print(f"  ✓ Leader added successfully")

# Add all .tar.gz files as members
print(f"\nAdding {len(member_files)} member files:")
for member_file in sorted(member_files):
    member_size = os.path.getsize(member_file)
    member_name = os.path.basename(member_file)
    
    print(f"  Adding: {member_name} ({member_size} bytes)...", end=" ")
    
    member_backup = BackupRequest(
        Key=member_file,
        Body=chunked_file_reader(member_file),
        Filespace=filespace,
        SizeEstimate=member_size,  # REQUIRED: Actual file size
        PreCompressed=False,  # JSON files are not compressed
        ObjType=ObjType.FILE,
        MountWait=MountWait.SKIP
    )
    
    group.add_member(member_backup)
    print("✓")

# Save and close the group
print("\nSaving group...")
group.save()
print("Closing group...")
group.close()

# Display group information
print("\n" + "="*60)
print("GROUP BACKUP COMPLETED")
print("="*60)
print(f"Group name: {group.name}")
print(f"Leader ID: {group.leader_id['hi']}-{group.leader_id['lo']}")
print(f"Filespace: {filespace}")
print(f"Total objects: {len(member_files) + 1}")  # +1 for leader
print(f"  - 1 leader (metadata.json)")
print(f"  - {len(member_files)} members (data files)")
print("="*60)

# Logout
session.logout()
print("\nGroup backup operation completed successfully.")


