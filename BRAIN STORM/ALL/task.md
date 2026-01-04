# Task Checklist

- [x] Implement Phase 1: Cognitive Core <!-- id: 6 -->
  - [x] Create `src/core/cognitive` structure & `types.py`
  - [x] Implement `prompts.py` with `past_failures`
  - [x] Implement Nodes (Planner, Executor, Verifier, Memory)
  - [x] Build `graph.py` with LangGraph
  - [x] Implement `math_utils.py`
  - [x] Implement `HeartbeatGenerator` in `streaming.py`
  - [x] Update `ContextOrchestrator` to using Cognitive Context

- [ ] Implement Phase 2: Parallel Slots <!-- id: 7 -->
  - [x] Create `src/core/parallel` structure & `types.py`
  - [x] Implement `SlotManager` (Semaphore + Queue Heartbeat)
  - [x] Update `lm_client.py` to use Slots

  - [x] Update `lm_client.py` to use Slots

- [x] Implement Phase 3: Frontend (React) <!-- id: 8 -->
  - [x] Update `useChat` hook for new events
  - [x] Update `ThinkingPanel` (Pulse Animation)
  - [x] Add Queue State UI

- [x] Final Integration (V1.3)
  - [x] Implement Real Cognitive Nodes
  - [x] Integrate `api.py` with `thinking_mode='deep'`
