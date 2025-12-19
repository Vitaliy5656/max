# Fix Log

---

## 2025-12-15 18:17

**Режим:** FULL SWEEP (UI Audit)
**Issues исправлено:** 9

### Исправленные issues

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| P0 | useAgent interval leak | `useAgent.ts` | ✅ Fixed |
| P0 | useModels hardcoded URL | `useModels.ts` | ✅ Fixed |
| P0 | useConversations no error handling | `useConversations.ts` | ✅ Fixed |
| P0 | addLog memory leak | `useUI.ts` | ✅ Fixed |
| P0 | handleRegenerate не завершает action | `App.tsx` | ✅ Fixed |
| P1 | EmptyState English text | `ResearchLab.tsx` | ✅ Fixed (RU) |
| P1 | WebSocket без индикации статуса | `useResearch.ts` | ✅ Fixed |
| P1 | StatsDashboard статичный статус | `ResearchLab.tsx` | ✅ Fixed |
| P1 | sidebarOpen не персистится | `useUI.ts` | ✅ Fixed |

### Изменения

**useAgent.ts:**

- Добавлен `pollIntervalRef` для хранения interval ID
- useEffect cleanup очищает interval при unmount
- Добавлена функция `stopAgent()` для принудительной остановки

**useModels.ts:**

- Заменён hardcoded `http://localhost:8000` на `API_BASE`
- Добавлен rollback при ошибке `updateModelSelectionMode`

**useConversations.ts:**

- Добавлены `isLoading` и `error` states
- `createConversation` обёрнут в try/catch
- Добавлена функция `clearError()`

**useUI.ts:**

- `addLog()` ограничен до 100 записей (slice)
- `sidebarOpen` сохраняется в localStorage
- Добавлена функция `clearLogs()`

**App.tsx:**

- `handleRegenerate` теперь автоматически вызывает `handleSendMessage()`
- Локализован текст "Regenerating response..." → "Регенерация ответа..."

**ResearchLab.tsx:**

- EmptyState переведён на русский
- StatsDashboard получает `connectionStatus` и показывает реальный статус WS

**useResearch.ts:**

- Добавлен state `connectionStatus: 'connecting' | 'connected' | 'disconnected'`
- WebSocket события обновляют статус

**Tests:** ✅ TypeScript build passed (tsc --noEmit)

---

## 2025-12-15 18:26

**Режим:** P2 IMPROVEMENTS BATCH
**Issues исправлено:** 6

### Исправленные issues

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| P2 | QualityBar без объяснения | `ResearchLab.tsx` | ✅ Fixed (tooltip) |
| P2 | TopicCard buttons скрыты без hover | `ResearchLab.tsx` | ✅ Fixed (opacity-60) |
| P2 | TopicCard нет focus states | `ResearchLab.tsx` | ✅ Fixed (focus:ring) |
| P2 | InputArea button без tooltip | `InputArea.tsx` | ✅ Fixed |
| P2 | useMetrics без error callback | `useMetrics.ts` | ✅ Fixed (onError) |
| P2 | MessageBubble feedback без tooltip | `MessageBubble.tsx` | ✅ Fixed |

### Изменения

**ResearchLab.tsx:**

- QualityBar: tooltip explaining 70%+/40-69%/<40% thresholds
- TopicCard: buttons visible at `opacity-60` (was `opacity-0`)
- All buttons: `focus:ring-2` and `aria-label` for accessibility

**InputArea.tsx:**

- Dynamic button label (Send/Stop)
- Focus ring with offset
- Square icon from lucide-react for stop button

**useMetrics.ts:**

- Added `UseMetricsOptions` interface with `onError` callback
- Added `isLoading` and `error` states

**MessageBubble.tsx:**

- Feedback buttons: added `title` attribute
- Added `focus:ring-2` for keyboard navigation

**Tests:** ✅ TypeScript build passed

---

## 2025-12-15 18:31

**Режим:** P2 BATCH 4 (Stats & Progress)
**Issues исправлено:** 2

