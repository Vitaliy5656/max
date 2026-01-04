# 🧠 SmartRouter Features Plan

> **Создан:** 2025-12-14
> **Статус:** В разработке
> **Приоритет:** Высокий
> **Оптимизирован:** ✅ [router_optimization.md](./optimization/router_optimization.md)

---

## 🏗️ 6-LAYER PIPELINE ARCHITECTURE (Production Grade)

| Layer | Component | Latency | Status |
|-------|-----------|---------|--------|
| 1 | **Guardrails** (Regex/Blocklist) | <1ms | ✅ Ready |
| 2 | **Semantic Router** (Vector Search) | ~10ms | 🆕 CRITICAL |
| 3 | **Cache** (Semantic/Hash) | ~2ms | ✅ Ready |
| 4 | **LLM Router** + GBNF Grammar | ~400ms | 🆕 RELIABILITY |
| 5 | **CPU Fallback** | 0ms | ✅ Ready |
| 6 | **Tracing & Feedback** | Async | 🆕 QUALITY |

---

## 🚀 Performance Budget

| Сценарий | Target | Как достичь |
|----------|--------|-------------|
| **Cached** | < 50ms | LRU cache для повторных запросов |
| **Average** | < 500ms | Single LLM call + CPU features |
| **Worst** | < 100ms | Timeout → CPU fallback |

### 🎯 Ключевые Правила

#### 1. Single LLM Call (CRITICAL)

```python
# ❌ BAD: Multiple LLM calls = 2000ms+
intent = await llm_router.route(msg)      # 500ms
safety = await llm_check_safety(msg)      # 500ms
emotion = await llm_detect_emotion(msg)   # 500ms

# ✅ GOOD: One LLM call + CPU features = 520ms
decision = await llm_router.route(msg)    # 500ms
safety = cpu_check_safety(msg)            # 10ms
emotion = cpu_detect_emotion(msg)         # 5ms
```

#### 2. LLM Cache + Timeout Fallback

```python
# ⚠️ ВАЖНО: Cache по ПОЛНОМУ hash, НЕ по prefix!
# Prefix опасен: "Напиши код...Python" == "Напиши код...C++"
cache_key = hash(message)  # ✅ Уникальный
cache = TTLCache(maxsize=100, ttl=300)

# Fallback: zero worst-case
try:
    result = await asyncio.wait_for(llm_router.route(msg), timeout=0.5)
except asyncio.TimeoutError:
    result = cpu_router.route(msg)  # Instant fallback
```

#### 2.5. Speculative Decoding (Zero Latency Greetings)

```python
# Для simple_greeting — не вызываем LLM вообще!
# ⚠️ ВАЖНО: Нужно МНОГО вариантов (20+), иначе виден паттерн!
GREETING_RESPONSES = [
    "Привет!", "Слушаю.", "На связи.", "Чем помочь?",
    "Здравствуй!", "Рад тебя слышать!", "Привет, что нового?",
    "Хей!", "Приветствую!", "Доброго времени!",
    # ... 20+ вариантов в реальной реализации
]
if cpu_router.is_simple_greeting(message):
    return random.choice(GREETING_RESPONSES)  # 0ms!
```

#### 3. Privacy Check FIRST (Before LLM)

```python
# Check unlock phrase BEFORE expensive LLM call
if UNLOCK_PATTERN.match(message):
    session.private_unlocked = True
    return quick_response("Привет! Личная память разблокирована.")
```

#### 4. Skip RAG for Simple Intents

```python
SKIP_RAG_INTENTS = {IntentType.GREETING, IntentType.MATH}
use_rag = decision.intent not in SKIP_RAG_INTENTS
# Saves 100-500ms for simple queries
```

### 📊 Feature Latency Matrix

| Фича | Latency | Метод |
|------|---------|-------|
| Auto Mode | 0ms | Proxy from LLM Router |
| Temperature | 0ms | Lookup table |
| RAG Trigger | -100ms | Skip saves time |
| Context Optimizer | -50ms | Fewer tokens |
| Cost Estimator | 0ms | Simple formula |
| Privacy Lock | 5ms | Compiled regex |
| Safety Filter | 10ms | Set lookup O(1) |
| Streaming Strategy | 0ms | Decision only |
| Parallel Decomposition | 100ms | Only for complex |
| Emotional Tone | 5ms | CPU heuristics |

