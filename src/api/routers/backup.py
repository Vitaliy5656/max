"""
Backup Router for MAX AI API.

Endpoints:
- GET /api/backup/status
- GET /api/backup/list  
- POST /api/backup/trigger
"""
from fastapi import APIRouter

from src.core.backup import backup_manager

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/status")
async def get_backup_status():
    """Get current backup status."""
    return backup_manager.get_status()


@router.get("/list")
async def list_backups():
    """List recent backups."""
    return backup_manager.list_backups()


@router.post("/trigger")
async def trigger_backup():
    """Manually trigger a backup."""
    success = backup_manager.spawn_backup_worker()
    return {"success": success}