### Исправленные issues

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| P2 | Tokens/sec counter | `useChat.ts` | ✅ Fixed |
| P2 | Upload progress bar | `client.ts` | ✅ Fixed |

### Изменения

**useChat.ts:**

- Added `tokenCount`, `tokensPerSecond` states
- Added `generationStartRef` for timing
- Reset on new message, increment in `onToken`
- Calculate tokensPerSecond based on elapsed time
- Exposed in return object for UI display

**api/client.ts:**

- Added `uploadDocumentWithProgress()` function
- Uses XMLHttpRequest for native progress events
- `onProgress(percent)` callback for UI progress bar

**Tests:** ✅ TypeScript build passed

---

**Режим:** P0/P1 CRITICAL FIXES
**Issues исправлено:** 5

### Исправленные issues (из аудита /logic)

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| P0 | No Timeout on Cognitive Loop | `src/api/api.py` | ✅ Fixed (180s limit) |
| P0 | Potential Infinite Loop (replan) | `graph.py`, `types.py`, `memory.py`, `planner.py` | ✅ Fixed (total_iterations) |
| P1 | Prompts criteria ≠ code thresholds | `prompts.py` | ✅ Fixed (aligned 0.75) |
| P1 | CognitiveConfig dead code | `types.py`, `graph.py` | ✅ Fixed (now used!) |
| P1 | user_context not in Executor/Verifier | `executor.py`, `verifier.py` | ✅ Fixed |

### Изменения

**P0: Timeout на Cognitive Loop** (`api.py`)

- Добавлен `COGNITIVE_LOOP_TIMEOUT = 180` секунд
- Реальный `duration_ms` вместо захардкоженного `0`
- Fallback сообщение при timeout

**P0: Бесконечный цикл** (multiple files)

- Добавлено новое поле `total_iterations` в `CognitiveState`
- `total_iterations` **НИКОГДА** не сбрасывается (в отличие от `iterations`)
- Hard limit `MAX_TOTAL_ITERATIONS = 10` в `route_verification()`
- Обновлены `memory.py` и `planner.py` для инкремента `total_iterations`

**P1: Пороги и промпты** (`prompts.py`)

- Обновлены критерии в `VERIFIER_SYSTEM_PROMPT`
- Теперь явно указано: "Score 0.75+ = ACCEPTED"
- Модель будет давать более высокие оценки хорошим ответам

**P1: CognitiveConfig** (`types.py`, `graph.py`)

- Добавлены поля: `max_iterations_per_plan`, `max_total_iterations`, `accept_threshold`, etc.
- `graph.py` теперь использует `_config` вместо хардкода
- Добавлена функция `set_cognitive_config()` для переопределения

**P1: user_context** (`executor.py`, `verifier.py`)

- Executor теперь инжектит user_context в system prompt
- Verifier учитывает user preferences при оценке
- Critique увеличен до 300 символов (было 100)

**Tests:** Code Review + Logic Verification

---

## 2025-12-13 23:15

**Режим:** FULL SWEEP
**Issues исправлено:** 4

### Исправленные issues

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | RAG Broken References | `src/core/rag.py` | ✅ Fixed |
| 2 | Memory Summary Data Loss | `src/core/memory.py` | ✅ Fixed |
| 3 | AutoGPT Blind Trust | `src/core/autogpt.py` | ✅ Fixed |
| 4 | API No Pagination | `src/api/api.py` | ✅ Fixed |

### Изменения

- **src/core/rag.py**: File persistence implemented (copy to `data/uploads/`).
- **src/core/memory.py**: Recursive summarization (merging old+new).
- **src/core/autogpt.py**: Added LLM-based verification step for task completion.
- **src/core/memory.py**: SQL updated for OFFSET.
- **src/api/api.py**: Endpoint updated for OFFSET.

**Tests:** Verified via Code Review (Logic Hardening)

---

## 2025-12-13 23:10

**Режим:** FULL SWEEP
**Issues исправлено:** 5

