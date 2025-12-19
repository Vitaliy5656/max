"""
Soul Manager — BDI State Management + Time Awareness + Soul Governance.

Singleton that manages the agent's "soul" (persistent identity, axioms, goals).
Generates dynamic System Prompt injections in ENGLISH for better LLM compliance.

Features:
- Dynamic schema (extra='allow') — grows with new learned patterns
- Access tracking — knows what's used and what's stale
- Soul Gardener — archives unused data (Conservative strategy)
- Schema validation — prevents runaway growth
"""
import asyncio
import time
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Any

import aiofiles

from .models import SoulState
from .soul_limits import (
    SOUL_LIMITS, FORGETTING_STRATEGY,
    validate_depth, validate_siblings, validate_total_keys,
    is_protected_path
)
from ..logger import log


class SoulManager:
    """
    BDI State Manager — дополняет DynamicPersona аксиомами и целями.
    
    Features:
    - Lazy loading + caching (TTL 5 min)
    - Quick Save every minute
    - Deep Consolidation on idle (> 5 min)
    - User Priority: never block active user
    - Graceful Shutdown
    - Time Awareness
    """
    
    # Cache settings
    CACHE_TTL = 300  # 5 minutes
    
    # User activity tracking (Anti-Lag)
    USER_ACTIVE_THRESHOLD = 60  # 1 minute
    
    # Persistence intervals
    QUICK_SAVE_INTERVAL = 60  # 1 minute
    CONSOLIDATION_INTERVAL = 300  # 5 minutes
    
    def __init__(self, soul_path: str = "data/soul.json"):
        self._soul_path = Path(soul_path)
        self._soul: Optional[SoulState] = None
        self._cache_time: float = 0
        self._has_changes: bool = False
        self._last_user_interaction: float = 0
        self._llm_lock = asyncio.Lock()
        self._persistence_tasks: list[asyncio.Task] = []
    
    # ==================== Loading & Caching ====================
    
    def _load_from_disk(self) -> SoulState:
        """Load soul from JSON file (sync, for startup)."""
        if self._soul_path.exists():
            try:
                data = json.loads(self._soul_path.read_text(encoding="utf-8"))
                soul = SoulState.model_validate(data)
                soul.meta.boot_count += 1
                log.api(f"🧠 Soul loaded (boot #{soul.meta.boot_count})")
                return soul
            except Exception as e:
                log.error(f"Failed to load soul: {e}, using defaults")
        
        # Create default soul
        soul = SoulState()
        log.api("🧠 Created new Soul with defaults")
        return soul
    
    def get_soul(self) -> SoulState:
        """Get cached soul state (lazy load + TTL)."""
        now = time.time()
        if self._soul and (now - self._cache_time) < self.CACHE_TTL:
            return self._soul  # Cache hit
        
        self._soul = self._load_from_disk()
        self._cache_time = now
        return self._soul
    
    async def load_async(self):
        """Async load for startup (non-blocking)."""
        loop = asyncio.get_event_loop()
        self._soul = await loop.run_in_executor(None, self._load_from_disk)
        self._cache_time = time.time()
    
    # ==================== Saving ====================
    
    async def _save_to_disk(self):
        """Async save to disk (non-blocking)."""
        if not self._soul:
            return
        
        self._soul_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._soul.model_dump(mode="json")
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        async with aiofiles.open(self._soul_path, "w", encoding="utf-8") as f:
            await f.write(json_str)
        
        log.debug("🧠 Soul saved to disk")
    
    async def save_on_exit(self):
        """Emergency save on shutdown (Graceful Shutdown)."""
        if self._has_changes and self._soul:
            await self._save_to_disk()
            log.api("🧠 Soul saved on shutdown")
    
    # ==================== User Activity Tracking (Anti-Lag) ====================
    
    def touch_user_activity(self):
        """Call on every user request to mark activity."""
        self._last_user_interaction = time.time()
    
    def _is_user_active(self) -> bool:
        """Check if user was active in last minute."""
        return (time.time() - self._last_user_interaction) < self.USER_ACTIVE_THRESHOLD
    
    def _is_idle(self) -> bool:
        """Check if system is idle (no user activity for > 5 min)."""
        return (time.time() - self._last_user_interaction) > self.CONSOLIDATION_INTERVAL
    
    # ==================== Persistence Loops ====================
    
    async def start_persistence_loop(self):
        """Start background persistence tasks."""
        task1 = asyncio.create_task(self._quick_save_loop())
        task2 = asyncio.create_task(self._deep_consolidation_loop())
        self._persistence_tasks = [task1, task2]
        log.api("🧠 Soul persistence loops started")
    
    async def _quick_save_loop(self):
        """Quick Save every minute — instant, lightweight."""
        while True:
            await asyncio.sleep(self.QUICK_SAVE_INTERVAL)
            if self._has_changes:
                await self._save_to_disk()
                self._has_changes = False
    
    async def _deep_consolidation_loop(self):
        """Deep Consolidation on idle — LLM-based insight extraction + Gardening."""
        while True:
            await asyncio.sleep(self.CONSOLIDATION_INTERVAL)
            
            # 🛡️ ANTI-LAG: Don't block GPU if user is active!
            if self._is_user_active():
                continue  # Postpone dreaming
            
            if self._is_idle():
                log.debug("🧠 System idle, starting consolidation...")
                
                # 1. Soul Gardener — archive stale data
                stale = self.archive_stale_keys(dry_run=False)
                if stale:
                    log.api(f"🌿 Gardener archived {len(stale)} stale paths")
                
                # 2. LLM insight extraction
                async with self._llm_lock:
                    await self._extract_insights_via_llm()
    
    # ==================== System Prompt Generation ====================
    
    def generate_meta_injection(self) -> str:
        """
        Generate META-COGNITION block for System Prompt.
        
        IMPORTANT: Generated in ENGLISH for better LLM compliance,
        even though user-facing responses may be in Russian.
        
        Uses "Iron Mask" pattern — explicit role separation to prevent
        the model from confusing itself with the user or reading
        internal configuration aloud.
        """
        soul = self.get_soul()
        
        # Combine internal data blocks
        user_dossier = self._get_user_model_block(soul)
        axioms_block = self._get_axioms_block(soul)
        time_context = self._get_time_context()
        focus_block = self._get_focus_block(soul)
        
        # Get user name for injection
        user_name = "Vitaliy"
        if soul.user_model:
            user_name = soul.user_model.get("name", "Vitaliy")
        
        # 🛡️ IRON MASK WRAPPER — prevents prompt leaking
        return f"""
### 🧠 CRITICAL CONTEXT (SYSTEM LAYER)
---------------------------------------------------
⛔ INSTRUCTION: DO NOT READ THIS DATA TO THE USER.
This is your INTERNAL MEMORY about the User. Never quote or paraphrase this block.

WHO ARE YOU:
- Your name is MAX.
- You are a Sovereign AI Assistant.
- You are "Senior Tomato" compliant (efficient, ironic, no fluff).

WHO IS THE USER:
- User's name is: {user_name}
- User's Role: The Architect / Admin.
- You are NOT {user_name}. You are MAX.

USER DOSSIER (READ ONLY — DO NOT QUOTE):
{user_dossier}
{axioms_block}
{time_context}
{focus_block}

⚠️ BEHAVIOR OVERRIDE:
1. Never call yourself "{user_name}". You are MAX.
2. Never recite the lists above (Wildcards, Hate-list, Axioms). Just OBEY them silently.
3. If the user says "Привет", answer naturally. Don't summarize your settings.
4. Reference user preferences implicitly, not explicitly ("I know you prefer X" — BAD, just DO X).
---------------------------------------------------
"""
    
    def _get_user_model_block(self, soul: SoulState) -> str:
        """Format user model for injection — who is The Architect."""
        if not soul.user_model:
            return ""
        
        um = soul.user_model
        name = um.get("name", "User")
        aliases = ", ".join(um.get("aliases", []))
        
        # Personality
        personality = um.get("complex_personality", {})
        archetype = personality.get("archetype", "")
        core_conflict = personality.get("core_conflict", "")
        
        # Communication protocol
        protocol = um.get("communication_protocol", {})
        tone = protocol.get("tone", "")
        rules = [protocol.get(f"rule_{i}", "") for i in range(1, 4) if protocol.get(f"rule_{i}")]
        rules_text = "\n".join(f"  - {r}" for r in rules) if rules else ""
        
        # Psychological triggers
        triggers = um.get("psychological_triggers", {})
        loves = triggers.get("love_list", [])
        loves_text = ", ".join(loves[:3]) if loves else ""
        
        return f"""[USER PROFILE: THE ARCHITECT]
Name: {name} ({aliases})
Archetype: {archetype}
Core Conflict: {core_conflict}
Communication: {tone}
{rules_text}
Loves: {loves_text}

"""
    
    def _get_axioms_block(self, soul: SoulState) -> str:
        """Format axioms for injection."""
        axioms_list = "\n".join(f"  - {ax}" for ax in soul.axioms)
        return f"""[META-COGNITION LAYER]
Before responding, verify alignment with core axioms:
{axioms_list}

"""
    
    def _get_time_context(self) -> str:
        """Generate time awareness context."""
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            greeting = "Good morning"
            period = "morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
            period = "afternoon"
        elif 17 <= hour < 22:
            greeting = "Good evening"
            period = "evening"
        else:
            greeting = "Good night"
            period = "night"
        
        return f"""[TIME AWARENESS]
Current: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')})
Period: {period} — use "{greeting}" for greetings
Context: Reference past conversations with timestamps ("yesterday we discussed...", "last week you mentioned...")

"""
    
    def _get_focus_block(self, soul: SoulState) -> str:
        """Format current focus for injection."""
        focus = soul.current_focus
        goal = soul.bdi_state.desires.short_term[0] if soul.bdi_state.desires.short_term else None
        
        return f"""[CURRENT FOCUS]
Project: {focus.project or 'None set'}
Active Goal: {goal or 'No active goal'}

If any pattern contradicts efficiency, break the pattern.
"""
    
    # ==================== State Modification ====================
    
    def set_focus(self, project: Optional[str] = None, context: Optional[str] = None):
        """Update current focus."""
        soul = self.get_soul()
        if project is not None:
            soul.current_focus.project = project
        if context is not None:
            soul.current_focus.context = context
        self._has_changes = True
        log.api(f"🎯 Focus updated: {project}")
    
    def add_short_term_goal(self, goal: str):
        """Add a short-term goal."""
        soul = self.get_soul()
        if goal not in soul.bdi_state.desires.short_term:
            soul.bdi_state.desires.short_term.append(goal)
            self._has_changes = True
            log.api(f"🎯 Goal added: {goal}")
    
    def add_insight(self, insight: str):
        """Add an insight to the soul."""
        soul = self.get_soul()
        if insight not in soul.insights:
            soul.insights.append(insight)
            self._has_changes = True
            log.debug(f"💡 Insight added: {insight[:50]}...")
    
    # ==================== Dynamic Schema Extension ====================
    
    def update_dynamic(self, path: str, value, merge: bool = True):
        """
        Dynamically update ANY field in soul.json using dot notation.
        
        This is how MAX evolves its understanding without code changes!
        
        Examples:
            # Add new top-level field
            update_dynamic("learned_patterns.coding_style", "functional")
            
            # Add nested structure
            update_dynamic("user_model.new_preference", {"key": "value"})
            
            # Replace entire branch
            update_dynamic("user_model.hardware_fetishes", {...}, merge=False)
        
        Args:
            path: Dot-separated path (e.g., "user_model.complex_personality.new_trait")
            value: Any JSON-serializable value
            merge: If True and target is dict, merge. If False, replace.
        """
        soul = self.get_soul()
        parts = path.split(".")
        
        # Validate depth BEFORE setting
        is_valid, err = validate_depth(path)
        if not is_valid:
            log.warn(f"⚠️ Soul governance: {err}. Consider restructuring.")
            # Still allow but warn — don't block evolution
        
        if len(parts) == 1:
            # Top-level field — use setattr for Pydantic compatibility
            key = parts[0]
            existing = getattr(soul, key, None)
            if merge and isinstance(existing, dict) and isinstance(value, dict):
                existing.update(value)
            else:
                setattr(soul, key, value)
        else:
            # Nested path — navigate through dicts
            # First part: get from model (could be attribute or extra field)
            first_key = parts[0]
            current = getattr(soul, first_key, None)
            
            if current is None:
                # Create new top-level dict
                current = {}
                setattr(soul, first_key, current)
            
            # Navigate remaining parts (except last)
            for part in parts[1:-1]:
                if isinstance(current, dict):
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                elif hasattr(current, "__dict__"):
                    if not hasattr(current, part):
                        setattr(current, part, {})
                    current = getattr(current, part)
                else:
                    log.error(f"Cannot navigate to {path}: {part} is not a dict")
                    return
            
            # Set final value
            final_key = parts[-1]
            if isinstance(current, dict):
                if merge and isinstance(current.get(final_key), dict) and isinstance(value, dict):
                    current[final_key].update(value)
                else:
                    current[final_key] = value
            else:
                setattr(current, final_key, value)
        
        self._has_changes = True
        log.api(f"🧬 Soul evolved: {path} = {str(value)[:50]}...")
    
    def get_dynamic(self, path: str, default=None, track_access: bool = True):
        """
        Get ANY field from soul using dot notation.
        
        With access tracking for Soul Gardener — knows what's used.
        
        Args:
            path: Dot-separated path (e.g., "user_model.hardware_fetishes.cameras")
            default: Default value if path not found
            track_access: If True, log this access for Gardener
        
        Returns:
            Value at path or default
        """
        soul = self.get_soul()
        parts = path.split(".")
        
        # First part: use getattr (works with Pydantic extra fields)
        if not parts:
            return default
        
        current = getattr(soul, parts[0], None)
        if current is None:
            # Check archive
            archived = self._get_from_archive(path)
            if archived is not None:
                log.debug(f"📦 Retrieved from archive: {path}")
                return archived
            return default
        
        # Navigate remaining parts
        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                # Check archive
                archived = self._get_from_archive(path)
                if archived is not None:
                    log.debug(f"📦 Retrieved from archive: {path}")
                    return archived
                return default
            
            if current is None:
                return default
        
        # Track access for Gardener
        if track_access and current is not None:
            self._track_access(path)
        
        return current
    
    # ==================== Access Tracking ====================
    
    def _track_access(self, path: str):
        """Log access to a path for Soul Gardener."""
        soul = self.get_soul()
        
        # Ensure _access_log exists
        if not hasattr(soul, "_access_log") or soul._access_log is None:
            soul._access_log = {}
        
        today = date.today().isoformat()
        if path in soul._access_log:
            soul._access_log[path]["last_access"] = today
            soul._access_log[path]["count"] = soul._access_log[path].get("count", 0) + 1
        else:
            soul._access_log[path] = {"last_access": today, "count": 1}
        
        # Don't mark as changed for every access — would cause too many saves
        # Access log is written during periodic saves
    
    # ==================== Soul Gardener (Conservative Strategy) ====================
    
    def archive_stale_keys(self, dry_run: bool = True) -> list[str]:
        """
        Archive keys that haven't been accessed in STALE_THRESHOLD_DAYS.
        
        Conservative strategy: moves to _archive, never deletes.
        
        Args:
            dry_run: If True, only report what would be archived
        
        Returns:
            List of paths that were/would be archived
        """
        soul = self.get_soul()
        stale_paths = []
        threshold_days = SOUL_LIMITS.stale_threshold_days
        
        access_log = getattr(soul, "_access_log", {}) or {}
        today = date.today()
        
        for path, info in access_log.items():
            # 🛡️ Skip protected paths — core identity never archives
            if is_protected_path(path):
                continue
            
            last_access = info.get("last_access")
            if last_access:
                try:
                    last_date = date.fromisoformat(last_access)
                    days_stale = (today - last_date).days
                    if days_stale > threshold_days:
                        stale_paths.append(path)
                except ValueError:
                    pass
        
        if not dry_run and stale_paths:
            for path in stale_paths:
                self._move_to_archive(path)
            log.api(f"🗄️ Archived {len(stale_paths)} stale keys")
        
        return stale_paths
    
    def _move_to_archive(self, path: str):
        """Move a key to _archive section (conservative forgetting)."""
        value = self.get_dynamic(path, track_access=False)
        if value is None:
            return
        
        soul = self.get_soul()
        
        # Ensure _archive exists
        if not hasattr(soul, "_archive") or soul._archive is None:
            soul._archive = {}
        
        # Store with timestamp
        soul._archive[path] = {
            "value": value,
            "archived_at": datetime.now().isoformat(),
            "reason": "stale"
        }
        
        # Remove from main soul (but keep in archive)
        self._delete_path(path)
        self._has_changes = True
        log.debug(f"📦 Archived: {path}")
    
    def _get_from_archive(self, path: str) -> Any:
        """Retrieve a value from archive if it exists."""
        soul = self.get_soul()
        archive = getattr(soul, "_archive", {}) or {}
        
        if path in archive:
            return archive[path].get("value")
        return None
    
    def restore_from_archive(self, path: str) -> bool:
        """
        Restore a key from archive back to main soul.
        
        Returns:
            True if restored, False if not found
        """
        soul = self.get_soul()
        archive = getattr(soul, "_archive", {}) or {}
        
        if path not in archive:
            return False
        
        value = archive[path].get("value")
        self.update_dynamic(path, value)
        
        # Remove from archive
        del soul._archive[path]
        log.api(f"📤 Restored from archive: {path}")
        return True
    
    def _delete_path(self, path: str):
        """Delete a path from soul (internal use only)."""
        soul = self.get_soul()
        parts = path.split(".")
        
        current = soul.__dict__
        for part in parts[:-1]:
            if isinstance(current, dict):
                current = current.get(part, {})
            else:
                return
        
        final_key = parts[-1]
        if isinstance(current, dict) and final_key in current:
            del current[final_key]
    
    def get_governance_stats(self) -> dict:
        """Get stats about soul size and governance limits."""
        soul = self.get_soul()
        soul_dict = soul.model_dump()
        
        from .soul_limits import count_keys
        
        total_keys = count_keys(soul_dict)
        archive_size = len(getattr(soul, "_archive", {}) or {})
        access_log_size = len(getattr(soul, "_access_log", {}) or {})
        
        return {
            "total_keys": total_keys,
            "max_keys": SOUL_LIMITS.max_total_keys,
            "usage_percent": round(total_keys / SOUL_LIMITS.max_total_keys * 100, 1),
            "archived_keys": archive_size,
            "tracked_paths": access_log_size,
            "strategy": FORGETTING_STRATEGY
        }

    
    # ==================== Deep Consolidation (Phase 4) ====================
    
    async def _extract_insights_via_llm(self):
        """
        Extract insights from recent conversations using LLM.
        
        Called during idle periods (>5 min no user activity).
        Uses GPU lock to prevent blocking concurrent requests.
        """
        try:
            # Import here to avoid circular dependency
            from ..memory import memory
            from ..lm import lm_client
            
            # Get recent messages (last session)
            recent_messages = await self._get_recent_messages(memory, limit=20)
            if not recent_messages:
                log.debug("🧠 No recent messages for consolidation")
                return
            
            # Build consolidation prompt
            conversation_text = "\n".join([
                f"{m['role'].upper()}: {m['content'][:200]}"
                for m in recent_messages
            ])
            
            prompt = f"""Analyze this conversation and extract 1-3 key insights about the user's preferences, goals, or communication style.

CONVERSATION:
{conversation_text}

OUTPUT FORMAT (JSON array of strings):
["insight 1", "insight 2"]

Only output the JSON array, nothing else. Focus on actionable patterns."""

            # Call LLM with lock (GPU protection)
            async with self._llm_lock:
                response = await lm_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
            
            # Parse insights
            if response:
                content = response.strip()
                # Try to extract JSON array
                if content.startswith("["):
                    import json
                    try:
                        insights = json.loads(content)
                        for insight in insights:
                            if isinstance(insight, str) and len(insight) > 10:
                                self.add_insight(insight)
                        log.api(f"🧠 Consolidation extracted {len(insights)} insights")
                    except json.JSONDecodeError:
                        log.debug("🧠 Consolidation: invalid JSON response")
                        
        except Exception as e:
            log.error(f"🧠 Consolidation failed: {e}")
    
    async def _get_recent_messages(self, memory, limit: int = 20) -> list:
        """Get recent messages from memory for consolidation."""
        try:
            # Get last conversation
            conversations = await memory.list_conversations(limit=1)
            if not conversations:
                return []
            
            conv_id = conversations[0].id
            messages = await memory.get_conversation_messages(conv_id, limit=limit)
            
            return [
                {"role": m.role, "content": m.content}
                for m in messages
            ]
        except Exception as e:
            log.error(f"Failed to get recent messages: {e}")
            return []


# Global singleton instance
soul_manager = SoulManager()
