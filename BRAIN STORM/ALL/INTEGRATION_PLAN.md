# MAX AI: Integration Plan for Advanced Reasoning & Multi-Agent Architecture

> **Дата:** 2025-12-13
> **Автор:** Solutions Architect Analysis
> **Статус:** DESIGN PHASE
> **Версия:** 1.0

---

## Executive Summary (Резюме)

На основе анализа трех глубоких исследований и текущей архитектуры MAX AI выделены **3 стратегических вектора развития**:

1. **Когнитивная Оркестрация (Cognitive Orchestration)** — System 2 мышление через LangGraph
2. **Параллельные Микро-Агенты (Parallel Micro-Agents)** — параллельные слоты через OLLAMA_NUM_PARALLEL
3. **Гетерогенный Инференс (Heterogeneous Inference)** — CPU-резидентные микро-модели для маршрутизации/валидации

---

## ЭТАП 0: VISIONARY CHECK — Скрытые Возможности

### "Низко висящие фрукты" (Low Hanging Fruits) - малые усилия, высокая ценность

| # | Фича | Усилия | Ценность | Текущий статус MAX |
|---|------|--------|----------|-------------------|
| 1 | **Thinking Tags Streaming** | LOW | HIGH | ✅ УЖЕ ЕСТЬ в `streaming.py` |
| 2 | **KV Cache Quantization** | LOW | HIGH | ❌ Нет (Ollama config) |
| 3 | **OLLAMA_NUM_PARALLEL** | LOW | MEDIUM | ❌ Нет (env config) |
| 4 | **Task Type Routing** | LOW | HIGH | ✅ УЖЕ ЕСТЬ в `routing.py` |
| 5 | **Confidence Scoring** | MEDIUM | HIGH | ⚠️ Частично в `metrics/` |

### Индустриальный Стандарт (Best Practice)

| Практика | Лидеры рынка | Статус MAX | Gap |
|----------|--------------|------------|-----|
| Generator-Verifier-Refiner | OpenAI o1, DeepSeek-R1 | ❌ | Критичный |
| Structured Output (JSON Schema) | GPT-4, Claude | ⚠️ Частично | Средний |
| Self-Reflection Loop | Reflexion, AutoGPT | ✅ `ReflectiveAgent` | Минимальный |
| Dynamic Temperature/TopP | Entropix | ❌ | Низкий приоритет |
| Multi-Slot Batching | vLLM, Ollama 0.2+ | ❌ | Критичный |

### Синергия с Существующими Компонентами

