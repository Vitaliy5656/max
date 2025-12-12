#!/usr/bin/env python3
"""
Backup Worker - Detached Process for MAX AI.

This script runs as an independent process that:
1. Creates a compressed local backup of max.db
2. Uploads to Google Drive (if credentials exist)
3. Updates backup_status.json
4. Self-terminates after completion

Usage:
    python backup_worker.py /path/to/max.db
    
The process is designed to survive if the main application crashes.
"""
import sys
import json
import gzip
import sqlite3
from pathlib import Path
from datetime import datetime


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_status_path(db_path: Path) -> Path:
    """Get path to status file."""
    return db_path.parent / "backup_status.json"


def update_status(db_path: Path, status: str, **extra):
    """Update backup status file."""
    status_path = get_status_path(db_path)
    try:
        data = json.loads(status_path.read_text()) if status_path.exists() else {}
    except Exception:
        data = {}
    
    data.update({
        "status": status,
        "last_update": datetime.now().isoformat(),
        **extra
    })
    status_path.write_text(json.dumps(data, indent=2))


def backup_local(db_path: Path) -> Path:
    """Create compressed local backup using SQLite backup API."""
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"max_{timestamp}.db.gz"
    temp_file = backup_dir / f"max_{timestamp}.db"
    
    # SQLite backup (safe for live DB)
    log(f"Creating backup of {db_path.name}...")
    source = sqlite3.connect(str(db_path))
    dest = sqlite3.connect(str(temp_file))
    source.backup(dest)
    source.close()
    dest.close()
    
    # Compress
    log("Compressing...")
    with open(temp_file, 'rb') as f_in:
        with gzip.open(backup_file, 'wb') as f_out:
            f_out.writelines(f_in)
    
    temp_file.unlink()
    size_mb = round(backup_file.stat().st_size / (1024 * 1024), 2)
    log(f"✓ Local backup: {backup_file.name} ({size_mb} MB)")
    
    return backup_file


def upload_to_gdrive(backup_file: Path, credentials_path: Path) -> bool:
    """Upload backup to Google Drive."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        log("⚠️ Google libraries not installed, skipping cloud upload")
        return False
    
    if not credentials_path.exists():
        log("⚠️ No Google Drive credentials, skipping cloud upload")
        return False
    
    try:
        log("Uploading to Google Drive...")
        creds = service_account.Credentials.from_service_account_file(
            str(credentials_path),
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        service = build('drive', 'v3', credentials=creds)
        
        # Find or create MAX_AI_Backup folder
        folder_name = "MAX_AI_Backup"
        results = service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)"
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            folder_id = folders[0]['id']
        else:
            # Create folder
            folder = service.files().create(body={
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }).execute()
            folder_id = folder['id']
            log(f"Created folder: {folder_name}")
        
        # Upload file
        media = MediaFileUpload(
            str(backup_file),
            mimetype='application/gzip',
            resumable=True
        )
        file = service.files().create(
            body={'name': backup_file.name, 'parents': [folder_id]},
            media_body=media
        ).execute()
        
        log(f"✓ Uploaded to Google Drive: {file['id']}")
        return True
        
    except Exception as e:
        log(f"✗ Google Drive upload failed: {e}")
        return False


def cleanup_old_backups(backup_dir: Path, keep: int = 10):
    """Keep only N most recent backups."""
    backups = sorted(backup_dir.glob("max_*.db.gz"), reverse=True)
    for old_backup in backups[keep:]:
        log(f"Removing old backup: {old_backup.name}")
        old_backup.unlink()


def main():
    if len(sys.argv) < 2:
        print("Usage: backup_worker.py /path/to/max.db")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        log(f"✗ Database not found: {db_path}")
        sys.exit(1)
    
    credentials_path = db_path.parent / "gdrive_credentials.json"
    
    try:
        # Update status: in progress
        update_status(db_path, "backing_up")
        
        # 1. Local backup
        backup_file = backup_local(db_path)
        update_status(db_path, "local_complete", last_backup=datetime.now().isoformat())
        
        # 2. Google Drive upload
        cloud_success = upload_to_gdrive(backup_file, credentials_path)
        
        # 3. Cleanup old backups
        cleanup_old_backups(db_path.parent / "backups", keep=10)
        
        # 4. Final status
        update_status(
            db_path, 
            "complete",
            cloud_synced=cloud_success,
            last_backup=datetime.now().isoformat(),
            last_cloud_sync=datetime.now().isoformat() if cloud_success else None
        )
        
        log("✓ Backup complete!")
        
    except Exception as e:
        log(f"✗ Backup failed: {e}")
        update_status(db_path, "error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
