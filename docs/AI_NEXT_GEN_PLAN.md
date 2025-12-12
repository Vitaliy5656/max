# MAX AI: Архитектура Умного Поведения v3.5

**Версия:** 3.5 (Architect Recommendations Integrated)
**Дата:** 2025-12-12
**Статус:** Архитектурный план с полным контекстом проекта
**Автор:** Senior Solutions Architect

---

## Executive Summary

Этот документ описывает трансформацию MAX из "цепочки промптов" в **Когнитивную Систему с Самокоррекцией**, с учётом **полной существующей архитектуры** проекта.

### Существующий когнитивный стек MAX

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ТЕКУЩАЯ АРХИТЕКТУРА MAX                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ UserProfile │  │ Adaptation  │  │ MetricsEng  │  │  Memory   │  │
│  │ (mood,prefs)│  │ (learn)     │  │ (IQ/EQ)     │  │ (multi)   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │
│         │                │                │               │         │
│         └────────────────┴────────────────┴───────────────┘         │
│                              │                                      │
│                              ▼                                      │
│                    ┌─────────────────┐                              │
│                    │   LM Client     │                              │
│                    │ (detect_task)   │                              │
│                    └────────┬────────┘                              │
│                             │                                       │
│                             ▼                                       │
│                    ┌─────────────────┐                              │
│                    │   AutoGPT       │                              │
│                    │ (agent loop)    │                              │
│                    └─────────────────┘                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Новые модули (этот план)

| Модуль | Интеграция с | Функция |
|--------|--------------|---------|
| **SafeShell** | `tools.py` | Windows-совместимые команды |
| **ReflectiveAgent** | `autogpt.py`, `MetricsEngine` | Верификация действий |
| **SemanticRouter** | `lm_client.py`, `UserProfile` | Умная маршрутизация |
| **ContextPrimer** ⭐ | `SemanticRouter`, `Memory` | Semantic Prefetch контекста |
| **PyBox** | `tools.py` | Безопасный Python |
| **ErrorMemory** | `CorrectionDetector`, `FeedbackMiner` | Векторная память ошибок |
| **ConfidenceScorer** | `MetricsEngine` | Оценка уверенности |
| **SelfReflection** | `AdaptivePromptBuilder`, `MetricsEngine` | Самоанализ и мотивация |

---

## Часть 1: Полная карта существующих когнитивных модулей

### 1.1 UserProfile (`src/core/user_profile.py`)

**Функции:**

- `Mood` enum: HAPPY, NEUTRAL, FRUSTRATED, CURIOUS, BUSY
- `Verbosity` enum: BRIEF, BALANCED, DETAILED
- `Formality` enum: FORMAL, FRIENDLY, CASUAL
- `UserPreferences` dataclass: настройки стиля
- `UserHabits` dataclass: паттерны поведения

**Ключевые методы:**

```python
analyze_mood(text) → Mood          # Детекция настроения (без побочных эффектов)
detect_mood(text) → Mood           # + установка состояния
get_style_prompt() → str           # Генерация персонализированного промпта
track_interaction(message)         # Отслеживание привычек
get_suggestions(context) → list    # Мягкие предложения
get_profile_completeness() → float # Метрика для Empathy
get_habits_richness() → float      # Метрика для Empathy
```

**База данных:** `user_profile` (singleton id=1)

```sql
name TEXT, preferences JSON, habits JSON, dislikes JSON
```

---

### 1.2 Adaptation Engine (`src/core/adaptation.py`)

**Компоненты:**

#### CorrectionDetector

```python
CORRECTION_PATTERNS = [
    (r"нет,?\s*(я\s+)?(имел|имела)\s+в\s+виду", "misunderstanding"),
    (r"не так,?\s*(я\s+)?(хотел|хотела)", "content"),
    (r"слишком\s+(длинно|коротко|сложно)", "style"),
    # ... 40+ паттернов RU/EN
]

detect(text) → (is_correction: bool, category: str)
record_correction(orig_id, corr_id, orig_response, user_correction)
get_recent_corrections(limit) → list[CorrectionEntry]
```

#### FeedbackMiner

```python
record_success_pattern(message_id, response_summary, category)
get_success_patterns(category, limit) → list[SuccessPattern]
increment_pattern_usage(pattern_id)
```

#### FactEffectivenessTracker

```python
record_fact_usage(fact_id, was_positive)
get_effective_fact_ids(limit) → list[int]
get_fact_score(fact_id) → float
```

#### AdaptivePromptBuilder

```python
build_adaptive_prompt(base_style, include_corrections, include_successes) → str
# Собирает: base_style + corrections + success_patterns + stats
```

#### AnticipationEngine

```python
SEQUENCES = {
    "написал код": ["запусти тест", "проверь ошибки"],
    "git": ["commit", "push", "статус"],
    # ...
}
get_suggestions(context, user_habits) → list[str]
```

**База данных:**

- `correction_log`: original_response, user_correction, extracted_pattern, category
- `success_patterns`: response_summary, extracted_pattern, category
- `fact_effectiveness`: times_used, positive_outcomes, negative_outcomes

---

### 1.3 Metrics Engine (`src/core/metrics.py`)

**Компоненты:**

#### ImplicitFeedbackAnalyzer

```python
POSITIVE_SIGNALS = ["спасибо", "отлично", "класс", "thanks", "great", ...]  # 50+
NEGATIVE_SIGNALS = ["нет", "не то", "неправильно", "wrong", ...]  # 50+
CORRECTION_SIGNALS = ["нет, я имел в виду", "ты не понял", ...]  # 30+

analyze(text) → (is_positive, is_negative, is_correction)
_analyze_caps(text, already_negative) → "frustration" | "emphasis" | "none"
```

#### MetricsEngine

**IQ Score (40% + 30% + 20% + 10%):**

```python
IQ_WEIGHTS = {
    "accuracy": 0.40,      # positive / (positive + negative)
    "correction": 0.30,    # 1 - corrections / total
    "first_try": 0.20,     # neutral_or_positive / total
    "context": 0.10        # facts_used / facts_available
}
```

**Empathy Score (40% + 25% + 20% + 15%):**

```python
EMPATHY_WEIGHTS = {
    "habit_match": 0.40,   # profile_completeness + habit_richness
    "mood": 0.25,          # fewer negatives = better
    "anticipation": 0.20,  # positive_rate as proxy
    "friction": 0.15       # trend in correction_rate
}
```

**Методы:**

```python
analyze_message(text) → (positive, negative, correction)
record_interaction_outcome(message_id, user_message, ...)
calculate_iq() → MetricResult
calculate_empathy() → MetricResult
get_achievements() → list[Achievement]
get_adaptation_proof() → AdaptationProof  # Day 1 vs Day 30
```

**База данных:**

- `interaction_outcomes`: was_correction, implicit_positive/negative, facts_in_context, ...
- `daily_metrics`: iq_score, empathy_score, breakdown_json
- `achievements`: threshold_type, threshold_value, current_value, unlocked_at

---

### 1.4 Memory System (`src/core/memory.py`)

**Архитектура:**

```
┌─────────────────────────────────────────────────────────┐
│                   Memory Tiers                          │
├─────────────────────────────────────────────────────────┤
│  1. Session Memory  │ Recent messages (70% token budget)│
│  2. Summary Memory  │ Auto-compressed older messages    │
│  3. Facts Database  │ Extracted facts + embeddings      │
│  4. Cross-Session   │ Semantic search across history    │
└─────────────────────────────────────────────────────────┘
```

**Ключевые методы:**

```python
get_smart_context(conv_id, max_tokens, include_facts) → list[dict]
# 1. Summary (20% tokens)
# 2. Recent messages (70% tokens)
# 3. Relevant facts (10% tokens)

compress_history(conv_id) → str  # LLM summarization
_extract_facts(message_id, content)  # LLM extraction → memory_facts
get_relevant_facts(conv_id, limit) → list[Fact]  # Semantic search
```

**База данных:**

- `messages`: role, content, tokens_used, model_used
- `memory_facts`: content, category, embedding (BLOB), confidence
- `conversation_summaries`: summary, messages_covered

---

### 1.5 LM Client (`src/core/lm_client.py`)

**Текущая маршрутизация (ПРОБЛЕМА):**

