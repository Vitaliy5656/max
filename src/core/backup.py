"""
Backup Manager for MAX AI Assistant.

Features:
- Local backups using SQLite Online Backup API
- Google Drive sync (when credentials available)
- Detached process for crash-safe backup
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import sqlite3
import gzip


class BackupManager:
    """
    Manages database backups to local storage and Google Drive.
    
    The backup process runs as a detached subprocess that survives
    if the main application crashes.
    """
    
    def __init__(self):
        from .paths import get_db_path, get_backup_dir, get_backup_status_path, get_credentials_path
        self.db_path = get_db_path()
        self.backup_dir = get_backup_dir()
        self.status_path = get_backup_status_path()
        self.credentials_path = get_credentials_path()
    
    def get_status(self) -> dict:
        """Get current backup status."""
        if self.status_path.exists():
            try:
                return json.loads(self.status_path.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {
            "last_backup": None,
            "last_cloud_sync": None,
            "status": "unknown",
            "cloud_synced": False
        }
    
    def spawn_backup_worker(self) -> bool:
        """
        Spawn detached backup worker process.
        
        The worker runs independently and survives if main app crashes.
        It performs local backup + Google Drive upload.
        
        Returns:
            True if worker was spawned successfully
        """
        if not self.db_path.exists():
            print("⚠️ Database not found, skipping backup")
            return False
        
        worker_script = Path(__file__).parent.parent.parent / "scripts" / "backup_worker.py"
        
        if not worker_script.exists():
            print(f"⚠️ Backup worker script not found: {worker_script}")
            return False
        
        try:
            # Update status to "in_progress"
            self._update_status("in_progress", cloud_synced=False)
            
            # Spawn detached process (Windows)
            if sys.platform == 'win32':
                CREATE_NO_WINDOW = 0x08000000
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(
                    [sys.executable, str(worker_script), str(self.db_path)],
                    creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                    close_fds=True
                )
            else:
                # Unix: use nohup-like behavior
                subprocess.Popen(
                    [sys.executable, str(worker_script), str(self.db_path)],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            print("✓ Backup worker spawned")
            return True
            
        except Exception as e:
            print(f"✗ Failed to spawn backup worker: {e}")
            self._update_status("error", error=str(e))
            return False
    
    def backup_local_sync(self) -> Optional[Path]:
        """
        Create local backup synchronously.
        
        Uses SQLite's backup API for safe live database backup.
        
        Returns:
            Path to backup file or None on failure
        """
        if not self.db_path.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"max_{timestamp}.db.gz"
        
        try:
            # Use SQLite's backup API (safe for live DB)
            source = sqlite3.connect(str(self.db_path))
            
            # Create uncompressed backup first
            temp_backup = self.backup_dir / f"max_{timestamp}.db"
            dest = sqlite3.connect(str(temp_backup))
            source.backup(dest)
            source.close()
            dest.close()
            
            # Compress the backup
            with open(temp_backup, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove uncompressed temp file
            temp_backup.unlink()
            
            print(f"✓ Local backup created: {backup_file.name}")
            return backup_file
            
        except Exception as e:
            print(f"✗ Backup failed: {e}")
            return None
    
    def _update_status(self, status: str, cloud_synced: bool = False, error: str = None):
        """Update backup status file."""
        data = self.get_status()
        data["status"] = status
        data["cloud_synced"] = cloud_synced
        data["last_update"] = datetime.now().isoformat()
        if error:
            data["error"] = error
        self.status_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    def has_gdrive_credentials(self) -> bool:
        """Check if Google Drive credentials are configured."""
        return self.credentials_path.exists()
    
    def list_backups(self, limit: int = 10) -> list[dict]:
        """List recent local backups."""
        backups = []
        for f in sorted(self.backup_dir.glob("max_*.db.gz"), reverse=True)[:limit]:
            backups.append({
                "name": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        return backups


# Global instance
backup_manager = BackupManager()
