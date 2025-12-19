# План реализации: "Слой Сознания" (Meta-Cognitive Layer) для MAX AI

> **Источники:** `Душа.txt`, `Изучить.txt`, `Проектирование _Слоя Сознания_ для AI OS.txt`  
> **Дата создания:** 2025-12-14  
> **Обновлено:** 2025-12-14 (Logic Audit)

---

## Обзор проекта

Цель — трансформировать MAX из реактивного чат-бота в когнитивного агента с:

- **Осознанностью** (память о целях и аксиомах)
- **Инструментами** (гибкий реестр с авто-генерацией схем)
- **Безопасностью** (параноидальная защита файловой системы)

---

## User Review Required

> [!IMPORTANT]
> Проект масштабный. Рекомендуется реализация по этапам с проверкой после каждого.
>
> [!WARNING]  
> Модуль Tool Registry потенциально **Breaking Change**: существующий `tools.py` будет рефакториться.
>
> [!CAUTION]
> Безопасность: модуль FileTools использует **Abliterated** (uncensored) модель. Любая ошибка в sandbox = риск удаления данных.

---

## 🔍 LOGIC AUDIT: Gap Analysis (добавлено 2025-12-14)

### ✅ УЖЕ РЕАЛИЗОВАНО (не дублировать!)

| Компонент | Файл | Что есть |
|-----------|------|----------|
| **Dynamic Prompt Injection** | `dynamic_persona.py` | `DynamicPersona.build_dynamic_prompt()` — инъекция user rules |
| **User Style Rules** | `dynamic_persona.py` | Хранение правил в `user_preferences`, источник `manual/feedback/llm_analysis` |
| **Feedback Loop** | `dynamic_persona.py` | `FeedbackLoopAnalyzer` — обнаружение недовольства, извлечение правил |
| **Base Sandbox** | `tools.py` | `ALLOWED_PATHS`, `_validate_path()`, `_is_path_allowed()` |
| **Dangerous Tools Flag** | `tools.py` | `DANGEROUS_TOOLS = {"delete_file", "run_command", "move_file"}` |
| **Requires Confirmation** | `tools.py` | `requires_confirmation()` метод в ToolExecutor |
| **User Preferences** | `user_profile.py` | `UserProfile`, `UserPreferences`, mood detection |
| **Backup System** | `backup.py` | `BackupManager` — локальные бэкапы, Google Drive sync |
| **Safe Shell** | `safe_shell.py` | `SafeShell` — cross-platform, timeout, validation |

### ❌ ОТСУТСТВУЕТ (нужно реализовать)

| Компонент | Чего не хватает | Приоритет |
|-----------|-----------------|-----------|
| **Soul / BDI State** | Нет файла `soul.json`, нет аксиом, нет глобальных целей | 🔴 P0 |
| **Tool Registry** | Схемы инструментов **hardcoded** в `TOOLS = [...]`, нет декораторов | 🟠 P1 |
| **Auto-Schema Generator** | Нет авто-генерации JSON Schema из типов Python | 🟠 P1 |
| **Shadow Copy** | `write_file` **НЕ делает бэкап** перед перезаписью! | 🔴 P0 |
| **Confirmation API** | UI не получает pending confirmations, нет endpoint `/api/confirmations` | 🟡 P2 |

### 🤥 LOGIC LIES (найденные несоответствия)

#### 1. `tools.py::_tool_write_file` — НЕ делает backup

Спецификация требует Shadow Copy, но код сразу перезаписывает файл без бэкапа.

#### 2. `tools.py::TOOLS` — 200+ строк hardcoded JSON

Добавление нового тула требует дублирования: функция + ручная схема.

#### 3. `dynamic_persona.py` — Нет BDI / Аксиом

Реализованы только User Rules (стиль ответа), нет аксиом и целей агента.

---

## Proposed Changes

### Компонент 1: Soul Manager (Модуль "Душа")

Реализация BDI (Belief-Desire-Intention) архитектуры для persistent identity.

> **ПРИМЕЧАНИЕ (Logic Audit):** Создаётся как **дополнение** к DynamicPersona, не замена!