### Исправленные issues

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | P0: Command Injection | src/core/safe_shell.py | ✅ Fixed |
| 2 | P1: Race Condition | src/api/api.py | ✅ Fixed |
| 3 | P1: Dead Code | src/api/routers/chat.py | ✅ Deleted |
| 4 | P2: Hardcoded Config | src/core/config.py | ✅ Fixed |
| 5 | P2: AutoGPT Singleton | src/api/api.py | ✅ Fixed (409) |

### Изменения

- **safe_shell.py**: Implemented strict validation for dangerous characters (`&`, `|`, `>`, etc) and fixed logic bug in return code.
- **api.py**: Removed global `_current_conversation_id` state. Changed agent busy error to 409 Conflict.
- **config.py**: Added `os.getenv("LM_STUDIO_URL")` support.
- **routers/chat.py**: Deleted duplicate dead code.

**Tests:** ✅ Passed (`test_safe_shell_injection.py`)

---

## 2025-12-13 02:25 — Fix Memory Extraction Crash

**Проблема:**
`AttributeError: 'Logger' object has no attribute 'core'`
При отправке сообщений фоновая задача извлечения фактов (`_extract_facts`) падала с ошибкой.
Результат: ИИ не запоминал имя пользователя, так как процесс падал до сохранения факта.

**Причина:**
В `memory.py` использовался метод `log.core()`, который отсутствовал в классе `Logger` (он имеет только `api`, `lm`, `stream`, `debug` и т.д.).

**Решение:**
Заменен вызов `log.core(...)` на `log.debug(...)` в `src/core/memory.py`.

**Статус:** ✅ FIXED

---

## 2025-12-13 02:15 — Fix MetricsEngine API Mismatch

**Проблема:**
`TypeError: record_interaction_outcome() got an unexpected keyword argument 'detected_positive'`
При отправке фидбека (лайк/дизлайк) API падало с 500 ошибкой.

**Причина:**
Метод `metrics_engine.record_interaction_outcome` был рассчитан только на неявный (implicit) анализ текста и не принимал явные аргументы `detected_positive/negative`, которые передавал `api.py`.

**Решение:**
Обновлен `src/core/metrics.py`: добавлены опциональные аргументы `detected_positive` и `detected_negative`, которые имеют приоритет над автоматическим анализом.

**Статус:** ✅ FIXED

---

## 2025-12-12 16:25 — Logic/Model Management Fixes

**Режим:** FULL SWEEP (Logic Audit)
**Issues исправлено:** 5

### Исправленные issues

| # | Приоритет | Issue | Статус |
|---|-----------|-------|--------|
| 1 | P0 🔴 | Race Condition (lm_client) | ✅ Fixed (AsyncLock) |
| 2 | P1 🟠 | Model List Lie | ✅ Fixed (CLI Scan) |
| 3 | P1 🟠 | State Desync | ✅ Fixed (Sync State side-channel) |
| 4 | P2 🟡 | Lazy Impl (No Loading Feedback) | ✅ Fixed (SSE 'loading' event) |
| 5 | P2 🟡 | Data Gap (Fake Models API) | ✅ Fixed (Async + Real Data) |

### Изменения

- `lm_client.py`: Добавлен `asyncio.Lock`, интеграция с `lms ls` и `get_loaded_model`.
- `api.py`: Переписан `GET /api/models` на async, добавлен SSE feedback при смене модели.
- `api.py`: Добавлена логика `ensure_model_loaded` перед генерацией.

**Build:** ✅ Verified (Syntax Check Passed)

---

## [2025-12-12 16:17] — Critical Regression Fix

**Режим:** SINGLE FIX (Focus Bug)
**Issues исправлено:** 1

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | P0: Input Focus Loss (Regression) | App.tsx | ✅ Fixed |

### Изменения

- **App.tsx:** Вынесены компоненты `TextAreaContainer`, `IconButton`, `ActionBtn` из тела `App` на уровень модуля. Это предотвращает их пересоздание при каждом рендере и потерю фокуса в поле ввода.

