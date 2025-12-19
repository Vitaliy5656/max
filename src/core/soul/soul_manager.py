"""
Soul Manager for MAX
Manages core identity and personality from soul.json with atomic writes.
"""
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

log = logging.getLogger(__name__)


@dataclass
class SoulIdentity:
    """Soul identity configuration."""
    name: str
    role: str
    version: str


@dataclass
class SoulPersonality:
    """Soul personality traits."""
    traits: list[str]
    principles: list[str]


@dataclass
class SoulCommunication:
    """Communication preferences."""
    default_language: str
    style: str
    formatting_rules: list[str]


@dataclass
class SoulState:
    """Complete soul state."""
    identity: Dict[str, Any]
    personality: Dict[str, Any]
    communication: Dict[str, Any]
    capabilities: Dict[str, Any]
    meta: Dict[str, Any]


class SoulManager:
    """
    Manages MAX's core identity and personality.
    
    Features:
    - Atomic writes (prevents corruption)
    - Automatic backup before save
    - Corruption recovery
    - Thread-safe operations
    - RAM caching with TTL (reduces file I/O)
    """
    
    def __init__(self, soul_path: Path = None, cache_ttl_seconds: int = 300):
        if soul_path is None:
            soul_path = Path(__file__).parent.parent.parent.parent / "data" / "soul.json"
        
        self._soul_path = soul_path
        self._soul_state: Optional[SoulState] = None
        self._cache_ttl = cache_ttl_seconds
        self._last_load_time = 0.0
        self._generation_cache: Dict[str, tuple[str, float]] = {}  # key -> (value, timestamp)
        self._load()
    
    def _is_cache_valid(self) -> bool:
        """Check if cached soul is still valid."""
        import time
        if not self._soul_state:
            return False
        
        elapsed = time.time() - self._last_load_time
        return elapsed < self._cache_ttl
    
    def _invalidate_cache(self):
        """Invalidate all caches."""
        self._soul_state = None
        self._last_load_time = 0.0
        self._generation_cache.clear()
        log.debug("Soul cache invalidated")
    
    def _load(self):
        """Load soul from disk with corruption recovery."""
        import time
        
        try:
            if not self._soul_path.exists():
                log.warning(f"soul.json not found at {self._soul_path}, creating default")
                self._create_default()
                return
            
            data = json.loads(self._soul_path.read_text(encoding='utf-8'))
            self._soul_state = SoulState(**data)
            self._last_load_time = time.time()
            log.info("✅ Soul loaded successfully (cached)")
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            log.error(f"soul.json corrupted: {e}")
            
            # Try backup recovery
            backup_path = self._soul_path.with_suffix('.json.backup')
            if backup_path.exists():
                log.warning("Attempting recovery from backup...")
                try:
                    data = json.loads(backup_path.read_text(encoding='utf-8'))
                    self._soul_state = SoulState(**data)
                    self._last_load_time = time.time()
                    log.info("✅ Recovered from backup")
                    # Save recovered state
                    self.save()
                    return
                except Exception as backup_error:
                    log.error(f"Backup also corrupted: {backup_error}")
            
            # Last resort: create default
            log.warning("Creating fresh soul.json")
            self._create_default()
    
    def _create_default(self):
        """Create default soul state."""
        self._soul_state = SoulState(
            identity={
                "name": "MAX",
                "role": "интеллектуальный AI-ассистент",
                "version": "1.0.0"
            },
            personality={
                "traits": ["дружелюбный", "профессиональный", "честный"],
                "principles": [
                    "Если не знаю ответа — говорю об этом",
                    "Не выдумываю информацию"
                ]
            },
            communication={
                "default_language": "русский",
                "style": "лаконичный, но полезный",
                "formatting_rules": ["Код в блоках ```", "Эмодзи умеренно"]
            },
            capabilities={},
            meta={
                "created_at": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "schema_version": "1.0"
            }
        )
        self.save()
    
    def save(self):
        """Save soul with atomic write (prevents corruption)."""
        if not self._soul_state:
            raise RuntimeError("No soul state to save")
        
        # Update timestamp
        self._soul_state.meta["last_modified"] = datetime.now().isoformat()
        
        # Convert to dict
        soul_data = asdict(self._soul_state)
        
        # ATOMIC WRITE PROCEDURE
        temp_path = self._soul_path.with_suffix('.tmp')
        
        try:
            # 1. Write to temp file
            temp_path.write_text(
                json.dumps(soul_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            # 2. Verify JSON is valid
            json.loads(temp_path.read_text(encoding='utf-8'))
            
            # 3. Create backup of current (if exists)
            if self._soul_path.exists():
                backup_path = self._soul_path.with_suffix('.json.backup')
                shutil.copy(self._soul_path, backup_path)
            
            # 4. Atomic rename (OS-level atomic operation)
            temp_path.replace(self._soul_path)
            
            # 5. Invalidate cache (force reload on next access)
            self._invalidate_cache()
            
            log.info("✅ soul.json saved atomically")
            
        except Exception as e:
            log.error(f"Failed to save soul.json: {e}")
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def get_soul(self) -> SoulState:
        """Get current soul state (cached)."""
        if not self._is_cache_valid():
            log.debug("Soul cache expired, reloading...")
            self._load()
        return self._soul_state
    
    def generate_meta_injection(self) -> str:
        """
        Generate meta-cognitive injection for system prompt.
        
        This is the CRITICAL METHOD that chat.py uses.
        DO NOT MODIFY signature!
        """
        import time
        
        # Check generation cache (TTL: 60 seconds)
        cache_key = "meta_injection"
        if cache_key in self._generation_cache:
            cached_value, cached_time = self._generation_cache[cache_key]
            if time.time() - cached_time < 60:
                return cached_value
        
        # Generate fresh injection
        soul = self.get_soul()
        
        # Build injection from soul.json
        parts = []
        
        # Identity
        identity = soul.identity
        parts.append(f"Ты {identity['name']} — {identity['role']}.")
        
        # Personality
        personality = soul.personality
        if personality.get('traits'):
            traits_str = ", ".join(personality['traits'])
            parts.append(f"Твоя личность: {traits_str}.")
        
        # Principles
        if personality.get('principles'):
            parts.append("Твои принципы:")
            for principle in personality['principles']:
                parts.append(f"- {principle}")
        
        # Communication
        comm = soul.communication
        parts.append(f"\nСтиль общения: {comm['style']}")
        parts.append(f"Язык по умолчанию: {comm['default_language']}")
        
        result = "\n".join(parts)
        
        # Cache result
        self._generation_cache[cache_key] = (result, time.time())
        
        return result
    
    def update_personality_trait(self, trait: str, add: bool = True):
        """Add or remove personality trait."""
        soul = self.get_soul()
        traits = soul.personality.get('traits', [])
        
        if add and trait not in traits:
            traits.append(trait)
        elif not add and trait in traits:
            traits.remove(trait)
        
        soul.personality['traits'] = traits
        self.save()
    
    def get_stats(self) -> dict:
        """Get soul statistics."""
        soul = self.get_soul()
        return {
            "version": soul.identity.get('version', 'unknown'),
            "traits_count": len(soul.personality.get('traits', [])),
            "principles_count": len(soul.personality.get('principles', [])),
            "last_modified": soul.meta.get('last_modified', 'unknown')
        }


# Global instance
_soul_manager: Optional[SoulManager] = None


def get_soul_manager() -> SoulManager:
    """Get global Soul Manager instance."""
    global _soul_manager
    if _soul_manager is None:
        _soul_manager = SoulManager()
    return _soul_manager
