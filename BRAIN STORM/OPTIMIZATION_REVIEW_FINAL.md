# Optimization Review: Integration Plan (Final Pass)

> **Role:** Senior Performance Engineer
> **Scope:** Performance Budgets & Trade-offs in `INTEGRATION_PLAN.md`

## 1. Budget Checks

### ⚖️ VRAM Budget (Critical)

* **Current Plan:** `OLLAMA_NUM_PARALLEL=2`, Q4_K_M (14B).
* **Math:** 9GB (weights) + 1GB (buf) + 2 * 2.5GB (KV approx) = 15GB.
* **Verdict:** ⚠️ **Extreme Edge**. On 16GB card, we have <1GB headroom.
* **Recommendation:** Force `OLLAMA_KV_CACHE_TYPE=q8_0` or `q4_0` if available, OR reduce context to 8k per slot (down from 13k).
* **Constraint:** Add explicit `num_ctx` limit in `LMStudioClient`.

### ⚡ Feature: "Reactive Pulse"

* **Impact:** Adds slight CPU overhead (timer every 100ms).
* **Verdict:** ✅ Negligible. High UX value.

## 2. Free Wins (Optimization)

### 🚀 `orjson` for Structured Output

* **Finding:** If we use `outlines` (from Architect review) + `orjson` for parsing, we save ~50ms per Cycle.
* **Action:** Add `orjson` to dependencies for `cognitive` package.

### 🧠 Smart Context Truncation

* **Finding:** `MemoryNode` summaries can grow.
* **Action:** Implement "Rolling Window" for `past_failures` prompt injection. Limit to last 3 attempts.

## Recommendation

Add `num_ctx=8192` limit to `LMStudioClient` calls for safety.
Use `orjson` for fast JSON parsing.
Limit error history to 3 items.
