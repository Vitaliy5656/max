# Integration Points Map for MAX

> **Created:** 2025-12-19 Phase 0.5  
> **Purpose:** Document existing system integration points for safe extension

---

## 1. System Prompt Assembly Flow (chat.py)

### Entry Point

**File:** `src/api/routers/chat.py`  
**Function:** `chat(request: ChatRequest)`

### Assembly Sequence

```python
# Step 1: Dynamic Persona
dynamic_prompt = await dynamic_persona.build_dynamic_prompt(user_id)
system_prompts.append(dynamic_prompt)

# Step 2: Soul Manager  
meta_injection = soul_manager.generate_meta_injection()
system_prompts.append(meta_injection)

# Step 3: Smart Router (conditional)
route = await smart_router.route(message)
if route.system_prompt:
    system_prompts.append(route.system_prompt)

# Final: Join
final_system_prompt = "\n\n".join(system_prompts)
```

### Critical Dependencies

1. **Dynamic Persona** (`src/core/dynamic_persona.py`)
   - Reads: `user_preferences`, `conversation_summaries`
   - Returns: User-specific system prompt adaptations

2. **Soul Manager** (`src/core/soul/soul_manager.py`)
   - Reads: `data/soul.json`
   - Returns: Meta-cognitive injection

3. **Smart Router** (`src/core/routing/smart_router.py`)
   - 6-layer pipeline: Language → Intent → Topic → Mode → Complexity → Caching
   - Returns: Route with optional system_prompt

---

## 2. Database Tables Used

### Core Tables

- `conversations` - Conversation metadata
- `messages` - All messages (user + assistant)
- `conversation_summaries` - Compressed history
- `memory_facts` - Extracted facts with embeddings
- `user_preferences` - Dynamic Persona settings

### Metrics Tables

- `implicit_feedback` - User satisfaction signals
- `achievements` - Gamification

### Research Tables (new)

- `research_topics`
- `research_tasks`
- `research_skills`

---

## 3. Existing Systems to PRESERVE

### System 1: Soul Manager

**Location:** `src/core/soul/soul_manager.py`  
**Size:** 707 LOC  
**Critical Method:** `generate_meta_injection()` - DO NOT MODIFY

### System 2: Dynamic Persona

**Location:** `src/core/dynamic_persona.py`  
**Size:** 395 LOC  
**Critical:** User rules system, mood detection

### System 3: Memory Manager

**Location:** `src/core/memory.py`  
**Size:** 947 LOC  
**Multi-tier:** Facts extraction + summarization + semantic search

### System 4: Smart Router

**Location:** `src/core/routing/smart_router.py`  
**6 Layers:** Language, Intent, Topic, Mode triggers, Complexity, Caching

### System 5: User Profile

**Location:** `src/core/user_profile.py`  
**Size:** 572 LOC  
**Critical:** Mood detection, style adaptation

### System 6: Cognitive Ensemble

**Location:** `src/core/cognitive/ensemble_loop.py`  
**Size:** 675 LOC  
**Critical:** Multi-agent reasoning loop

### System 7: Tool Registry

**Location:** `src/core/tool_registry/registry.py`  
**Critical:** Decorator system for tool registration

---

## 4. Integration Strategy

### Extension Points (Safe to Modify)

1. ✅ Add new parameters to existing methods
2. ✅ Add new optional features (with flags)
3. ✅ Extend dataclasses (backward compatible)

### No-Touch Zones (DO NOT MODIFY)

1. ❌ Soul Manager's `generate_meta_injection()` signature
2. ❌ Memory Manager's facts extraction logic
3. ❌ Smart Router's 6-layer pipeline order
4. ❌ Cognitive Ensemble's loop structure

### Safe Integration Pattern

```python
# GOOD: Extend with optional parameter
await memory.add_fact(conv_id, content, category="general")  # New param

# BAD: Replace existing method
# memory.add_fact = new_implementation  # BREAKS EVERYTHING
```

---

## 5. SQL Schema

### Key Tables Structure

```sql
-- Conversations
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    user_id TEXT DEFAULT '1'
);

-- Messages
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    created_at TIMESTAMP
);

-- Memory Facts
CREATE TABLE memory_facts (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    content TEXT,
    embedding BLOB,  -- JSON array
    created_at TIMESTAMP,
    confidence REAL DEFAULT 1.0
);
```

---

## 6. Verification Checklist

Before ANY changes:

- [ ] Read architectural_audit.md
- [ ] Check integration points above
- [ ] Verify method exists before calling
- [ ] Add regression test
- [ ] Preserve existing functionality

---

**Last Updated:** 2025-12-19 Phase 0.5  
**Status:** ✅ Integration map complete