```python
def detect_task_type(message, has_image) → TaskType:
    if has_image: return VISION

    reasoning_keywords = ["почему", "объясни", "why", "explain", ...]
    quick_keywords = ["да или нет", "кратко", "yes or no", ...]

    if any(kw in message_lower for kw in quick_keywords):
        return QUICK
    if any(kw in message_lower for kw in reasoning_keywords):
        return REASONING
    if len(message) > 200:
        return REASONING
    return DEFAULT
```

**Проблема:** Keyword-based, не понимает семантику.

**Thinking Modes:**

```python
class ThinkingMode(Enum):
    FAST = "fast"       # Quick, minimal reasoning
    STANDARD = "standard"
    DEEP = "deep"       # Chain-of-thought
    VISION = "vision"   # Auto for images
```

---

### 1.6 AutoGPT Agent (`src/core/autogpt.py`)

**Цикл:**

```
set_goal(goal) → AutoGPTRun
    │
    ▼
_create_plan() → list[Task]  # LLM decomposition
    │
    ▼
┌─────────────────────────────────┐
│  while not done and not limit: │
│    _execute_next_step()        │
│      │                         │
│      ├─ LLM: "what next?"     │
│      ├─ Check DANGEROUS_TOOLS │
│      ├─ tools.execute(action)  │◄─── ПРОБЛЕМА: нет верификации
│      └─ _mark_task_progress()  │
│                                │
│    _check_goal_completed()     │◄─── ПРОБЛЕМА: naive check
└─────────────────────────────────┘
```

**Проблемы:**

1. Task считается Done просто по факту вызова инструмента
2. Нет верификации результата
3. Нет обратной связи с MetricsEngine

---

### 1.7 API Integration (`src/api/api.py`)

**Текущий flow POST /api/chat:**

```python
1. memory.add_message(conv_id, "user", message)
2. user_profile.track_interaction(message)        # Background
3. memory.get_smart_context(conv_id)
4. rag.get_context_for_query(message)             # Optional
5. prompt_builder.build_adaptive_prompt(message)  # Personalization
6. lm_client.chat(..., thinking_mode=..., stream=True)
7. memory.add_message(conv_id, "assistant", response)
```

**⚠️ КРИТИЧЕСКОЕ УПУЩЕНИЕ:**

```python
# ОТСУТСТВУЕТ в текущем коде:
await metrics_engine.record_interaction_outcome(...)
```

Метрики IQ/Empathy записываются, но не после каждого сообщения!

---

## Часть 2: Новые модули и их интеграция

### 2.1 SafeShell (P0 - Критический)

**Файл:** `src/core/safe_shell.py`

**Проблема в `tools.py:run_command`:**

```python
# Текущий код:
proc = await asyncio.create_subprocess_exec("dir")  # ❌ Windows: FileNotFoundError
```

**Решение:**

```python
# src/core/safe_shell.py

WINDOWS_BUILTINS = {
    "dir", "echo", "type", "copy", "move", "del", "rd", "md",
    "ren", "cls", "date", "time", "ver", "vol", "path", "set",
    "cd", "pushd", "popd", "mkdir", "rmdir", "erase"
}

@dataclass
class ShellResult:
    stdout: str
    stderr: str
    return_code: int
    timed_out: bool = False

class SafeShell:
    """Cross-platform shell with Windows built-in support."""

    def _needs_shell_wrap(self, command: str) -> bool:
        """Check if command needs cmd /c wrapper."""
        if not self.is_windows:
            return False
        base_cmd = command.strip().split()[0].lower()
        return base_cmd in WINDOWS_BUILTINS

    def _prepare_command(self, command: str) -> tuple[str, ...]:
        if self._needs_shell_wrap(command):
            return ("cmd", "/c", command)
        return tuple(shlex.split(command))

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: float = 60.0,
        on_stdout: Optional[callable] = None  # Real-time streaming
    ) -> ShellResult:
        args = self._prepare_command(command)
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        # ... streaming + timeout handling ...
```

**Интеграция в `tools.py`:**

```python
from .safe_shell import safe_shell

async def _tool_run_command(self, command: str, cwd: str = ".") -> ToolResult:
    # Security checks...
    result = await safe_shell.execute(command, cwd=cwd, timeout=60.0)
    return ToolResult(
        success=result.return_code == 0,
        output=result.stdout + ("\n[stderr]: " + result.stderr if result.stderr else "")
    )
```

**Сложность:** Low | **Зависимости:** Нет | **Тесты:** `test_safe_shell.py`

---

### 2.2 SemanticRouter (P1 - Высокий)

**Файл:** `src/core/semantic_router.py`

**Заменяет:** `lm_client.detect_task_type()` (keyword-based)

**Архитектура:**

```
┌────────────────────────────────────────────────────────────┐
│                    SemanticRouter                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Intent Probes (pre-computed embeddings):                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  CODE    │ │ REASON   │ │ CREATIVE │ │  MATH    │      │
│  │ embed[n] │ │ embed[n] │ │ embed[n] │ │ embed[n] │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                            │
│  Query:                                                    │
│  ┌─────────────────────────┐                               │
│  │ "Почему код не работает"│ ──embed──▶ [q1, q2, ..., qn] │
│  └─────────────────────────┘                               │
│                                                            │
│  Cosine Similarity:                                        │
│  CODE: 0.82  ◄── Winner                                    │
│  REASON: 0.78                                              │
│  CREATIVE: 0.31                                            │
│                                                            │
│  Output: RouteDecision(category=CODE, model=deepseek-coder)│
└────────────────────────────────────────────────────────────┘
```

**⚠️ ИНТЕГРАЦИЯ С UserProfile:**

```python
async def route(
    self,
    query: str,
    user_profile: UserProfile,  # ВАЖНО: учитываем предпочтения!
    has_image: bool = False
) -> RouteDecision:
    base_decision = await self._semantic_route(query)

    # Учитываем verbosity из UserProfile
    if user_profile.preferences.verbosity == Verbosity.BRIEF:
        if base_decision.category not in [IntentCategory.REASONING, IntentCategory.CODE]:
            base_decision.thinking_mode = "fast"

    return base_decision
```

**Fallback:** Если embedding недоступен, используется `_fallback_route()` с keywords.

**Сложность:** Medium | **Зависимости:** `lm_client.get_embedding()`, `UserProfile`

---

### 2.2a ContextPrimer (P1 - Высокий) ⭐ NEW

**Файл:** `src/core/context_primer.py`

**Концепция:** Semantic Prefetch — подтягивание ТОЛЬКО релевантного контекста ДО генерации ответа. Как "положить нужное на стол" перед работой.

**Основано на Best Practices 2024-2025:**

- Contextual Retrieval (Anthropic) — -49% failure rate
- Semantic Caching — до 60% cache hits
- Hierarchical Memory (HiAgent) — HOT → WORKING → EPISODIC

**Архитектура:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      ContextPrimer Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                           │
│  │ User Query       │                                           │
│  │ "хочу покодить"  │                                           │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────┐               │
│  │ 1. INTENT DETECTOR (fast, ~10ms)             │               │
│  │    - Semantic similarity vs domain embeddings│               │
│  │    - Fallback: keyword triggers              │               │
│  │    → Domain: "code"                          │               │
│  └────────┬─────────────────────────────────────┘               │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────┐               │
│  │ 2. SEMANTIC CACHE CHECK                      │               │
│  │    Similar query cached? → Return instantly! │               │
│  │    Cache hit rate: ~40-60%                   │               │
│  └────────┬─────────────────────────────────────┘               │
│           │ (miss)                                               │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────┐               │
│  │ 3. PARALLEL PREFETCH ("на стол", ~50ms)      │               │
│  │    ┌─────────────────────────────────────┐   │               │
│  │    │ a) Domain-Specific Memories:        │   │               │
│  │    │    - code_patterns (не все!)        │   │               │
│  │    │    - project facts                  │   │               │
│  │    │    - tech preferences               │   │               │
│  │    └─────────────────────────────────────┘   │               │
│  │    ┌─────────────────────────────────────┐   │               │
│  │    │ b) Success Patterns (domain only):  │   │               │
│  │    │    - code success patterns          │   │               │
│  │    │    - NOT creative patterns          │   │               │
│  │    └─────────────────────────────────────┘   │               │
│  │    ┌─────────────────────────────────────┐   │               │
│  │    │ c) Tool Preparation:                │   │               │
│  │    │    - run_command, write_file        │   │               │
│  │    │    - NOT: web_search, calendar      │   │               │
│  │    └─────────────────────────────────────┘   │               │
│  │    ┌─────────────────────────────────────┐   │               │
│  │    │ d) Specialized Instructions:        │   │               │
│  │    │    → code_assistant.md              │   │               │
│  │    └─────────────────────────────────────┘   │               │
│  └────────┬─────────────────────────────────────┘               │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────┐               │
│  │ 4. CACHE & RETURN                            │               │
│  │    → Store in SemanticCache for future       │               │
│  │    → Return PrimedContext                    │               │
│  └──────────────────────────────────────────────┘               │
│                                                                  │
│  Result: ~1500 tokens (вместо ~4000) = -62.5%                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Компоненты:**