### 🔧 Pipeline Architecture (Референс)

```python
class SmartRouter:
    async def process(self, message: str) -> RouteResult:
        # Layer 1: INSTANT CHECKS (CPU) - 0-5ms
        if self._check_privacy_unlock(message):
            return RouteResult(action="unlock_memory")
        
        if self._is_simple_greeting(message):
            return RouteResult(response=random.choice(GREETINGS))  # 0ms!

        # Layer 2: CACHE - 0ms
        cache_key = hash(message)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Layer 3: LLM ROUTING - ~500ms (with fallback)
        route = await self._llm_route_with_fallback(message)
        
        # Layer 4: CPU POST-PROCESSING - 0ms
        route.temperature = self.temp_map.get(route.intent, 0.7)
        route.prompt = self.prompt_library.get(route.intent)
        
        self.cache[cache_key] = route
        return route
```

---

## 🆕 ADVANCED FEATURES (Production Grade)

### 17. Semantic Router (Vector Search) ⭐ CRITICAL

> **Вместо Regex → 10ms умный поиск, снимает 60% нагрузки с LLM**

```python
# semantic_router или FAISS/ChromaDB
from sentence_transformers import SentenceTransformer

embed_model = SentenceTransformer("all-MiniLM-L6-v2")  # 3ms
vector_db = FAISSIndex()

# Training: добавляем примеры запросов
vector_db.add("Напиши код для сортировки", intent="coding")
vector_db.add("Как ты?", intent="greeting")
vector_db.add("Найди информацию о...", intent="search")

# Runtime: 5-10ms вместо 500ms LLM
async def semantic_route(message: str) -> Optional[str]:
    embedding = embed_model.encode(message)  # 3ms
    match = vector_db.search(embedding, k=1)  # 2ms
    if match.score > 0.85:
        return match.intent  # Confident match, skip LLM!
    return None  # Fallback to LLM
```

**Библиотеки:** `semantic-router`, `faiss-cpu`, `chromadb`

---

### 18. GBNF Grammar (Structured Outputs) ⭐ RELIABILITY

> **Гарантия валидного JSON от LLM, 0 ошибок парсинга**

```python
# Для llama.cpp / LM Studio с grammar support
ROUTING_GRAMMAR = """
root ::= "{" ws "\"intent\":" ws intent "," ws "\"complexity\":" ws complexity "}"
intent ::= "\"coding\"" | "\"search\"" | "\"chat\"" | "\"greeting\""
complexity ::= "\"simple\"" | "\"medium\"" | "\"complex\""
ws ::= [ \\t\\n]*
"""

# LM Studio API (если поддерживается)
response = await client.chat.completions.create(
    model="bartowski/phi-3.5-mini-instruct",
    messages=[...],
    extra_body={"grammar": ROUTING_GRAMMAR}  # 100% valid JSON!
)
```

**Fallback:** Если grammar не поддерживается → текущий regex парсинг

---

### 19. Observability & Feedback Loop ⭐ QUALITY

> **Узнаём когда роутер ошибся, собираем данные для улучшения**

```python
@dataclass
class RoutingTrace:
    timestamp: datetime
    input_message: str
    predicted_intent: str
    predicted_complexity: str
    routing_time_ms: float
    user_feedback: Optional[str] = None  # "good" / "bad"
    actual_intent: Optional[str] = None  # Если юзер исправил

# Логируем каждое решение
async def route_with_trace(message: str) -> RouteResult:
    start = time.perf_counter()
    result = await smart_router.route(message)
    
    trace = RoutingTrace(
        input_message=message,
        predicted_intent=result.intent,
        routing_time_ms=(time.perf_counter() - start) * 1000
    )
    await trace_storage.save(trace)  # Async, не блокирует
    return result
```

**UI Feedback:**

```
[Сообщение] ... 
           [👍] [👎 Неверно понял]  ← Если нажато → сохраняем для обучения
```

---

### 20. Entity Extraction + Smart Summarization ⭐

> **Не режем контекст тупо, а сжимаем в сущности**

