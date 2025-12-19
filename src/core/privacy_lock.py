"""
Privacy Lock Manager for MAX
Protects sensitive fact categories (shadow, vault) with lock/unlock mechanism.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


class PrivacyLock:
    """
    Manages access to sensitive data categories.
    
    Categories:
    - general: Always accessible
    - shadow: Locked by default, requires unlock
    - vault: Highest security, requires unlock
    """
    
    SENSITIVE_CATEGORIES = {"shadow", "vault"}
    
    def __init__(self):
        self._unlocked_until: Optional[datetime] = None
        self._unlock_duration_minutes = 30  # Auto-lock after 30 min
    
    def is_locked(self) -> bool:
        """Check if privacy lock is active."""
        if self._unlocked_until is None:
            return True
        
        # Check if unlock expired
        if datetime.now() > self._unlocked_until:
            self._unlocked_until = None
            return True
        
        return False
    
    def unlock(self, duration_minutes: int = 30) -> bool:
        """
        Unlock sensitive categories.
        
        Args:
            duration_minutes: How long to keep unlocked (default 30 min)
        
        Returns:
            True if unlocked successfully
        """
        self._unlock_duration_minutes = duration_minutes
        self._unlocked_until = datetime.now() + timedelta(minutes=duration_minutes)
        
        log.info(f"🔓 Privacy unlocked for {duration_minutes} minutes")
        return True
    
    def lock(self):
        """Lock sensitive categories immediately."""
        self._unlocked_until = None
        log.info("🔒 Privacy locked")
    
    def can_access(self, category: str) -> bool:
        """
        Check if category can be accessed.
        
        Args:
            category: Fact category to check
        
        Returns:
            True if access allowed
        """
        # General category always accessible
        if category not in self.SENSITIVE_CATEGORIES:
            return True
        
        # Sensitive categories require unlock
        return not self.is_locked()
    
    def get_status(self) -> dict:
        """Get current lock status."""
        locked = self.is_locked()
        
        status = {
            "locked": locked,
            "sensitive_categories": list(self.SENSITIVE_CATEGORIES)
        }
        
        if not locked and self._unlocked_until:
            remaining = (self._unlocked_until - datetime.now()).total_seconds() / 60
            status["unlocked_minutes_remaining"] = round(remaining, 1)
        
        return status


# Global instance
_privacy_lock: Optional[PrivacyLock] = None


def get_privacy_lock() -> PrivacyLock:
    """Get global Privacy Lock instance."""
    global _privacy_lock
    if _privacy_lock is None:
        _privacy_lock = PrivacyLock()
    return _privacy_lock