```
┌─────────────────────────────────────────────────────────────────┐
│                     MAX AI Current Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [ContextOrchestrator] ←──── NEW: CognitiveOrchestrator         │
│         ↓                           │                            │
│  [SemanticRouter]      ←──── NEW: EntropyRouter (Entropix)      │
│         ↓                           │                            │
│  [LMStudioClient]      ←──── NEW: ParallelSlotManager           │
│         ↓                           │                            │
│  [AutoGPTAgent]        ←──── ENHANCE: Generator-Verifier Loop   │
│         ↓                           │                            │
│  [ReflectiveAgent]     ←──── ENHANCE: Memory Node (Summarizer)  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Векторы Развития (Roadmap)

1. **V1.3 (Краткосрочный):** Cognitive Loop + Parallel Slots
2. **V1.4 (Среднесрочный):** Heterogeneous Inference (CPU Router)
3. **V2.0 (Долгосрочный):** Full LangGraph Migration + BitNet Support

---

## ЭТАП 0.5: ОЦЕНКА РИСКОВ (RISK ASSESSMENT)

### Критические изменения (Breaking Changes)

| Компонент | Риск | Митигация |
|-----------|------|-----------|
| `LMStudioClient.chat()` | MEDIUM | Добавить флаг `cognitive_mode=False` |
| `AutoGPTAgent` | LOW | Расширить через наследование |
| `ContextOrchestrator` | LOW | Добавить новый метод `build_cognitive_context()` |
| Frontend SSE | LOW | Новые event types: `VERIFICATION`, `REFINEMENT` |

### Performance Budget

| Операция | Текущее | С Cognitive Loop | Budget |
|----------|---------|------------------|--------|
| Simple Chat | 2-3s | 2-3s (без изменений) | ✅ |
| Complex Task | 5-10s | 30-60s (expected) | ⚠️ UX Warning |
| Parallel Agents | N/A | 14s (vs 20s sequential) | ✅ 30% gain |
| VRAM Usage | ~10GB | ~10GB + KV slots | ⚠️ 16GB limit |

### Security Surface

| Вектор | Риск | Митигация |
|--------|------|-----------|
| JSON Schema Injection | LOW | Outlines/Guidance validation |
| Context Overflow | MEDIUM | `MemoryNode` summarization |
| Prompt Injection via Verification | LOW | Separate system prompts |

### Dependency Risk

| Библиотека | Стабильность | Необходимость |
|------------|--------------|---------------|
| LangGraph | ⭐⭐⭐⭐ | OPTIONAL (можно без) |
| Outlines | ⭐⭐⭐ | REQUIRED (Structured Verification) |
| orjson | ⭐⭐⭐⭐⭐ | REQUIRED (Fast Parsing) |
| pydantic | ⭐⭐⭐⭐⭐ | УЖЕ ЕСТЬ |
| asyncio | ⭐⭐⭐⭐⭐ | УЖЕ ЕСТЬ |

---

## ЭТАП 1: ТЕХНИЧЕСКИЙ ДИЗАЙН

### 1.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        COGNITIVE ORCHESTRATION LAYER                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   User Request                                                            │
│        │                                                                  │
│        ▼                                                                  │
│   ┌─────────────┐                                                         │
│   │   Router    │ ←── Classify: SIMPLE | COMPLEX | VISION                │
│   │  (CPU/GPU)  │                                                         │
│   └──────┬──────┘                                                         │
│          │                                                                │
│    ┌─────┴─────┐                                                          │
│    │           │                                                          │
│    ▼           ▼                                                          │
│ SIMPLE      COMPLEX                                                       │
│    │           │                                                          │
│    │      ┌────┴────────────────────────────────────────┐                │
│    │      │         COGNITIVE LOOP (LangGraph)          │                │
│    │      │                                              │                │
│    │      │  ┌─────────┐    ┌──────────┐    ┌────────┐ │                │
│    │      │  │ PLANNER │───▶│ EXECUTOR │───▶│VERIFIER│ │                │
│    │      │  └─────────┘    └──────────┘    └────┬───┘ │                │
│    │      │                                      │      │                │
│    │      │       ┌──────────────────────────────┘      │                │
│    │      │       │                                      │                │
│    │      │       ▼         score < 0.9?                │                │
│    │      │  ┌─────────┐         │                      │                │
│    │      │  │ MEMORY  │◀────────┘                      │                │
│    │      │  │  NODE   │ (Summarize failures)           │                │
│    │      │  └────┬────┘                                │                │
│    │      │       │                                      │                │
│    │      │       └──────▶ Back to EXECUTOR             │                │
│    │      │                                              │                │
│    │      │  *New: Fail-Fast Check after PLANNER*        │                │
│    │      └──────────────────────────────────────────────┘                │
│    │                          │                                           │
│    ▼                          ▼                                           │
│   Response                 Response                                       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 New Modules Structure

```
src/core/
├── cognitive/                    # NEW PACKAGE
│   ├── __init__.py
│   ├── types.py                  # AgentState, CognitiveConfig
│   ├── graph.py                  # LangGraph StateGraph definition
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── planner.py            # Task decomposition
│   │   ├── executor.py           # CoT execution with <think> tags
│   │   ├── verifier.py           # Critique & score
│   │   └── memory.py             # Failure summarization
│   └── prompts.py                # System prompts for each node
│
├── parallel/                     # NEW PACKAGE
│   ├── __init__.py
│   ├── slot_manager.py           # OLLAMA_NUM_PARALLEL management
│   ├── fan_out.py                # Async fan-out pattern
│   └── batch_collector.py        # Result aggregation
│
└── routing/                      # ENHANCE existing
    ├── entropy_router.py         # NEW: Entropix-style routing
    └── cpu_router.py             # NEW: CPU-resident classifier
```

### 1.3 Data Structures

```python
# src/core/cognitive/types.py

from typing import TypedDict, List, Optional
from enum import Enum
from dataclasses import dataclass

class CognitiveState(TypedDict):
    """State passed between LangGraph nodes."""
    input: str                      # Original user request
    conversation_id: str            # For memory context
    plan: Optional[str]             # Decomposed plan
    steps: List[str]                # Executed steps
    draft_answer: str               # Current draft
    critique: str                   # Verification feedback
    score: float                    # Quality score (0-1)
    iterations: int                 # Cycle counter
    past_failures: List[str]        # Summarized failures
    thinking_tokens: List[str]      # <think> content for UI

class VerificationResult(Enum):
    VALID = "valid"
    NEEDS_REFINEMENT = "needs_refinement"
    CRITICAL_ERROR = "critical_error"

@dataclass
class CognitiveConfig:
    """Configuration for cognitive loop."""
    max_iterations: int = 5
    verification_threshold: float = 0.85
    enable_cot: bool = True
    enable_streaming: bool = True
    model_override: Optional[str] = None
    fallback_parsing: bool = True # Regex backup if JSON fails