```python
# Вместо: "Напомни купить хлеб" → mode=standard
# Делаем: Intent=TASK, Entities={item: "хлеб", action: "buy", remind: true}

# Summarization on idle
async def summarize_old_messages(session_id: str):
    """Фоновый процесс когда юзер молчит 30+ сек"""
    old_messages = await get_messages_older_than(session_id, minutes=5)
    if len(old_messages) > 20:
        summary = await llm.summarize(old_messages)
        await replace_with_summary(session_id, old_messages, summary)
        # 20 сообщений → 1 summary = меньше токенов, та же суть
```

---

## ⚡ ADVANCED PATTERNS (Best Practices 2025)

### 21. Fire-and-Forget Side Effects

> **Tracing и Learning НЕ должны блокировать ответ пользователю**

```python
async def process(self, message: str) -> RouteResult:
    route = await self._calculate_route(message)
    
    # 🚀 FIRE-AND-FORGET: Не ждем завершения!
    # Они выполнятся в фоне, пока юзер уже читает ответ
    asyncio.create_task(self.trace_storage.save(route, message))
    asyncio.create_task(self.preference_learner.analyze(message, route))
    
    return route  # Сразу возвращаем, не блокируемся
```

⚠️ **Важно:** Для критических задач (типа сохранения данных) использовать `TaskGroup` с обработкой ошибок.

---

### 22. Dynamic Thresholds по Intent

> **Разные intent = разная цена ошибки = разные пороги!**

```python
# src/core/routing/thresholds.py

INTENT_THRESHOLDS = {
    "greeting": 0.75,       # Можно ошибиться, не страшно
    "search": 0.80,         # Средний риск
    "coding": 0.82,         # Важно понять правильно
    "question": 0.80,       # Стандартный порог
    "system_cmd": 0.92,     # 🔥 СТРОГИЙ! Опасные действия
    "privacy_unlock": 0.95, # ⚠️ ТОЛЬКО точное совпадение
    "delete": 0.95,         # Критичные операции
}

# В semantic router:
async def semantic_route(message: str) -> Optional[str]:
    match = vector_db.search(embedding, k=1)
    threshold = INTENT_THRESHOLDS.get(match.intent, 0.85)
    
    if match.score > threshold:
        return match.intent  # Confident!
    return None  # → LLM fallback
```

---

### 23. Shadow Mode (A/B Testing для роутера)

> **Тестируем новую версию без риска для пользователя**

```python
class SmartRouter:
    def __init__(self):
        self.primary_router = SemanticRouter(version="v1")
        self.shadow_router = SemanticRouter(version="v2")  # Новая версия
        self.shadow_mode = True  # Включить теневой режим
    
    async def route(self, message: str) -> RouteResult:
        # Основной роутер — влияет на ответ
        result = await self.primary_router.route(message)
        
        if self.shadow_mode:
            # Теневой роутер — только логирование, 0 влияния
            asyncio.create_task(self._shadow_compare(message, result))
        
        return result
    
    async def _shadow_compare(self, message: str, primary_result: RouteResult):
        shadow_result = await self.shadow_router.route(message)
        
        if shadow_result.intent != primary_result.intent:
            await self.log_discrepancy(
                message=message,
                primary=primary_result,
                shadow=shadow_result
            )
            # Потом смотрим логи: "Кто был прав?"
```

**Workflow:**

1. Включаем `shadow_mode = True`
2. Даём поработать неделю
3. Смотрим логи: новый роутер лучше? → выкатываем
4. Хуже? → откатываемся без потерь

---

## � PRE-CODING CHECKLIST (Избежать багов!)

### 24. Cache Invalidation with Version

> **Проблема:** Если обновишь промт/модель — старый кэш станет ядом!

```python
# src/core/routing/cache_manager.py
import hashlib

SYSTEM_VERSION = "1.0.0"  # ⚠️ МЕНЯТЬ при обновлении логики!

def get_cache_key(message: str) -> str:
    """Версия + сообщение = безопасный кэш"""
    raw_key = f"{SYSTEM_VERSION}:{message}"
    return hashlib.sha256(raw_key.encode()).hexdigest()

# При обновлении:
# 1. Меняем SYSTEM_VERSION = "1.0.1"
# 2. Старый кэш автоматически игнорируется
```

---

### 25. Bootstrap Dataset для Semantic Router

> **Проблема:** Semantic Router пустой на старте = hit rate 0%  
> **Решение:** 200-300 синтетических примеров = мгновенная точность ~80%