---

---

## [2025-12-12 16:10] — UI Accessibility & Performance Fixes

**Режим:** FULL SWEEP (UI Fixes)
**Issues исправлено:** 5

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | P0: NavItem Accessibility (Blindness) | App.tsx | ✅ Fixed |
| 2 | P0: Action Buttons Accessibility | App.tsx | ✅ Fixed |
| 3 | P2: Keyboard Navigation Styles | App.tsx | ✅ Fixed |
| 4 | P3: NavItem Performance (Re-renders) | App.tsx | ✅ Fixed |
| 5 | P3: Mobile Safe Area Support | App.tsx | ✅ Fixed |

### Изменения

**App.tsx:**

- **NavItem Refactor:** Компонент вынесен из `App` (L26), добавлены `aria-label`, `title` и `collapsed` пропсы. Добавлены стили `focus:ring-2` для клавиатурной навигации.
- **ActionBtn / IconButton:** Добавлен проп `label` для `aria-label` и `title`. Обновлены все использования (Copy, Regenerate, Theme) с понятными текстовыми метками.
- **Safe Area:** Создан wrapper component `TextAreaContainer` с `padding-bottom: env(safe-area-inset-bottom)` для корректного отображения на iOS.

**Build:** N/A (React Syntax Checked)

---

---

## [2025-12-12 15:51] — Final Audit Fixes (P0 + P3)

**Режим:** FULL SWEEP
**Issues исправлено:** 2

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | P0: AutoGPT confirmation bypass | autogpt.py | ✅ Already Fixed |
| 2 | P3: eslint-disable / unused hasImage | App.tsx | ✅ Fixed |

### Анализ P0

При аудите обнаружено, что **P0 уже исправлен в `autogpt.py:381-391`**:

- Если `_on_confirmation_needed` callback не установлен, опасные действия (`delete_file`, `run_command`) **блокируются** со статусом `SKIPPED`
- Сообщение: "Action blocked: Security policy requires confirmation callback (P0 Fix)"
- Это означает что ИИ агент НЕ может выполнять опасные команды без явного UI подтверждения

### Изменения P3

**App.tsx:**

- L59-62: Удалён `eslint-disable-next-line` и неиспользуемый `hasImage` state
- L260: Заменён `hasImage` на `false` (image upload not implemented)
- L631-635: Удалён Vision badge (появится когда будет image upload)

**Build:** N/A (TypeScript check passed)

---

## [2025-12-12 15:46] — Full Audit Fix Batch

**Режим:** FULL SWEEP
**Issues исправлено:** 8

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | P1: Fire-and-forget без exception handler | api.py | ✅ Fixed |
| 2 | P1: Temp file leak при загрузке документов | api.py | ✅ Fixed |
| 3 | P1: API не возвращает message_count | api.py | ✅ Fixed |
| 4 | P1: Singleton race condition | api.py | ✅ Fixed (lock added) |
| 5 | P2: CORS allow_methods=["*"] | api.py | ✅ Fixed |
| 6 | P2: Dead buttons (Plus/Globe) | App.tsx | ✅ Removed |
| 7 | P2: Dropdown не закрывается | App.tsx | ✅ Fixed (outside click) |
| 8 | P3: Unused Globe import | App.tsx | ✅ Removed |

### Изменения

**api.py:**

- L49: CORS `allow_methods` → `["GET", "POST", "DELETE", "OPTIONS"]`
- L57: Добавлен `_agent_lock = asyncio.Lock()` для race condition
- L60-67: Добавлен `_log_task_exception()` callback для fire-and-forget
- L176: `asyncio.create_task(...).add_done_callback(_log_task_exception)`
- L277-290: `list_conversations` теперь возвращает `message_count`
- L329-343: Добавлен `finally:` блок с `os.remove(temp_path)` для cleanup

**App.tsx:**

