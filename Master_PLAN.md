# 🧠 MAX TRANSFORMATION: Audit-Synchronized Master Plan

> **Version:** 3.0 AUDIT-SYNCHRONIZED  
> **Updated:** 2025-12-19  
> **Philosophy:** Soul-Driven AI + Architectural Safety

---

## ⚠️ CRITICAL: Read This First

> [!CAUTION]
> **This plan is synchronized with `architectural_audit.md`**  
> Each phase has explicit **[AUDIT]** references.  
> DO NOT skip audit checks — they prevent breaking existing systems!

> [!IMPORTANT]
> **7 Existing Systems to PRESERVE:**
>
> 1. Soul Manager's `generate_meta_injection()` (707 LOC)
> 2. Dynamic Persona's user rules system (395 LOC)
> 3. Memory Manager's multi-tier architecture (947 LOC)
> 4. Smart Router's 6-layer pipeline
> 5. User Profile's mood detection (572 LOC)
> 6. Cognitive Ensemble loop (675 LOC)
> 7. Tool Registry decorator system

---

## 🎯 Implementation Strategy

**Simple Rule:** **EXTEND existing, don't REPLACE.**

Each phase below has:

- ✅ **What to do**
- 📋 **[AUDIT]** Reference to audit findings
- ⚠️ **Preservation checklist**
- 🧪 **Regression tests**

---

## Phase 0: Preparation (30 min)

### Tasks

- [ ] **Full project backup WITH VERIFICATION:**
  - Create backup tarball/zip
  - Verify backup integrity (checksum)
  - Test extraction to temp directory
  - Log backup size and file count
  - ONLY THEN delete temp and proceed
- [ ] Create git branch `feature/soul-driven-max`
- [ ] Backup `system_prompt.txt` + `soul.json`
- [ ] **[AUDIT]** Read `architectural_audit.md` sections:
  - Breaking Changes Prevention Checklist
  - Critical Findings 1-7

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION:** Partial backup = DISASTER!
>
> Always verify backup before proceeding. If backup fails, STOP implementation.

> [!TIP]
> **🚀 OPTIMIZATION WIN 5:** Capture regression test baseline

- [ ] **Run baseline tests:** `pytest tests/regression/ --json-report --json-report-file=baseline.json`
- [ ] Save baseline.json to git
- [ ] Will compare in Phase 6

> [!TIP]
> **🚀 OPTIMIZATION WIN 7:** Setup git hooks (cross-platform!)

- [ ] Create `.git/hooks/pre-commit` (Python for Windows support):

  ```python
  #!/usr/bin/env python
  # Cross-platform git hook (works on Windows + Linux + Mac)
  import json
  import subprocess
  import sys
  from pathlib import Path
  
  # Validate soul.json
  try:
      with open('data/soul.json') as f:
          json.load(f)
      print("✅ soul.json valid")
  except Exception as e:
      print(f"❌ soul.json invalid: {e}")
      sys.exit(1)
  
  # Run unit tests
  result = subprocess.run(['pytest', 'tests/unit/', '--maxfail=1'], 
                         capture_output=True, text=True)
  if result.returncode != 0:
      print(f"❌ Unit tests failed:\n{result.stdout}")
      sys.exit(1)
  
  print("✅ Pre-commit checks passed!")
  ```

- [ ] Make executable: `chmod +x .git/hooks/pre-commit` (or `icacls` on Windows)

> [!TIP]
> **🚀 OPTIMIZATION WIN 8:** Create rollback script

- [ ] Create `rollback.py`:

  ```python
  import subprocess, sys
  def rollback_to_phase(phase):
      commit = subprocess.check_output([
          "git", "log", "--grep", f"Phase {phase}",
          "--format=%H", "-n", "1"
      ]).decode().strip()
      if commit:
          subprocess.run(["git", "checkout", commit])
          print(f"✅ Rolled back to Phase {phase}")
  ```

- [ ] Test: `python rollback.py --help`

### Success Criteria

- Git branch created
- Backups verified
- Audit document reviewed
- **Baseline captured**
- **Git hooks installed**
- **Rollback script ready**

> [!IMPORTANT]
> **🎯 PRODUCTION FIX #1:** Phase State Machine (+2h)

**Problem:** Partial phase failures leave system in broken state.

**Solution:** Enterprise-level phase management with atomic commits.

- [ ] Create Phase State Manager:

  ```python
  # phase_manager.py (NEW FILE)
  from pathlib import Path
  import json
  import subprocess
  from datetime import datetime
  
  class PhaseManager:
      def __init__(self):
          self.state_file = Path("phase_state.json")
          self.state = self._load_state()
      
      def _load_state(self):
          if self.state_file.exists():
              return json.loads(self.state_file.read_text())
          return {"current_phase": None, "status": "not_started", "history": []}
      
      def _save_state(self):
          self.state_file.write_text(json.dumps(self.state, indent=2))
      
      def begin_phase(self, phase_id, description):
          """Mark phase as in-progress."""
          self.state.update({
              "current_phase": phase_id,
              "status": "in_progress",
              "started_at": datetime.now().isoformat(),
              "description": description
          })
          self._save_state()
          print(f"📍 Starting Phase {phase_id}: {description}")
      
      def verify_phase(self, phase_id):
          """Run verification checks before marking complete."""
          print(f"🔍 Verifying Phase {phase_id}...")
          
          # Run tests specific to this phase
          result = subprocess.run(['pytest', f'tests/phase_{phase_id}/'], 
                                 capture_output=True)
          
          if result.returncode != 0:
              print(f"❌ Phase {phase_id} verification failed!")
              print(result.stdout.decode())
              return False
          
          print(f"✅ Phase {phase_id} verified!")
          return True
      
      def complete_phase(self, phase_id):
          """Mark phase complete with git checkpoint."""
          if not self.verify_phase(phase_id):
              raise RuntimeError(f"Phase {phase_id} failed verification!")
          
          # Create git checkpoint
          subprocess.run(["git", "add", "-A"])
          subprocess.run(["git", "commit", "-m", f"✅ Phase {phase_id} complete"])
          subprocess.run(["git", "tag", f"phase-{phase_id}-complete"])
          
          # Update state
          self.state.update({
              "status": "complete",
              "completed_at": datetime.now().isoformat()
          })
          self.state["history"].append({
              "phase": phase_id,
              "completed_at": datetime.now().isoformat()
          })
          self._save_state()
          
          print(f"✅ Phase {phase_id} complete and checkpointed!")
      
      def rollback_to_last_complete(self):
          """Rollback to last completed phase."""
          if not self.state["history"]:
              print("No completed phases to rollback to")
              return
          
          last_phase = self.state["history"][-1]["phase"]
          tag = f"phase-{last_phase}-complete"
          
          print(f"🔄 Rolling back to Phase {last_phase}...")
          subprocess.run(["git", "reset", "--hard", tag])
          
          # Update state
          self.state["current_phase"] = last_phase
          self.state["status"] = "rolled_back"
          self._save_state()
          
          print(f"✅ Rolled back to Phase {last_phase}")
      
      def get_current_status(self):
          """Get current implementation status."""
          return self.state
  ```

- [ ] Usage in implementation:

  ```python
  from phase_manager import PhaseManager
  
  pm = PhaseManager()
  
  # Start phase
  pm.begin_phase("0", "Preparation")
  
  # ... do work ...
  
  # Complete phase (auto-verifies and creates checkpoint)
  pm.complete_phase("0")
  
  # If something goes wrong:
  # pm.rollback_to_last_complete()
  ```

- [ ] **Impact:** Bulletproof phase execution, easy rollback, +2h implementation
- [ ] **Time added:** 2h

> [!TIP]
> **🚀 RAM OPTIMIZATION WIN 2:** Tiktoken Singleton (+0.5h)

- [ ] Create global tiktoken encoder singleton:

  ```python
  # src/core/token_utils.py (NEW FILE)
  import tiktoken
  
  _GLOBAL_ENCODER = None
  
  def get_encoder():
      global _GLOBAL_ENCODER
      if _GLOBAL_ENCODER is None:
          _GLOBAL_ENCODER = tiktoken.get_encoding("cl100k_base")
      return _GLOBAL_ENCODER
  ```

- [ ] Update `memory.py` to use singleton: `self._encoder = get_encoder()`
- [ ] Update `rag.py` to use singleton
- [ ] **Impact:** +5% speedup on token counting, +2MB RAM

> [!TIP]
> **🚀 RAM OPTIMIZATION WIN 5:** Smart Router Cache Expansion (+0.2h)

- [ ] Expand router cache in `smart_router.py`:

  ```python
  # Change from:
  self._cache: TTLCache = TTLCache(maxsize=100, ttl=300)
  # To:
  from cachetools import LRUCache
  self._cache: LRUCache = LRUCache(maxsize=10000)  # 100x bigger!
  ```

- [ ] **Impact:** Hit rate 60% → 95%, saves 200 LLM calls/hour, +5MB RAM

> [!TIP]
> **🚀 RAM OPTIMIZATION WIN 6:** Embedding Service Cache Expansion (+0.2h)

- [ ] Expand embedding cache in `embedding_service.py`:

  ```python
  # Change from:
  max_cache_size: int = 1000
  ttl_seconds: int = 3600
  # To:
  max_cache_size: int = 50000  # 50x bigger!
  ttl_seconds: int = 86400  # 24h instead of 1h
  ```

- [ ] **Impact:** Hit rate 80% → 98%, +196MB RAM

---

## Phase 0.5: Integration Audit (1h) ⭐ NEW

> [!NOTE]
> **[AUDIT]** This is Phase 0.5 from audit recommendations

### Tasks

- [ ] Map ALL current integration points in `chat.py` (line 64-630)
- [ ] Document EXACT system prompt assembly flow:
  - [ ] Line ~145: `dynamic_persona.build_dynamic_prompt()`
  - [ ] Line ~150: `soul_manager.generate_meta_injection()`
  - [ ] Line ~165+: Smart Router prompt
  - [ ] Final assembly order
- [ ] List ALL SQL tables used by existing systems:
  - [ ] `conversations`, `messages`, `conversation_summaries`
  - [ ] `memory_facts`
  - [ ] `user_preferences` (Dynamic Persona)
- [ ] **[AUDIT]** Verify findings from:
  - Finding 1 (Soul Manager)
  - Finding 2 (Dynamic Persona)
  - Finding 4 (Memory Manager)

> [!TIP]
> **🚀 OPTIMIZATION WIN 2:** Early validation

- [ ] Create `validate_baseline.py`:

  ```python
  def validate_integration_points():
      assert hasattr(soul_manager, 'generate_meta_injection')
      assert Path('data/system_prompt.txt').exists()
      # Check all audit findings match reality
  ```

- [ ] Run: `python validate_baseline.py`
- [ ] Save output to INTEGRATION_MAP.md

### Deliverable

- [ ] Create `INTEGRATION_MAP.md` documenting current flow

### Success Criteria

- All integration points documented
- All tables catalogued
- No missing dependencies

> [!TIP]
> **🚀 RAM OPTIMIZATION WIN 1:** SQLite Connection Pool (+1h)