```yaml
# data/semantic_training.yaml

CODING:
  - "Напиши функцию"
  - "Пофикси баг"
  - "Сделай скрипт"
  - "Отрефактори код"
  - "Добавь комментарии"
  # ... 50 вариаций

SEARCH:
  - "Найди информацию о"
  - "Поищи в интернете"
  - "Какие новости"
  # ... 50 вариаций

GREETING:
  - "Привет"
  - "Здравствуй"
  - "Добрый день"
  # ... 50 вариаций
```

**TODO:** Сгенерировать через GPT-4/Claude перед запуском.

---

### 26. Pydantic → GBNF (Авто-генерация грамматики)

> **Не писать GBNF руками — это боль и баги!**

```python
from pydantic import BaseModel
from typing import Literal

# 1. Определяем структуру как Pydantic модель
class RouterResponse(BaseModel):
    intent: Literal["coding", "search", "chat", "greeting"]
    complexity: Literal["simple", "medium", "complex"]
    confidence: float

# 2. Авто-генерация грамматики
from llama_cpp.llama_grammar import LlamaGrammar

grammar = LlamaGrammar.from_json_schema(
    RouterResponse.model_json_schema()
)

# 3. Использование (100% valid JSON!)
response = llm(prompt, grammar=grammar)
parsed = RouterResponse.model_validate_json(response)  # Guaranteed to work
```

---

### 27. Auto-Learning from Conversations ⭐ NEW

> **Роутер учится на лету, когда появляются новые темы**

```python
# Когда Semantic Router не уверен (score < 0.75):
# 1. LLM Router классифицирует
# 2. Пользователь подтверждает (feedback или молча)
# 3. Система АВТОМАТИЧЕСКИ добавляет пример

async def learn_from_conversation(
    message: str,
    llm_result: RouteResult,
    user_feedback: Optional[str]
):
    """Автоматическое обучение на разговорах."""
    
    if user_feedback == "bad":
        return  # Не учимся на ошибках
    
    # Добавляем как новый пример
    router.add_example(
        text=message,
        intent=llm_result.intent,
        topic=llm_result.detected_topic  # NEW: тема
    )
    
    # Сохраняем в persistent storage
    await training_db.save(message, llm_result.intent, llm_result.topic)
```

**Динамические темы:**

```yaml
# Автоматически добавляются:
ASTRONOMY:
  - "Какие характеристики у звезды Бетельгейзе?"
  
JEWELRY:
  - "Расскажи про карат в бриллианте"
  
CONSTRUCTION:
  - "Как рассчитать фундамент?"
```

**Prompt Library подбирает промт по теме:**

```python
if match.topic == "astronomy":
    prompt = prompts.get("astronomy_expert")
elif match.topic == "jewelry":
    prompt = prompts.get("jewelry_expert")
else:
    prompt = prompts.get("general")
```

---

## �📊 Текущее Состояние (Аудит)

### ✅ УЖЕ РЕАЛИЗОВАНО

| Фича | Где реализовано | Готовность |
|------|-----------------|------------|
| thinking_mode (fast/standard/deep) | `semantic_router.py`, `config.py` | 100% |
| Temperature config | `config.py` → thinking_modes | 100% |
| LLM Router (intent/complexity) | `routing/llm_router.py` (Phi-3.5) | 100% |
| CPU Router (heuristics) | `routing/cpu_router.py` | 100% |
| Entropy Router (sampling) | `routing/entropy_router.py` | 100% |
| RAG Engine | `rag.py` | 90% |
| Tools System | `tools.py` | 90% |
| Fan-Out (parallel) | `parallel/fan_out.py` | 80% |

### ⚠️ ЧАСТИЧНО РЕАЛИЗОВАНО

| Фича | Где | Что нужно |
|------|-----|-----------|
| Model Selection | `semantic_router.py` | Интеграция с LLM Router |
| Context Control | `context_orchestrator.py` | Добавить размер окна |

### ❌ НЕ РЕАЛИЗОВАНО

| Фича | Приоритет |
|------|-----------|
| **Privacy Lock System** | 🔴 HIGH |
| Streaming Strategy | 🔴 HIGH |
| Parallel Decomposition | 🔴 HIGH |
| Smart Tool Activation | 🟡 MEDIUM |
| Cost Estimator | 🟡 MEDIUM |
| Safety Filter | 🟡 MEDIUM |
| Caching Strategy | 🟡 MEDIUM |
| Emotional Tone | 🟢 LOW |
| User Preference Learning | 🟢 LOW |

