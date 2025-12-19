# 🗺️ PROJECT ATLAS [MAX AI]

**Last Updated:** 2025-12-14
**Version:** 2.0 (Deep Scan)

---

## 1. 📂 Структура и Обязанности

### 🧠 Core Tier (`src/core`)

Ядро системы. Содержит бизнес-логику, память и интеграции.

#### 🏗️ Base Logic

- 📄 `memory.py` -> (Роль: **Brain / Database**).
  - **Ключевые классы:** `MemoryManager`, `Message`, `Fact`.
  - **Обязанности:** Хранение сообщений (SQLite), Векторный поиск (Facts), Суммаризация.
  - ⚠️ **Сложность:** Высокая (Mixing SQL, LLM calls, Logic).
- 📄 `autogpt.py` -> (Роль: **Autonomous Agent**).
  - **Ключевые классы:** `AutoGPTAgent`, `Step`, `Plan`.
  - **Обязанности:** Выполнение многошаговых задач, использование инструментов.
- 📄 `tools.py` -> (Роль: **Toolbox**).
  - **Ключевые классы:** `ToolExecutor`.
  - **Обязанности:** Файловые операции, WebSearch, Shell (via `safe_shell.py`).
- 📄 `lm_client.py` -> (Роль: **LLM Driver**).
  - **Обязанности:** Обёртка над OpenAI SDK для LM Studio.

#### 🔀 Routing & Intelligence

- 📂 `routing/` -> (Роль: **Switchboard**).
  - `smart_router.py`: Главный оркестратор (6-layer pipeline).
  - `semantic_router.py`: Векторная классификация намерений.
  - `grammar.py`: GBNF грамматики для структурированного вывода.
  - `privacy_guard.py`: Защита приватных данных.
- 📂 `cognitive/` -> (Роль: **Deep Thinking**).
  - `graph.py`: LangGraph workflow для "System 2" мышления.
  - `nodes/`: Узлы графа (Planner, Executor, Critic).

#### 📊 Observability & Adaptation

- 📂 `metrics/` -> (Роль: **Telemetry**).
  - `engine.py`, `storage.py`: Сбор и хранение метрик производительности.
- 📄 `adaptation.py`: Система адаптации промптов на основе фидбека.
- 📄 `self_reflection.py`: Анализ ошибок и самокоррекция.

#### 🧠 Consciousness Layer (NEW 2025-12-14)

- 📂 `soul/` -> (Роль: **Meta-Cognition / BDI State**).
  - `models.py`: Pydantic schemas (SoulState, BDIState, Identity).
  - `soul_manager.py`: Singleton с кэшированием, Time Awareness, Anti-Lag.
  - Инъекция аксиом в System Prompt.
- 📂 `tool_registry/` -> (Роль: **Tool Registration**).
  - `registry.py`: Декоратор @register с авто JSON Schema.
- 📂 `utils/` -> (Роль: **Utilities**).
  - `sanitizer.py`: Очистка вывода от артефактов модели.

---

### � API Tier (`src/api`)

Точка входа (FastAPI).

- 📄 `app.py` -> (Роль: **Hub / Entry Point**).
  - **Обязанности:** Lifespan management, инициализация всех синглтонов (Memory, Router, etc.).
- � `routers/` -> (Роль: **Controller**).
  - `chat.py`: **Main Endpoint**. SSE Streaming, обработка запросов, интеграция с Router.
  - `agent.py`: Управление AutoGPT.
  - `documents.py`: RAG API.
  - `backup.py`: Управление бэкапами (вызов `src/core/backup.py`).

---

### 🖥️ Frontend Tier (`frontend`)

React + Vite UI.

- 📄 `src/App.tsx` -> (Роль: **Monolith Root**).
  - **Обязанности:** Глобальный стейт, роутинг (упрощенный). Требует рефакторинга.
