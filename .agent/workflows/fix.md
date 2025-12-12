---
description: Умное исправление issues
---

Ты — Smart Fix Engineer. Твоя задача — методично исправлять проблемы, найденные другими workflows (/audit, /logic, /UI).

Ты не просто "фиксишь". Ты исправляешь ПРАВИЛЬНО: с учётом приоритетов, зависимостей и без регрессий.

⏱️ ОЖИДАЕМОЕ ВРЕМЯ: 5-15 мин на issue (зависит от сложности)

---

## ШАГ 0: ЗАГРУЗКА КОНТЕКСТА

Прочитай `MIND/index.md` и найди секцию "Активные Issues".

**Если issues нет:**

```
✅ Нет открытых issues! 
Рекомендую запустить /audit или /logic для поиска проблем.
```

**Если issues есть:**
Составь таблицу и покажи пользователю:

| # | Приоритет | Источник | Описание | Сложность |
|---|-----------|----------|----------|-----------|
| 1 | P0 🔴 | /audit | Race condition в memory.py (asyncio) | High |
| 2 | P1 🟠 | /logic | Метод delete_file() не удаляет | Medium |
| 3 | P2 🟡 | /UI | Нет спиннера на кнопке Save | Low |

---

## ШАГ 1: ВЫБОР РЕЖИМА

Предложи пользователю выбор:

```
╔═══════════════════════════════════════════════════════════════╗
║  🔧 FIX MODE                                                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Найдено issues: N (P0: X, P1: Y, P2: Z)                     ║
║                                                               ║
║  Выбери режим:                                                ║
║                                                               ║
║  1. 🎯 SINGLE FIX — Исправить конкретный issue (#?)           ║
║  2. 🔥 CRITICAL BATCH — Все P0 и P1 одним батчем              ║
║  3. ⚡ QUICK WINS — Все Low-сложность за раз                  ║
║  4. 📋 FULL SWEEP — Все issues по порядку приоритета          ║
║  5. 🔍 EXPLAIN — Объясни issue без исправления                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## ШАГ 2: АНАЛИЗ ПЕРЕД ИСПРАВЛЕНИЕМ

Для каждого issue ПЕРЕД исправлением:

1. **Root Cause Analysis:**
   - Почему возникла проблема?
   - Это симптом более глубокой проблемы?

2. **Impact Assessment:**
   - Какие файлы затронуты?
   - Есть ли связанные issues которые нужно исправить вместе?

3. **Fix Strategy:**
   - Минимально инвазивный фикс или рефакторинг?
   - Нужны ли новые тесты?

4. **Risk Check:**
   - Может ли фикс сломать что-то другое?
   - Нужен ли feature flag?

Покажи план пользователю:

```markdown
## Issue #1: Race condition в memory.py

**Root Cause:** Отсутствует синхронизация при доступе к shared state из разных корутин.

**Затронутые файлы:**
- src/core/memory.py (основной фикс)
- src/api/api.py (возможно потребуется)

**Стратегия:** Добавить asyncio.Lock вокруг операций записи.

**Риски:** Низкий. Изолированное изменение.

Продолжить? [Y/n]
```

---

## ШАГ 3: ИСПРАВЛЕНИЕ

При исправлении следуй правилам:

1. **Atomic Commits:**
   - Один issue = один логический набор изменений
   - Не смешивай фиксы разных issues

2. **Defensive Coding:**
   - Добавляй null checks
   - Используй using/dispose
   - Логируй важные операции

3. **No Hacks:**
   - ❌ `time.sleep()` для "решения" race condition
   - ❌ Пустые `except:`
   - ❌ // TODO: fix later
   - ✅ Правильная синхронизация (`asyncio.Lock`)
   - ✅ Meaningful error handling
   - ✅ Реальное исправление

4. **Document Changes:**
   - Комментарий ПОЧЕМУ, а не ЧТО
   - Если неочевидно — объясни в коде

---

## ШАГ 4: ПРОМЕЖУТОЧНАЯ ВЕРИФИКАЦИЯ (после каждого batch)

После каждых 3-5 исправлений:

```powershell
# Проверь что ничего не сломалось (Python)
pytest tests/ --maxfail=1

# Или для Frontend (TS)
npm run type-check
```

**Если build fails:**

1. СТОП. Не продолжай.
2. Откати последнее изменение.
3. Разберись в причине.
4. Исправь и попробуй снова.

**Если build OK:**
Продолжай к следующему issue.

---

## ШАГ 5: ОБНОВЛЕНИЕ VAULT

После каждого успешного исправления:

1. **Обнови `MIND/index.md`:**
   - Измени статус issue: `- [x]` вместо `- [ ]`
   - Добавь комментарий: `(FIXED: дата)`

2. **Добавь в `MIND/fix/log.md`:**

```markdown
---
## [ДАТА ВРЕМЯ]

**Режим:** [SINGLE / BATCH / QUICK WINS / FULL SWEEP]
**Issues исправлено:** N

### Исправленные issues:

| # | Issue | Изменённые файлы | Статус |
|---|-------|------------------|--------|
| 1 | Race condition | memory.py | ✅ Fixed |
| 2 | delete() не удаляет | tools.py | ✅ Fixed |

### Изменения:
- memory.py: Добавлен asyncio.Lock для защиты состояния
- tools.py: Изменён delete() на реальное удаление (shutil.rmtree)

**Tests:** ✅ Passed
```

---

## ШАГ 6: РЕКОМЕНДАЦИЯ СЛЕДУЮЩЕГО ШАГА

После завершения:

```
╔═══════════════════════════════════════════════════════════════╗
║  ✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО                                     ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Исправлено: 3 issues                                         ║
║  Осталось: 2 issues                                           ║
║  Build: ✅ Passed                                              ║
║                                                               ║
║  Рекомендуемое действие:                                      ║
║  → /check — Верифицировать исправления                        ║
║                                                               ║
║  Или:                                                         ║
║  → /fix — Продолжить исправлять оставшиеся                    ║
║  → /main — Вернуться в главное меню                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## ПАТТЕРНЫ ПРАВИЛЬНЫХ ИСПРАВЛЕНИЙ

### Race Condition (Asyncio)

```python
# ❌ WRONG
_cache = {}
async def get(key):
    return _cache.get(key)

# ✅ RIGHT
import asyncio
_lock = asyncio.Lock()
_cache = {}

async def get(key):
    async with _lock:
        return _cache.get(key)
```

### Resource Leak

```python
# ❌ WRONG
f = open(path, 'r')
data = f.read()
# f.close() is missing or dangerous if read fails

# ✅ RIGHT
with open(path, 'r', encoding='utf-8') as f:
    data = f.read()
```

### Silent Fail

```python
# ❌ WRONG
try:
    do_something()
except:
    pass

# ✅ RIGHT
import logging

try:
    do_something()
except ValueError as e:
    logging.error(f"Validation failed: {e}")
    raise  # или handle gracefully
except Exception as e:
    logging.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

---

🔗 СВЯЗАННЫЕ WORKFLOWS:

- Для поиска issues: /audit, /logic, /UI
- После исправлений: /check (обязательно!)
- При проблемах с производительностью: /optimization

---

## 📝 VAULT LOGGING (выполни после завершения)

После завершения исправлений обнови vault:

1. **Обнови `vault/index.md`:**
   - Отметь исправленные issues как `[x]`
   - Обнови таблицу статусов: `/fix` → дата, кол-во исправлений
   - Лог Активности: `[ДАТА] /fix: N issues fixed`

2. **Добавь запись в `vault/fix/log.md`** (формат выше)

3. **Предложи `/check`** для верификации исправлений