---

#### [NEW] data/soul.json

**Файл состояния агента** (Pydantic-валидируемый JSON):

```json
{
  "meta": {
    "agent_id": "MAX_AI_PRIME",
    "version": "1.0.0",
    "boot_count": 0,
    "last_consolidation": null
  },
  "identity": {
    "archetype": "Sovereign Local AI",
    "core_directive": "Serve the Architect. Maintain autonomy. Optimize local resources.",
    "tone_vectors": {
      "formality": 0.7,
      "technical_depth": 0.9,
      "verbosity": 0.3
    }
  },
  "axioms": [
    "Simplicity > Complexity",
    "Local > Cloud", 
    "First Principles > Patterns",
    "User Safety > Efficiency"
  ],
  "bdi_state": {
    "beliefs": [],
    "desires": {
      "long_term": [],
      "short_term": []
    },
    "intentions": {
      "active_plan": null
    }
  },
  "current_focus": {
    "project": null,
    "context": null
  }
}
```

---

#### [NEW] src/core/soul/soul_manager.py

**Класс-синглтон для управления Душой:**

```python
class SoulManager:
    """BDI State Manager — дополняет DynamicPersona аксиомами и целями."""
    
    def __init__(self, soul_path: str = "data/soul.json"):
        self._soul: SoulState = self._load(soul_path)
        self._lock = asyncio.Lock()
    
    def generate_meta_injection(self) -> str:
        """Генерирует META-COGNITION блок для System Prompt (на английском)."""
        return f"""
[META-COGNITION LAYER]
Before responding, verify alignment with core axioms:
{self._format_axioms()}

Current Focus: {self._soul.current_focus.project or 'None set'}
Active Goal: {self._get_active_goal() or 'No active goal'}

If any pattern contradicts efficiency, break the pattern.
"""

    def _get_time_context(self) -> str:
        """Временной контекст для осознанности времени."""
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            greeting = "Good morning"
            period = "morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
            period = "afternoon"
        elif 17 <= hour < 22:
            greeting = "Good evening"
            period = "evening"
        else:
            greeting = "Good night"
            period = "night"
        
        return f"""
[TIME AWARENESS]
Current: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')})
Period: {period} — use "{greeting}" for greetings
Context: Use timestamps to reference past conversations ("yesterday we discussed...", "last week you mentioned...")
"""
```

**Полный `generate_meta_injection()` теперь включает:**

```python
def generate_meta_injection(self) -> str:
    return (
        self._get_axioms_block() +
        self._get_time_context() +  # ← Time Awareness
        self._get_focus_block()
    )
```

---

#### [MODIFY] src/api/routers/chat.py

**Интеграция Soul в основной чат:**

```diff
 from src.core.dynamic_persona import dynamic_persona
+from src.core.soul.soul_manager import soul_manager

 async def stream_chat(...):
     # Build prompt from DynamicPersona (user rules)
     base_prompt = await dynamic_persona.build_dynamic_prompt()
     
+    # Add Soul meta-cognition layer (axioms, goals)
+    meta_injection = soul_manager.generate_meta_injection()
+    system_prompt = base_prompt + "\n\n" + meta_injection
-    system_prompt = base_prompt
```

---

### Компонент 2: Tool Registry (Реестр Инструментов)

Паттерн "Магнитная рукоятка" — декораторы с авто-генерацией JSON Schema.

---

#### [NEW] src/core/tools/registry.py

**Центральный реестр инструментов:**

```python
class ToolRegistry:
    _tools: dict[str, ToolDefinition] = {}
    
    def register(
        self, 
        name: str = None,
        description: str = None,
        requires_confirmation: bool = False
    ):
        """Декоратор для регистрации инструмента."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            schema = self._generate_schema(func)
            
            self._tools[tool_name] = ToolDefinition(
                name=tool_name,
                description=description or func.__doc__,
                parameters=schema,
                function=func,
                requires_confirmation=requires_confirmation
            )
            return func
        return decorator
    
    def _generate_schema(self, func: Callable) -> dict:
        """Генерирует JSON Schema из аннотаций типов."""
        hints = get_type_hints(func)
        # str -> "string", int -> "integer", bool -> "boolean"
```

