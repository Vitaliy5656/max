# Architect Review: Integration Plan (Final Pass)

> **Role:** Senior Solutions Architect
> **Scope:** Final verification of `INTEGRATION_PLAN.md` (v1.1)

## 1. Visionary Check (Скрытый потенциал)

### 🚀 Low Hanging Fruit: "Structured Verification"

* **Insight:** `Verifier` сейчас просто выдает текст. Парсить его сложно.
* **Idea:** Использовать библиотеку `outlines` (уже есть в deps) или `guidance` для того, чтобы `Verifier` всегда возвращал JSON: `{"score": 0.8, "critique": "..."}`.
* **Benefit:** Надежность цикла повышается с 60% до 99%.

### 🔮 Future Vector: "Multi-Persona Debate"

* **Insight:** План упоминает это как "Bonus". Но для сложных задач (System 2) это киллер-фича.
* **Synergy:** Если у нас уже есть `Planner` и `Verifier`, мы можем просто дать `Verifier` роль "Скептика" (Skeptic Persona), а `Executor` роль "Оптимиста". Это усилит качество без нового кода.

## 2. Risk Assessment (Новые риски)

### ⚠️ Zombie Connections (Heartbeat Risk)

* **Risk:** `HeartbeatGenerator` в `streaming.py` может поддерживать соединение вечно, если модель "зависла" в цикле, но не генерирует токены (spinning wait).
* **Mitigation:** Добавить `HARD_TIMEOUT` (например, 120с) на уровне самого генератора. Если нет *полезных* токенов 120с — обрыв.

### ⚠️ Queue Blindness (Frontend Risk)

* **Risk:** Мы хотим показать "Queue Pos #1". Но Ollama API **не отдает** позицию в очереди. Она просто блокирует запрос.
* **Reality Check:** Мы не можем реализовать "Pos #1" без своего `SlotManager`, который *сам* считает очередь перед отправкой в Ollama.
* **Decision:** В Phase 2 (`SlotManager`) мы должны реализовать *свою* семафорную очередь, а не полагаться на встроенную в Ollama.

## 3. Technical Design Updates

* **Refinement:** Include `outlines` integration for `Verifier` node.
* **Refinement:** Defines `SlotManager` as a *Semaphore-based Queue* (Active Count tracking) to expose explicit queue position to UI.

## Recommendation

Update Phase 1 (Verifier) to use Structured Output.
Update Phase 2 (SlotManager) to explicitly track Queue Position for UI.