- L5: Удалён неиспользуемый импорт `Globe`
- L75: Добавлен `modelDropdownRef = useRef<HTMLDivElement>(null)`
- L113-124: useEffect для закрытия dropdown при клике снаружи
- L574: Добавлен `ref={modelDropdownRef}` к wrapper
- L741-744: Заменены dead buttons на hint текст

**Build:** ⚠️ Skipped (PowerShell execution policy)
**Code Check:** ✅ No syntax errors

### Не исправлено (backlog)

- P0: AutoGPT confirmation bypass (требует full UI flow implementation)
- P3: eslint-disable comment (minor, не влияет на функционал)

---

## [2025-12-12 13:18] — LM Studio API Issues

**Режим:** FULL SWEEP
**Issues исправлено:** 2 (+ 2 исправленных ранее)

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | STATE BUG: _current_model не обновлялся | lm_client.py | ✅ Fixed |
| 2 | LAZY IMPL: нет fallback в get_available_models | ui/app.py | ✅ Fixed |
| 3 | LOGIC LIE: onDone → onComplete | client.ts | ✅ Fixed (earlier) |
| 4 | LOGIC LIE: current_model/get_available_models отсутствовали | lm_client.py | ✅ Fixed (earlier) |

### Изменения

- **lm_client.py:267**: Добавлен `self._current_model = model` перед стримингом
- **ui/app.py:246**: Добавлен try/except с fallback на ["auto"] при ошибке list_models()
- **client.ts:137**: Заменён `onDone(data)` на `onComplete(data)` (ранее)
- **lm_client.py:67-80**: Добавлены `@property current_model` и `get_available_models()` (ранее)

**Syntax Check:** ✅ Passed

---

## [2025-12-12 04:00] — IQ/Empathy Logic Issues

**Режим:** FULL SWEEP
**Issues исправлено:** 4

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | first_try = correction_rate (P2) | metrics.py | ✅ Fixed |
| 2 | Анализ не того момента (P2) | app.py | ✅ Fixed |
| 3 | Placeholders mood/anticipation (P3) | metrics.py | ✅ Fixed |
| 4 | cache_ttl не используется (P3) | metrics.py | ✅ Fixed |

### Изменения

- **metrics.py:540**: `first_try = (total - negative) / total` вместо дублирования correction
- **app.py**: Добавлен `_pending_feedback_msg_id` для анализа СЛЕДУЮЩЕГО сообщения как реакции
- **metrics.py:886-920**: `mood_success` и `anticipation` теперь считаются из `interaction_outcomes`
- **metrics.py:520-533**: Добавлены `_is_cache_valid()` и `_set_cache()` для TTL

**Syntax Check:** ✅ Passed
**Imports:** ✅ OK

---

## [2025-12-12 03:05]

**Режим:** FULL SWEEP
**Issues исправлено:** 4

### Исправленные issues

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | P2: Race condition audio vs typing | app.py | ✅ Fixed |
| 2 | P2: Silent fail in is_available() | speech.py | ✅ Fixed |
| 3 | P3: Double templates.initialize() | app.py | ✅ Fixed |
| 4 | P3: Duplicate use_humor save | app.py | ✅ Fixed |

### Изменения

- **app.py:55-56**: Удалён дубликат `templates.initialize()`
- **app.py:389-400**: Заменён `audio_input.change()` на append-логику, чтобы голосовой ввод не перезаписывал текст
- **app.py:496-497**: Удалён дубликат `update_preference("use_humor", ...)`
- **speech.py:161-180**: Заменён `except:` на конкретные исключения с логированием

**Syntax Check:** ✅ Passed

---

## [2025-12-12 02:35]

**Режим:** SINGLE FIX (Path Traversal)
**Issues исправлено:** 1

### Исправленные issues

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | Path Traversal (P0 #2) | tools.py | ✅ Fixed |

### Изменения

- tools.py: Внедрена принудительная проверка `_validate_path` во все файловые операции (`list_directory`, `move_file`, `copy_file`, `delete_file`, `create_directory`, `create_archive`).

**Build:** N/A (Python)
**Tests:** ✅ Passed (tests/verify_security.py)
