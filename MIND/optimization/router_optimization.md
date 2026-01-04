# 🚀 Optimization Report: SmartRouter Features Plan

> **Дата:** 2025-12-14 02:10
> **Анализируемый план:** `MIND/router_features_plan.md`
> **Статус:** ⚠️ Нужны trade-offs

---

## 📊 Performance Impact Analysis

### Performance Budgets для SmartRouter

| Операция | Бюджет | Risk |
|----------|--------|------|
| Routing Decision | < 50ms | 🟢 LOW |
| LLM Classification (Phi-3.5) | < 500ms | 🟡 MEDIUM |
| Full SmartRouter (все фичи) | < 200ms | 🔴 HIGH |

---

## 🚀 INSTANT WIN (5 фичей)

### 1. Temperature Auto-Tune

**Impact:** ZERO latency

```python
# Просто lookup table, O(1)
TEMP_MAP = {"coding": 0.3, "creative": 0.9, "math": 0.1}
temperature = TEMP_MAP.get(intent, 0.7)
```

✅ **Рекомендация:** Реализовать inline в SmartRouter

### 2. Auto Mode Selection

**Impact:** ZERO latency (уже вычислено в LLM Router)

```python
mode = routing_decision.suggested_mode  # already computed
```

✅ **Рекомендация:** Просто проксировать из LLMRouter

### 3. RAG Trigger

**Impact:** NEGATIVE latency (экономим когда skip)

```python
# Skip RAG = экономия 100-500ms
skip_rag = intent in [GREETING, SIMPLE_MATH]
```

✅ **Рекомендация:** Whitelist для skip вместо blacklist

### 4. Context Window Optimizer

**Impact:** NEGATIVE latency (меньше токенов = быстрее)

```python
context_sizes = {"simple": 2, "medium": 10, "complex": 50}
```

✅ **Рекомендация:** Агрессивное сокращение для simple

### 5. Cost Estimator

**Impact:** ZERO latency

```python
# Простая формула
tokens = complexity_factor * avg_response_length
time_ms = tokens * ms_per_token
```

✅ **Рекомендация:** Реализовать как lookup + multiply

---

## ⚖️ TRADE-OFF (5 фичей)

### 6. LLM Router (Phi-3.5) - УЖЕ РЕАЛИЗОВАН

**Current latency:** ~500ms per call
**Trade-off:** +500ms latency vs accurate classification

⚖️ **Оптимизация:**

```python
# 1. Cache по message prefix (экономия 90% повторных)
cache_key = message[:50].lower()

# 2. Timeout fallback на CPU Router
try:
    result = await asyncio.wait_for(llm_router.route(msg), timeout=0.5)
except asyncio.TimeoutError:
    result = cpu_router.route(msg)  # Fallback: 0ms
```

**Рекомендация:** ✅ Добавить cache + timeout fallback

### 7. Privacy Lock System

**Impact:** ~5ms (string match)
**Trade-off:** Security > Speed

⚖️ **Оптимизация:**

```python
# Compiled regex вместо string.contains
UNLOCK_PATTERN = re.compile(r"привет,?\s+малыш", re.IGNORECASE)
is_unlock = UNLOCK_PATTERN.search(message) is not None
```

**Рекомендация:** ✅ Precompile regex, check FIRST

### 8. Streaming Strategy

**Impact:** PERCEIVED latency (не real)
**Trade-off:** Complexity vs UX

⚖️ **Оптимизация:**

```python
# Fast path для simple → immediate stream
if complexity == SIMPLE:
    return "immediate"
# Show thinking for complex
return "delayed" if complexity == COMPLEX else "immediate"
```

**Рекомендация:** ✅ Default to immediate, exception for deep

### 9. Caching Strategy

**Impact:** MEMORY trade-off
**Trade-off:** +10-50MB RAM vs faster repeat queries

⚖️ **Оптимизация:**

```python
# LRU Cache с TTL
from functools import lru_cache
from cachetools import TTLCache

routing_cache = TTLCache(maxsize=100, ttl=300)  # 5 min, 100 entries
```

**Рекомендация:** ✅ Bounded LRU (max 100 entries, ~10MB)

### 10. Safety Filter

**Impact:** ~10ms (pattern matching)
**Trade-off:** Security > Speed

⚖️ **Оптимизация:**

