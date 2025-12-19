# Soul Manager Module

BDI (Belief-Desire-Intention) state management for MAX AI.

## Features

- **Lazy Loading + Caching**: Soul loads from `data/soul.json` with 5-min TTL
- **Time Awareness**: Generates time-context for greetings (morning/afternoon/evening/night)
- **Anti-Lag**: Defers background tasks when user is active (<1 min)
- **Quick Save**: Auto-saves every 60 seconds
- **Graceful Shutdown**: Saves on app exit
- **Deep Consolidation**: LLM-based insight extraction during idle (>5 min)

## Usage

```python
from src.core.soul import soul_manager

# Get soul state
soul = soul_manager.get_soul()
print(soul.meta.agent_id)  # MAX_AI_PRIME

# Generate system prompt injection
meta_block = soul_manager.generate_meta_injection()

# Track user activity
soul_manager.touch_user_activity()

# Modify state
soul_manager.set_focus(project="MAX AI")
soul_manager.add_short_term_goal("Complete Phase 6")
```

## Files

| File | Description |
|------|-------------|
| `models.py` | Pydantic schemas: SoulState, BDIState, Identity |
| `soul_manager.py` | SoulManager singleton class |
| `__init__.py` | Package exports |

## Data File

`data/soul.json` contains:

- `meta`: agent_id, version, boot_count
- `identity`: archetype, core_directive, tone_vectors
- `axioms`: core principles (Simplicity > Complexity, etc.)
- `bdi_state`: beliefs, desires, intentions
- `current_focus`: active project/context
- `insights`: extracted learnings from conversations
