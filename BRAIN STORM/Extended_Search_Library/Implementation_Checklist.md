# 📋 Research Lab — Implementation Checklist

> Полный чеклист для реализации Research Lab (Phase 1) и Brain Map (Phase 2).
>
> **Файлы планов:**
>
> - [НОвые фичи.md](file:///c:/Users/Vitaliy/Desktop/MAX/BRAIN%20STORM/Extended_Search_Library/НОвые%20фичи.md) — Phase 1 (Research Lab)
> - [Brain_Map_Plan.md](file:///c:/Users/Vitaliy/Desktop/MAX/BRAIN%20STORM/Extended_Search_Library/Brain_Map_Plan.md) — Phase 2 (Brain Map)

---

## 🚀 PHASE 1: Research Lab

### Dependencies

- [ ] Добавить в `requirements.txt`:
  - [ ] `chromadb>=0.4.0`
  - [ ] `trafilatura>=1.6.0`

### Backend Core Files

- [ ] **`src/core/research/__init__.py`**
  - [ ] Экспорт всех модулей

- [ ] **`src/core/research/storage.py`**
  - [ ] `TopicInfo` dataclass с `status` полем
  - [ ] `ResearchStorage` class
  - [ ] `create_topic(name, description, status="incomplete")`
  - [ ] `update_topic_status(topic_id, status)`
  - [ ] `add_chunk()` — embeddings вычисляются СНАРУЖИ
  - [ ] `search()` / `search_all()`
  - [ ] `list_topics()`
  - [ ] `delete_topic()`
  - [ ] `save_skill()` / `get_skill()`
  - [ ] Skills file: `data/research/skills.json`

- [ ] **`src/core/research/parser.py`**
  - [ ] `DualParser` class
  - [ ] `trafilatura` как primary
  - [ ] `BeautifulSoup` как fallback
  - [ ] `asyncio.wait_for(..., timeout=10)` для trafilatura
  - [ ] Stats tracking (success/fail по парсеру)
  - [ ] `MIN_CONTENT_LENGTH = 200` filter

- [ ] **`src/core/research/agent.py`**
  - [ ] `ResearchAgent` class
  - [ ] `research(topic, description, max_pages)` — main method
  - [ ] `_fetch_page(url)` — БЫЛО MISSING!
  - [ ] `_generate_queries(topic)` — LLM generates 5-10 queries
  - [ ] `_mine(content)` — Pass 1, JSON mode
  - [ ] `_deduplicate_facts(facts)` — cosine similarity 0.9
  - [ ] `_polish(facts)` — Pass 2, KB entry
  - [ ] `_generate_skill(summary)` — Pass 3, Topic Lens
  - [ ] `_chunk_by_tokens()` — MAX_CHUNK_TOKENS = 6000
  - [ ] Sources tracking в metadata
  - [ ] Stats tracking (pages found/processed/skipped)
  - [ ] `status="incomplete"` на старте, `"complete"` в конце
  - [ ] `asyncio.CancelledError` handling
  - [ ] `research_into_existing(topic_id, ...)` — для refresh

- [ ] **`src/core/research/worker.py`**
  - [ ] `ResearchWorker` class
  - [ ] `start()` с duplicate check (409 Conflict)
  - [ ] `start_refresh()` — для refresh в существующий topic
  - [ ] `_update_progress()` с `detail` и `eta_seconds`
  - [ ] `cleanup_zombies()` при старте сервера
  - [ ] Task state persistence: `data/research/active_tasks.json`
  - [ ] WebSocket broadcast
  - [ ] Log files: `data/research/logs/`

### API Endpoints

- [ ] **`src/api/routers/research.py`**
  - [ ] `POST /start` — start research
  - [ ] `GET /status/{task_id}` — get progress
  - [ ] `POST /cancel/{task_id}` — cancel task (с проверкой `task.done()`)
  - [ ] `GET /topics` — list all topics
  - [ ] `GET /topics/{topic_id}` — get topic details
  - [ ] `GET /topics/{topic_id}/skill` — get skill prompt
  - [ ] `POST /topics/{topic_id}/refresh` — refresh topic (в existing!)
  - [ ] `GET /topics/{topic_id}/search` — semantic search
  - [ ] `DELETE /topics/{topic_id}` — delete topic
  - [ ] `GET /parser-stats` — parser comparison
  - [ ] `WebSocket /ws/progress` — real-time updates

- [ ] **`src/api/app.py`**
  - [ ] Импорт и регистрация `research_router`
  - [ ] `research_storage.initialize()` в lifespan
  - [ ] `research_worker.cleanup_zombies()` в lifespan

### LLM Prompts

- [ ] `MINER_PROMPT` — JSON Schema для entities/dates/numbers/claims
- [ ] `JEWELER_PROMPT` — Academic style KB entry
- [ ] `DIPLOMA_PROMPT` — Topic Lens generation (Few-Shot)
- [ ] `QUERY_GENERATOR_PROMPT` — 5-10 search queries

### Frontend

- [ ] **`frontend/src/components/ResearchLab.tsx`** (NEW)
  - [ ] Topic list
  - [ ] Start research form
  - [ ] Progress display (5-stage stepper)
  - [ ] ETA countdown
  - [ ] "Safe to close" toast
  - [ ] Empty state
  - [ ] Cancel confirmation dialog
  - [ ] Skeleton loading
  - [ ] Celebration modal

- [ ] **`frontend/src/hooks/useResearch.ts`** (NEW)
  - [ ] State management
  - [ ] WebSocket connection
  - [ ] API calls

### UX Requirements

- [ ] Visual stepper (5 stages: Planning → Hunting → Mining → Polishing → Diploma)
- [ ] ETA display (minutes remaining)
- [ ] "Safe to close" toast (5 sec)
- [ ] Empty state с CTA
- [ ] Cancel confirmation dialog
- [ ] Skeleton loading (pulse animation)
- [ ] Celebration modal 🎉

### Integration

- [ ] Router Integration TODO:
  - [ ] `semantic_router.py` или `dynamic_persona.py`
  - [ ] Чтение `data/research/skills.json`
  - [ ] Инъекция "Дипломов" в System Prompt

### Testing

- [ ] Unit tests: DualParser
- [ ] Unit tests: ResearchStorage
- [ ] Unit tests: Fact deduplication
- [ ] Integration tests: API endpoints
- [ ] Manual test: Full research flow

---

## 🧠 PHASE 2: Brain Map

### Dependencies

- [ ] Добавить в `requirements.txt`:
  - [ ] `umap-learn>=0.5.0`
- [ ] Добавить в frontend:
  - [ ] `npm install @react-three/fiber @react-three/drei`

### Backend

- [ ] **`src/core/research/brain_map.py`** (NEW)
  - [ ] `generate_brain_map(level, topic_id, force_recompute)`
  - [ ] `_compute_topic_centroids()` — level 0
  - [ ] `_compute_projection()` — UMAP с `run_in_executor`!
  - [ ] `invalidate_cache()` — called after research
  - [ ] Cached reducer: `data/research/umap_reducer.pkl`
  - [ ] Cached projections: `data/research/brain_map_cache.json`
  - [ ] `MAX_POINTS_PER_LEVEL = 100` limit
  - [ ] `_topic_color()` — deterministic colors

- [ ] **API Endpoints**
  - [ ] `GET /brain-map?level=0|1|2&topic_id=xxx`
  - [ ] `POST /brain-map/invalidate`

### Frontend

- [ ] **`frontend/src/components/BrainCore.tsx`** (MODIFY from DenseCore)
  - [ ] `onClick` handler
  - [ ] Hover hint
  - [ ] Scale animation on hover

- [ ] **`frontend/src/components/BrainMapModal.tsx`** (NEW)
  - [ ] Canvas + OrbitControls
  - [ ] `Point` component с hover
  - [ ] `LoadingSkeleton` (3D ghost spheres)
  - [ ] `EmptyState`
  - [ ] Selected point panel
  - [ ] Hierarchical drill-down
  - [ ] Back navigation
  - [ ] Legend

- [ ] **`frontend/src/hooks/useBrainMap.ts`** (NEW)
  - [ ] `isOpen` state
  - [ ] `openBrainMap()`
  - [ ] `closeBrainMap()`

### Integration

- [ ] **`Sidebar.tsx`**
  - [ ] Replace `DenseCore` → `BrainCore`
  - [ ] Add `BrainMapModal`
  - [ ] Wire up `useBrainMap` hook

- [ ] **`worker.py`**
  - [ ] Call `invalidate_cache()` after research completes

### Testing

- [ ] `run_in_executor` не блокирует event loop
- [ ] Hierarchical levels работают (0→1→2)
- [ ] Cache invalidates при новом research
- [ ] Loading skeleton отображается
- [ ] Empty state при пустых данных
- [ ] Drill-down работает
- [ ] OrbitControls smooth

---

## 📊 Summary

| Phase | Files | Complexity | Est. Time |
|-------|-------|------------|-----------|
| Phase 1 | ~15 files | High | 2-3 days |
| Phase 2 | ~5 files | Medium | 1 day |

### Order of Implementation

1. ✅ Dependencies (requirements.txt, package.json)
2. ✅ Backend: storage.py
3. ✅ Backend: parser.py
4. ✅ Backend: agent.py
5. ✅ Backend: worker.py
6. ✅ API: research.py
7. ✅ API: app.py integration
8. ✅ Frontend: useResearch.ts
9. ✅ Frontend: ResearchLab.tsx
10. ✅ Testing: Phase 1
11. ✅ Backend: brain_map.py (Phase 2)
12. ✅ Frontend: BrainCore.tsx, BrainMapModal.tsx
13. ✅ Testing: Phase 2
14. ✅ Router Integration (TODO)

---

## ⚠️ Critical Fixes Included

| Issue | Fix | Where |
|-------|-----|-------|
| `_fetch_page` missing | Added method | agent.py |
| Empty topics created | `status="incomplete"` | storage.py, agent.py |
| Refresh creates duplicate | `research_into_existing()` | agent.py |
| Parallel research race | 409 Conflict check | worker.py |
| Sources not saved | `sources[]` in metadata | agent.py |
| Stats not saved | `stats{}` in metadata | agent.py |
| UMAP blocks event loop | `run_in_executor` | brain_map.py |
| No data limit | Hierarchical UMAP | brain_map.py |
| Unstable projections | Cached reducer | brain_map.py |
| No loading state | 3D Skeleton | BrainMapModal.tsx |