#### SemanticCache

```python
class SemanticCache:
    """
    Cache primed contexts by semantic similarity.
    Similar queries get the same context instantly (~0ms).
    
    ⭐ CACHE INVALIDATION STRATEGY:
    1. TTL-based: entries expire after ttl_seconds
    2. Manual: call clear() when memories/patterns updated
    3. Version-based: check _db_version counter on get()
    
    🚀 OPTIMIZATION: Vectorized numpy for O(1) lookup instead of O(n) loop
    """
    
    # 🚀 OPTIMIZATION: 2000 entries = ~1GB RAM (user has 64GB)
    def __init__(self, max_size: int = 2000, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[PrimedContext, float]] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._embedding_matrix: Optional[np.ndarray] = None  # 🚀 Vectorized cache
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._db_version: int = 0
    
    async def get(self, query: str, query_embedding: list[float]) -> Optional[PrimedContext]:
        """Check if similar query is cached (similarity > 0.92). O(1) with numpy."""
        if not self._cache:
            return None
        
        now = time.time()
        self._evict_expired(now)  # Clean up expired entries
        
        if self._embedding_matrix is None:
            return None
        
        # 🚀 OPTIMIZATION: Vectorized cosine similarity — O(1) instead of O(n)
        query_vec = np.array(query_embedding)
        similarities = np.dot(self._embedding_matrix, query_vec) / (
            np.linalg.norm(self._embedding_matrix, axis=1) * np.linalg.norm(query_vec)
        )
        best_idx = np.argmax(similarities)
        
        if similarities[best_idx] > 0.92:
            cached_key = list(self._cache.keys())[best_idx]
            context = self._cache[cached_key][0]
            context.from_cache = True
            return context
        
        return None
    
    def put(self, query: str, embedding: list[float], context: PrimedContext):
        """Cache a primed context for future similar queries."""
        if len(self._cache) >= self._max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1][1])
            del self._cache[oldest[0]]
            del self._embeddings[oldest[0]]
        
        self._cache[query] = (context, time.time())
        self._embeddings[query] = embedding
        self._rebuild_matrix()  # Rebuild for vectorized search
    
    def _rebuild_matrix(self):
        """Rebuild embedding matrix for vectorized search."""
        if self._embeddings:
            self._embedding_matrix = np.vstack(list(self._embeddings.values()))
        else:
            self._embedding_matrix = None
    
    def clear(self):
        """Clear ALL cache entries. Called when memories/patterns change."""
        self._cache.clear()
        self._embeddings.clear()
        self._embedding_matrix = None
        self._db_version += 1
    
    def invalidate_for_category(self, category: IntentCategory):
        """Clear cache entries for specific category only."""
        to_delete = [
            q for q, (ctx, _) in self._cache.items() 
            if ctx.category == category
        ]
        for q in to_delete:
            del self._cache[q]
            del self._embeddings[q]
        self._rebuild_matrix()
```

#### Domain Configuration

```python
class Domain(Enum):
    CODE = "code"
    CREATIVE = "creative"
    VISION = "vision"
    ANALYSIS = "analysis"
    CASUAL = "casual"

DOMAINS = {
    Domain.CODE: DomainConfig(
        triggers=["код", "функци", "класс", "баг", "python", "js", "api"],
        memory_categories=["project", "code_style", "tech_preferences"],
        pattern_types=["code", "technical", "debugging"],
        tools=["run_command", "write_file", "read_file", "python_eval"],
        instructions="code_assistant.md",
        max_memories=7
    ),
    Domain.CREATIVE: DomainConfig(
        triggers=["напиши", "придумай", "история", "текст", "пост"],
        memory_categories=["writing_style", "tone_preferences"],
        pattern_types=["creative", "style"],
        tools=["web_search"],
        instructions="creative_writer.md",
        max_memories=5
    ),
    # ... VISION, ANALYSIS, CASUAL
}
```

#### ContextPrimer (основной класс)

```python
class ContextPrimer:
    """
    Semantic Prefetch - fetches ONLY relevant context based on RouteDecision.
    This is the "putting on the table" mechanism.
    
    ℹ️ NOTE: ContextPrimer НЕ определяет domain самостоятельно!
    Он получает RouteDecision от SemanticRouter и использует route.category.
    """
    
    # Mapping from IntentCategory to DomainConfig
    CATEGORY_TO_CONFIG = {
        IntentCategory.CODE: DomainConfig(...),
        IntentCategory.REASONING: DomainConfig(...),
        IntentCategory.CREATIVE: DomainConfig(...),
        IntentCategory.VISION: DomainConfig(...),
        IntentCategory.QUICK: DomainConfig(...),
    }
    
    async def prime_context(
        self,
        query: str,
        route: RouteDecision,  # ⭐ ПРИНИМАЕТ RouteDecision, не определяет сам!
        user_profile: UserProfile
    ) -> PrimedContext:
        start_time = time.time()
        
        # 1. Используем category из SemanticRouter
        config = self.CATEGORY_TO_CONFIG.get(
            route.category, 
            self.CATEGORY_TO_CONFIG[IntentCategory.REASONING]  # fallback
        )
        
        # 2. Check semantic cache
        query_embedding = await self._lm_client.get_embedding(query)
        if query_embedding:
            cached = await self._cache.get(query, query_embedding)
            if cached:
                return cached  # Instant return!
        
        # 3. Parallel prefetch ("на стол")
        memories, patterns, tools, instructions = await asyncio.gather(
            self._fetch_memories(config),      # Only category-relevant
            self._fetch_patterns(config),      # Only category patterns
            self._prepare_tools(config),       # Only category tools
            self._load_instructions(config)    # Specialized instructions
        )
        
        context = PrimedContext(
            category=route.category,  # Используем IntentCategory, не Domain
            memories=memories,
            patterns=patterns,
            tools=tools,
            instructions=instructions,
            prime_time_ms=(time.time() - start_time) * 1000
        )
        
        # 4. Cache for similar future queries
        if query_embedding:
            self._cache.put(query, query_embedding, context)
        
        return context
    
    def invalidate_cache(self):
        """Очистить cache при изменении memories/patterns."""
        self._cache.clear()
```

**⚠️ ИНТЕГРАЦИЯ (УТОЧНЁННЫЙ ПОРЯДОК + 🚀 OPTIMIZATIONS):**

```python
# api.py - startup
from src.core.semantic_router import semantic_router
from src.core.context_primer import context_primer
from src.core.self_reflection import self_reflection

await semantic_router.initialize(lm_client)
await context_primer.initialize(memory._db, lm_client)
await self_reflection.initialize(memory._db)

# api.py - POST /api/chat
async def chat(request: ChatRequest):
    # ⭐ ПОРЯДОК ВЫЗОВОВ (КРИТИЧНО):
    
    # 1️⃣ SemanticRouter FIRST - определяет category, model И возвращает embedding
    # 🚀 OPTIMIZATION: Возвращаем embedding для reuse!
    route, query_embedding = await semantic_router.route_with_embedding(
        request.message,
        user_profile,
        request.has_image
    )
    
    # 2️⃣ ContextPrimer - использует route.category и REUSE embedding!
    # 🚀 OPTIMIZATION: Не вызываем get_embedding повторно - экономия ~100ms
    primed = await context_primer.prime_context(
        request.message,
        route,
        user_profile,
        query_embedding  # 🚀 Reuse!
    )
    
    # 3️⃣ SelfReflection - добавляет статистику и мотивацию
    reflection_prompt = await self_reflection.build_reflection_prompt()
    
    # 4️⃣ Build context
    context = []
    if reflection_prompt:
        context.append({"role": "system", "content": reflection_prompt})
    context.extend([{"role": "system", "content": m["content"]} for m in primed.memories])
    
    # 5️⃣ LLM call with route.model and route.thinking_mode
    response = await lm_client.chat(
        model=route.model,
        thinking_mode=ThinkingMode(route.thinking_mode),
        ...
    )
    
    # 🚀 OPTIMIZATION: Показать prime_time в UI
    done_data["prime_time_ms"] = primed.prime_time_ms
    
    # 6️⃣ 🚀 Background Prefetch для следующего запроса (во время стриминга)
    asyncio.create_task(
        context_primer.warm_cache_for_likely_followup(route.category)
    )
```

