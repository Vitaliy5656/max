# UX Audit Report: System 2 & Multi-Agent Features

> **Date:** 2025-12-13
> **Target:** Frontend (`App.tsx`, `ThinkingPanel.tsx`)
> **Focus:** Priority Queues, Thinking Pulse, Feedback Loops

## 1. Cognitive Load & Hierarchy

* **Thinking Panel:** ✅ Good hierarchy. "MAX думает" is clear.
* **Input Area:** ✅ Standard.

## 2. Responsiveness & Feedback (CRITICAL)

### 🔴 CRITICAL: Missing "Queued" State

* **Issue:** With `OLLAMA_NUM_PARALLEL=2`, a user request might wait 5-10s if background tasks are running.
* **Current State:** UI shows "Generating..." or generic loading immediately.
* **Risk:** User thinks app is frozen if it stays in "Loading" for 10s without token generation.
* **Solution:** Introduce a visible **"Waiting for Slot..."** or **"Queued (Pos: 1)"** state in `MessageBubble` or status bar.
  * *Backend Reference:* `SlotManager` should return queue position.

### 🟡 UX FAIL: "Blind" Thinking Animation

* **Issue:** `ThinkingPanel` animation is a CSS loop. It spins regardless of whether the backend is actually working or hung.
* **Improvement:** **Reactive Pulse**.
  * Bind a small UI element (e.g., a "heartbeat" dot) to actual `keep-alive` events from the stream.
  * If no events for >3s, turn dot yellow/red (Connection unstability indicator).

## 3. "Fool-proof" & Validation

* **Stop Button:** Exists in `InputArea`.
* **Retry:** Only for Agents. Should be available for stalled Chat requests too.

## 4. Technical Implementation

* **Accessibility:** `ThinkingPanel` uses `animate-pulse` which might trigger motion sensitivity. Ensure `prefers-reduced-motion` is respected.
* **Mobile:** Panel is `max-w-sm`. On mobile, it might take too much vertical space. Consider collapsible by default on mobile.

## Recommended UI Actions for Phase 1

1. **Update `ThinkingPanel`:**
    * Add `pulseState` prop (Active/Stalled).
    * Add "Thinking Steps" counter (if backend provides it).

2. **Update `InputArea` / `MessageBubble`:**
    * Add "Queued" status indicator.

3. **Update `useChat` hook:**
    * Handle `queue_update` events from backend.
