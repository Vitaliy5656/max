# Logic Review: Integration Plan (Final Pass)

> **Role:** Senior Product Architect
> **Scope:** Semantic Logic & User Journeys in `INTEGRATION_PLAN.md`

## 1. User Journey: "Queue Waiting"

* **Scenario:** User 3 enters while User 1 & 2 are thinking.
* **Logic Check:** `SlotManager` (Semaphore) blocks User 3.
* **Problem:** User 3 socket connection might timeout if `SlotManager.acquire()` takes >60s.
* **Fix:** `SlotManager` must throw `BusyError` immediately if queue > 5 (Fail Fast), OR we need a "Queue Heartbeat" while waiting for the slot.
* **Decision:** Add "Queue Heartbeat" to `streaming.py` *before* acquiring the slot.

## 2. Logic Lie: "Structured Verification"

* **Claim:** "Verifier returns JSON".
* **Reality:** Models are bad at JSON without help. Even with `outlines`, prompt must be perfect.
* **Risk:** If model returns invalid JSON, the whole loop crashes.
* **Fix:** `Verifier` code must have a "Fallback Parser" (regex) if JSON fails, so we don't crash on a missing bracket.

## Recommendation

Implement "Queue Heartbeat" (waiting state events).
Add specific "Fallback Parser" requirement for Verifier node.