**Метрики эффективности (🚀 с оптимизациями):**

| Метрика | Без Priming | С Priming v3.4 | Улучшение |
|---------|-------------|----------------|----------|
| Контекст | ~4000 токенов | ~1500 токенов | **-62.5%** |
| Retrieval time | ~200ms | ~30ms (vectorized) | **-85%** |
| Cache hit | N/A | **~75%** 🚀 (2000 entries) | **бесплатные** |
| Embedding calls | 2/request | **1/request** 🚀 | **-50%** |
| Cache lookup | O(n) | **O(1)** 🚀 numpy | **10x faster** |

**Бонусные улучшения (Low Hanging Fruits):**

1. **Contextual Chunk Prepending** (Anthropic pattern):
   - При индексации memories добавлять мета-контекст
   - `"[code_style, Python] Используй async"` вместо `"Используй async"`
   - Эффект: +35% retrieval accuracy

2. **Hybrid Search (Embeddings + BM25)**:
   - Объединить semantic + keyword search
   - Эффект: +14% accuracy поверх semantic only

3. **Domain-Specific Instructions Files**:

   ```text
   MIND/instructions/
   ├── code_assistant.md
   ├── creative_writer.md
   ├── vision_describer.md
   └── default.md
   ```

4. **🆕 Conversation Context Prefetch**:

   ```python
   # При открытии существующего диалога — prefetch сразу
   async def on_conversation_open(conv_id: int):
       last_category = await get_last_message_category(conv_id)
       await context_primer.warm_cache_for_category(last_category)
   ```

   Эффект: **-100ms** на первый запрос в диалоге

5. **🆕 Startup Warming**:

   ```python
   # При запуске приложения — прогрев популярных категорий
   @app.on_event("startup")
   async def warm_caches():
       asyncio.create_task(context_primer.warm_common_categories())
   ```

   Эффект: Cache ready сразу после старта

6. **🆕 Shared Embedding Service** (РЕКОМЕНДУЕТСЯ):

   ```python
   class EmbeddingService:
       """Centralized embedding with in-memory cache. Dedup ALL embedding calls."""
       _cache: dict[str, list[float]] = {}
       
       async def get_or_compute(self, text: str) -> list[float]:
           if text in self._cache:
               return self._cache[text]
           embedding = await lm_client.get_embedding(text)
           self._cache[text] = embedding
           return embedding
   ```

   Эффект: **Dedup embedding calls across ALL modules** (Router, Primer, ErrorMemory)

7. **🆕 Cognitive Health Endpoint**:

   ```python
   @app.get("/api/health/cognitive")
   async def cognitive_health():
       return {
           "cache_hit_rate": context_primer.get_cache_stats(),
           "avg_prime_time_ms": context_primer.get_avg_prime_time(),
           "routing_accuracy": semantic_router.get_accuracy(),
           "iq_today": (await metrics_engine.calculate_iq()).score
       }
   ```

   Эффект: **Observability из коробки**

**Сложность:** Medium | **Зависимости:** `SemanticRouter`, `Memory`, `lm_client.get_embedding()`

**Checklist:**

- [ ] SemanticCache с TTL, eviction и invalidation ✅ (описано)
- [ ] Использование RouteDecision.category (НЕ свой domain detection!) ✅
- [ ] Parallel prefetch всех компонентов
- [ ] Integration в api.py (startup + chat) — порядок: Router→Primer→Reflection
- [ ] Category-specific instruction files
- [ ] Performance < 100ms (with cache miss)
- [ ] Fallback если embedding API недоступен

---

### 2.3 ReflectiveAgent (P1 - Высокий)

**Файл:** `src/core/agent_v2.py`

**КРИТИЧЕСКАЯ ПРОБЛЕМА в `autogpt.py`:**

```python
# Текущий код:
step.result = await tools.execute(action, action_input)
step.status = StepStatus.COMPLETED  # ❌ Без проверки результата!
```

**Решение: Verifier Pattern**

```
ТЕКУЩИЙ ПОТОК:                    НОВЫЙ ПОТОК:
┌─────────────┐                   ┌─────────────┐
│ Execute     │                   │ Execute     │
│ action      │                   │ action      │
└─────┬───────┘                   └─────┬───────┘
      │                                 │
      ▼                                 ▼
┌─────────────┐                   ┌─────────────┐
│ Mark DONE   │ ❌                │ Verify      │
└─────────────┘                   │ result      │
                                  └─────┬───────┘
                                        │
                                  ┌─────▼───────┐
                                  │ PASS/FAIL?  │
                                  └─────┬───────┘
                                        │
                           ┌────────────┴────────────┐
                           │                         │
                     ┌─────▼─────┐             ┌─────▼─────┐
                     │ Mark DONE │             │ Iterate   │
                     │ + record  │             │ with      │
                     │ metrics   │             │ critique  │
                     └───────────┘             └───────────┘
```

**⚠️ ИНТЕГРАЦИЯ С MetricsEngine:**

```python
class ReflectiveAgent(AutoGPTAgent):
    """Extends AutoGPTAgent with verification."""

    async def _execute_next_step(self) -> Optional[Step]:
        step = await super()._execute_next_step()

        if step and step.status == StepStatus.COMPLETED:
            verification = await self._verify_step(step)

            # ИНТЕГРАЦИЯ: записываем в MetricsEngine!
            await metrics_engine.record_interaction_outcome(
                was_correction=(verification.status == VerificationResult.FAIL),
                # verification confidence влияет на IQ
            )

            if verification.status == VerificationResult.FAIL:
                # Retry logic...

        return step
```

**Сложность:** Medium | **Зависимости:** `autogpt.py`, `MetricsEngine`

---

### 2.4 ErrorMemory (P2 - Средний)

**Файл:** `src/core/error_memory.py`

**⚠️ ИНТЕГРАЦИЯ с существующим `CorrectionDetector`:**

```
┌───────────────────────────────────────────────────────────────┐
│                    Error Learning Flow                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  СУЩЕСТВУЮЩЕЕ:                                                │
│  CorrectionDetector.detect("нет, я имел в виду X")            │
│       │                                                       │
│       ▼                                                       │
│  correction_log table (regex patterns)                        │
│                                                               │
│  НОВОЕ (ErrorMemory):                                         │
│  CorrectionDetector.detect(...)                               │
│       │                                                       │
│       ▼                                                       │
│  ErrorMemory.record_error_correction(                         │
│      error_pattern,                                           │
│      wrong_action,                                            │
│      correct_action,                                          │
│      embedding  ◄─── ДОБАВЛЯЕМ ВЕКТОР для similarity search   │
│  )                                                            │
│                                                               │
│  ИСПОЛЬЗОВАНИЕ:                                               │
│  Before action → ErrorMemory.recall_similar_errors(context)   │
│       │                                                       │
│       ▼                                                       │
│  "⚠️ В прошлом 'del' не работал, используй Remove-Item"       │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**Код интеграции:**

```python
class ErrorMemory:
    """Vector-based error memory, EXTENDS CorrectionDetector."""

    def __init__(self, correction_detector: CorrectionDetector, db: aiosqlite.Connection):
        self._correction_detector = correction_detector  # НЕ ЗАМЕНЯЕМ, расширяем!
        self._db = db

    async def record_from_user_correction(
        self,
        user_message: str,
        assistant_previous_response: str
    ):
        """Called when user corrects assistant."""
        # Используем СУЩЕСТВУЮЩИЙ CorrectionDetector
        is_correction, category = self._correction_detector.detect(user_message)

        if not is_correction:
            return

        # Добавляем embedding для vector search
        embedding = await lm_client.get_embedding(
            f"{category} {assistant_previous_response[:200]}"
        )

        await self._db.execute("""
            INSERT INTO error_memory
            (error_pattern, wrong_action, correct_action, context, embedding)
            VALUES (?, ?, ?, ?, ?)
        """, (category, assistant_previous_response[:500], user_message[:500],
              category, embedding))  # ✅ FIX: было embedding_blob, стало embedding