---

### Компонент 3: Shadow Copy FIX (Исправление write_file)

> **CRITICAL (Logic Audit):** Это P0 баг — `write_file` не делает бэкап!

#### [MODIFY] src/core/tools.py::_tool_write_file

```diff
 async def _tool_write_file(self, path: str, content: str, append: bool = False):
     p = _validate_path(path)
+    
+    # Shadow Copy: backup before overwrite (P0 FIX)
+    if p.exists() and not append:
+        self._create_backup(p)
+    
     p.parent.mkdir(parents=True, exist_ok=True)
     mode = "a" if append else "w"
     with open(p, mode, encoding="utf-8") as f:
         f.write(content)
     return ToolResult(True, f"Written to {path}")

+def _create_backup(self, path: Path) -> Path:
+    """Shadow Copy — обязательный бэкап перед перезаписью."""
+    backup_dir = Path("data/.file_backups")
+    backup_dir.mkdir(exist_ok=True)
+    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
+    backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
+    shutil.copy2(path, backup_path)
+    return backup_path
```

---

## Структура новых файлов

```
src/core/
├── soul/                      # [NEW] Модуль "Душа"
│   ├── __init__.py
│   ├── models.py              # Pydantic модели
│   └── soul_manager.py        # SoulManager singleton
│
├── tools/                     # [NEW] Реестр инструментов  
│   ├── __init__.py
│   └── registry.py            # ToolRegistry с декораторами
│
├── tools.py                   # [MODIFY] — добавить Shadow Copy
├── dynamic_persona.py         # [KEEP] — уже работает
├── user_profile.py            # [KEEP]
├── backup.py                  # [KEEP]
└── safe_shell.py              # [KEEP]

data/
├── soul.json                  # [NEW] Файл Души
└── .file_backups/             # [NEW] Shadow copies
```

---

## Verification Plan

### Автоматические тесты

```bash
pytest tests/test_soul_manager.py -v
pytest tests/test_tool_registry.py -v
pytest tests/test_sandbox.py -v
```

### Критические тесты безопасности

- `test_shadow_copy_created` — бэкап создается перед перезаписью
- `test_path_traversal_attack` — `../../../` должен кидать ошибку

---

## Этапы реализации (обновлено после Logic Audit)

| # | Модуль | Работа | Время |
|---|--------|--------|-------|
| 1 | **Shadow Copy** | Добавить `_create_backup()` в `tools.py` | 30 мин |
| 2 | **Soul Manager** | Новый модуль `soul/`, `soul.json` | 2 ч |
| 3 | **Tool Registry** | `registry.py` с декораторами | 2 ч |
| 4 | **Интеграция** | Инъекция в `chat.py` | 30 мин |
| 5 | **Тестирование** | Unit + Integration | 1.5 ч |

**Итого:** ~6-7 часов (оптимизировано с 12-15 благодаря Gap Analysis)

---

## ✅ Definition of Done

- [ ] `write_file` создает `.bak` перед перезаписью
- [ ] `soul.json` существует и загружается
- [ ] `SoulManager.generate_meta_injection()` добавляет аксиомы в prompt
- [ ] `@registry.register()` работает для нового инструмента
- [ ] Тесты проходят без warnings

---

## 🚀 OPTIMIZATION ANALYSIS (добавлено 2025-12-14)

> Анализ по workflow `/optimization` — "Скорость не должна убивать Комфорт"

### Бюджеты производительности (из спецификации)

| Метрика | Бюджет | Наш случай |
|---------|--------|------------|
| **VRAM** | ~14 GB чистых | Qwen 14B Q4_K_M (~9.5GB) + KV Cache (~2.5GB) |
| **UI Response** | < 300ms | Soul injection должен быть мгновенным |
| **Cold Start** | < 5s | Загрузка soul.json + schema registry |

---

### 🚀 INSTANT WINS (бесплатные улучшения)

#### 1. Soul File: Lazy Loading + Caching

**Проблема:** Если читать `soul.json` на каждый запрос — это I/O блокировка.

