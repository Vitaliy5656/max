# Logic Audit: Integration Plan

> **Date:** 2025-12-13
> **Target:** `INTEGRATION_PLAN.md` & `src/core/`
> **Auditor:** Senior Product Architect

## 1. User Journey Mapping (Scenario Stress Test)

### Scenario A: "Deep Thought" (Cognitive)

User asks complex question -> `Planner` -> `Executor` (20s) -> `Verifier` (Fail) -> `Memory` -> `Executor` (Retry).

* **Checkpoint:** Does the user see *anything* during the 20s execution?
* **Gap:** If `ThinkingPulse` is not implemented at the *protocol level* (SSE), the connection might timeout or user will refresh.
* **Gap:** If `Verifier` is also an LLM call, does it take a slot? If `max_parallel=2`, and `Executor` is running + `Verifier` starts... do they deadlock? (No, sequential in graph, but check implementation).

### Scenario B: "Queue Jam"

User 1 (Complex) + User 2 (Complex) occupy 2 slots. User 3 (Simple "Hi") arrives.

* **Expectation:** "Hi" should be fast.
* **Reality (Plan):** It waits 60s for User 1/2 to finish.
* **Correction:** Priority Queue is mentioned in Optimization, but *how*? We need `priority=1` for regular chat and `priority=0` for background. But User 3 is also regular chat.
* **Logic Lie:** "Parallel Micro-Agents" implies responsiveness, but without *preemption*, it's just "Concurrent Blocking".

## 2. Logic & Intent Checks

### 🤥 LOGIC LIE: "Streaming Pulse"

* **Claim:** "Pulse mechanism to keep connection alive".
* **Reality:** `streaming.py` yields generator. If model doesn't yield token, generator pauses. We need a specific `asyncio.wait_for` loop to inject pulse events. This is NOT in `streaming.py` currently.
* **Fix:** Must implement `HeartbeatGenerator` wrapper.

### 🧩 STATE BUG: Verification Loops

* **Risk:** `Verifier` rejects -> `Executor` retries -> `Verifier` rejects same error.
* **Mitigation:** `MemoryNode` summarizes past failures.
* **Gap:** Does `Executor` *read* the `past_failures`? PROMPT must explicitly include: "Avoid these previous mistakes: {past_failures}".

### 📉 LAZY IMPLEMENTATION: VRAM Management

* **Current:** `OLLAMA_NUM_PARALLEL=2`.
* **Lazy:** Static config.
* **Better:** Dynamic check. If User 1 uses 4k context, and User 2 uses 4k, we have RAM. If User 1 uses 28k context, User 2 causes OOM.
* **Fix:** `SlotManager` must check *estimated context usage* before scheduling. (Too complex for Phase 1, but mark as known limit).

## 3. Boundary Checks

* **Timeout:** What if `Verifier` hangs? We need `step_timeout` in Graph.
* **Max Iterations:** Plan says `MAX_COGNITIVE_ITERATIONS=5`. Is this hard limit? Yes.
* **Cancel:** Can user cancel *during* verification step? If `Executor` is finished but `Verifier` running, does Stop button kill `Verifier`? (Need to link AbortController to Graph).

## Recommendations (Pre-Implementation)

1. **Modify `streaming.py`:** Add `HeartbeatGenerator` (wrapper).
2. **Update `prompts.py`:** Ensure `Executor` prompt includes `{past_failures}` variable.
3. **Update `SlotManager`:** Add simple *User vs Background* priority logic.
4. **Graph Timeout:** Add global timeout (e.g., 120s) to the Cognitive Graph.