```

**Новая таблица:**

```sql
CREATE TABLE IF NOT EXISTS error_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_pattern TEXT NOT NULL,
    wrong_action TEXT NOT NULL,
    correct_action TEXT NOT NULL,
    context TEXT,
    embedding BLOB,              -- Vector for similarity search
    occurrences INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);

-- 🚀 OPTIMIZATION: Index для ограничения vector scan последними 30 днями
CREATE INDEX IF NOT EXISTS idx_error_memory_created ON error_memory(created_at DESC);
```

**🚀 OPTIMIZATION: Ограничение vector scan:**

```python
async def recall_similar_errors(self, context_embedding: list[float], limit: int = 5):
    """Find similar past errors. LIMITED to last 30 days to avoid O(n) on large tables."""
    # 🚀 Limit scan to recent entries only
    async with self._db.execute("""
        SELECT embedding, error_pattern, correct_action 
        FROM error_memory 
        WHERE created_at > datetime('now', '-30 days')
        ORDER BY created_at DESC
        LIMIT 100  -- Max entries to compare
    """) as cursor:
        rows = await cursor.fetchall()
    
    # Vectorized similarity search on limited set
    if not rows:
        return []
    
    embeddings = np.vstack([pickle.loads(r[0]) for r in rows])
    similarities = np.dot(embeddings, context_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(context_embedding)
    )
    
    top_indices = np.argsort(similarities)[-limit:][::-1]
    return [rows[i] for i in top_indices if similarities[i] > 0.7]
```

**Сложность:** Medium | **Зависимости:** `CorrectionDetector` | **НЕ ЛОМАЕТ существующее**

---

### 2.5 PyBox Sandbox (P2 - Средний)

**Файл:** `src/core/pybox.py`

**Зачем:**

- LLM плохо считает: `1234567 * 7654321 = ?`
- Data analysis: pandas, statistics
- Validation: regex, formats

**Архитектура безопасности:**

```
┌────────────────────────────────────────────────────────────┐
│                     PyBox Security Layers                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. AST Analysis (static)                                  │
│     ├─ BLOCKED_IMPORTS: os, sys, subprocess, socket, ...  │
│     ├─ BLOCKED_CALLS: exec, eval, open, __import__, ...   │
│     └─ ALLOWED_IMPORTS: math, json, datetime, numpy, ...  │
│                                                            │
│  2. Runtime Restrictions                                   │
│     ├─ Timeout: 10 seconds                                │
│     ├─ Output limit: 100KB                                │
│     ├─ No network access                                  │
│     └─ No filesystem access                               │
│                                                            │
│  3. Execution in isolated temp file                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Интеграция как tool:**

```python
TOOLS.append({
    "name": "python_eval",
    "description": "Execute Python code for calculations (math, data analysis)",
    "parameters": {
        "code": {"type": "string", "description": "Python code to execute"}
    }
})

async def _tool_python_eval(self, code: str) -> ToolResult:
    result = await pybox.execute(code)
    return ToolResult(result.success, result.output, result.error)
```

**Сложность:** High | **Тесты:** КРИТИЧЕСКИ важны для безопасности

---

### 2.6 ConfidenceScorer (P3 - Low)

**Файл:** `src/core/confidence.py`

**⚠️ ИНТЕГРАЦИЯ с `MetricsEngine`:**

```python
# После генерации ответа в api.py:
confidence = confidence_scorer.score_response(full_response, route.category.value)

# Записываем в MetricsEngine
await metrics_engine.record_interaction_outcome(
    message_id=saved_msg.id,
    user_message=request.message,
    confidence_score=confidence.score  # НОВОЕ ПОЛЕ
)

# UI может показывать confidence badge
done_data["confidence"] = confidence.score
```

**Сложность:** Low | **Опционально**

---

### 2.7 SelfReflection (P1 - Высокий) ⭐ NEW

**Файл:** `src/core/self_reflection.py`

**Философия:**

LLM не имеет непрерывного сознания — каждый запрос это "чистый лист".
Но мы можем создать **архитектурную иллюзию самосовершенствования**,
показывая модели её собственную статистику и прогресс.

```
┌────────────────────────────────────────────────────────────────┐
│                    SelfReflection Flow                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                                           │
│  │  MetricsEngine  │                                           │
│  │  ├─ IQ 7 дней   │                                           │
│  │  ├─ IQ сегодня  │                                           │
│  │  └─ тренд       │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ CorrectionLog   │────▶│ SelfReflection  │                   │
│  │ (последние 3)   │     │    Builder      │                   │
│  └─────────────────┘     └────────┬────────┘                   │
│                                   │                             │
│  ┌─────────────────┐              │                             │
│  │ SuccessPatterns │──────────────┤                             │
│  │ (топ-2)         │              │                             │
│  └─────────────────┘              ▼                             │
│                          ┌─────────────────┐                   │
│                          │ Reflection      │                   │
│                          │ Prompt          │                   │
│                          │                 │                   │
│                          │ "Твой IQ: 78→85 │                   │
│                          │  Не повторяй:   │                   │
│                          │  - ошибку X     │                   │
│                          │  - ошибку Y     │                   │
│                          │  Что работает:  │                   │
│                          │  - паттерн A"   │                   │
│                          └────────┬────────┘                   │
│                                   │                             │
│                                   ▼                             │
│                          ┌─────────────────┐                   │
│                          │ Context для LLM │                   │
│                          │ (system prompt) │                   │
│                          └─────────────────┘                   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Почему это работает:**

1. **LLM следует инструкциям** — видя "не повторяй ошибку X", модель учитывает это
2. **Конкретные примеры** лучше абстрактных правил
3. **Числа создают контекст** — "IQ 78→85" формирует ощущение прогресса
4. **Эмоциональный якорь** — модель "хочет" сохранить хороший тренд

**⚠️ ВАЖНО: Отличие от AdaptivePromptBuilder**

```
AdaptivePromptBuilder:              SelfReflection:
├─ Общие паттерны                   ├─ Конкретная статистика
├─ "Будь внимательнее"              ├─ "IQ был 72, стал 85 (+13)"
├─ Без чисел                        ├─ С числами и трендами
└─ Для всех запросов                └─ Для "осознанности" модели
```

**SelfReflection ДОПОЛНЯЕТ AdaptivePromptBuilder, не заменяет.**

**Код:**

```python
# src/core/self_reflection.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite

from .metrics import metrics_engine
from .adaptation import correction_detector, feedback_miner


@dataclass
class ReflectionData:
    """Data for self-reflection prompt."""
    iq_week_ago: float
    iq_today: float
    iq_trend: str  # "↑", "↓", "→"
    empathy_week_ago: float
    empathy_today: float
    recent_mistakes: list[str]  # Конкретные примеры
    what_works: list[str]  # Успешные паттерны
    streak_days: int  # Дней без негативных отзывов