---

## 🎯 Фичи к Реализации (15)

### 🔴 MANDATORY (Первая очередь)

#### 1. Auto Mode Selection

- **Что:** Автовыбор thinking_mode на основе LLM Router complexity
- **Где:** `SmartRouter.route()` → `suggested_mode`
- **Зависит от:** LLM Router ✅

#### 2. Smart Tool Activation  

- **Что:** Включение tools на основе `needs_search`, `needs_code`
- **Где:** Добавить `enable_tools[]` в результат роутинга
- **Зависит от:** LLM Router ✅

#### 8. Parallel Decomposition ⭐

- **Что:** Разбиение сложных задач на параллельные sub-tasks
- **Где:** Новый модуль `routing/decomposer.py`
- **Использует:** `fan_out.py` ✅

#### 14. Streaming Strategy ⭐

- **Что:** Решение как стримить ответ
- **Варианты:**
  - `immediate` — сразу стрим
  - `delayed` — показать "Думаю..." потом стрим
  - `chunked` — буферизованные блоки
- **Где:** `SmartRoutingResult.streaming_strategy`

#### 15. Privacy Lock System ⭐ NEW

- **Что:** Защита личных данных секретной фразой
- **Триггер:** "Привет, малыш" → `session.private_unlocked = True`
- **Где:** Новый модуль `routing/privacy_guard.py`
- **Влияет на:**
  - Memory (фильтрация фактов)
  - System prompt (не упоминать личное)
  - Session state

#### 16. Prompt Library (Hierarchical) ⭐ NEW

- **Что:** Иерархическая база системных промтов для разных ролей/задач
- **Структура:**

  ```
  CODING
    ├── CodeFixer       🔧 "Исправляй баги элегантно..."
    ├── UIDesigner      🎨 "Фокус на UX и красоте..."
    ├── Architect       📐 "Думай о масштабировании..."
    └── Optimizer       ⚡ "Ищи bottlenecks..."
  
  PSYCHOLOGY
    ├── Therapist       💚 "Мягкий, эмпатичный подход..."
    ├── Coach           🎯 "Мотивирующий, action-oriented..."
    └── CrisisHelper    🆘 "Спокойный, безопасный..."
  
  CREATIVE
    ├── StoryWriter     📖 "Яркие образы, plot twists..."
    └── CopyEditor      ✍️ "Чистый, продающий текст..."
  ```

- **Автовыбор:** SmartRouter выбирает промт по intent + keywords
- **UI Badge:** Показывает [🔧 Fix Mode] или [💚 Therapist] в сообщении
- **Где:**
  - `src/core/prompts/` — библиотека промтов
  - `src/core/prompts/library.py` — PromptLibrary class
  - `src/core/prompts/templates/*.yaml` — YAML файлы промтов
- **SmartRoutingResult:**
  - `prompt_id: "coding/fixer"`
  - `prompt_name: "CodeFixer"`
  - `prompt_icon: "🔧"`
  - `system_prompt: "..."`
- **API:** CRUD для кастомных промтов пользователя

---

### 🟡 MEDIUM (Вторая очередь)

#### 4. Context Window Optimizer

- **Что:** Решение сколько сообщений включать
- **Правила:**
  - simple → 2 сообщения
  - medium → 10 сообщений
  - complex → full history
- **Где:** `SmartRoutingResult.context_window_size`

#### 5. RAG Trigger

- **Что:** Когда включать RAG
- **Правила:**
  - skip для greeting, simple math
  - enable для document questions
- **Где:** `SmartRoutingResult.use_rag`

#### 7. Cost Estimator

- **Что:** Оценка tokens и времени
- **Где:** `SmartRoutingResult.estimated_tokens/time`

#### 9. Safety Filter

- **Что:** Определение опасных операций
- **Флаги:** file operations, system commands
- **Где:** `SmartRoutingResult.safety_level`, `requires_confirmation`

#### 12. Caching Strategy

- **Что:** Решение о кешировании
- **Правила:**
  - greeting → cache 1h
  - search → no cache
  - static → cache forever