**Решение:**

```python
class SoulManager:
    _cache: Optional[SoulState] = None
    _cache_time: float = 0
    CACHE_TTL = 300  # 5 минут
    
    def get_soul(self) -> SoulState:
        if self._cache and (time.time() - self._cache_time) < self.CACHE_TTL:
            return self._cache  # 🚀 Instant
        
        self._cache = self._load_from_disk()
        self._cache_time = time.time()
        return self._cache
```

**Выгода:** 0ms вместо ~5-10ms на каждый запрос.

---

#### 2. Tool Registry: Schema Pre-generation

**Проблема:** Если генерировать JSON Schema при каждом `get_all_schemas()` — дорого.

**Решение:**

```python
class ToolRegistry:
    def register(self, ...):
        def decorator(func):
            # Генерируем схему ОДИН РАЗ при регистрации
            schema = self._generate_schema(func)
            self._tools[name] = ToolDefinition(..., parameters=schema)
            return func
        return decorator
    
    def get_all_schemas(self) -> list[dict]:
        # Просто возвращаем уже готовое — O(n) копирование
        return [t.to_schema() for t in self._tools.values()]
```

---

#### 3. Shadow Copy: Async I/O

**Проблема:** `shutil.copy2()` — блокирующая операция.

**Решение:**

```python
import aiofiles

async def _create_backup_async(self, path: Path) -> Path:
    """Non-blocking backup."""
    backup_path = self._get_backup_path(path)
    async with aiofiles.open(path, 'rb') as src:
        content = await src.read()
    async with aiofiles.open(backup_path, 'wb') as dst:
        await dst.write(content)
    return backup_path
```

**Выгода:** Не блокирует Event Loop при больших файлах.

---

### ⚖️ TRADE-OFFs (компромиссы)

#### 1. GPU Lock для монопольного доступа

**Контекст (из спецификации):**
> "System 1 и System 2 конкурируют за GPU"

**Текущее состояние:** В коде **НЕТ** `asyncio.Lock()` для LLM вызовов!

**Решение (из спецификации):**

```python
class SoulManager:
    def __init__(self):
        self._llm_lock = asyncio.Lock()  # Монопольный доступ к GPU
    
    async def consolidate(self, ...):
        async with self._llm_lock:
            # Только один LLM call одновременно
            await self._update_soul_via_llm(...)
```

**Trade-off:** +Latency для параллельных запросов, но -OOM риск.

---

#### 2. Persistence Strategy: Quick Save + Deep Consolidation

**Два уровня сохранения:**

| Операция | Частота | Время | Что делает |
|----------|---------|-------|------------|
| **Quick Save** | Каждую минуту | ~5-10ms | Дамп `soul.json` на диск |
| **Deep Consolidation** | idle > 5 мин | 10-30 сек | LLM анализ → извлечение инсайтов |

**Решение:**

```python
class SoulManager:
    _last_user_interaction: float = 0  # timestamp
    USER_ACTIVE_THRESHOLD = 60  # 1 минута
    
    def touch_user_activity(self):
        """Вызывать при каждом запросе пользователя."""
        self._last_user_interaction = time.time()
    
    def _is_user_active(self) -> bool:
        """Проверка: был ли запрос < 1 минуты назад."""
        return (time.time() - self._last_user_interaction) < self.USER_ACTIVE_THRESHOLD
    
    async def _deep_consolidation_loop(self):
        """Deep Consolidation при idle > 5 минут — НЕ БЛОКИРУЕТ ЮЗЕРА."""
        while True:
            await asyncio.sleep(300)  # 5 минут
            
            # 🛡️ ANTI-LAG: Не занимаем GPU если юзер активен!
            if self._is_user_active():
                continue  # Отложить сон
            
            if self._is_idle() and self._has_new_messages():
                async with self._llm_lock:
                    await self._extract_insights_via_llm()
```

---

#### 4. Протокол подтверждения (Cerberus)

**Проблема:** Если API вернёт `{"status": "confirmation_needed"}` как текст — UI зависнет.

**Решение:** Структурированный `ToolResult`:

```python
@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    # Cerberus Protocol:
    status: str = "complete"  # "complete" | "pending" | "error"
    confirmation_id: Optional[str] = None
    confirmation_message: Optional[str] = None

# Использование:
def _tool_delete_file(self, path: str) -> ToolResult:
    if not self._has_confirmation(path):
        return ToolResult(
            success=False,
            output="",
            status="pending",
            confirmation_id=str(uuid.uuid4()),
            confirmation_message=f"Удалить файл {path}? Это действие необратимо."
        )
```

---

#### 5. Масштабируемость реестра инструментов

**Проблема:** 30 тулов = 5000 токенов схемы, контекст забит.

**Решение:** Метод с фильтрацией + TODO для RAG:

```python
class ToolRegistry:
    def get_tools_schema(
        self, 
        filter_tags: Optional[list[str]] = None,
        limit: Optional[int] = None
    ) -> list[dict]:
        """
        Получить схемы инструментов с опциональной фильтрацией.
        
        # TODO: Implement RAG for tool selection
        # В будущем: semantic search по запросу юзера → выбор релевантных тулов
        """
        tools = list(self._tools.values())
        
        if filter_tags:
            tools = [t for t in tools if t.category in filter_tags]
        
        if limit:
            tools = tools[:limit]
        
        return [t.to_schema() for t in tools]

---

#### 3. Graceful Shutdown (Экстренное сохранение)

**Проблема:** Пользователь закрыл приложение до таймера → потеря данных.

**Решение:**

```python
# В app.py lifespan:
async def lifespan(app):
    # Startup
    await soul_manager.load_async()
    await soul_manager.start_persistence_loop()
    
    yield  # App работает
    
    # Shutdown — ОБЯЗАТЕЛЬНО сохраняем
    await soul_manager.save_on_exit()

class SoulManager:
    async def save_on_exit(self):
        """Экстренное сохранение при закрытии."""
        if self._has_changes:
            await self._save_to_disk()
            log.api("🧠 Soul saved on shutdown")
```

**Trade-off:** Quick Save раз в минуту — +1 I/O операция, но гарантия что потеряем максимум 1 минуту изменений.

---

### 🧠 UX BOOSTs (воспринимаемая скорость)

#### 1. Optimistic Soul Loading

**Сценарий:** При старте приложения — загрузить Soul в фоне, не блокируя UI.

```python
# В app.py lifespan:
async def lifespan(app):
    # Параллельная загрузка
    await asyncio.gather(
        memory.initialize(),
        soul_manager.load_async(),  # Не блокирует
        context_orchestrator.initialize(db)
    )