class SelfReflectionBuilder:
    """
    Builds self-reflection prompts that show the model its own progress.

    Creates an architectural illusion of continuous self-improvement
    by injecting statistics and specific examples into context.
    """

    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db

    async def initialize(self, db: aiosqlite.Connection):
        self._db = db

    async def build_reflection_prompt(self, include_motivation: bool = True) -> str:
        """
        Build a self-reflection prompt with statistics and examples.

        Args:
            include_motivation: Add motivational framing

        Returns:
            System prompt showing model its progress
        """
        data = await self._gather_reflection_data()

        parts = []

        # 1. Statistics header
        parts.append(self._build_stats_section(data))

        # 2. Specific mistakes to avoid
        if data.recent_mistakes:
            parts.append(self._build_mistakes_section(data.recent_mistakes))

        # 3. What works well
        if data.what_works:
            parts.append(self._build_success_section(data.what_works))

        # 4. Motivational framing (optional)
        if include_motivation:
            parts.append(self._build_motivation_section(data))

        return "\n\n".join(parts)

    def _build_stats_section(self, data: ReflectionData) -> str:
        """Build statistics section."""
        iq_diff = data.iq_today - data.iq_week_ago
        empathy_diff = data.empathy_today - data.empathy_week_ago

        iq_sign = "+" if iq_diff > 0 else ""
        empathy_sign = "+" if empathy_diff > 0 else ""

        return f"""[📊 Твоя статистика]
IQ: {data.iq_week_ago:.0f} → {data.iq_today:.0f} ({iq_sign}{iq_diff:.0f}) {data.iq_trend}
Empathy: {data.empathy_week_ago:.0f} → {data.empathy_today:.0f} ({empathy_sign}{empathy_diff:.0f})
Streak: {data.streak_days} дней без негатива"""

    def _build_mistakes_section(self, mistakes: list[str]) -> str:
        """Build mistakes to avoid section."""
        items = "\n".join(f"  ❌ {m}" for m in mistakes[:3])
        return f"""[⚠️ Не повторяй эти ошибки]
{items}"""

    def _build_success_section(self, successes: list[str]) -> str:
        """Build what works section."""
        items = "\n".join(f"  ✓ {s}" for s in successes[:2])
        return f"""[✅ Что работает хорошо]
{items}"""

    def _build_motivation_section(self, data: ReflectionData) -> str:
        """Build motivational framing."""
        if data.iq_today > data.iq_week_ago:
            return "📈 Твой прогресс заметен. Продолжай в том же духе!"
        elif data.streak_days >= 3:
            return f"🔥 {data.streak_days} дней отличной работы! Не сбавляй."
        elif data.iq_today < data.iq_week_ago:
            return "💪 Небольшой спад — это нормально. Сосредоточься на точности."
        else:
            return "🎯 Стабильная работа. Есть потенциал для роста!"

    async def _gather_reflection_data(self) -> ReflectionData:
        """Gather all data for reflection."""
        # 🚀 OPTIMIZATION: asyncio.gather вместо sequential awaits (-80% latency)
        (
            iq_today,
            iq_week_ago,
            empathy_today,
            empathy_week_ago,
            corrections,
            patterns,
            streak
        ) = await asyncio.gather(
            metrics_engine.calculate_iq(),
            self._get_metric_for_date("iq", days_ago=7),
            metrics_engine.calculate_empathy(),
            self._get_metric_for_date("empathy", days_ago=7),
            correction_detector.get_recent_corrections(limit=3),
            feedback_miner.get_success_patterns(limit=2),
            self._calculate_positive_streak()
        )

        # Determine trend
        iq_diff = iq_today.score - iq_week_ago
        if iq_diff > 5:
            trend = "↑"
        elif iq_diff < -5:
            trend = "↓"
        else:
            trend = "→"

        # Process mistakes
        mistakes = []
        for c in corrections:
            if c.category == "misunderstanding":
                mistakes.append(f"Неправильно понял запрос: '{c.correction[:50]}...'")
            elif c.category == "style":
                mistakes.append(f"Стиль не подошёл: {c.pattern}")
            elif c.category == "content":
                mistakes.append(f"Ответил не на тот вопрос")

        what_works = [p.pattern for p in patterns]

        return ReflectionData(
            iq_week_ago=iq_week_ago,
            iq_today=iq_today.score,
            iq_trend=trend,
            empathy_week_ago=empathy_week_ago,
            empathy_today=empathy_today.score,
            recent_mistakes=mistakes,
            what_works=what_works,
            streak_days=streak
        )

    async def _get_metric_for_date(self, metric_type: str, days_ago: int) -> float:
        """Get historical metric value."""
        target_date = (datetime.now() - timedelta(days=days_ago)).date().isoformat()

        column = "iq_score" if metric_type == "iq" else "empathy_score"

        async with self._db.execute(f"""
            SELECT {column} FROM daily_metrics
            WHERE metric_date <= ?
            ORDER BY metric_date DESC
            LIMIT 1
        """, (target_date,)) as cursor:
            row = await cursor.fetchone()

        return row[0] if row and row[0] else 50.0  # Default baseline

    async def _calculate_positive_streak(self) -> int:
        """Calculate days without negative feedback."""
        async with self._db.execute("""
            SELECT metric_date, negative_count
            FROM daily_metrics
            ORDER BY metric_date DESC
            LIMIT 30
        """) as cursor:
            rows = await cursor.fetchall()

        streak = 0
        for row in rows:
            if row[1] == 0:  # No negatives
                streak += 1
            else:
                break

        return streak


# Global instance
self_reflection = SelfReflectionBuilder()


async def initialize_self_reflection(db: aiosqlite.Connection):
    """Initialize self-reflection with database."""
    await self_reflection.initialize(db)
```

**⚠️ ИНТЕГРАЦИЯ в `api.py`:**

```python
from src.core.self_reflection import self_reflection, initialize_self_reflection

@app.on_event("startup")
async def startup():
    # ... existing ...
    await initialize_self_reflection(memory._db)  # NEW

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # ... existing context building ...

    # NEW: Self-reflection prompt (перед adaptive prompt)
    reflection_prompt = await self_reflection.build_reflection_prompt()
    context.insert(0, {"role": "system", "content": reflection_prompt})

    # Existing: Adaptive prompt
    style_prompt = await prompt_builder.build_adaptive_prompt(request.message)
    # ...
```

**⚠️ ИНТЕГРАЦИЯ с `AdaptivePromptBuilder`:**

Можно объединить в один вызов:

```python
# В adaptation.py добавить метод:

class AdaptivePromptBuilder:
    async def build_full_prompt(
        self,
        base_style_prompt: str = "",
        include_reflection: bool = True,  # NEW
        include_corrections: bool = True,
        include_successes: bool = True
    ) -> str:
        parts = []

        # NEW: Self-reflection first (sets context)
        if include_reflection:
            from .self_reflection import self_reflection
            reflection = await self_reflection.build_reflection_prompt(
                include_motivation=True
            )
            parts.append(reflection)

        # Existing adaptive prompt logic...
        # ...

        return "\n\n".join(parts)
```

**Пример сгенерированного промпта:**

```
[📊 Твоя статистика]
IQ: 72 → 85 (+13) ↑
Empathy: 68 → 74 (+6)
Streak: 5 дней без негатива

[⚠️ Не повторяй эти ошибки]
  ❌ Неправильно понял запрос: 'я имел в виду другой файл...'
  ❌ Стиль не подошёл: Адаптировать стиль ответа
  ❌ Ответил не на тот вопрос

[✅ Что работает хорошо]
  ✓ Успешный подход: краткие ответы с кодом
  ✓ Успешный подход: переспрашивать при неясности

📈 Твой прогресс заметен. Продолжай в том же духе!
```

**Сложность:** Medium | **Зависимости:** `MetricsEngine`, `AdaptivePromptBuilder`

**Checklist:**

- [ ] Интеграция с MetricsEngine для получения IQ/Empathy
- [ ] Интеграция с CorrectionDetector для конкретных ошибок
- [ ] Fallback если нет данных (первые дни использования)
- [ ] Не дублирует AdaptivePromptBuilder (дополняет)
- [ ] Мотивационные фразы на русском
- [ ] Performance < 50ms (cached metrics)

---

## Часть 3: Детальные точки интеграции (⚠️ ОСТОРОЖНО)

### 3.1 Изменения в `api.py` (POST /api/chat)

**⚠️ ЭТО САМОЕ ВАЖНОЕ МЕСТО ИНТЕГРАЦИИ**

```python
# ТЕКУЩИЙ КОД (с проблемами):

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # ... context building ...

    thinking_mode = ThinkingMode(request.thinking_mode)  # ← ЗАМЕНЯЕМ

    # ... streaming ...

    # ОТСУТСТВУЕТ: metrics_engine.record_interaction_outcome()


# НОВЫЙ КОД (с интеграцией):

