"""
Privacy Guard for MAX AI.

Manages privacy-sensitive data access with unlock/lock mechanism.
Works with Memory system to filter private facts when locked.

Key features:
    - Session-based privacy lock (default: LOCKED)
    - Unlock trigger phrase: "Привет, малыш"
    - Auto-lock after 30 min inactivity
    - Memory filter for is_private facts
"""
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class PrivacyLevel(Enum):
    """Privacy levels for facts/data."""
    PUBLIC = "public"      # Safe to share anytime
    PRIVATE = "private"    # Only when unlocked
    SECRET = "secret"      # Extra confirmation required


# Unlock patterns
UNLOCK_PATTERNS = [
    re.compile(r"привет,?\s*малыш", re.IGNORECASE),
    re.compile(r"hello,?\s*baby", re.IGNORECASE),  # English variant
]

# Lock patterns (explicit lock)
LOCK_PATTERNS = [
    re.compile(r"закрой\s+личн", re.IGNORECASE),
    re.compile(r"заблокируй", re.IGNORECASE),
    re.compile(r"lock\s+priv", re.IGNORECASE),
]

# Auto-lock timeout
AUTO_LOCK_MINUTES = 30

# Private topic keywords (for detecting private content)
PRIVATE_KEYWORDS = {
    # Personal data
    "пароль", "password", "pin", "код доступа",
    # Health
    "болезнь", "диагноз", "таблетки", "лекарства", "врач",
    # Finance
    "зарплата", "кредит", "долг", "счёт", "банк", "карта",
    # Family
    "жена", "муж", "девушка", "парень", "мама", "папа", "ребёнок",
    # Secrets
    "секрет", "никому", "между нами", "не говори",
}


@dataclass
class PrivacyState:
    """Current privacy state for a session."""
    is_unlocked: bool = False
    unlock_time: Optional[datetime] = None
    unlock_count: int = 0
    last_activity: Optional[datetime] = None


class PrivacyGuard:
    """
    Guards access to private data based on session state.
    
    Usage:
        guard = PrivacyGuard()
        
        # Check unlock trigger
        if guard.check_unlock_trigger(message):
            # User said magic phrase
            guard.unlock()
        
        # Filter facts based on privacy state
        safe_facts = guard.filter_facts(all_facts)
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or "default"
        self._state = PrivacyState()
        
        log.debug(f"PrivacyGuard initialized for session: {self.session_id}")
    
    # =========================================
    # Unlock/Lock Management
    # =========================================
    
    def check_unlock_trigger(self, message: str) -> bool:
        """Check if message contains unlock phrase."""
        for pattern in UNLOCK_PATTERNS:
            if pattern.search(message):
                return True
        return False
    
    def check_lock_trigger(self, message: str) -> bool:
        """Check if message contains explicit lock phrase."""
        for pattern in LOCK_PATTERNS:
            if pattern.search(message):
                return True
        return False
    
    def unlock(self) -> str:
        """
        Unlock private memory access.
        
        Returns:
            Confirmation message
        """
        now = datetime.now()
        self._state.is_unlocked = True
        self._state.unlock_time = now
        self._state.last_activity = now
        self._state.unlock_count += 1
        
        log.debug(f"Privacy UNLOCKED for session {self.session_id}")
        
        return "Привет! Личная память разблокирована. Теперь я помню всё о тебе."
    
    def lock(self) -> str:
        """
        Lock private memory access.
        
        Returns:
            Confirmation message
        """
        self._state.is_unlocked = False
        self._state.unlock_time = None
        
        log.debug(f"Privacy LOCKED for session {self.session_id}")
        
        return "Личная память заблокирована. До следующего раза!"
    
    def is_unlocked(self) -> bool:
        """
        Check if private access is currently unlocked.
        
        Handles auto-lock after timeout.
        """
        if not self._state.is_unlocked:
            return False
        
        # Check auto-lock timeout
        if self._state.last_activity:
            elapsed = datetime.now() - self._state.last_activity
            if elapsed > timedelta(minutes=AUTO_LOCK_MINUTES):
                log.debug(f"Privacy AUTO-LOCKED after {AUTO_LOCK_MINUTES}min inactivity")
                self._state.is_unlocked = False
                self._state.unlock_time = None
                return False
        
        return True
    
    def touch(self) -> None:
        """Update last activity time (prevents auto-lock)."""
        if self._state.is_unlocked:
            self._state.last_activity = datetime.now()
    
    # =========================================
    # Fact Filtering
    # =========================================
    
    def filter_facts(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter facts based on current privacy state.
        
        Args:
            facts: List of fact dicts with optional 'is_private' key
            
        Returns:
            Filtered list (only public facts if locked)
        """
        if self.is_unlocked():
            # Full access - return all facts
            return facts
        
        # Locked - filter out private facts
        return [f for f in facts if not f.get("is_private", False)]
    
    def filter_context(self, context: str) -> str:
        """
        Filter context string to remove private mentions.
        
        Used when building system prompt.
        """
        if self.is_unlocked():
            return context
        
        # Remove lines containing private keywords
        lines = context.split("\n")
        filtered = []
        
        for line in lines:
            line_lower = line.lower()
            has_private = any(kw in line_lower for kw in PRIVATE_KEYWORDS)
            if not has_private:
                filtered.append(line)
        
        return "\n".join(filtered)
    
    # =========================================
    # Privacy Detection
    # =========================================
    
    def is_private_content(self, text: str) -> bool:
        """
        Detect if text contains private information.
        
        Used when extracting facts to mark them as is_private=True.
        """
        text_lower = text.lower()
        return any(kw in text_lower for kw in PRIVATE_KEYWORDS)
    
    def suggest_privacy_level(self, fact_text: str) -> PrivacyLevel:
        """
        Suggest privacy level for a new fact.
        
        Args:
            fact_text: The fact content
            
        Returns:
            Suggested privacy level
        """
        text_lower = fact_text.lower()
        
        # Check for secrets
        secret_words = {"секрет", "никому", "пароль", "password", "pin"}
        if any(w in text_lower for w in secret_words):
            return PrivacyLevel.SECRET
        
        # Check for private content
        if self.is_private_content(fact_text):
            return PrivacyLevel.PRIVATE
        
        return PrivacyLevel.PUBLIC
    
    # =========================================
    # State Management
    # =========================================
    
    def get_state(self) -> Dict[str, Any]:
        """Get current privacy state as dict."""
        return {
            "session_id": self.session_id,
            "is_unlocked": self.is_unlocked(),
            "unlock_time": self._state.unlock_time.isoformat() if self._state.unlock_time else None,
            "unlock_count": self._state.unlock_count,
            "auto_lock_minutes": AUTO_LOCK_MINUTES,
        }
    
    def get_status_message(self) -> str:
        """Get human-readable status."""
        if self.is_unlocked():
            elapsed = datetime.now() - self._state.unlock_time if self._state.unlock_time else timedelta(0)
            remaining = AUTO_LOCK_MINUTES - int(elapsed.total_seconds() / 60)
            return f"🔓 Личная память открыта (автоблокировка через {remaining} мин)"
        else:
            return "🔒 Личная память заблокирована"


# Global instance per session (simple in-memory storage)
_guards: Dict[str, PrivacyGuard] = {}


def get_privacy_guard(session_id: str = "default") -> PrivacyGuard:
    """Get or create PrivacyGuard for session."""
    if session_id not in _guards:
        _guards[session_id] = PrivacyGuard(session_id)
    return _guards[session_id]