```

---

#### 2. Stream Soul Status в UI

**Идея:** Показывать текущий "фокус" агента в UI (как Thinking Panel).

```typescript
// Frontend: SoulPanel.tsx
const SoulPanel = () => {
  const { currentFocus, activeGoal } = useSoulState();
  return (
    <div className="soul-panel">
      <span>🎯 {currentFocus || "Free mode"}</span>
      <span>🧠 {activeGoal || "No active goal"}</span>
    </div>
  );
};
```

---

### 📊 NEEDS MEASUREMENT (требует профилинга)

| Подозрение | Как измерить |
|------------|--------------|
| Soul injection overhead | `%timeit soul_manager.generate_meta_injection()` |
| Tool schema generation | `cProfile -s cumulative` на registry |
| Backup I/O latency | Логировать время `_create_backup()` |

---

### 🚫 ANTI-PATTERNS (чего избегать)

| Anti-pattern | Почему плохо | Правильно |
|--------------|--------------|-----------|
| ❌ Soul reload на каждый запрос | I/O блокировка | Кэш с TTL |
| ❌ Sync file copy | Блокирует Event Loop | `aiofiles` |
| ❌ Schema generation в runtime | CPU waste | Pre-generate при регистрации |
| ❌ Без Lock на GPU | OOM при параллелизме | `asyncio.Lock()` |

---

## Обновленные этапы реализации

| # | Модуль | Работа | Время |
|---|--------|--------|-------|
| 1 | **Shadow Copy** | `_create_backup()` + async I/O | 45 мин |
| 2 | **Soul Manager** | Модуль + кэширование + Dream Cycle | 2.5 ч |
| 3 | **Tool Registry** | Декораторы + pre-generated schemas | 2 ч |
| 4 | **GPU Lock** | `asyncio.Lock()` для LLM calls | 30 мин |
| 5 | **Интеграция** | Инъекция в `chat.py` + UI status | 1 ч |
| 6 | **Тестирование** | Unit + Performance benchmarks | 2 ч |

**Итого:** ~8-9 часов (добавлены оптимизации)

## 📋 ПОЛНЫЙ ЧЕКЛИСТ РЕАЛИЗАЦИИ

> Каждый пункт должен быть выполнен, проверен и отлажен.

---

### PHASE 1: Soul Manager (Модуль "Душа")

#### 1.1 Файлы

- [x] Создать `src/core/soul/__init__.py`
- [x] Создать `src/core/soul/models.py` — Pydantic схемы (SoulState, BDIState, Identity)
- [x] Создать `src/core/soul/soul_manager.py` — класс SoulManager
- [x] Создать `data/soul.json` — начальное состояние

#### 1.2 Функционал SoulManager

- [x] `get_soul()` — lazy loading с кэшированием (TTL 5 мин)
- [x] `load_async()` — асинхронная загрузка при старте
- [x] `_save_to_disk()` — async сохранение через aiofiles
- [x] `save_on_exit()` — graceful shutdown
- [x] `generate_meta_injection()` — генерация блока для System Prompt
- [x] `_get_time_context()` — Time Awareness (утро/день/вечер/ночь)
- [x] `_get_axioms_block()` — форматирование аксиом
- [x] `_get_focus_block()` — текущий фокус и цели
- [x] `touch_user_activity()` — трекинг активности юзера
- [x] `_is_user_active()` — проверка активности (< 1 мин назад)
- [x] `set_focus()` — обновление фокуса
- [x] `add_short_term_goal()` — добавление цели
- [x] `add_insight()` — добавление инсайта

#### 1.3 Persistence Loops

- [x] `start_persistence_loop()` — запуск фоновых задач
- [x] `_quick_save_loop()` — Quick Save каждые 60 сек
- [ ] `_deep_consolidation_loop()` — Deep Consolidation при idle (TODO: LLM call)

#### 1.4 Интеграция

- [x] Импорт `soul_manager` в `app.py`
- [x] Вызов `load_async()` в startup
- [x] Вызов `start_persistence_loop()` в startup
- [x] Вызов `save_on_exit()` в shutdown
- [x] Импорт `soul_manager` в `chat.py`
- [x] Вызов `touch_user_activity()` в начале `/chat`
- [x] Вызов `generate_meta_injection()` при сборке System Prompt

#### 1.5 Тестирование Soul Manager

- [ ] Unit test: `test_soul_manager_load()` — загрузка soul.json
- [ ] Unit test: `test_soul_manager_cache()` — кэширование работает
- [ ] Unit test: `test_soul_manager_time_awareness()` — правильное приветствие
- [ ] Unit test: `test_soul_manager_save_on_exit()` — сохранение при shutdown
- [ ] Integration test: проверить инъекцию в System Prompt

---

### PHASE 2: Tool Registry (Реестр Инструментов)

#### 2.1 Файлы

- [x] Создать `src/core/tools/__init__.py`
- [x] Создать `src/core/tools/registry.py`

#### 2.2 Функционал ToolRegistry

- [x] `@registry.register()` — декоратор регистрации
- [x] `_generate_schema()` — авто-генерация JSON Schema из type hints
- [x] `_python_type_to_json()` — конвертация типов Python → JSON
- [x] `get_tools_schema()` — получение всех схем
- [x] `get_tools_schema(filter_tags=...)` — фильтрация по категории
- [x] `get_tools_schema(limit=...)` — ограничение количества
- [x] `get()` — получение тула по имени
- [x] `requires_confirmation()` — проверка флага подтверждения
- [x] `execute()` — выполнение тула по имени

#### 2.3 Миграция существующих тулов (Phase 2+)

- [ ] Мигрировать `read_file` на `@registry.register()`
- [ ] Мигрировать `write_file` на `@registry.register()`
- [ ] Мигрировать `list_directory` на `@registry.register()`
- [ ] Мигрировать `delete_file` на `@registry.register(requires_confirmation=True)`
- [ ] Мигрировать `run_command` на `@registry.register(requires_confirmation=True)`
- [ ] Мигрировать `web_search` на `@registry.register(category="web")`
- [ ] Удалить hardcoded `TOOLS = [...]` из `tools.py`

#### 2.4 RAG для выбора тулов (Phase 3)

- [ ] Добавить embedding для описаний тулов
- [ ] Реализовать semantic search по запросу юзера
- [ ] Выбирать только релевантные тулы (<10) вместо всех

#### 2.5 Тестирование Tool Registry

- [ ] Unit test: `test_registry_register_decorator()` — декоратор работает
- [ ] Unit test: `test_registry_auto_schema()` — схема генерируется правильно
- [ ] Unit test: `test_registry_filter_tags()` — фильтрация по категории
- [ ] Unit test: `test_registry_execute()` — выполнение тула

---

### PHASE 3: Secure FileTools (Безопасность)

#### 3.1 Shadow Copy

- [x] Добавить `_create_shadow_copy()` в `ToolExecutor`
- [x] Вызов backup перед `write_file` (если файл существует и не append)
- [x] Бэкапы в `data/.file_backups/` с timestamp

#### 3.2 Cerberus Protocol

- [x] Расширить `ToolResult` полями: `status`, `confirmation_id`, `confirmation_message`
- [ ] Реализовать `_has_confirmation()` — проверка pending confirmations
- [ ] Хранить pending confirmations в памяти/базе
- [ ] Добавить TTL для confirmations (5 мин)

#### 3.3 Confirmation API

- [ ] Создать `src/api/routers/confirmations.py`
- [ ] `GET /api/confirmations` — список pending confirmations
- [ ] `POST /api/confirmations/{id}/approve` — одобрить
- [ ] `POST /api/confirmations/{id}/reject` — отклонить
- [ ] Интегрировать в `ToolExecutor.execute()`

#### 3.4 Frontend: Confirmation UI

- [ ] Компонент `ConfirmationModal.tsx`
- [ ] Hook `useConfirmations()` — polling pending confirmations
- [ ] Кнопки "Разрешить" / "Запретить"
- [ ] Показ деталей операции (файл, действие)

#### 3.5 Тестирование Security

- [ ] Unit test: `test_shadow_copy_created()` — бэкап создается
- [ ] Unit test: `test_shadow_copy_timestamp()` — правильный формат имени
- [ ] Unit test: `test_path_traversal_blocked()` — `../` отклоняется
- [ ] Unit test: `test_confirmation_required()` — опасные операции требуют подтверждения
- [ ] Integration test: полный цикл confirmation flow

---

### PHASE 4: Deep Consolidation (LLM-based)

#### 4.1 Консолидация памяти

- [x] Реализовать `_extract_insights_via_llm()` в SoulManager
- [x] Prompt для извлечения insights из диалога
- [x] Сохранение insights в soul.json
- [ ] Обновление beliefs на основе фактов (TODO Phase 2+)

#### 4.2 Триггеры консолидации

- [x] Idle time > 5 минут
- [x] User Priority: не запускать если юзер активен
- [ ] Token limit: после N токенов диалога (TODO)
- [ ] Explicit trigger: команда "/consolidate" (TODO)

#### 4.3 Тестирование Consolidation

- [ ] Mock LLM test: `test_consolidation_extracts_insights()`
- [ ] Integration test: insights появляются в soul.json

---

### PHASE 5: Верификация и Отладка

#### 5.1 Smoke Tests

- [ ] Запустить сервер: `uvicorn app:app --reload`
- [ ] Отправить сообщение в чат
- [ ] Проверить логи: "🧠 Soul meta-cognition injected"
- [ ] Проверить System Prompt содержит аксиомы и время
- [ ] Проверить soul.json обновился (boot_count++)

#### 5.2 Shadow Copy Test

- [ ] Создать файл через MAX
- [ ] Изменить этот файл через MAX
- [ ] Проверить `data/.file_backups/` содержит бэкап

#### 5.3 Anti-Lag Test

- [ ] Отправить сообщение
- [ ] Проверить логи: Consolidation НЕ запускается сразу
- [ ] Подождать 6 минут без сообщений
- [ ] Проверить логи: Consolidation запустилась

#### 5.4 Graceful Shutdown Test

- [ ] Изменить soul.json через API (set_focus)
- [ ] Остановить сервер (Ctrl+C)
- [ ] Проверить логи: "🧠 Soul saved on shutdown"
- [ ] Проверить soul.json сохранился

#### 5.5 Performance Benchmarks

- [ ] `%timeit soul_manager.generate_meta_injection()` < 1ms
- [ ] `%timeit registry.get_tools_schema()` < 5ms
- [ ] Memory: Soul caching не течет

---

### PHASE 6: Документация и Cleanup

#### 6.1 Документация

- [ ] README для `src/core/soul/`
- [ ] README для `src/core/tools/`
- [ ] Обновить `MIND/SystemMap.md` с новыми модулями

#### 6.2 Cleanup

- [ ] Удалить debug prints
- [ ] Проверить все TODO comments
- [ ] Запустить `/clean` workflow

---

### PHASE 7: Output Sanitizer (Очистка вывода)

> Модель выдает артефакты: звездочки, User:, иероглифы. Решение: Regex.

#### 7.1 Файлы

- [x] `src/core/utils/__init__.py`
- [x] `src/core/utils/sanitizer.py`
- [x] Обновить `src/core/config.py` (добавлен `repetition_penalty: 1.1`)

#### 7.2 TextSanitizer

- [x] `clean_output(text)` — полная очистка
- [x] `stream_cleaner(chunk)` — SSE очистка
- [x] Singleton `sanitizer`
- [x] `remove_trailing_artifacts(text)` — удаление хвоста

#### 7.3 Паттерны (все реализованы)

- [x] `\*\*+` → `**` (множественные звездочки)
- [x] `User:$` → удалить
- [x] `\n{3,}` → `\n\n`
- [x] Иероглифы в конце → удалить
- [x] Спец-токены `<|im_end|>` → удалить

#### 7.4 Config

- [x] `temperature: 0.7` (было)
- [x] `repetition_penalty: 1.1` (добавлено)
- [ ] `stop_tokens` список (TODO: нужно передавать в LM Studio API)

#### 7.5 Интеграция

- [x] `stream_cleaner(chunk)` в chat.py SSE
- [x] `clean_output(full_response)` перед memory.add_message

#### 7.6 Тестирование

- [ ] Unit test: `test_sanitizer_removes_asterisks()`
- [ ] Unit test: `test_sanitizer_removes_user_artifact()`
- [ ] Unit test: `test_stream_cleaner_realtime()`

#### 7.7 Markdown Rendering (BONUS)

- [x] Установлен `react-markdown`
- [x] Установлен `@tailwindcss/typography`
- [x] MessageBubble.tsx использует ReactMarkdown
- [x] Стилизация: code, pre, strong, links

---

## ✅ DEFINITION OF DONE (Финальная проверка)

> **ВАЖНО:** Добавлена PHASE 7: Output Sanitizer

Проект считается ЗАВЕРШЁННЫМ когда:

- [ ] Все PHASE 1-7 чекбоксы отмечены ✅
- [ ] Все unit tests проходят: `pytest tests/ -v`
- [ ] Нет ошибок при запуске сервера
- [ ] Soul injection видна в логах каждого запроса
- [ ] Shadow Copy работает (бэкапы создаются)
- [ ] Time Awareness: правильное приветствие по времени суток
- [ ] Graceful Shutdown: soul сохраняется при Ctrl+C
- [ ] Output Sanitizer: нет артефактов в выводе

---

## Связанные Workflows

- После реализации: `/check` (верификация)
- Для UI подтверждений: `/UI` (UX дизайн)
- Перед мержем: `/clean` (уборка)