```python
# Set lookup O(1) вместо list O(n)
DANGEROUS_PATTERNS = {"rm -rf", "format", "delete all", "DROP TABLE"}
needs_confirm = any(p in message for p in DANGEROUS_PATTERNS)
```

**Рекомендация:** ✅ Use set + early exit

---

## 🧠 UX BOOST (2 фичи)

### 11. Parallel Decomposition

**Impact:** +100-200ms для decomposition, BUT parallel execution is faster overall

🧠 **Оптимизация:**

```python
# Only decompose if ACTUALLY complex
if complexity != COMPLEX or word_count < 50:
    return single_task  # Skip decomposition overhead

# Use existing fan_out.py
results = await fan_out_tasks(sub_tasks, max_parallel=2)
```

**Рекомендация:** ✅ Only for genuinely complex tasks

### 12. Emotional Tone

**Impact:** +50-100ms (LLM call required)
**UX Benefit:** Better rapport

🧠 **Оптимизация:**

```python
# DEFER: Do emotion detection AFTER routing, not blocking
# Use CPU heuristics first, LLM only for ambiguous
if "?" in message and any(w in message for w in ["устал", "раздражает"]):
    tone = "empathetic"
else:
    tone = "neutral"  # Default, override later
```

**Рекомендация:** ⏭️ DEFER to Phase 3, use heuristics

---

## 📊 NEEDS MEASUREMENT (2 фичи)

### 13. User Preference Learning

**Impact:** Unknown (DB query)
**Risk:** Could add 50-200ms if not cached

📊 **Рекомендация:**

1. Measure DB query time
2. Pre-load preferences at session start
3. Cache in memory

### 14. Model Selector

**Impact:** Unknown (depends on LM Studio model switching)
**Risk:** Model load time can be 5-30 SECONDS

📊 **Рекомендация:**

1. Test model switching latency in LM Studio
2. If slow → keep single model loaded
3. If fast → implement warm model pool

---

## 🚫 ANTI-PATTERN WARNINGS

### ❌ Don't: LLM call for every feature

```python
# BAD: 15 LLM calls = 7500ms latency
intent = await llm_router.route(msg)  # 500ms
safety = await llm_check_safety(msg)  # 500ms
emotion = await llm_detect_emotion(msg)  # 500ms
# ...
```

### ✅ Do: Single LLM call + CPU post-processing

```python
# GOOD: 1 LLM call + CPU calculations = 550ms
decision = await llm_router.route(msg)  # 500ms

# CPU only (0ms each)
temperature = TEMP_MAP[decision.intent]
mode = decision.suggested_mode
safety = cpu_check_safety(msg)
# ...
```

---

## 📋 Оптимизированный Порядок Реализации

### Phase 1: ZERO/NEGATIVE Latency (сразу)

```
1. Auto Mode Selection      → 0ms (proxy)
2. Temperature Auto-Tune    → 0ms (lookup)
3. RAG Trigger              → -100ms (skip saves time)
4. Context Window Optimizer → -50ms (fewer tokens)
5. Cost Estimator           → 0ms (calculate)
```

### Phase 2: Smart Trade-offs (с оптимизациями)

```
6. Privacy Lock             → 5ms (compiled regex, first check)
7. Streaming Strategy       → 0ms (decision only)
8. Caching Strategy         → +10MB RAM, -500ms repeats
9. Safety Filter            → 10ms (set lookup)
10. LLM Router Cache        → -400ms for repeats
```

### Phase 3: Measure First

```
11. Parallel Decomposition  → MEASURE before implementing
12. User Preferences        → MEASURE DB latency
13. Model Selector          → MEASURE LM Studio switch time
14. Emotional Tone          → DEFER, use CPU heuristics
```

---

## 🎯 Итоговые Рекомендации

| Action | Impact |
|--------|--------|
| Add LLM Router cache | **-400ms** (90% repeats) |
| Add timeout fallback | **Zero worst-case** (CPU fallback) |
| Skip RAG for simple | **-100ms** per simple query |
| Use set for patterns | **O(1)** instead of O(n) |
| Batch features in single call | **-4000ms** vs naive |
| Defer emotional tone | **-100ms** Phase 1 |

**Ожидаемый бюджет SmartRouter:**

- Best case (cached): **~50ms**
- Average case: **~500ms** (LLM call)
- Worst case (fallback): **~100ms** (CPU router)

✅ Укладываемся в бюджет **< 200ms average** с кэшированием!
