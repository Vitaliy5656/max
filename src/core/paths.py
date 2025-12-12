"""
System paths for MAX AI Assistant.

Provides cross-platform paths using system-appropriate locations:
- Windows: %APPDATA%/MAX_AI
- macOS: ~/Library/Application Support/MAX_AI
- Linux: ~/.local/share/MAX_AI
"""
import os
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """
    Get system-appropriate application data directory.
    
    Returns:
        Path to MAX_AI data directory (created if not exists)
    """
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':  # macOS
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Linux/Unix
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    
    app_dir = base / 'MAX_AI'
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_db_path() -> Path:
    """Get path to main SQLite database."""
    return get_app_data_dir() / 'max.db'


def get_backup_dir() -> Path:
    """Get path to backup directory."""
    backup_dir = get_app_data_dir() / 'backups'
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def get_logs_dir() -> Path:
    """Get path to logs directory."""
    logs_dir = get_app_data_dir() / 'logs'
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def get_credentials_path() -> Path:
    """Get path to Google Drive credentials file."""
    return get_app_data_dir() / 'gdrive_credentials.json'


def get_backup_status_path() -> Path:
    """Get path to backup status JSON file."""
    return get_app_data_dir() / 'backup_status.json'


# For backwards compatibility with existing data
def migrate_legacy_data(project_root: Path) -> bool:
    """
    Migrate data from project folder to AppData.
    
    Args:
        project_root: Path to project root containing old data/max.db
        
    Returns:
        True if migration was performed, False if not needed
    """
    import shutil
    
    old_db = project_root / 'data' / 'max.db'
    new_db = get_db_path()
    
    if old_db.exists() and not new_db.exists():
        print(f"📦 Migrating database from {old_db} to {new_db}")
        shutil.copy2(old_db, new_db)
        
        # Rename old file to indicate migration
        old_db.rename(old_db.with_suffix('.db.migrated'))
        print(f"✓ Migration complete. Old file renamed to {old_db.with_suffix('.db.migrated')}")
        return True
    
    return False