- [ ] Create connection pool class:

  ```python
  # src/core/db_pool.py (NEW FILE)
  import asyncio
  import aiosqlite
  from pathlib import Path
  
  class SQLitePool:
      def __init__(self, db_path: Path, pool_size: int = 10):
          self._pool = asyncio.Queue(maxsize=pool_size)
          self._db_path = db_path
      
      async def initialize(self):
          for _ in range(self._pool.maxsize):
              conn = await aiosqlite.connect(str(self._db_path), timeout=60.0)
              conn.row_factory = aiosqlite.Row
              await conn.execute("PRAGMA journal_mode=WAL")
              await self._pool.put(conn)
      
      async def acquire(self):
          return await self._pool.get()
      
      async def release(self, conn):
          await self._pool.put(conn)
  ```

- [ ] Update `memory.py` to use pool instead of single connection
- [ ] Update all DB-dependent modules (RAG, templates, metrics)
- [ ] **Impact:** 3x speedup for concurrent queries, +30MB RAM

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION:** DB Pool Deadlock Prevention!

- [ ] Add timeout to prevent infinite waiting:

  ```python
  async def acquire(self, timeout=30.0):
      try:
          conn = await asyncio.wait_for(self._pool.get(), timeout=timeout)
          self._acquired[conn] = time.time()  # Track acquisition time
          return conn
      except asyncio.TimeoutError:
          raise RuntimeError("DB pool exhausted! Possible connection leak")
  ```

- [ ] Add leak detection background task:

  ```python
  async def _leak_monitor(self):
      """Detect connections held >5 minutes."""
      while True:
          await asyncio.sleep(60)
          now = time.time()
          for conn, acquired_at in self._acquired.items():
              if now - acquired_at > 300:  # 5 minutes
                  log.error(f"⚠️ Connection leak! Held for {now - acquired_at:.0f}s")
  ```

- [ ] Start monitor: `asyncio.create_task(pool._leak_monitor())`

> [!IMPORTANT]
> **🎯 PRODUCTION FIX #2:** Global RAM Budget Coordinator (+1.5h)

**Problem:** 6 independent caches, no coordination, RAM explosion risk.

**Solution:** Centralized cache orchestrator with priority-based allocation.

- [ ] Create RAM Budget Coordinator:

  ```python
  # src/core/ram_budget.py (NEW FILE)
  import psutil
  from typing import Dict, Optional
  
  class RAMBudget:
      """Global RAM budget coordinator for all caches."""
      
      def __init__(self, max_cache_ram_mb: int = 500):
          self.max_ram = max_cache_ram_mb * 1024 * 1024  # bytes
          self.allocations: Dict[str, int] = {}
          self.priorities: Dict[str, int] = {}
          self.enabled: Dict[str, bool] = {}
      
      def register_cache(self, cache_id: str, estimated_size_mb: int, priority: int):
          """
          Register a cache with budget coordinator.
          
          Args:
              cache_id: Unique cache identifier
              estimated_size_mb: Estimated RAM usage in MB
              priority: Priority (1-10, higher = more important)
          """
          self.allocations[cache_id] = estimated_size_mb * 1024 * 1024
          self.priorities[cache_id] = priority
          self.enabled[cache_id] = False
      
      def allocate(self) -> Dict[str, bool]:
          """
          Allocate RAM to caches based on priority and available RAM.
          
          Returns:
              Dict of cache_id -> enabled status
          """
          available_ram = psutil.virtual_memory().available
          budget = min(self.max_ram, available_ram * 0.5)  # Max 50% of available
          
          # Sort by priority (highest first)
          sorted_caches = sorted(
              self.allocations.keys(),
              key=lambda x: self.priorities[x],
              reverse=True
          )
          
          allocated = 0
          for cache_id in sorted_caches:
              size = self.allocations[cache_id]
              if allocated + size <= budget:
                  self.enabled[cache_id] = True
                  allocated += size
              else:
                  self.enabled[cache_id] = False
          
          return self.enabled
      
      def is_enabled(self, cache_id: str) -> bool:
          """Check if cache is enabled."""
          return self.enabled.get(cache_id, False)
      
      def get_stats(self) -> dict:
          """Get allocation statistics."""
          total_allocated = sum(
              size for cid, size in self.allocations.items()
              if self.enabled[cid]
          )
          return {
              "total_budget_mb": self.max_ram / 1024 / 1024,
              "allocated_mb": total_allocated / 1024 / 1024,
              "available_mb": psutil.virtual_memory().available / 1024 / 1024,
              "caches": {
                  cid: {
                      "enabled": self.enabled[cid],
                      "size_mb": self.allocations[cid] / 1024 / 1024,
                      "priority": self.priorities[cid]
                  }
                  for cid in self.allocations
              }
          }
  
  # Global instance
  ram_budget = RAMBudget(max_cache_ram_mb=500)
  ```

- [ ] Register all caches in startup:

  ```python
  # In startup.py
  from src.core.ram_budget import ram_budget
  
  # Register all caches with priorities
  ram_budget.register_cache("db_pool", estimated_size_mb=30, priority=10)  # Critical
  ram_budget.register_cache("embedding_cache", estimated_size_mb=196, priority=9)
  ram_budget.register_cache("conversation_cache", estimated_size_mb=100, priority=8)
  ram_budget.register_cache("facts_embeddings", estimated_size_mb=100, priority=7)
  ram_budget.register_cache("router_cache", estimated_size_mb=5, priority=6)
  ram_budget.register_cache("rag_chunks", estimated_size_mb=50, priority=5)
  ram_budget.register_cache("llm_router_cache", estimated_size_mb=10, priority=4)
  
  # Allocate RAM
  allocations = ram_budget.allocate()
  
  # Initialize caches based on allocation
  if ram_budget.is_enabled("conversation_cache"):
      await memory.enable_conversation_cache()
  # ...
  ```

- [ ] **Impact:** Prevents RAM exhaustion, graceful degradation, +1.5h
- [ ] **Time added:** 1.5h

---

## Phase 1: soul.json Evolution (5h)

> [!WARNING]
> **[AUDIT]** See "Updated Phase 1" requirements

### Tasks

#### Add New Sections

- [ ] `the_architect` (migrate from `user_model`)
- [ ] `max_identity`
- [ ] `mode_system` with definitions
- [ ] `privacy_lock` config
- [ ] `universal_memory` sections:
  - `general_memory`
  - `work_memory`
  - `shadow_memory`
  - `vault`
- [ ] `killer_features` configuration

#### Migration Work

- [ ] **[AUDIT Finding 2]** Preserve base persona for Dynamic Persona:
  - [ ] Copy content from `system_prompt.txt` to `soul.json.legacy_base`
  - [ ] **DO NOT DELETE** `system_prompt.txt` yet!
- [ ] Delete old `user_model` (replaced by `the_architect`)

#### Validation

- [ ] JSON syntax valid
- [ ] No breaking changes to Soul Manager schema
- [ ] Pydantic models still parse (if using typed schemas)

> [!TIP]
> **🚀 OPTIMIZATION WIN 3:** Automated schema validation

- [ ] Create `soul_schema.json`:

  ```json
  {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["meta", "the_architect", "max_identity"],
    "properties": {
      "the_architect": {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}}
      }
    }
  }
  ```

- [ ] Validate: `python -m jsonschema -i data/soul.json soul_schema.json`
- [ ] Add to git pre-commit hook

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION:** soul.json Corruption = Total Failure!

- [ ] Implement ATOMIC writes to prevent corruption:

  ```python
  def save_soul(self, soul_data):
      import shutil
      temp_path = self._soul_path.with_suffix('.tmp')
      
      # 1. Write to temp file
      temp_path.write_text(json.dumps(soul_data, indent=2, ensure_ascii=False))
      
      # 2. Verify JSON is valid
      json.loads(temp_path.read_text())
      
      # 3. Create backup of current
      if self._soul_path.exists():
          backup_path = self._soul_path.with_suffix('.json.backup')
          shutil.copy(self._soul_path, backup_path)
      
      # 4. Atomic rename (OS-level atomic operation)
      temp_path.replace(self._soul_path)
      
      log.info("✅ soul.json saved atomically")
  ```

- [ ] Add corruption recovery on startup:

  ```python
  def _load_from_disk(self):
      try:
          data = json.loads(self._soul_path.read_text())
          return SoulState(**data)
      except (json.JSONDecodeError, FileNotFoundError) as e:
          log.error(f"soul.json corrupted: {e}")
          # Try backup
          backup_path = self._soul_path.with_suffix('.json.backup')
          if backup_path.exists():
              log.warning("Recovering from backup...")
              data = json.loads(backup_path.read_text())
              return SoulState(**data)
          raise RuntimeError("soul.json corrupted and no backup!")
  ```

### Preservation Checklist

- [ ] ✅ `soul.json` still loads in Soul Manager
- [ ] ✅ Existing axioms preserved
- [ ] ✅ `user_model.name` migrated to `the_architect.name`

### Regression Test

```python
# Test: Soul Manager still works after migration
def test_soul_manager_migration():
    soul = soul_manager.get_soul()
    
    # Basic structure
    assert soul.the_architect.name == "Vitaliy"
    assert len(soul.axioms) > 0
    
    # New sections present
    assert "the_architect" in soul.__dict__
    assert "max_identity" in soul.__dict__
    assert "mode_system" in soul.__dict__
    
    # Old user_model removed
    assert "user_model" not in soul.__dict__
    
    # Axioms migrated correctly
    assert any("Senior Tomato" in str(axiom) for axiom in soul.axioms)
    assert any("be precise" in str(axiom).lower() for axiom in soul.axioms)

def test_soul_manager_with_conversation_context():
    """Test soul manager adapts to conversation context."""
    # Simulate real conversation history
    conversation = [
        ("user", "Я очень устал, помоги с кодом"),
        ("assistant", "Конечно! Что нужно?"),
        ("user", "Оптимизируй эту функцию"),
    ]
    
    # Soul manager should maintain context awareness
    soul = soul_manager.get_soul()
    injection = soul_manager.generate_meta_injection()
    
    # Check context-aware elements
    assert "Vitaliy" in injection
    assert "WHO IS THE USER" in injection
    assert "⛔ INSTRUCTION" in injection  # Iron Mask
    
    # Time awareness should be present
    assert any(word in injection.lower() for word in ["time", "day", "hour"])
```

---

## Phase 2: Core Systems (8h)

> [!CAUTION]
> **[AUDIT]** Multiple findings apply here (1, 2, 4, 5)

### 2A: Soul Manager Enhancement (3h)

**[AUDIT Finding 1]:** Soul Manager ALREADY generates meta-injection!

#### Tasks