```

### 1.4 Integration Points

| Existing Component | Integration Method | Changes Required |
|-------------------|-------------------|------------------|
| `LMStudioClient` | Composition | Add `cognitive_chat()` method |
| `ContextOrchestrator` | Inheritance | Extend with cognitive context |
| `AutoGPTAgent` | Composition | Use cognitive loop for complex tasks |
| `streaming.py` | Extension | New event types + **Thinking Pulse** (HeartbeatGenerator) + **Flush Logic** |
| `chat.py` router | Parameter | `cognitive=true` query param |

---

## ЭТАП 2: IMPLEMENTATION PLAN

### Phase 1: Cognitive Loop Core (Приоритет: HIGH)

**Файлы для создания:**

1. `src/core/cognitive/__init__.py`
2. `src/core/cognitive/types.py`
3. `src/core/cognitive/prompts.py` (Must include `{past_failures}` injection)
4. `src/core/cognitive/nodes/planner.py`
5. `src/core/cognitive/nodes/executor.py`
6. `src/core/cognitive/nodes/verifier.py`
7. `src/core/cognitive/nodes/memory.py`
7. `src/core/cognitive/nodes/memory.py`
8. `src/core/cognitive/graph.py`
9. `src/core/math_utils.py` (**NEW**: Unified cosine similarity)

**Ключевой код (псевдо):**

```python
# src/core/cognitive/graph.py

from langgraph.graph import StateGraph, END
from .types import CognitiveState
from .nodes import planner, executor, verifier, memory
# Note: Use orjson for state serialization speedup

def build_cognitive_graph() -> StateGraph:
    """Build the Generator-Verifier-Refiner graph."""

    builder = StateGraph(CognitiveState)

    # Add nodes
    builder.add_node("planner", planner.plan_task)
    builder.add_node("executor", executor.execute_with_cot)
    builder.add_node("verifier", verifier.verify_answer)
    builder.add_node("memory", memory.summarize_failure)

    # Define edges
    builder.set_entry_point("planner")
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "verifier")

    # Conditional routing from verifier
    builder.add_conditional_edges(
        "verifier",
        route_verification,
        {
            "accept": END,
            "refine": "memory",
            "abort": END
        }
    )

    builder.add_edge("memory", "executor")

    return builder.compile()

def route_verification(state: CognitiveState) -> str:
    """Route based on verification result."""
    if state["score"] >= 0.85:
        return "accept"
    if state["iterations"] >= 5:
        return "abort"
    return "refine"
```

### Phase 2: Parallel Slots (Приоритет: MEDIUM)

**Конфигурация Ollama:**

```bash
# Environment variables for multi-agent
export OLLAMA_NUM_PARALLEL=2 # Start safe (was 4)
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_FLASH_ATTENTION=1
```

**Файлы для создания:**

1. `src/core/parallel/__init__.py`
2. `src/core/parallel/slot_manager.py` (**NOTE**: Must implement Priority Queue: User > Background)
3. `src/core/parallel/fan_out.py`

**Ключевой код:**

```python
# src/core/parallel/fan_out.py

import asyncio
from typing import List, Callable, Any

# Suggestion: DynamicSlotManager class to monitor VRAM
# before spawning too many tasks.

async def fan_out_tasks(
    tasks: List[Callable],
    max_parallel: int = 4
) -> List[Any]:
    """
    Execute multiple LLM calls in parallel using Ollama slots.

    Each task should be an async function that calls LMStudioClient.
    Ollama's continuous batching handles the actual parallelism.
    """
    semaphore = asyncio.Semaphore(max_parallel)

    async def bounded_task(task):
        async with semaphore:
            return await task()

    return await asyncio.gather(*[bounded_task(t) for t in tasks])

    # Note: Must send "Queue Heartbeat" events if slot wait > 1s
    # Note: Hard limit num_ctx=8192 to prevent OOM

### Phase 3: Frontend (React) (Приоритет: HIGH)

**Задачи:**

- [ ] **useChat hook:** Handle `queue_update` & `pulse` events
- [ ] **ThinkingPanel:** Add "Pulse" visuals (Red/Yellow state for timeout)
- [ ] **MessageBubble:** Add "Queued... (Pos #)" indicator
- [ ] **App.tsx:** Show global queue status if busy

```

### Phase 4: CPU Router (Приоритет: LOW — Future)

**Архитектура "Рептильный мозг":**

```python
# src/core/routing/cpu_router.py (FUTURE)

class CPURouter:
    """
    Lightweight CPU-resident model for intent classification.

    Uses Phi-3.5-mini (Q4_K_M) on CPU for:
    - Intent classification
    - PII detection
    - RAG chunk reranking
    """

    def __init__(self, model_path: str):
        # Load via llama-cpp-python with n_gpu_layers=0
        pass

    async def classify_intent(self, query: str) -> str:
        """Fast intent classification without GPU."""
        pass
