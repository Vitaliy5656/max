# Fix Log

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