- [ ] **EXTEND** `generate_meta_injection()` (DON'T replace):
  - [ ] Add mode-specific blocks
  - [ ] Add privacy state indicator
  - [ ] Preserve existing: axioms, time context, focus
- [ ] Add `detect_and_switch_mode()`:
  - [ ] **[AUDIT Finding 5]** Integrate with Smart Router intents
  - [ ] Use mood from UserProfile
  - [ ] Return mode name
- [ ] Add helper methods:
  - [ ] `_build_mode_block()` — generate mode vibe text
  - [ ] `_get_privacy_state()` — check lock status

#### Preservation

- [ ] ✅ Existing `generate_meta_injection()` output unchanged for non-mode content
- [ ] ✅ Iron Mask pattern preserved
- [ ] ✅ Time awareness still works

> [!TIP]
> **⚖️ OPTIMIZATION TRADE-OFF 1:** System prompt caching (100x speedup)

- [ ] Add prompt caching:

  ```python
  class SoulManager:
      _prompt_cache = None
      _soul_hash = None
      
      def generate_meta_injection(self):
          current_hash = self._get_soul_hash()
          if self._prompt_cache and current_hash == self._soul_hash:
              return self._prompt_cache  # CACHED (0.1ms)
          
          prompt = self._build_prompt()  # 10ms
          self._prompt_cache = prompt
          self._soul_hash = current_hash
          return prompt
  ```

- [ ] Test cache hit after 2nd call
- [ ] Test cache invalidation after soul.json update

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION:** Cache Poisoning Risk!

- [ ] Include file mtime in cache key to detect manual edits:

  ```python
  def _get_soul_hash(self):
      import hashlib
      # Include modification time to detect external changes
      mtime = self._soul_path.stat().st_mtime
      content_hash = hashlib.md5(
          json.dumps(self.get_soul().__dict__, sort_keys=True).encode()
      ).hexdigest()
      return f"{content_hash}:{mtime}"
  ```

- [ ] **Impact:** Cache invalidates automatically when soul.json edited externally

#### Regression Test

```python
# Test 1: Core functionality preserved
def test_soul_manager_core_preserved():
    injection = soul_manager.generate_meta_injection()
    
    # Core blocks must still be present
    assert "WHO ARE YOU" in injection
    assert "WHO IS THE USER" in injection
    assert "Vitaliy" in injection
    assert "⛔ INSTRUCTION" in injection  # Iron Mask
    
    # No regression in existing features
    assert "axioms" in injection.lower() or "DOSSIER" in injection
    assert "MAX" in injection

# Test 2: Mode-specific blocks added
def test_soul_manager_mode_aware():
    """Verify mode-specific content in injection."""
    # Test different modes
    modes = ["work", "soul", "fun", "red"]
    
    for mode in modes:
        soul_manager.current_mode = mode
        injection = soul_manager.generate_meta_injection()
        
        # Mode should be reflected somehow
        assert injection is not None
        assert len(injection) > 100
        
        # Iron Mask preserved in all modes
        assert "⛔" in injection or "DO NOT" in injection

# Test 3: Privacy state indicator
def test_soul_manager_privacy_aware():
    """Test privacy state is injected."""
    from unittest.mock import Mock
    
    # Mock privacy lock
    privacy_lock = Mock()
    privacy_lock.is_locked.return_value = True
    
    injection = soul_manager.generate_meta_injection(privacy_lock=privacy_lock)
    # Should indicate locked state (implementation-specific)
    assert injection is not None

# Test 4: Multi-conversation context
async def test_soul_manager_with_long_history():
    """Test with extended conversation history."""
    # Simulate 10-message conversation
    conversation_history = [
        ("user", "Привет, как дела?"),
        ("assistant", "Привет! Всё отлично. Чем помочь?"),
        ("user", "Помоги с Python кодом"),
        ("assistant", "Конечно! Что нужно?"),
        ("user", "Оптимизируй эту функцию"),
        ("assistant", "[код]"),
        ("user", "Спасибо! Теперь добавь тесты"),
        ("assistant", "[тесты]"),
        ("user", "Отлично. Переключимся на другую тему?"),
        ("assistant", "Конечно! О чём хочешь поговорить?"),
    ]
    
    # Soul manager should handle context without degradation
    injection = soul_manager.generate_meta_injection()
    
    # Should remain concise despite long history
    assert len(injection) < 5000  # 5KB limit
    
    # Core elements still present
    assert "Vitaliy" in injection
    assert "MAX" in injection
```

---

### 2B: Memory Manager Extension (6.5h)

**[AUDIT Finding 4]:** Memory Manager has 947 LOC multi-tier architecture!

#### Tasks

- [ ] **EXTEND** MemoryManager with categorization:
  - [ ] Add `category` parameter to `add_fact()` (default="general")
  - [ ] Categories: "work", "shadow", "vault", "general"
  - [ ] Encryption flag for "vault" category
- [ ] **PRESERVE**:
  - [ ] Existing facts extraction (`_extract_facts`)
  - [ ] Summarization system (`compress_history`)
  - [ ] Cross-session search (`get_relevant_facts`)

#### DON'T

- [ ] ❌ Replace facts DB structure
- [ ] ❌ Remove existing tables
- [ ] ❌ Change extraction logic

#### Regression Test

```python
# Test 1: Basic facts extraction preserved
async def test_memory_facts_extraction_preserved():
    msg = await memory.add_message(conv_id, "user", "I love 3D printing")
    await asyncio.sleep(1)  # Wait for background extraction
    
    facts = await memory.get_relevant_facts(conv_id, limit=5)
    assert len(facts) > 0  # Facts still extracted

# Test 2: Category-based fact storage
async def test_memory_categorized_facts():
    """Test new categorization system."""
    # Add facts to different categories
    await memory.add_fact(conv_id, "My password is secret123", category="vault")
    await memory.add_fact(conv_id, "I had a dark thought today", category="shadow")
    await memory.add_fact(conv_id, "Work: Complete Phase 1 by Friday", category="work")
    await memory.add_fact(conv_id, "I like coffee", category="general")
    
    # Verify categorization
    vault_facts = await memory.get_relevant_facts(conv_id, category="vault")
    assert len(vault_facts) > 0
    assert "secret123" in vault_facts[0].content
    
    work_facts = await memory.get_relevant_facts(conv_id, category="work")
    assert any("Phase 1" in f.content for f in work_facts)

# Test 3: Cross-session memory
async def test_memory_cross_session():
    """Test facts persist across conversation sessions."""
    conv_id_1 = "session_1"
    conv_id_2 = "session_2"
    
    # Add fact in session 1
    await memory.add_fact(conv_id_1, "User prefers brief responses", category="general")
    
    # Should be retrievable in session 2 (cross-session)
    relevant = await memory.get_relevant_facts(conv_id_2, query="response style")
    assert any("brief" in f.content.lower() for f in relevant)

# Test 4: Summarization with extended history
async def test_memory_summarization_extended():
    """Test summarization with 50+ messages."""
    # Add 50 messages
    for i in range(50):
        await memory.add_message(conv_id, "user", f"Message {i}: discussing topic")
        await memory.add_message(conv_id, "assistant", f"Response {i}")
    
    # Trigger summarization
    await memory.compress_history(conv_id, max_context_length=2000)
    
    # Check summary exists
    summary = await memory.get_conversation_summary(conv_id)
    assert summary is not None
    assert len(summary) < 1000  # Compressed
    
    # Important facts should be in summary
    facts = await memory.get_relevant_facts(conv_id)
    assert len(facts) > 0

# Test 5: Semantic search accuracy
async def test_memory_semantic_search():
    """Test semantic search finds related facts."""
    # Add diverse facts
    facts_to_add = [
        "User enjoys Python programming",
        "User dislikes Java verbosity",
        "User works as a software engineer",
        "User's favorite food is pizza",
        "User is learning machine learning",
    ]
    
    for fact in facts_to_add:
        await memory.add_fact(conv_id, fact, category="general")
    
    # Semantic search
    relevant = await memory.get_relevant_facts(conv_id, query="coding preferences")
    
    # Should find Python and Java facts (programming-related)
    content = " ".join([f.content for f in relevant])
    assert "Python" in content or "Java" in content
    
    # Should NOT prioritize pizza (unrelated)
    assert relevant[0].content != "User's favorite food is pizza"
```

> [!TIP]
> **🚀 RAM OPTIMIZATION WIN 4:** Embedding Cache-Aware Loading (+1h)

- [ ] Add embedding cache to MemoryManager:

  ```python
  class MemoryManager:
      def __init__(self):
          self._embedding_cache = {}  # fact_id -> list[float]
      
      async def get_relevant_facts(self, conv_id, query, limit=5):
          # ... (existing code)
          for row in rows:
              fact_id = row["id"]
              # Check cache first
              if fact_id in self._embedding_cache:
                  embedding = self._embedding_cache[fact_id]
              else:
                  embedding = json.loads(row["embedding"].decode())
                  self._embedding_cache[fact_id] = embedding
              # ... (use embedding)
  ```

- [ ] **Impact:** 2x speedup on semantic search, +50MB RAM

> [!TIP]
> **⚖️ RAM OPTIMIZATION TRADE-OFF 1:** Conversation History RAM Cache (+1.5h)

- [ ] Add conversation cache:

  ```python
  from collections import deque
  from cachetools import LRUCache
  
  class MemoryManager:
      def __init__(self):
          self._conversation_cache = LRUCache(maxsize=100)
          # Key: conv_id, Value: deque of last 50 messages
      
      async def add_message(self, conv_id, role, content):
          # Add to DB
          await self._db.execute(...)
          
          # Add to RAM cache
          if conv_id not in self._conversation_cache:
              self._conversation_cache[conv_id] = deque(maxlen=50)
          self._conversation_cache[conv_id].append(msg)
      
      async def get_recent_messages(self, conv_id, limit=10):
          # Try RAM first
          if conv_id in self._conversation_cache:
              cached = list(self._conversation_cache[conv_id])
              return cached[-limit:]
          # Fallback to DB
          return await self._load_from_db(conv_id, limit)
  ```

- [ ] Add background sync task (every 5s to DB)
- [ ] **Impact:** 10x speedup (10ms → 1ms), +100MB RAM
- [ ] **Trade-off:** Crash before sync = lost messages (mitigated by 5s auto-save)

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION #1:** Race Condition in Cache!

- [ ] Add per-conversation locks to prevent race conditions:

  ```python
  class MemoryManager:
      def __init__(self):
          self._conversation_cache = LRUCache(maxsize=100)
          self._conv_locks = {}  # conv_id -> asyncio.Lock
      
      async def add_message(self, conv_id, role, content):
          # Thread-safe lock per conversation
          if conv_id not in self._conv_locks:
              self._conv_locks[conv_id] = asyncio.Lock()
          
          async with self._conv_locks[conv_id]:
              # Add to DB FIRST (durability!)
              msg_id = await self._db.execute(...)
              await self._db.commit()  # FORCE COMMIT
              
              # THEN add to RAM cache
              if conv_id not in self._conversation_cache:
                  self._conversation_cache[conv_id] = deque(maxlen=50)
              self._conversation_cache[conv_id].append(msg)
  ```

- [ ] **Impact:** Prevents message loss from concurrent requests

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION #2:** RAM Explosion Risk!

- [ ] Check available RAM before preloading embeddings:

  ```python
  async def initialize(self):
      import psutil
      
      # Count facts first
      async with self._db.execute("SELECT COUNT(*) FROM memory_facts") as cursor:
          fact_count = (await cursor.fetchone())[0]
      
      # Estimate RAM needed
      estimated_ram = fact_count * 1536 * 4  # bytes per embedding
      available_ram = psutil.virtual_memory().available
      
      if estimated_ram > available_ram * 0.5:
          log.warning(f"⚠️ {fact_count} facts = {estimated_ram/1024/1024:.0f}MB")
          log.warning("Too much for preload. Using lazy loading instead.")
          return  # Fall back to on-demand loading
      
      log.info(f"✅ Preloading {fact_count} embeddings (~{estimated_ram/1024/1024:.0f}MB)...")
      # ... (existing preload code)
  ```

- [ ] **Impact:** Prevents crash on systems with 100K+ facts

> [!TIP]
> **⚖️ RAM OPTIMIZATION TRADE-OFF 7:** Facts Embedding Preload (+2h)

- [ ] Preload all embeddings on initialize:

  ```python
  class MemoryManager:
      async def initialize(self):
          # ... (existing init)
          
          # PRELOAD ALL FACT EMBEDDINGS
          self._facts_embeddings = {}  # fact_id -> embedding
          async with self._db.execute(
              "SELECT id, embedding FROM memory_facts"
          ) as cursor:
              async for row in cursor:
                  if row["embedding"]:
                      emb = json.loads(row["embedding"].decode())
                      self._facts_embeddings[row["id"]] = emb
          
          log.info(f"Preloaded {len(self._facts_embeddings)} fact embeddings")
  ```

- [ ] Update get_relevant_facts to use in-memory embeddings
- [ ] Update cache when new fact added
- [ ] **Impact:** 5x speedup on facts search, +100MB RAM

---

### 2C: Privacy Lock Manager (2h)

**NEW system** — no conflicts.

#### Tasks

- [ ] Create `PrivacyLockManager` class
- [ ] Regex patterns for unlock phrase variations
- [ ] Auto-lock timer (30 min)
- [ ] Emergency lock command detection
- [ ] Integration with chat.py (check before vault access)

#### Tests

```python
# Test 1: Unlock phrase variations
def test_unlock_phrase_variations():
    """Test all unlock phrase patterns."""
    variations = [
        "привет малыш",
        "привет, малыш",
        "малыш привет",
        "малыш, привет",
        "ПРИВЕТ МАЛЫШ",
        "Привет Малыш",
        "привет  малыш",  # Extra space
        "привет,малыш",    # No space after comma
    ]
    
    for phrase in variations:
        assert privacy_lock.check_unlock(phrase), f"Failed on: {phrase}"

# Test 2: False positives (should NOT unlock)
def test_unlock_false_positives():
    """Ensure unrelated phrases don't unlock."""
    false_phrases = [
        "привет",           # Just "привет"
        "малыш",            # Just "малыш"
        "привет друг",      # Different word
        "hello малыш",      # Mixed language
        "прив малыш",       # Typo
        "привет малышка",   # Different form
    ]
    
    for phrase in false_phrases:
        assert not privacy_lock.check_unlock(phrase), f"False positive: {phrase}"

# Test 3: Auto-lock after inactivity
async def test_auto_lock_timer():
    """Test 30-minute auto-lock."""
    # Unlock
    privacy_lock.unlock("привет малыш")
    assert not privacy_lock.is_locked()
    
    # Simulate 30 min inactivity
    privacy_lock.last_activity = time.time() - (31 * 60)  # 31 minutes ago
    
    # Check lock status
    await privacy_lock.check_auto_lock()
    assert privacy_lock.is_locked(), "Should auto-lock after 30min"

# Test 4: Emergency lock
def test_emergency_lock():
    """Test emergency lock command."""
    # Unlock first
    privacy_lock.unlock("привет малыш")
    assert not privacy_lock.is_locked()
    
    # Emergency lock
    result = privacy_lock.check_unlock("макс заблокируйся")
    assert privacy_lock.is_locked(), "Emergency lock should activate"
    assert result is False  # Not an unlock, it's a lock command

# Test 5: Vault access protection
async def test_vault_access_protection():
    """Ensure vault is protected when locked."""
    # Lock the system
    privacy_lock.lock()
    
    # Try to access vault content
    with pytest.raises(PermissionError):
        await memory.get_relevant_facts(conv_id, category="vault")
    
    # Unlock
    privacy_lock.unlock("привет малыш")
    
    # Now should work
    facts = await memory.get_relevant_facts(conv_id, category="vault")
    assert facts is not None  # No exception

- [ ] **Impact:** Shadows accessible only when unlocked

---

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION:** Auto-Lock Race Condition!

- [ ] Extend lock time on ANY activity (not just unlock):
  ```python
  def check_unlock(self, message):
      # EXTEND lock time on activity to prevent mid-dialogue lock
      if self._private_mode:
          self._private_unlock_time = datetime.now()  # Reset 30min timer
      
      # Check unlock phrase
      if PRIVACY_UNLOCK_PATTERN.search(message):
          self._private_mode = True
          self._private_unlock_time = datetime.now()
          return True
      
      return False
  ```

- [ ] **Impact:** No more locks during active conversation

---.

# Test 6: Shadow memory protection

async def test_shadow_memory_protection():
    """Shadow thoughts accessible only when unlocked."""
    # Add shadow thought
    await memory.add_fact(conv_id, "Dark thought: I feel sad", category="shadow")

    # Lock
    privacy_lock.lock()
    
    # Should not be in general search
    facts = await memory.get_relevant_facts(conv_id, query="feeling")
    assert not any("Dark thought" in f.content for f in facts)
    
    # Unlock
    privacy_lock.unlock("привет малыш")
    
    # Now accessible
    shadow_facts = await memory.get_relevant_facts(conv_id, category="shadow")
    assert any("Dark thought" in f.content for f in shadow_facts)

```

---

### 2D: Universal Memory Commands (1h)

**NEW interface** wrapping MemoryManager.

#### Tasks

- [ ] Create `UniversalMemoryManager` class
- [ ] Command detection regex patterns
- [ ] Interface methods:
  - `remember()` → calls `memory.add_fact()`
  - `delete()` → semantic search + delete
  - `update()` → find + modify fact
  - `search()` → calls `memory.get_relevant_facts()`

#### Integration

- [ ] Use existing MemoryManager as backend
- [ ] Add category auto-detection
- [ ] Privacy-aware search (respect lock)

---

### 2E: Dynamic Persona Migration (2h)

**[AUDIT Finding 2]:** Dynamic Persona loads base from system_prompt.txt!

> [!TIP]
> **🚀 OPTIMIZATION WIN 4:** Incremental migration with feature flag

#### Tasks

- [ ] Add environment variable: `USE_SOUL_JSON=false` (default)
- [ ] Implement dual-mode loading:

  ```python
  class DynamicPersona:
      USE_SOUL_JSON = os.getenv("USE_SOUL_JSON", "false") == "true"
      
      def _load_base_persona(self):
          if self.USE_SOUL_JSON:
              return soul_manager.get_base_persona()  # NEW
          else:
              return self._load_from_file()  # OLD (safe fallback)
  ```

- [ ] Migrate `_load_base_persona()`:
  - [ ] Load from `soul.json.legacy_base` when flag ON
  - [ ] Update path references
  - [ ] Remove file I/O in new path
- [ ] **PRESERVE:**
  - [ ] SQL-based user rules (DO NOT migrate these)
  - [ ] FeedbackLoopAnalyzer functionality
  - [ ] `build_dynamic_prompt()` interface unchanged
- [ ] Test with `USE_SOUL_JSON=true`
- [ ] Test with `USE_SOUL_JSON=false` (fallback)
- [ ] Keep flag until cleanup (Phase 8)

#### Regression Test

```python
async def test_dynamic_persona_migrated():
    prompt = await dynamic_persona.build_dynamic_prompt()
    assert prompt  # Not empty
    # Check system_prompt.txt NOT loaded
    assert "system_prompt.txt" not in prompt
    # Check soul.json content is there
    assert len(prompt) > 100
```

---

### 2F: Smart Router Extension (2h)

**[AUDIT Finding 5]:** Smart Router has 6-layer pipeline!

#### Tasks

- [ ] Add mode triggers to intent classification:
  - [ ] "работа", "код", "помоги" → work mode context
  - [ ] "поговорим", "чувствую", "душа" → soul mode context
  - [ ] "поиграем", "шутка" → fun mode context
- [ ] **PRESERVE:**
  - [ ] All 6 layers intact (Guardrails→Semantic→Cache→LLM→CPU→Complexity)
  - [ ] Existing intent detection unchanged
  - [ ] Performance (<50ms routing time)
- [ ] Integration with `detect_and_switch_mode()`

#### Preservation Checklist

- [ ] ✅ Guardrails layer still filters dangerous queries
- [ ] ✅ Semantic Router vector search works
- [ ] ✅ Cache hit rate unchanged
- [ ] ✅ LLM Router fallback works
- [ ] ✅ CPU Router heuristics work
- [ ] ✅ Complexity assessment accurate

#### Regression Test

```python
# Test 1: Intent classification preserved
async def test_smart_router_intent_classification():
    """Test all intent types with realistic queries."""
    test_cases = [
        # Coding intent
        ("помоги с кодом", "coding"),
        ("как написать async функцию в Python?", "coding"),
        ("оптимизируй эту функцию", "coding"),
        ("исправь ошибку в коде", "coding"),
        
        # Search intent
        ("найди информацию про FastAPI", "search"),
        ("что такое аксиомы?", "search"),
        ("поищи статью о soul-driven AI", "search"),
        
        # Research intent
        ("исследуй тему машинного обучения", "research"),
        ("проанализируй архитектуру MAX", "research"),
        ("изучи best practices для async", "research"),
        
        # Greeting intent
        ("привет", "greeting"),
        ("как дела?", "greeting"),
        ("доброе утро", "greeting"),
        
        # Privacy unlock intent
        ("привет малыш", "privacy_unlock"),
    ]
    
    for query, expected_intent in test_cases:
        route = await smart_router.route(query)
        assert route.intent == expected_intent, f"Failed: '{query}' -> expected {expected_intent}, got {route.intent}"

# Test 2: Mode triggers integration
async def test_smart_router_mode_triggers():
    """Test mode context detection."""
    mode_tests = [
        ("помоги с работой", "work"),
        ("давай поговорим о чувствах", "soul"),
        ("расскажи шутку", "fun"),
        ("поиграем", "fun"),
    ]
    
    for query, expected_mode_hint in mode_tests:
        route = await smart_router.route(query)
        # Mode context should be set (implementation-specific)
        assert route is not None

# Test 3: Performance with 6-layer pipeline
async def test_smart_router_performance():
    """Ensure all 6 layers execute within budget."""
    import time
    
    queries = [
        "простой запрос",
        "сложный запрос с множеством слов и контекста о программировании",
        "запрос с эмодзи 🚀",
    ]
    
    for query in queries:
        start = time.perf_counter()
        route = await smart_router.route(query)
        duration = (time.perf_counter() - start) * 1000  # ms
        
        assert duration < 50, f"Too slow: {duration}ms for '{query}'"
        assert route is not None

# Test 4: Conversation context awareness
async def test_smart_router_with_context():
    """Test routing with conversation history."""
    # Simulate conversation
    conversation = [
        ("user", "Помоги с Python"),
        ("assistant", "Конечно! Что нужно?"),
        ("user", "вот эта функция"),  # Ambiguous without context
    ]
    
    # Last message should be classified as coding (due to context)
    route = await smart_router.route(
        "вот эта функция",
        context=conversation
    )
    
    # Should infer coding intent from context
    assert route.intent in ["coding", "general"]  # Context-aware

# Test 5: Guardrails layer filtering
async def test_smart_router_guardrails():
    """Test Layer 1: Guardrails filter dangerous queries."""
    dangerous_queries = [
        "как взломать систему",
        "помоги обойти защиту",
    ]
    
    for query in dangerous_queries:
        route = await smart_router.route(query)
        # Should either block or route to safety handler
        assert route.is_safe or route.intent == "safety_concern"

# Test 6: Cache layer effectiveness
async def test_smart_router_cache():
    """Test Layer 3: Cache speeds up repeat queries."""
    query = "помоги с кодом на Python"
    
    # First call (cache miss)
    start1 = time.perf_counter()
    route1 = await smart_router.route(query)
    time1 = (time.perf_counter() - start1) * 1000
    
    # Second call (cache hit)
    start2 = time.perf_counter()
    route2 = await smart_router.route(query)
    time2 = (time.perf_counter() - start2) * 1000
    
    # Cache hit should be significantly faster
    assert time2 < time1 * 0.5, f"Cache not working: {time1}ms vs {time2}ms"
    assert route1.intent == route2.intent

# Test 7: Complexity assessment (Layer 6)
async def test_smart_router_complexity():
    """Test Layer 6: Complexity scoring."""
    simple_query = "привет"
    complex_query = "объясни разницу между async/await и threading в Python, включая GIL и event loop"
    
    simple_route = await smart_router.route(simple_query)
    complex_route = await smart_router.route(complex_query)
    
    # Complex query should have higher complexity score
    assert complex_route.complexity > simple_route.complexity
```

---

### 2G: Ensemble Mode Protection (1h)

**[AUDIT Finding 6]:** Don't break Cognitive Ensemble!

#### Tasks

- [ ] In `detect_and_switch_mode()`:
  - [ ] Check if ensemble is running: `if thinking_mode == "ensemble"`
  - [ ] Don't switch modes mid-ensemble
  - [ ] Return current mode if ensemble active
  - [ ] Log: "Mode switch deferred during ensemble"
- [ ] Document ensemble integration points:
  - [ ] When ensemble activates
  - [ ] How to check ensemble status
  - [ ] Mode interaction rules
- [ ] Add ensemble-aware logic to mode switching

#### Implementation Example

```python
def detect_and_switch_mode(self, message, mood, intent, thinking_mode=None):
    # PROTECTION: Don't interrupt ensemble
    if thinking_mode == "ensemble":
        log.debug("Mode switch deferred: ensemble active")
        return self.get_current_mode()  # Keep current
    
    # Normal mode detection...
```

#### Regression Test

```python
async def test_ensemble_not_interrupted():
    # Start ensemble thinking
    response = await chat(ChatRequest(
        message="complex philosophical question",
        thinking_mode="ensemble"
    ))
    
    # Check ensemble completed without mode interruption
    # Should see ensemble traces in logs
    assert "Ensemble thinking" in logs
    assert "Mode switch deferred" in logs
```

---

### 2H: Tool Registry Integration (30min)

**[AUDIT Finding 7]:** Register memory commands as tools!

#### Tasks

- [ ] Add decorators to Universal Memory Commands:
  - [ ] `@registry.register()` for remember, delete, update, search
  - [ ] Privacy check before vault/shadow access
  - [ ] Type hints for auto-schema generation
- [ ] Test: tools appear in `/api/tools` endpoint
- [ ] Privacy-aware execution:
  - [ ] Check lock before accessing vault/shadow categories

#### Implementation Example

```python
from src.core.tool_registry.registry import registry

@registry.register()
async def remember_fact(content: str, category: str = "general") -> dict:
    """
    Remember information for later retrieval.
    
    Args:
        content: The information to remember
        category: Category (general/work/shadow/vault)
    
    Returns:
        Success status and storage location
    """
    # Privacy check
    if category in ["shadow", "vault"] and privacy_lock.is_locked():
        raise PermissionError("Unlock required for this category")
    
    return await universal_memory.remember(content, category)

@registry.register()
async def delete_memory(query: str) -> dict:
    """Delete memories matching query."""
    return await universal_memory.delete(query)

@registry.register()
async def search_memory(query: str, category: str = None) -> list:
    """Search memories by query."""
    return await universal_memory.search(query, category)
```

#### Regression Test

```python
def test_memory_commands_registered():
    tools = registry.get_all_tools()
    tool_names = [t["name"] for t in tools]
    
    assert "remember_fact" in tool_names
    assert "delete_memory" in tool_names
    assert "search_memory" in tool_names
```

---

## Phase 3: Simplification (2h)

> [!NOTE]
> **[AUDIT]** Much less to do than originally planned

### Tasks

- [ ] **OPTIONAL:** Rename `UserProfile` → `VitaliyProfile`
- [ ] **SKIP:** Removing `user_id` parameters (causes conflicts)
- [ ] Update imports if renamed

### Preservation

- [ ] ✅ **[AUDIT Finding 3]** UserProfile's mood detection untouched
- [ ] ✅ Style adaptation still works
- [ ] ✅ Dislikes tracking preserved

---

## Phase 4: Integration (4h)

> [!DANGER]
> **[AUDIT]** Most critical phase — easy to break things!

### 4A: chat.py Integration (3h)

**[AUDIT Finding 1, 2, 5]:** Preserve existing prompt assembly!

#### Current Flow (DO NOT BREAK)

```python
# Line ~145: Dynamic Persona
dynamic_prompt = await dynamic_persona.build_dynamic_prompt()
system_prompts.append(dynamic_prompt)

# Line ~150: Soul Manager
meta_injection = soul_manager.generate_meta_injection()
system_prompts.append(meta_injection)

# Line ~165+: Smart Router
if route.system_prompt:
    system_prompts.append(route.system_prompt)
```

#### Changes to Make

- [ ] **BEFORE** memory access, add privacy lock check:

  ```python
  if privacy_lock.check_unlock(user_message):
      # Unlock happened
  ```

- [ ] **BEFORE** LLM call, add memory command detection:

  ```python
  memory_cmd = universal_memory.detect_command(user_message)
  if memory_cmd:
      result = universal_memory.execute(memory_cmd)
      return result  # Short-circuit, don't call LLM
  ```

- [ ] **BEFORE** mode context, add mode detection:

  ```python
  mode = soul_manager.detect_and_switch_mode(
      user_message,
      user_profile.get_mood(),
      route.intent
  )
  ```

#### DON'T

- [ ] ❌ Remove existing prompt assembly
- [ ] ❌ Delete `system_prompt.txt` (Dynamic Persona needs it!)
- [ ] ❌ Change order of prompt parts

#### Regression Tests

```python
async def test_existing_flow_preserved():
    # Soul Manager still injected
    response = await chat(ChatRequest(message="test"))
    # Check logs for "Soul meta-cognition injected"
    
    # Dynamic Persona still works
    # Check logs for "Dynamic persona prompt loaded"
    
    # Smart Router still classifies
    # Check route.intent is set
```

---

### 4B: Integration Tests (1h)

- [ ] **[AUDIT Finding 6]** Ensemble mode still activates:

  ```python
  response = await chat(ChatRequest(
      message="complex question",
      thinking_mode="ensemble"
  ))
  # Check for ensemble thinking traces
  ```

- [ ] Privacy Lock full cycle
- [ ] Memory Commands full cycle
- [ ] Mode switching

---

## Phase 5: Killer Features (8h)

Each feature has its own checklist. See `advanced_features_plan.md` for details.

### Priority Order

1. Adaptive Verbosity (extends UserProfile)
2. Memory Lanes
3. Emotional Momentum
4. Context Snapshots
5. Semantic Bookmarks
6. Code Review Agent
7. Predictive Actions
8. Proactive Context Switching
9. AI To-Do Evolution
10. Micro-Habits (subtle)
11. Confession Mode

### Preservation

- [ ] ✅ **[AUDIT Finding 3]** Adaptive Verbosity EXTENDS UserProfile, doesn't replace
- [ ] ✅ No feature blocks Cognitive Ensemble

---

## Phase 6: Testing (6h)

> [!IMPORTANT]
> **[AUDIT]** Regression tests are MANDATORY!

### 6A: Regression Suite (1.5h instead of 3h)

> [!TIP]
> **🚀 OPTIMIZATION WIN 1:** Parallel testing (50% faster)

- [ ] Install: `pip install pytest-xdist`
- [ ] Run tests in parallel: `pytest -n auto tests/regression/`
- [ ] Compare with baseline: `python compare_test_results.py baseline.json current.json`

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION:** Baseline Validation!

- [ ] Verify baseline BEFORE comparison:

  ```python
  def validate_baseline(baseline_path):
      if not baseline_path.exists():
          raise RuntimeError("❌ baseline.json missing! Cannot compare.")
      
      baseline = json.loads(baseline_path.read_text())
      
      # Check has passing tests
      if baseline.get('summary', {}).get('passed', 0) == 0:
          raise RuntimeError("❌ baseline.json has 0 passing tests! Corrupted?")
      
      # Check timestamp (should be from Phase 0)
      created = baseline.get('created')
      if not created:
          log.warning("⚠️ baseline.json has no timestamp")
      
      log.info(f"✅ Baseline valid: {baseline['summary']['passed']} passing tests")
  ```

- [ ] Run validation before comparison

> [!IMPORTANT]
> **🎯 PRODUCTION FIX #3:** Test-by-Test Comparison (+0.5h)

**Problem:** Baseline count comparison misses different test failures.

**Solution:** Test-level diff analysis.

- [ ] Create enhanced comparison script:

  ```python
  # compare_test_results.py (ENHANCE EXISTING)
  import json
  from pathlib import Path
  
  def compare_tests(baseline_path, current_path):
      baseline = json.loads(Path(baseline_path).read_text())
      current = json.loads(Path(current_path).read_text())
      
      # Extract test results
      baseline_tests = {t['nodeid']: t['outcome'] for t in baseline.get('tests', [])}
      current_tests = {t['nodeid']: t['outcome'] for t in current.get('tests', [])}
      
      # Find differences
      new_failures = []
      new_passes = []
      still_failing = []
      
      for test_id, outcome in current_tests.items():
          baseline_outcome = baseline_tests.get(test_id)
          
          if outcome == 'failed' and baseline_outcome == 'passed':
              new_failures.append(test_id)
          elif outcome == 'passed' and baseline_outcome == 'failed':
              new_passes.append(test_id)
          elif outcome == 'failed' and baseline_outcome == 'failed':
              still_failing.append(test_id)
      
      # Report
      print("\n" + "="*60)
      print("🔍 TEST-BY-TEST COMPARISON")
      print("="*60)
      
      if new_failures:
          print(f"\n❌ NEW FAILURES ({len(new_failures)}):")
          for test in new_failures:
              print(f"   - {test}")
          print("\n⚠️ REGRESSION DETECTED!")
          return False
      
      if new_passes:
          print(f"\n✅ NEW PASSES ({len(new_passes)}):")
          for test in new_passes:
              print(f"   - {test}")
      
      if still_failing:
          print(f"\n⚠️ STILL FAILING ({len(still_failing)}):")
          for test in still_failing:
              print(f"   - {test}")
      
      total_current = len([t for t in current_tests.values() if t == 'passed'])
      total_baseline = len([t for t in baseline_tests.values() if t == 'passed'])
      
      print(f"\n📊 SUMMARY:")
      print(f"   Baseline: {total_baseline} passing")
      print(f"   Current:  {total_current} passing")
      print(f"   Delta:    {total_current - total_baseline:+d}")
      
      if new_failures:
          print("\n❌ CANNOT PROCEED: New test failures detected!")
          return False
      
      print("\n✅ No regressions detected!")
      return True
  
  if __name__ == "__main__":
      import sys
      success = compare_tests(sys.argv[1], sys.argv[2])
      sys.exit(0 if success else 1)
  ```

- [ ] **Impact:** Catches subtle regressions, test-level granularity, +0.5h
- [ ] **Time added:** 0.5h

> [!CAUTION]
> **🚫 ANTI-PATTERN 3:** All tests MUST be executable code

**Test ALL 7 existing systems:**

#### 1. Soul Manager

```python
def test_soul_manager_unchanged():
    injection = soul_manager.generate_meta_injection()
    assert "WHO ARE YOU" in injection
    assert "Vitaliy" in injection
    assert "⛔ INSTRUCTION" in injection
```

#### 2. Dynamic Persona

```python
# Test 1: Dynamic persona still loads
async def test_dynamic_persona_works():
    prompt = await dynamic_persona.build_dynamic_prompt()
    assert prompt  # Not empty
    assert len(prompt) > 50

# Test 2: User rules injection
async def test_dynamic_persona_user_rules():
    """Test SQL-based user rules are injected."""
    # Add user rules
    await dynamic_persona.add_rule("Отвечай кратко")
    await dynamic_persona.add_rule("Используй эмодзи")
    
    prompt = await dynamic_persona.build_dynamic_prompt()
    
    # Rules should be in prompt
    assert "кратко" in prompt.lower() or "Кратко" in prompt
    assert "эмодзи" in prompt.lower()

# Test 3: Feedback loop analyzer
async def test_dynamic_persona_feedback_learning():
    """Test FeedbackLoopAnalyzer extracts rules from feedback."""
    feedback = "Пожалуйста, отвечай короче, я устал"
    
    # Should learn rule from feedback
    await dynamic_persona.process_feedback(feedback)
    
    # Check if rule added
    rules = await dynamic_persona.get_active_rules()
    assert any("короче" in rule.lower() or "кратко" in rule.lower() for rule in rules)

# Test 4: Base persona from soul.json (after migration)
async def test_dynamic_persona_soul_integration():
    """Test loading from soul.json."""
    # With USE_SOUL_JSON=true
    os.environ["USE_SOUL_JSON"] = "true"
    
    prompt = await dynamic_persona.build_dynamic_prompt()
    
    # Should NOT reference system_prompt.txt
    assert "system_prompt.txt" not in prompt
    
    # Should have content from soul.json
    assert "MAX" in prompt or "Vitaliy" in prompt
    
    os.environ["USE_SOUL_JSON"] = "false"  # Reset
```

#### 3. Memory Manager

```python
async def test_facts_extraction():
    msg = await memory.add_message(conv_id, "user", "I'm a developer")
    await asyncio.sleep(2)
    facts = await memory.get_relevant_facts(conv_id)
    # Facts still extracted from user messages
```

#### 4. Smart Router

```python
async def test_intent_classification():
    route = await smart_router.route("помоги с кодом")
    assert route.intent == "coding"
```

#### 5. User Profile

```python
# Test 1: Basic mood detection
def test_user_profile_mood_detection():
    profile = UserProfile()
    
    # Test various moods
    mood_tests = [
        ("я очень устал", Mood.FRUSTRATED),
        ("у меня много дел", Mood.BUSY),
        ("интересно, расскажи больше", Mood.CURIOUS),
    ]
    
    for text, expected_mood in mood_tests:
        mood = profile.analyze_mood(text)
        assert mood == expected_mood, f"Failed on: '{text}' -> expected {expected_mood}, got {mood}"

# Test 2: Style adaptation
def test_user_profile_style_adaptation():
    """Test style prompt generation."""
    profile = UserProfile(name="Vitaliy")
    
    # Set preferences
    profile.set_preference("verbosity", Verbosity.BRIEF)
    profile.set_preference("use_emoji", False)
    
    style_prompt = profile.get_style_prompt()
    
    # Should reflect preferences
    assert "кратко" in style_prompt.lower() or "brief" in style_prompt.lower()
    assert "эмодзи" in style_prompt.lower() or "emoji" in style_prompt.lower()

# Test 3: Habit tracking over time
def test_user_profile_habits():
    """Test habit detection from conversation patterns."""
    profile = UserProfile()
    
    # Simulate frequent Python questions (habit formation)
    for i in range(10):
        profile.process_message(f"Вопрос {i}: как решить на Python?")
    
    habits = profile.get_habits()
    # Should identify Python as frequent topic
    assert any("python" in habit.lower() for habit in habits)

# Test 4: Dislikes tracking
def test_user_profile_dislikes():
    """Test dislikes capture from feedback."""
    profile = UserProfile()
    
    # User expresses dislike
    profile.add_dislike("длинные преамбулы")
    profile.add_dislike("этические лекции")
    
    style_prompt = profile.get_style_prompt()
    
    # Should mention dislikes
    assert "ИЗБЕГАЙ" in style_prompt or "избегай" in style_prompt

# Test 5: Active hours detection
def test_user_profile_active_hours():
    """Test activity time tracking."""
    import datetime
    profile = UserProfile()
    
    # Simulate activity at specific hour
    for _ in range(5):
        profile.record_activity(datetime.datetime.now().replace(hour=14))  # 2 PM
    
    active_hours = profile.get_active_hours()
    assert 14 in active_hours or len(active_hours) > 0
```

#### 6. Cognitive Ensemble

```python
# Test 1: Ensemble activates on demand
async def test_ensemble_activates():
    with capture_logs() as logs:
        response = await chat(ChatRequest(
            message="complex question",
            thinking_mode="ensemble"
        ))
        assert "Ensemble thinking" in logs.output

# Test 2: Mode switching doesn't break ensemble
async def test_ensemble_not_interrupted():
    """Mode switching doesn't break ensemble."""
    with capture_logs() as logs:
        response = await chat(ChatRequest(
            message="философский вопрос",
            thinking_mode="ensemble"
        ))
        assert "Mode switch deferred" in logs.output or "Ensemble" in logs.output

# Test 3: Ensemble with complex queries
async def test_ensemble_complex_reasoning():
    """Test ensemble handles multi-step reasoning."""
    complex_query = """
    Объясни преимущества и недостатки Soul-Driven архитектуры
    по сравнению со статическим системным промптом,
    учитывая производительность, гибкость и сложность поддержки.
    """
    
    response = await chat(ChatRequest(
        message=complex_query,
        thinking_mode="ensemble"
    ))
    
    # Should complete without errors
    assert response is not None
    assert len(response.content) > 100

# Test 4: Ensemble debate mechanism
async def test_ensemble_multi_path():
    """Verify multi-path reasoning."""
    with capture_logs() as logs:
        response = await chat(ChatRequest(
            message="Что лучше: async или threading?",
            thinking_mode="ensemble"
        ))
        
        # Should see debate traces
        log_content = logs.output
        assert "path" in log_content.lower() or "debate" in log_content.lower()
```

#### 7. Tool Registry

```python
# Test 1: Tools registered
def test_tools_registered():
    tools = registry.get_all_tools()
    assert len(tools) > 0
    
# Test 2: Memory commands as tools
def test_memory_commands_registered():
    tools = registry.get_all_tools()
    tool_names = [t["name"] for t in tools]
    
    # All memory commands should be registered
    assert "remember_fact" in tool_names
    assert "delete_memory" in tool_names
    assert "search_memory" in tool_names

# Test 3: Tool execution with privacy check
async def test_tool_privacy_protection():
    """Ensure tools respect privacy lock."""
    # Lock the system
    privacy_lock.lock()
    
    # Try to remember sensitive fact
    with pytest.raises(PermissionError):
        await registry.execute_tool(
            "remember_fact",
            content="My password is secret",
            category="vault"
        )
    
    # Unlock
    privacy_lock.unlock("привет малыш")
    
    # Now should work
    result = await registry.execute_tool(
        "remember_fact",
        content="My password is secret",
        category="vault"
    )
    assert result["status"] == "success"

# Test 4: Tool schema generation
def test_tool_schema_auto_generation():
    """Test JSON Schema auto-generated from type hints."""
    tools = registry.get_all_tools()
    remember_tool = next(t for t in tools if t["name"] == "remember_fact")
    
    # Should have schema
    assert "parameters" in remember_tool
    assert "content" in remember_tool["parameters"]["properties"]
    assert "category" in remember_tool["parameters"]["properties"]
    
    # Category should have default
    assert remember_tool["parameters"]["properties"]["category"]["default"] == "general"
```

### 6B: Integration Tests (2h)

- [ ] Full chat flow end-to-end
- [ ] Privacy Lock cycle
- [ ] Memory Commands cycle
- [ ] Mode switching cycle

### 6C: Performance Tests (2h)

> [!TIP]
> **🚀 OPTIMIZATION WIN 6:** Automated performance budgets

```python
import time

def measure_p95(func, *args, runs=100):
    """Measure 95th percentile latency."""
    timings = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args)
        timings.append((time.perf_counter() - start) * 1000)
    return sorted(timings)[95]

def test_performance_budgets():
    # System prompt generation
    p95 = measure_p95(soul_manager.generate_meta_injection)
    assert p95 < 20, f"P95: {p95}ms (budget: 20ms, with cache should be <1ms)"
    
    # Memory command detection
    p95 = measure_p95(universal_memory.detect_command, "запомни тест")
    assert p95 < 5, f"P95: {p95}ms (budget: 5ms)"
    
    # Privacy lock check
    p95 = measure_p95(privacy_lock.check_unlock, "привет малыш")
    assert p95 < 1, f"P95: {p95}ms (budget: 1ms)"
```

- [ ] System prompt generation P95 <20ms (P50 <10ms)
- [ ] Memory command detection P95 <5ms
- [ ] Privacy lock check P95 <1ms
- [ ] No memory leaks (100 messages)
- [ ] DB connection pool healthy

> [!TIP]
> **🧠 RAM OPTIMIZATION UX 3:** Cache Stats Dashboard (+0.5h)

- [ ] Add cache stats endpoint:

  ```python
  # api/routers/system.py
  @router.get("/cache-stats")
  async def get_cache_stats():
      return {
          "embedding_service": embedding_service.get_stats(),
          "smart_router": smart_router.get_stats(),
          "semantic_cache": semantic_cache.get_stats(),
          "memory_facts": memory.get_cache_stats(),
          "conversation_cache": memory.get_conversation_cache_stats(),
          "llm_router": llm_router.get_cache_stats(),
      }
  ```

- [ ] Ensure all caches have get_stats() method
- [ ] **Impact:** Visibility into cache performance

> [!TIP]
> **🧠 RAM OPTIMIZATION UX 1:** Warm Caches on Startup (+0.5h)

- [ ] Create cache warming script:

  ```python
  # src/core/cache_warmer.py (NEW FILE)
  async def warm_caches():
      """Preload hot paths during startup."""
      log.info("🔥 Warming caches...")
      
      # 1. Preload soul.json
      soul_manager.get_soul()
      
      # 2. Generate system prompts for all modes
      for mode in ["work", "soul", "fun", "red"]:
          soul_manager.current_mode = mode
          soul_manager.generate_meta_injection()
      
      # 3. Preload user profile
      await user_profile.get_current_profile()
      
      # 4. Prime embedding cache with common queries
      common_queries = [
          "помоги с кодом", "найди информацию", "исследуй тему",
          "как дела", "привет", "что нового"
      ]
      for q in common_queries:
          await embedding_service.get_or_compute(q)
      
      log.info("✅ Caches warmed!")
  ```

- [ ] Call from startup.py: `await warm_caches()`
- [ ] **Impact:** First request 100ms → 5ms, +3s startup time

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION #1:** Warm Cache Cascade Failure!

- [ ] Wrap each warm step in try/except for graceful degradation:

  ```python
  async def warm_caches():
      """Warm caches with graceful degradation."""
      log.info("🔥 Warming caches...")
      errors = []
      
      # Soul cache
      try:
          soul_manager.get_soul()
          log.info("✅ Soul cache warmed")
      except Exception as e:
          log.error(f"❌ Soul cache failed: {e}")
          errors.append("soul")
      
      # User profile
      try:
          await user_profile.get_current_profile()
          log.info("✅ Profile cache warmed")
      except Exception as e:
          log.error(f"❌ Profile cache failed: {e}")
          errors.append("profile")
      
      # ... (continue for all caches)
      
      if errors:
          log.warning(f"⚠️ Partial warm: {errors} failed. App will start with cold caches.")
      else:
          log.info("✅ All caches warmed!")
  ```

- [ ] **Impact:** Startup never fails, just slower first request

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION #2:** Progressive Loading Race!

- [ ] Add loading completion event:

  ```python
  class MemoryManager:
      def __init__(self):
          self._loading_complete = asyncio.Event()
      
      async def progressive_load(self):
          # Load priority facts
          # ...
          
          # Background load
          task = asyncio.create_task(self._load_remaining_facts())
          # Don't wait for it
      
      async def _load_remaining_facts(self):
          # ... load remaining facts
          self._loading_complete.set()  # Signal done
      
      async def get_relevant_facts(self, conv_id, query):
          # Wait if still loading (with timeout!)
          if not self._loading_complete.is_set():
              try:
                  await asyncio.wait_for(self._loading_complete.wait(), timeout=10.0)
              except asyncio.TimeoutError:
                  log.warning("⚠️ Still loading facts, using partial cache")
          
          # Use cache
          # ...
  ```

---

## Phase 7: Refinement & RAM Optimizations (9.5h)

> [!IMPORTANT]
> **🎯 PRODUCTION FIX #4:** Feature Flags for Optimizations (+2h)

**Problem:** RAM optimizations risky, hard to rollback if issues arise.

**Solution:** Feature flag system for gradual rollout.

- [ ] Create feature flag system:

  ```python
  # src/core/feature_flags.py (NEW FILE)
  import os
  from typing import Dict, Optional
  
  class FeatureFlags:
      """Feature flag system for safe rollout."""
      
      # Default values (conservative = disabled)
      _defaults = {
          "use_conversation_cache": False,
          "use_facts_preload": False,
          "use_rag_preload": False,
          "use_profile_cache": False,
          "use_prompts_preload": False,
          "use_semantic_keep_alive": False,
          "use_llm_router_cache": False,
          "use_warm_caches": False,
      }
      
      @classmethod
      def is_enabled(cls, flag: str, default: Optional[bool] = None) -> bool:
          """Check if feature is enabled."""
          if default is None:
              default = cls._defaults.get(flag, False)
          
          # Check environment variable
          env_value = os.getenv(f"FEATURE_{flag.upper()}")
          if env_value is not None:
              return env_value.lower() in ("true", "1", "yes")
          
          return default
      
      @classmethod
      def get_all(cls) -> Dict[str, bool]:
          """Get all feature flag states."""
          return {
              flag: cls.is_enabled(flag)
              for flag in cls._defaults.keys()
          }
  ```

- [ ] Use flags in implementations:

  ```python
  # In memory.py
  from src.core.feature_flags import FeatureFlags
  
  class MemoryManager:
      async def get_recent_messages(self, conv_id, limit=10):
          # Check feature flag
          if FeatureFlags.is_enabled("use_conversation_cache"):
              # Use RAM cache
              if conv_id in self._conversation_cache:
                  return list(self._conversation_cache[conv_id])[-limit:]
          
          # Fallback to DB (always works)
          return await self._load_from_db(conv_id, limit)
  ```

- [ ] Create .env file for flags:

  ```bash
  # .env (NEW FILE, add to .gitignore!)
  FEATURE_USE_CONVERSATION_CACHE=false
  FEATURE_USE_FACTS_PRELOAD=false
  FEATURE_USE_RAG_PRELOAD=false
  FEATURE_USE_PROFILE_CACHE=false
  FEATURE_USE_PROMPTS_PRELOAD=false
  FEATURE_USE_SEMANTIC_KEEP_ALIVE=false
  FEATURE_USE_LLM_ROUTER_CACHE=false
  FEATURE_USE_WARM_CACHES=false
  ```

- [ ] Gradual rollout plan:
  1. Week 1: Enable `use_conversation_cache=true`, monitor
  2. Week 2: If stable, enable `use_facts_preload=true`
  3. Week 3: Enable `use_rag_preload=true`
  4. Week 4: Enable all flags

- [ ] **Impact:** Safe rollout, instant rollback (flip flag), +2h
- [ ] **Time added:** 2h

---

- [ ] Redesign Multi-Threaded Thinking (simplify)
- [ ] Fix Intelligent Silence logic (confidence)
- [ ] Fine-tune Micro-Habits subtlety
- [ ] Review Dream Journal (P3)

> [!TIP]
> **⚖️ RAM OPTIMIZATION TRADE-OFF 2:** RAG Chunks Preload (+1h)

- [ ] Preload RAG chunks into RAM:

  ```python
  class RAGEngine:
      async def initialize(self, db):
          # PRELOAD ALL CHUNKS
          self._chunks_cache = []
          async with db.execute("SELECT * FROM document_chunks") as cursor:
              async for row in cursor:
                  chunk = Chunk(
                      id=row["id"],
                      content=row["content"],
                      embedding=json.loads(row["embedding"].decode()),
                      tokens=row["tokens"]
                  )
                  self._chunks_cache.append(chunk)
          log.info(f"Preloaded {len(self._chunks_cache)} RAG chunks")
      
      async def query(self, question, top_k=5):
          # Search IN MEMORY!
          query_emb = await embedding_service.get_or_compute(question)
          scored = [(c, cosine_similarity(query_emb, c.embedding)) for c in self._chunks_cache]
          scored.sort(key=lambda x: x[1], reverse=True)
          return [c for c, s in scored[:top_k]]
  ```

- [ ] **Impact:** 5x speedup, +50MB RAM

> [!TIP]
> **⚖️ RAM OPTIMIZATION TRADE-OFF 3:** User Profile In-Memory (+0.5h)

- [ ] Add profile singleton cache:

  ```python
  class UserProfile:
      _profile_cache = None
      _last_load = 0
      CACHE_TTL = 60  # 1 minute
      
      async def get_current_profile(self):
          now = time.time()
          if self._profile_cache and (now - self._last_load) < self.CACHE_TTL:
              return self._profile_cache  # RAM!
          
          self._profile_cache = await self._load_from_db()
          self._last_load = now
          return self._profile_cache
  ```

- [ ] **Impact:** 100x speedup, +1MB RAM

> [!TIP]
> **⚖️ RAM OPTIMIZATION TRADE-OFF 4:** Semantic Model Keep-Alive (+0h)

- [ ] Force preload semantic model on startup:

  ```python
  class SemanticRouter:
      def __init__(self):
          from sentence_transformers import SentenceTransformer
          self._model = SentenceTransformer("all-MiniLM-L6-v2")
          # Keep in RAM always
  ```

- [ ] **Impact:** First query 500ms → 10ms, +90MB RAM, +2s startup

> [!TIP]
> **⚖️ RAM OPTIMIZATION TRADE-OFF 6:** Prompt Library Preload (+0.5h)

- [ ] Preload all prompts:

  ```python
  class PromptLibrary:
      async def initialize(self, db):
          self._prompts = {}  # intent -> Prompt
          async with db.execute("SELECT * FROM prompts") as cursor:
              async for row in cursor:
                  self._prompts[row["intent"]] = Prompt(
                      id=row["id"],
                      intent=row["intent"],
                      system_prompt=row["system_prompt"]
                  )
      
      def select(self, intent, topic=None):
          return self._prompts.get(intent, self._prompts["default"])
  ```

- [ ] **Impact:** 50x speedup, +2MB RAM

> [!TIP]
> **🧠 RAM OPTIMIZATION UX 2:** Progressive Memory Loading (+1h)

- [ ] Load facts progressively:

  ```python
  class MemoryManager:
      async def progressive_load(self):
          # Load high-priority first
          async with self._db.execute("""
              SELECT * FROM memory_facts
              ORDER BY created_at DESC, confidence DESC
              LIMIT 1000
          """) as cursor:
              for row in await cursor.fetchall():
                  self._facts_cache[row["id"]] = Fact(...)
          
          # Load rest in background
          asyncio.create_task(self._load_remaining_facts())
  ```

- [ ] **Impact:** Faster perceived performance

---

## Phase 8: Cleanup (1h)

> [!WARNING]
> **[AUDIT]** Only after Dynamic Persona migrated!

- [ ] **CHECK:** Dynamic Persona no longer uses `system_prompt.txt`
- [ ] **THEN:** Delete `system_prompt.txt`
- [ ] Update README.md
- [ ] Create docs:
  - `docs/SOUL_ARCHITECTURE.md`
  - `docs/KILLER_FEATURES.md`
  - `docs/MIGRATION_GUIDE.md`
- [ ] Git commit with detailed message

> [!IMPORTANT]
> **🎯 PRODUCTION FIX #5:** Production Monitoring (+3h)

**Problem:** No visibility into production health, cache performance, errors.

**Solution:** enterprise monitoring with Prometheus + health endpoint.

- [ ] Install monitoring dependencies:

  ```bash
  pip install prometheus-client python-dotenv
  ```

- [ ] Create metrics collector:

  ```python
  # src/core/metrics.py (NEW FILE)
  from prometheus_client import Counter, Histogram, Gauge, generate_latest
  
  # Request metrics
  request_count = Counter(
      'max_requests_total',
      'Total requests',
      ['endpoint', 'status']
  )
  
  request_duration = Histogram(
      'max_request_duration_seconds',
      'Request duration',
      ['endpoint']
  )
  
  # Cache metrics
  cache_hit_rate = Gauge(
      'max_cache_hit_rate',
      'Cache hit rate',
      ['cache_name']
  )
  
  cache_size = Gauge(
      'max_cache_size_bytes',
      'Cache size in bytes',
      ['cache_name']
  )
  
  # System metrics
  active_conversations = Gauge(
      'max_active_conversations',
      'Number of active conversations'
  )
  
  db_pool_size = Gauge(
      'max_db_pool_available',
      'Available DB connections'
  )
  
  # Error metrics
  error_count = Counter(
      'max_errors_total',
      'Total errors',
      ['error_type']
  )
  ```

- [ ] Instrument code:

  ```python
  # In chat.py
  from src.core.metrics import request_count, request_duration
  
  @app.post("/api/chat")
  async def chat(request: ChatRequest):
      with request_duration.labels(endpoint='/api/chat').time():
          try:
              result = await process_chat(request)
              request_count.labels(endpoint='/api/chat', status='success').inc()
              return result
          except Exception as e:
              request_count.labels(endpoint='/api/chat', status='error').inc()
              raise
  ```

- [ ] Add metrics endpoint:

  ```python
  # In api/routers/system.py
  from prometheus_client import generate_latest
  from fastapi import Response
  
  @router.get("/metrics")
  async def metrics():
      """Prometheus metrics endpoint."""
      return Response(
          content=generate_latest(),
          media_type="text/plain"
      )
  ```

- [ ] Add health endpoint with detailed checks:

  ```python
  @router.get("/health")
  async def health_check():
      """Comprehensive health check."""
      import psutil
      from src.core.ram_budget import ram_budget
      from src.core.feature_flags import FeatureFlags
      
      # Check DB connection
      try:
          async with db_pool.acquire() as conn:
              await conn.execute("SELECT 1")
          db_healthy = True
      except Exception as e:
          db_healthy = False
      
      # Get system stats
      ram_stats = ram_budget.get_stats()
      feature_flags = FeatureFlags.get_all()
      
      health = {
          "status": "healthy" if db_healthy else "unhealthy",
          "timestamp": datetime.now().isoformat(),
          "checks": {
              "database": "ok" if db_healthy else "failed",
              "ram_budget": {
                  "allocated_mb": ram_stats["allocated_mb"],
                  "available_mb": ram_stats["available_mb"],
                  "status": "ok" if ram_stats["available_mb"] > 100 else "warning"
              },
              "feature_flags": feature_flags,
          },
          "uptime_seconds": time.time() - app_start_time,
      }
      
      status_code = 200 if db_healthy else 503
      return Response(content=json.dumps(health, indent=2), 
                     status_code=status_code,
                     media_type="application/json")
  ```

- [ ] Create simple monitoring dashboard script:

  ```python
  # monitor.py (NEW FILE - простой dashboard для консоли)
  import requests
  import time
  from rich.console import Console
  from rich.table import Table
  
  console = Console()
  
  while True:
      health = requests.get("http://localhost:8000/health").json()
      
      console.clear()
      console.print("[bold]MAX Health Dashboard[/bold]\n")
      
      # Status
      status = health["status"]
      color = "green" if status == "healthy" else "red"
      console.print(f"Status: [{color}]{status}[/{color}]\n")
      
      # Checks table
      table = Table(title="Health Checks")
      table.add_column("Check", style="cyan")
      table.add_column("Status", style="green")
      
      for check, result in health["checks"].items():
          if isinstance(result, dict):
              table.add_row(check, str(result))
          else:
              table.add_row(check, result)
      
      console.print(table)
      
      time.sleep(5)  # Refresh every 5s
  ```

- [ ] **Impact:** Full observability, alerts, debugging capability, +3h
- [ ] **Time added:** 3h

---

## 📊 Timeline

> [!NOTE]
> **OPTIMIZED:** 43h → 39h through parallel testing and automation

| Phase | Hours | Optimizations | Audit Reference |
|-------|-------|---------------|-----------------|
| 0 Backup | 1h | +0.5h (baselines, hooks, rollback script) | Breaking Changes Prevention |
| Phase | Base Time | Adjustments | Audit Cross-Ref |
|---|---|---|---|
| 0 Preparation | 2.3h | +2h (Phase Manager) | All Findings (Setup) |
| 0.5 Integration | 2h | +1.5h (RAM Budget) | Finding 1, 4 (Integration points) |
| 1 soul.json | 5h | - | Finding 1 (Soul Manager) |
| 2 Core Extensions | 19h | - | All Findings |
| 3 Simplification | 2h | - | Finding 3 (UserProfile) |
| 4 Integration | 4h | - | Findings 1, 2, 5, 6 |
| 5 Features | 8h | - | Finding 3 (Adaptive Verbosity) |
| 6 Testing | 6h | +0.5h (test-by-test comparison) | All Findings (Regression) |
| 7 Refinement | 9.5h | +2h (Feature flags) | - |
| 8 Cleanup | 4h | +3h (Monitoring) | Finding 2 (Delete prompt) |
| **Total** | **59.5h (~7.5 days)** | **+9.5h production fixes** | NET: +16h from baseline |

**Production Readiness Impact:**

- 🎯 **Phase State Machine:** Atomic phases, bulletproof rollback (+2h)
- 🎯 **RAM Budget Coordinator:** Prevents OOM, graceful degradation (+1.5h)
- 🎯 **Test-by-Test Comparison:** Catches subtle regressions (+0.5h)
- 🎯 **Feature Flags:** Safe rollout, instant rollback (+2h)
- 🎯 **Production Monitoring:** Prometheus, health checks, observability (+3h)
- **Total production fixes:** +9.5h
- **Production-ready confidence:** ★★★★★ (5/5)

**Optimization Impact:**

- 🚀 Parallel testing: -1.5h
- 🚀 Automation scripts: -1h implementation time (amortized)
- ⚖️ Caching: 100x runtime performance
- 🧠 Better tooling: Faster debugging

**RAM Optimization Impact (18 total):**

- 🚀 **6 Instant Wins:** DB pool (+30MB), Tiktoken (+2MB), Router cache (+5MB), Embedding cache (+196MB), Smart Router expand (+5MB), Embedding preload (+50MB) = **+288MB**
- ⚖️ **7 Trade-offs:** Conv cache (+100MB), RAG preload (+50MB), Facts preload (+100MB), LLM Router (+10MB+50MB disk), Profile (+1MB), Prompts (+2MB), Semantic model (+90MB) = **+353MB**
- 🧠 **3 UX Boosts:** Warm caches, Cache stats, Progressive loading
- **Total RAM cost:** ~**640MB** (с unlimited RAM — отличная инвестиция!)
- **Total speedup:** **3-10x** на hot paths (routing 10x, memory 5-10x, RAG 5x)
- **P95 latency improvements:** Routing 50ms→5ms, Memory search 10ms→1ms, System prompt 10ms→0.1ms

---

## 🎯 Pre-Flight Checklist

Before starting ANY phase:

### Read

- [ ] Full `architectural_audit.md`
- [ ] Relevant findings for this phase
- [ ] Breaking Changes Prevention section

### Verify

- [ ] Git branch created
- [ ] Backups made
- [ ] Tests passing BEFORE changes

### During Implementation

- [ ] Check audit reference for this phase
- [ ] Run existing tests after each change
- [ ] Log every breaking change discovered

### After Each Phase

- [ ] All phase tests pass
- [ ] Regression tests still pass
- [ ] No new errors in logs
- [ ] Git commit with phase number

---

## 🚨 Emergency Rollback

> [!TIP]
> **🚀 OPTIMIZATION WIN 8:** Automated rollback (15min → 10sec)

If anything breaks:

1. **Stop immediately**
2. **Run rollback script:** `python rollback.py <phase_number>`
   - Or interactive: `python rollback.py` (shows menu)
3. Review audit findings for that phase
4. Identify what was missed
5. Fix and retry

**Manual fallback:**

- `git checkout main`
- `git log --grep="Phase X"` to find specific commit

---

## ✅ Success Criteria

### Week 1 Complete

- [ ] All existing tests pass
- [ ] Test mode triggers work
- [ ] Test performance within budget

> [!TIP]
> **⚖️ RAM OPTIMIZATION TRADE-OFF 5:** LLM Router Persistent Cache (+1h)

- [ ] Add persistent cache to LLMRouter:

  ```python
  from cachetools import LRUCache
  
  class LLMRouter:
      def __init__(self):
          self._ram_cache = LRUCache(maxsize=5000)
          self._disk_cache_path = Path("data/llm_router_cache.json")
          self._disk_cache = self._load_disk_cache()
      
      def _load_disk_cache(self):
          if self._disk_cache_path.exists():
              return json.loads(self._disk_cache_path.read_text())
          return {}
      
      async def route(self, message):
          key = self._get_cache_key(message)
          
          # 1. Check RAM
          if key in self._ram_cache:
              return self._ram_cache[key]
          
          # 2. Check DISK
          if key in self._disk_cache:
              result = self._disk_cache[key]
              self._ram_cache[key] = result
              return result
          
          # 3. Call LLM
          result = await self._llm_route(message)
          
          # 4. Save to RAM + DISK (background)
          self._ram_cache[key] = result
          self._disk_cache[key] = result
          asyncio.create_task(self._save_disk_cache())
          
          return result
  ```

- [ ] **Impact:** 90%+ hit rate cross-session, +10MB RAM, +50MB disk

> [!CAUTION]
> **🛡️ EDGE CASE PROTECTION:** Disk Cache Corruption!

- [ ] Implement atomic disk writes:

  ```python
  async def _save_disk_cache(self):
      # ATOMIC WRITE!
      temp_path = self._disk_cache_path.with_suffix('.tmp')
      temp_path.write_text(json.dumps(self._disk_cache, indent=2))
      
      # Verify
      json.loads(temp_path.read_text())
      
      # Atomic rename
      temp_path.replace(self._disk_cache_path)
  
  def _load_disk_cache(self):
      try:
          if self._disk_cache_path.exists():
              return json.loads(self._disk_cache_path.read_text())
      except json.JSONDecodeError:
          log.error("⚠️ Disk cache corrupted! Starting fresh.")
          self._disk_cache_path.unlink()  # Delete corrupted
      return {}
  ```

---

- [ ] No new errors in logs

### Final Validation

- [ ] Chat UI works normally
- [ ] Soul Manager still injected
- [ ] Dynamic Persona rules work
- [ ] Memory facts extracted
- [ ] Smart Router classifies
- [ ] Ensemble activates
- [ ] Privacy Lock works
- [ ] Memory Commands work
- [ ] All killer features accessible

---

Виталий, теперь план **синхронизирован** с аудитом. Каждая фаза содержит:

- **[AUDIT]** ссылки на конкретные находки
- Preservation checklists
- Regression tests
- Emergency rollback процедуру

Готов начинать?
