# Optimization Report: Integration Plan & Core Components

> **Date:** 2025-12-13
> **Target:** `src/core/` & `INTEGRATION_PLAN.md`
> **Analyst:** Senior Performance Engineer

## 📊 Phase 0: Baseline & Static Analysis

| Component | Status | Issue |
|-----------|--------|-------|
| `memory.py` | ⚠️ Duplicate | `_cosine_similarity` duplicated in `context_primer.py` |
| `streaming.py` | ⚠️ Latency | Buffers "think tags" indefinitely until close tag or buffer limit |
| `slot_manager` | ⚠️ Blocking | Background tasks (facts) compete equally with User (chat) |
| `context_orchestrator` | ⚠️ Wasteful | Fetches all context types regardless of token budget saturation |

---

## Phase 1: Free Wins (🚀 INSTANT WIN)

1. **Unified Math Utils (DRY + Perf)**
    * **Finding:** `_cosine_similarity` logic exists in both `memory.py` and `context_primer.py`.
    * **Optimization:** Extract to `src/core/math_utils.py`. Use simplified dot product logic (assumes pre-normalized vectors if possible).
    * **Benefit:** Reduced code duplication, single point of optimization.

2. **Streaming "Flush" Logic**
    * **Finding:** In `streaming.py`, if a partial tag `<` is found, it waits for more tokens. If the model pauses there, the UI freezes.
    * **Optimization:** Add a time-based flush. If `pending_buffer` is non-empty for >200ms, yield it immediately (the parser will catch up later).
    * **Benefit:** Smoother UI, no "micro-stutters".

---

## Phase 2: Strategic Trade-offs (⚖️ TRADE-OFF)

3. **Priority Slot Queue (RAM vs Complexity)**
    * **Problem:** With `OLLAMA_NUM_PARALLEL=2`, a user chat + a background "Fact Extraction" + a background "Summary" = 3 tasks. The user might get blocked by a background task.
    * **Optimization:** Implement a **Priority Queue** in `SlotManager`.
        * User Request: **High Priority** (Preempts or jumps queue)
        * Fact Extraction: **Low Priority** (Wait until idle)
    * **Trade-off:** slightly more complex scheduler code, but critical for UX on 16GB VRAM.

4. **Smart Context Budgeting (CPU vs Accuracy)**
    * **Problem:** `context_orchestrator` fetches RAG + Memory + Primer (parallel). Then it truncates. This wastes CPU/IO on fetching data we throw away.
    * **Optimization:** Check token count *during* assembly stages? (Hard with parallel).
    * **Alternative:** Set strict hard limits per category *before* fetching based on routing.
        * e.g. `Reasoning` route -> Max 500 tokens for RAG, Max 2000 for Memory.
        * `Fact` route -> Max 2000 for RAG, Max 500 for Memory.

---

## Phase 3: UX Guard (🧠 UX BOOST)

5. **Thinking "Pulse" (Keep-Alive)**
    * **Problem:** Deep thinking models (R1) can "pause" generation while computing. The UI spinner just spins.
    * **Optimization:** In `streaming.py`, emit `{"_meta": "pulse"}` events every 1s if no tokens are received but stream is open. Frontend can pulse the "Brain" icon.
    * **Benefit:** user knows "it's still working", reduces abandonment.

---

## Recommendations for Integration Plan

Merge these into the plan:

1. Add **`src/core/math_utils.py`** to Phase 1.
2. Update `SlotManager` design to include **Priority Queues** (Phase 2).
3. Add **Keep-Alive Pulse** to `streaming.py` specs (Phase 1).