```

---

## ЭТАП 3: Definition of Done

### Критерии завершения Phase 1

- [ ] Код компилируется без warnings
- [ ] Cognitive loop работает для complex tasks
- [ ] Streaming <think> tags отображаются в UI
- [ ] **Streaming Pulse (Keep-Alive)** работает
- [ ] Verification score влияет на iteration
- [ ] Memory node сжимает историю ошибок
- [ ] Интеграция с существующим `chat.py` через флаг
- [ ] Unit tests для каждого node
- [ ] Документация в комментариях

### Критерии завершения Phase 2

- [ ] OLLAMA_NUM_PARALLEL работает
- [ ] Fan-out pattern для 2-3 агентов
- [ ] Throughput измерен и улучшен на 30%+
- [ ] Нет OOM при 16GB VRAM

### Критерии завершения Phase 3 (Frontend)

- [ ] "Pulse" индикатор реагирует на backend events
- [ ] Очередь (Queue Position) отображается пользователю
- [ ] Ошибки стриминга обрабатываются graceful (не висят вечно)

---

## ЭТАП 4: BONUS FEATURES MENU

### Реализуемые сейчас (Low Effort)

| # | Идея | Почему круто | Сложность |
|---|------|--------------|-----------|
| 1 | **Confidence Badge в UI** | Визуализация уверенности модели | LOW |
| 2 | **Iteration Counter в SSE** | Показать прогресс cognitive loop | LOW |
| 3 | **KV Cache Config** | Экономия VRAM для длинных сессий | LOW |

### Требуют отдельного этапа (Medium Effort)

| # | Идея | Почему круто | Сложность |
|---|------|--------------|-----------|
| 4 | **Chain of Verification (CoVe)** | Атомарная проверка фактов против галлюцинаций | MEDIUM |
| 5 | **Multi-Persona Debate** | A/B агенты с разными системными промптами | MEDIUM |
| 6 | **Dynamic g1 Prompting** | "Предложи 3 метода решения" auto-inject | MEDIUM |

### Долгосрочные (High Effort)

| # | Идея | Почему круто | Сложность |
|---|------|--------------|-----------|
| 7 | **Entropix Integration** | Адаптивный sampling на основе энтропии | HIGH |
| 8 | **Outlines JSON Grammar** | Гарантированный структурированный вывод | HIGH |
| 9 | **CPU Router (Phi-3.5)** | Гетерогенный инференс для экономии GPU | HIGH |
| 10 | **BitNet Support** | Нативные 1-bit модели когда появятся | FUTURE |

---

## Приложение A: Рекомендуемые Модели

| Задача | Модель | Квантование | VRAM |
|--------|--------|-------------|------|
| Main Reasoning | Qwen2.5-14B-Instruct | Q4_K_M | ~9GB |
| Deep Thinking | DeepSeek-R1-Distill-Qwen-14B | Q4_K_M | ~9GB |
| Vision | LLaVA-1.6-mistral-7B | Q4_K_M | ~5GB |
| Quick Tasks | Qwen2.5-7B-Instruct | Q4_K_M | ~5GB |
| CPU Router (Future) | Phi-3.5-mini | Q4_K_M | 0 (CPU) |

## Приложение B: VRAM Budget Calculator

```
16GB VRAM Budget:

Model Weights (Qwen-14B Q4_K_M):     ~9.0 GB
CUDA Overhead:                        ~0.7 GB
Activation Buffers:                   ~1.0 GB
────────────────────────────────────────────
Available for KV Cache:               ~5.3 GB

KV Cache per Token (GQA):             ~0.19 MB
Max Context (1 slot):                 ~27,000 tokens
Max Context (2 slots):                ~13,500 tokens each (RECOMMENDED)
Max Context (4 slots):                ~6,750 tokens each (RISKY)
```

## Приложение C: Environment Setup

```bash
# .env additions for cognitive features

# Ollama Parallel Slots
OLLAMA_NUM_PARALLEL=2
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_FLASH_ATTENTION=1

# Cognitive Loop
MAX_COGNITIVE_ITERATIONS=5
VERIFICATION_THRESHOLD=0.85
ENABLE_COT_STREAMING=true

# KV Cache Optimization (if supported)
OLLAMA_KV_CACHE_TYPE=q8_0
```

---

## Next Steps

1. **Утвердить план** с пользователем
2. **Phase 1 Implementation** — Cognitive Loop (~4-6 часов)
3. **Phase 2 Implementation** — Parallel Slots (~2-3 часа)
4. **Phase 3 Implementation** — Frontend UX (~2 часа)
5. **Testing & Integration** (~2 часа)
5. **Documentation Update**

---

*Документ создан на основе анализа исследований:*

- *Оптимизация мышления малых LLM.txt*
- *Параллельные микроагенты на одной GPU.txt*
- *Микромодели: Будущее локальных ИИ-агентов.txt*