- **Где:** `SmartRoutingResult.cache_ttl`

#### 13. Temperature Auto-Tune

- **Что:** Автонастройка temperature
- **Правила:**
  - coding → 0.3
  - creative → 0.9
  - math → 0.1
  - question → 0.7
- **Где:** `SmartRoutingResult.temperature`

---

### 🟢 LOW (Третья очередь)

#### 3. Model Selector (IF POSSIBLE)

- **Что:** Выбор модели под задачу
- **Mapping:**
  - coding → DeepSeek Coder
  - creative → Qwen
  - vision → Pixtral
  - simple → Phi-3.5
- **Где:** `SmartRoutingResult.model`
- **⚠️ Требует:** Registry моделей в LM Studio

#### 10. User Preference Learning

- **Что:** Запоминание предпочтений
- **Данные:**
  - Частые intent типы
  - Предпочитаемый стиль ответов
- **Где:** DB + `SmartRouter.adjust_for_user()`

#### 11. Emotional Tone Adjustment

- **Что:** Определение эмоций пользователя
- **Тоны:** neutral, empathetic, professional, urgent
- **Где:** `SmartRoutingResult.emotional_tone`

---

## 🏗️ Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│                      SmartRouter                              │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐  │
│  │ LLM Router  │  │ CPU Router  │  │ Privacy Guard        │  │
│  │ (Phi-3.5)   │  │ (Fallback)  │  │ (Unlock Detection)   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬───────────┘  │
│         │                │                     │              │
│         └────────────────┼─────────────────────┘              │
│                          │                                    │
│                          ▼                                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │             Feature Engine                              │  │
│  │  • Mode Selection    • Cost Estimation                 │  │
│  │  • Tool Activation   • Safety Filter                   │  │
│  │  • Temperature Tune  • Cache Strategy                  │  │
│  │  • Context Optimizer • Privacy Filter                  │  │
│  │  • Streaming Strategy• Parallel Decomposition          │  │
│  └────────────────────────────────────────────────────────┘  │
│                          │                                    │
│                          ▼                                    │
│              SmartRoutingResult                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 Файлы к Созданию/Изменению

### CREATE

| Файл | Описание |
|------|----------|
| `src/core/routing/smart_router.py` | Центральный оркестратор всех фичей |
| `src/core/routing/privacy_guard.py` | Privacy Lock система |
| `src/core/routing/decomposer.py` | Parallel task decomposition |
| `src/core/routing/features.py` | Feature Engine (все калькуляции) |

### MODIFY

| Файл | Изменения |
|------|-----------|
| `src/core/routing/__init__.py` | Добавить новые exports |
| `src/core/memory.py` | Добавить `is_private` флаг к фактам |
| `src/api/routers/chat.py` | Интегрировать SmartRouter |
| `data/schema.sql` | Добавить `is_private` колонку |

---

## ✅ Порядок Реализации

```
Phase 1 (MANDATORY):
  □ 15. Privacy Lock System
  □ 14. Streaming Strategy
  □ 8.  Parallel Decomposition
  □ 1.  Auto Mode Selection
  □ 2.  Smart Tool Activation

Phase 2 (OPTIMIZATION):
  □ 13. Temperature Auto-Tune
  □ 5.  RAG Trigger
  □ 4.  Context Window Optimizer
  □ 7.  Cost Estimator
  □ 9.  Safety Filter
  □ 12. Caching Strategy

Phase 3 (INTELLIGENCE):
  □ 11. Emotional Tone
  □ 10. User Preferences
  □ 3.  Model Selector
```

---

## 🔐 Privacy Lock System (Детали)

### Триггеры

| Фраза | Действие |
|-------|----------|
| "Привет, малыш" | UNLOCK private memory |
| 30 мин бездействия | AUTO-LOCK |
| Новая сессия | LOCKED by default |

### Memory Levels

```
PUBLIC (is_private = false):
  • Общие факты (любит Python)
  • Нейтральные предпочтения

PRIVATE (is_private = true):
  • Личные данные
  • Семья, здоровье, финансы
  • Секреты, планы
```

### Поведение

```
[LOCKED] "Как зовут мою девушку?"
  → "Извините, у меня нет такой информации."

[UNLOCKED] "Как зовут мою девушку?"
  → "Её зовут [имя], ты рассказывал..."
```