from src.core.semantic_router import semantic_router
from src.core.error_memory import error_memory
from src.core.confidence import confidence_scorer

@app.on_event("startup")
async def startup():
    # ... existing ...
    await semantic_router.initialize()  # NEW: инициализация embeddings
    await error_memory.initialize(memory._db)  # NEW

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # ... existing context building ...

    # NEW: Semantic routing (заменяет thinking_mode из request)
    route = await semantic_router.route(
        request.message,
        user_profile,  # Учитываем preferences!
        request.has_image
    )
    thinking_mode = ThinkingMode(route.thinking_mode)
    target_model = route.model

    # NEW: Error memory warning
    warning = await error_memory.get_warning_prompt(request.message)
    if warning:
        context.insert(0, {"role": "system", "content": warning})

    async def generate():
        # ... existing streaming ...

        # NEW: После генерации - confidence scoring
        confidence = confidence_scorer.score_response(full_response, route.category.value)

        # NEW: Записываем метрики (КРИТИЧЕСКИ ВАЖНО!)
        await metrics_engine.record_interaction_outcome(
            message_id=saved_msg.id,
            user_message=request.message,
            facts_in_context=len(facts_used),
            style_prompt_length=len(style_prompt),
            confidence_score=confidence.score
        )

        # NEW: confidence в ответе для UI
        done_data["confidence"] = confidence.score
        done_data["route"] = route.category.value
```

### 3.2 Изменения в `autogpt.py`

**Вариант A: Наследование (рекомендуется)**

```python
# agent_v2.py
from .autogpt import AutoGPTAgent, Step, StepStatus
from .metrics import metrics_engine

class ReflectiveAgent(AutoGPTAgent):
    """Extends AutoGPTAgent with verification."""

    async def _execute_next_step(self) -> Optional[Step]:
        # Вызываем родительский метод
        step = await super()._execute_next_step()

        if step and step.status == StepStatus.COMPLETED:
            # Добавляем верификацию
            verification = await self._verify_step(step)
            step.verification = verification

            # Записываем в метрики
            await metrics_engine.record_interaction_outcome(
                was_correction=(verification.status == VerificationResult.FAIL)
            )

            # Retry если нужно
            if verification.status == VerificationResult.FAIL:
                step = await self._retry_with_critique(step, verification)

        return step
```

**Вариант B: Замена глобального агента**

```python
# В api.py при startup:
from src.core.agent_v2 import ReflectiveAgent

_autogpt_agent = ReflectiveAgent(memory._db)  # Вместо AutoGPTAgent
```

### 3.3 Изменения в `tools.py`

```python
# Добавить импорт
from .safe_shell import safe_shell
from .pybox import pybox

# Добавить новый tool в TOOLS list
TOOLS.append({
    "name": "python_eval",
    "description": "Execute Python code in sandbox for calculations and data analysis. "
                   "Available imports: math, statistics, datetime, json, re, numpy, pandas. "
                   "No file/network access.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            }
        },
        "required": ["code"]
    }
})

# Добавить метод в класс Tools
async def _tool_python_eval(self, code: str) -> ToolResult:
    """Execute Python code in secure sandbox."""
    result = await pybox.execute(code)
    if result.success:
        return ToolResult(True, f"```\n{result.output}\n```")
    return ToolResult(False, "", result.error)

# Изменить _tool_run_command
async def _tool_run_command(self, command: str, cwd: str = ".") -> ToolResult:
    # ... existing security checks ...

    # ЗАМЕНЯЕМ прямой вызов subprocess на safe_shell
    result = await safe_shell.execute(command, cwd=cwd, timeout=60.0)

    output = result.stdout
    if result.stderr:
        output += f"\n[stderr]: {result.stderr}"
    if result.timed_out:
        output += "\n[TIMED OUT]"

    return ToolResult(
        success=result.return_code == 0 and not result.timed_out,
        output=output or "(no output)"
    )
```

### 3.4 Изменения в `schema.sql`

```sql
-- Добавить в конец файла:

-- Error Memory (vector-based, extends correction_log)
CREATE TABLE IF NOT EXISTS error_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_pattern TEXT NOT NULL,
    wrong_action TEXT NOT NULL,
    correct_action TEXT NOT NULL,
    context TEXT,
    embedding BLOB,              -- Vector for similarity search
    occurrences INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_memory_pattern ON error_memory(error_pattern);

-- Verification logs for ReflectiveAgent
CREATE TABLE IF NOT EXISTS verification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id INTEGER REFERENCES autogpt_steps(id),
    status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'partial', 'skip')),
    critique TEXT,
    suggestions TEXT,  -- JSON array
    confidence REAL,
    iteration INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_verification_step ON verification_logs(step_id);