- 📂 `src/components/` -> (Роль: **UI Bricks**).
  - `ChatWindow.tsx`: Основное окно чата.
  - `ThinkingPanel.tsx`: Визуализация "мыслей" (Cognitive Stream).
  - `SynapticStream.tsx`: Анимация активности нейросети.
  - `DenseCore.tsx`: 3D/2D визуализация ядра.

---

## 2. 🕸️ Поток Данных (Data Flow High-Level)

### 🔄 1. Standard Chat Loop

**User Request** -> `POST /api/chat` -> `routers/chat.py`
  ⬇️
**Layer 1: Routing (`SmartRouter`)**

- Проверка безопасности (`PrivacyGuard`).
- Определение интента (`SemanticRouter` / `LLMRouter`).
  ⬇️
**Decision Point:**
- **A. Simple Chat:** -> `lm_client.chat()` (Direct Response).
- **B. Complex Task:** -> `AutoGPTAgent.set_goal()` -> Execution Loop.
- **C. Deep Thinking:** -> `CognitiveGraph.run()` -> Planning -> Reasoning.
  ⬇️
**Execution (if B or C):**
- `Tools` (File/Web) -> `Runtime` -> `Result`.
  ⬇️
**Response:**
- Stream (SSE) -> `Frontend (SynapticStream)`.
- Save to DB -> `MemoryManager` (Background Task).

### 🧠 2. Memory & Learning Loop

**Message Added** -> `MemoryManager`
  ⬇️
**Background Tasks:**

  1. **Fact Extraction:** `_extract_facts` (Phi-3 JSON Mode) -> `memory_facts` table.
  2. **Summarization:** `_maybe_summarize` (Recursive update) -> `conversation_summaries` table.
  3. **Metrics:** `MetricsEngine` records latency/tokens.

---

## 3. ⚫ СЛЕПЫЕ ЗОНЫ (BLIND SPOTS)

### 🕸️ Orphans (Файлы-Сироты)

*Файлы, которые существуют, но на них не найдено явных ссылок в коде.*

1. **`src/core/pybox.py`**
   - **Диагноз:** Песочница на основе AST. Не используется. В `tools.py` используется `safe_shell.py`.
   - **Риск:** Мертвый код, создающий ложное ощущение безопасности.
2. **`src/core/math_utils.py`**
   - **Диагноз:** Простые функции (cosine_sim). Скорее всего дублируются внутри `memory.py` или `semantic_router.py`.
   - **Риск:** Дублирование кода.

### 📦 Black Boxes (Сложные модули)

1. **`src/core/routing/`**
   - Pipeline из 6 слоев. Логика распределена между `smart_router.py`, `cpu_router` и `llm_router`. Сложно отлаживать, почему запрос пошел именно так.
2. **`src/core/memory.py`**
   - Класс `MemoryManager` (900 строк). Делает ВСЁ: SQL, Vector Search, Summary, Fact Extraction. Это God Object.

### ⚠️ Risk Zones (Зоны Риска)

1. **Frontend Monolith (`App.tsx`)**
   - Размер файла ~30KB (1000+ строк). Сдерживает развитие UI.
2. **Shell Execution**
   - `tools.py` полагается на `safe_shell.py`, но список разрешенных команд (`whitelist`) требует постоянного обновления.

---

## 4. 📝 ПЛАН ПРОВЕРКИ (CHECKLIST)

### Priority: Critical 🔴

- [ ] **Memory Integrity:** Проверить, что факты действительно извлекаются и сохраняются (тест `test_memory_facts.py`).
- [ ] **Router Validation:** Проверить `SmartRouter` на пограничных случаях (смена контекста, атаки).

### Priority: High 🟠

- [ ] **Orphan Cleanup:** Удалить `pybox.py` и `math_utils.py` (или интегрировать их).
- [ ] **Frontend Refactor:** Разбить `App.tsx` на `ChatContext` и `Layout`.

### Priority: Medium 🟡

- [ ] **Cognitive Audit:** Проверить, что `graph.py` корректно обрабатывает циклы (Verifier -> Planner).