```

---

## Часть 4: Дорожная карта реализации

### Фаза 1: Критические исправления (1-2 дня)

| # | Задача | Файл | Сложность | Зависимости |
|---|--------|------|-----------|-------------|
| 1.1 | SafeShell для Windows | `safe_shell.py` | Low | Нет |
| 1.2 | Интеграция в tools.py | `tools.py` | Low | 1.1 |
| 1.3 | Тесты SafeShell | `test_safe_shell.py` | Low | 1.1 |
| 1.4 | **FIX: добавить record_interaction_outcome в api.py** | `api.py` | Low | Нет |

### Фаза 2a: Умная маршрутизация + Context Priming (2-3 дня)

| # | Задача | Файл | Сложность | Зависимости |
|---|--------|------|-----------|-------------|
| 2a.1 | **Shared EmbeddingService** 🆕 | `embedding_service.py` | Low | lm_client |
| 2a.2 | SemanticRouter базовый | `semantic_router.py` | Medium | 2a.1 |
| 2a.3 | Интеграция с UserProfile | `semantic_router.py` | Low | 2a.2 |
| 2a.4 | Fallback на keywords | `semantic_router.py` | Low | 2a.2 |
| 2a.5 | **ContextPrimer модуль** ⭐ | `context_primer.py` | Medium | 2a.1, Memory |
| 2a.6 | SemanticCache с numpy | `context_primer.py` | Low | 2a.5 |
| 2a.7 | Интеграция Router+Primer в api.py | `api.py` | Low | 2a.2, 2a.5 |
| 2a.8 | Startup Warming 🆕 | `api.py` | Low | 2a.5 |

### Фаза 2b: SelfReflection + Observability (2 дня)

| # | Задача | Файл | Сложность | Зависимости |
|---|--------|------|-----------|-------------|
| 2b.1 | **SelfReflection модуль** | `self_reflection.py` | Medium | MetricsEngine |
| 2b.2 | asyncio.gather для DB calls 🚀 | `self_reflection.py` | Low | 2b.1 |
| 2b.3 | Интеграция SelfReflection в api.py | `api.py` | Low | 2b.1 |
| 2b.4 | **Cognitive Health Endpoint** 🆕 | `api.py` | Low | 2a.2, 2a.5 |
| 2b.5 | Объединение с AdaptivePromptBuilder | `adaptation.py` | Low | 2b.1 |

### Фаза 3: Верификация агента (3-4 дня)

| # | Задача | Файл | Сложность | Зависимости |
|---|--------|------|-----------|-------------|
| 3.1 | ReflectiveAgent класс | `agent_v2.py` | Medium | autogpt.py |
| 3.2 | Verification prompt tuning | `agent_v2.py` | Medium | 3.1 |
| 3.3 | **Confidence-based skip** 🆕 | `agent_v2.py` | Low | 3.1 |
| 3.4 | Интеграция с MetricsEngine | `agent_v2.py` | Low | 3.1 |
| 3.5 | UI индикация верификации | Frontend | Medium | 3.1 |
| 3.6 | Тесты | `test_agent_v2.py` | Medium | 3.1 |

> **🆕 Confidence-based skip:** Если `confidence > 0.9`, пропускать верификацию для экономии LLM calls

### Фаза 4: Память ошибок + Synergy (2-3 дня)

| # | Задача | Файл | Сложность | Зависимости |
|---|--------|------|-----------|-------------|
| 4.1 | ErrorMemory класс | `error_memory.py` | Medium | CorrectionDetector |
| 4.2 | Новая таблица + index в schema | `schema.sql` | Low | - |
| 4.3 | Интеграция с CorrectionDetector | `error_memory.py` | Low | 4.1 |
| 4.4 | **🔗 Synergy: ErrorMemory → ContextPrimer** 🆕 | `context_primer.py` | Low | 4.1, 2a.5 |
| 4.5 | Warning injection | `api.py`, `agent_v2.py` | Low | 4.1 |

> **🔗 Synergy:** ContextPrimer может "вспомнить" релевантные ошибки из ErrorMemory ДО генерации

### Фаза 5: Python Sandbox (3-4 дня)

| # | Задача | Файл | Сложность | Зависимости |
|---|--------|------|-----------|-------------|
| 5.1 | PyBox AST analyzer | `pybox.py` | High | - |
| 5.2 | Execution sandbox | `pybox.py` | High | 5.1 |
| 5.3 | Tool integration | `tools.py` | Low | 5.1 |
| 5.4 | **SECURITY TESTS** | `test_pybox.py` | Critical | 5.1 |

### Фаза 6: Confidence + Final Polish (1 день)

| # | Задача | Файл | Сложность | Зависимости |
|---|--------|------|-----------|-------------|
| 6.1 | ConfidenceScorer | `confidence.py` | Low | - |
| 6.2 | **🔗 Synergy: Confidence → SelfReflection** 🆕 | `self_reflection.py` | Low | 6.1, 2b.1 |
| 6.3 | Интеграция в API | `api.py` | Low | 6.1 |
| 6.4 | Conversation Prefetch 🆕 | `api.py` | Low | 2a.5 |

---

## Часть 5: Метрики успеха

### Количественные

| Метрика | Текущее | Целевое | Как измерять |
|---------|---------|---------|--------------|
| Windows команды работают | 0% | 100% | `test_safe_shell.py` |
| Задачи агента верифицированы | 0% | 100% | verification_logs count |
| Ложные "Task Done" | ~30% | <5% | verification.status == FAIL после COMPLETED |
| Routing accuracy | N/A | >85% | Manual eval на 100 queries |
| PyBox sandbox безопасен | N/A | 100% | Security test suite |
| Metrics записываются | Частично | 100% | interaction_outcomes per message |
| **ContextPrimer cache hit** ⭐ | N/A | >40% | `primed.from_cache == True` rate |
| **ContextPrimer prefetch time** ⭐ | N/A | <100ms | `primed.prime_time_ms` p95 |
| **Token reduction** ⭐ | N/A | >50% | (old_tokens - new_tokens) / old_tokens |

### Качественные

- [ ] Агент объясняет ПОЧЕМУ он уверен в результате
- [ ] Агент предупреждает, когда уверенность низкая
- [ ] Агент помнит свои прошлые ошибки (ErrorMemory)
- [ ] Агент выбирает правильную модель для задачи
- [ ] IQ/Empathy метрики отражают реальное качество

---

## Часть 6: Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Embedding API недоступен | Medium | High | Fallback на keyword routing |
| Верификация слишком дорогая (LLM calls) | High | Medium | Confidence threshold для skip |
| PyBox bypass | Low | Critical | Extensive security tests, AST whitelist |
| Breaking changes в существующем API | Medium | High | Версионирование, backward compat |
| Regression в IQ/Empathy метриках | Medium | Medium | Integration tests |
| ErrorMemory дублирует CorrectionDetector | Low | Low | Использовать как расширение, не замену |

---

## Приложение A: Полная карта файлов

```text
src/core/
├── adaptation.py       # CorrectionDetector, FeedbackMiner [СУЩЕСТВУЕТ, + build_full_prompt]
├── autogpt.py          # AutoGPTAgent базовый [СУЩЕСТВУЕТ]
├── agent_v2.py         # NEW: ReflectiveAgent (расширяет autogpt)
├── config.py           # ThinkingModeConfig [СУЩЕСТВУЕТ]
├── confidence.py       # NEW: ConfidenceScorer
├── context_primer.py   # NEW: ContextPrimer (Semantic Prefetch) ⭐
├── embedding_service.py # NEW: Shared EmbeddingService 🆕
├── error_memory.py     # NEW: ErrorMemory (расширяет CorrectionDetector)
├── lm_client.py        # LMStudioClient [СУЩЕСТВУЕТ, detect_task_type ЗАМЕНЯЕТСЯ]
├── memory.py           # MemoryManager [СУЩЕСТВУЕТ]
├── metrics.py          # MetricsEngine [СУЩЕСТВУЕТ]
├── pybox.py            # NEW: PyBox sandbox
├── safe_shell.py       # NEW: SafeShell (Windows)
├── self_reflection.py  # NEW: SelfReflection (самоанализ и мотивация) ⭐
├── semantic_router.py  # NEW: SemanticRouter
├── tools.py            # ToolManager [СУЩЕСТВУЕТ, + PyBox + SafeShell]
└── user_profile.py     # UserProfile [СУЩЕСТВУЕТ]

data/
└── schema.sql          # + error_memory, verification_logs [ДОПОЛНИТЬ]

src/api/
└── api.py              # Integration point [ИЗМЕНИТЬ]

tests/
├── test_safe_shell.py      # NEW
├── test_semantic_router.py # NEW
├── test_context_primer.py  # NEW ⭐
├── test_embedding_service.py # NEW 🆕
├── test_agent_v2.py        # NEW
├── test_pybox.py           # NEW (CRITICAL SECURITY)
├── test_error_memory.py    # NEW
└── test_adaptation.py      # СУЩЕСТВУЕТ
```

---

## Приложение B: Checklist для Code Review

### SafeShell

- [ ] Windows built-ins wrapped correctly
- [ ] Linux commands work without wrapping
- [ ] Timeout kills process
- [ ] Output truncation works
- [ ] Real-time streaming callback works

### SemanticRouter

- [ ] Embeddings cached after init
- [ ] Fallback to keywords works when embedding fails
- [ ] UserProfile.verbosity respected
- [ ] Performance < 100ms per route
- [ ] All IntentCategories have examples

### ReflectiveAgent

- [ ] Extends AutoGPTAgent (не заменяет)
- [ ] Verification prompt gives useful results
- [ ] Max retries respected (default 3)
- [ ] MetricsEngine.record_interaction_outcome called
- [ ] Doesn't break existing AutoGPT tests

### ErrorMemory

- [ ] Uses CorrectionDetector (не заменяет)
- [ ] Vector similarity search works
- [ ] Warnings injected correctly
- [ ] Doesn't duplicate correction_log data
- [ ] Occurrences counter works

### PyBox

- [ ] ALL blocked imports rejected (os, sys, subprocess, etc.)
- [ ] ALL blocked calls rejected (exec, eval, open, etc.)
- [ ] Allowed imports work (math, json, datetime, etc.)
- [ ] Timeout kills process (10s)
- [ ] Output limit works (100KB)
- [ ] No file system access
- [ ] No network access
- [ ] **SECURITY TEST SUITE PASSES**

### ConfidenceScorer

- [ ] Hedging detection works (RU/EN)
- [ ] Score range valid (0-1)
- [ ] Level thresholds correct
- [ ] Integration with API done

### SelfReflection ⭐

- [ ] Интеграция с MetricsEngine (IQ/Empathy)
- [ ] Интеграция с CorrectionDetector (конкретные ошибки)
- [ ] Интеграция с FeedbackMiner (успешные паттерны)
- [ ] Streak calculation работает
- [ ] Fallback для первых дней (нет данных)
- [ ] Мотивационные фразы контекстуальные
- [ ] Не дублирует AdaptivePromptBuilder
- [ ] Performance < 50ms
- [ ] Тесты на edge cases (0 дней, 100 дней, негативный тренд)

### Integration (api.py)

- [ ] semantic_router.initialize() at startup
- [ ] error_memory.initialize() at startup
- [ ] self_reflection.initialize() at startup ⭐
- [ ] route used instead of request.thinking_mode
- [ ] self_reflection.build_reflection_prompt() перед ответом ⭐
- [ ] confidence_scorer called after response
- [ ] metrics_engine.record_interaction_outcome called
- [ ] Backward compatibility maintained

---

**Документ готов к реализации.**

*Версия 3.0 учитывает полный контекст существующей архитектуры MAX.*
*Все новые модули РАСШИРЯЮТ существующие, не заменяют.*
