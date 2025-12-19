# Thinking UI/UX Deep Audit Report

**Дата:** 2025-12-15
**Автор:** Senior Frontend Architect & UX Researcher
**Версия:** 1.0

---

## 1. Executive Summary

Данный отчёт представляет глубокий анализ UI/UX системы отображения состояния "Thinking" (когда модель рассуждает) в приложении MAX AI. Проанализированы все компоненты, hooks, API-клиент и backend streaming логика.

### Ключевые файлы системы:
- `frontend/src/components/ThinkingPanel.tsx` — UI компоненты индикаторов
- `frontend/src/hooks/useChat.ts` — state management для thinking
- `frontend/src/api/client.ts` — SSE streaming и event handling
- `frontend/src/components/tabs/ChatTab.tsx` — интеграция в чат
- `src/core/lm/streaming.py` — backend streaming с фильтрацией think-тегов

---

## 2. Текущая архитектура Thinking Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND FLOW                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LLM Response → streaming.py → Think Tag Detection → SSE Events     │
│       │                              │                    │          │
│       ↓                              ↓                    ↓          │
│  <think>...   ←──────────────→  _meta: thinking_start    │          │
│  </think>     ←──────────────→  _meta: thinking_end      │          │
│                                     + duration_ms         │          │
│                                     + think_content       │          │
│                                                           │          │
└───────────────────────────────────┬──────────────────────┘          │
                                    │                                  │
                                    ↓                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND FLOW                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SSE Event → api/client.ts → useChat.ts → ThinkingPanel.tsx         │
│       │           │              │               │                   │
│       ↓           ↓              ↓               ↓                   │
│  onThinking() → setIsThinking() → ThinkingIndicator                  │
│              → setThinkingSteps() → ThinkingStepsDisplay            │
│              → setThinkContent() → CollapsibleThink                  │
│              → setLastConfidence() → ConfidenceBadge                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. State Management Analysis

### 3.1 useChat.ts States

```typescript
// Thinking state
const [isThinking, setIsThinking] = useState(false);          // Активен ли режим thinking
const [thinkingStartTime, setThinkingStartTime] = useState(0); // Timestamp начала
const [thinkContent, setThinkContent] = useState('');          // Накопленный think контент
const [thinkExpanded, setThinkExpanded] = useState(false);     // UI expand state
const [thinkingSteps, setThinkingSteps] = useState<Array<{name: string; content: string}>>([]);

// Confidence state
const [lastConfidence, setLastConfidence] = useState<ConfidenceInfo | null>(null);

// Model loading state
const [loadingModel, setLoadingModel] = useState<string | null>(null);

// Queue state
const [queueStatus, setQueueStatus] = useState<'inactive' | 'waiting' | 'acquired'>('inactive');
```

### 3.2 Event Handlers в streamChat

```typescript
// ThinkingEvent handler
(thinkingEvent) => {
    setQueueStatus('acquired'); // Thinking означает получение слота
    if (thinkingEvent.status === 'start') {
        setIsThinking(true);
        setThinkingStartTime(Date.now());
        setThinkContent('');
        setThinkExpanded(false);
        setThinkingSteps([]);
    } else if (thinkingEvent.status === 'step') {
        // Live step update
        setThinkingSteps(prev => [...prev, { name, content }]);
    } else if (thinkingEvent.status === 'end') {
        setIsThinking(false);
        setThinkContent(thinkingEvent.think_content);
    }
}
```

---

## 4. UI Components Analysis

### 4.1 ThinkingIndicator
**Файл:** `ThinkingPanel.tsx:13-67`

**Функциональность:**
- Анимированный индикатор с иконкой мозга
- Live timer (обновляется каждые 100ms)
- Три анимированные точки (bounce)
- Spinning border + pulsing glow

**Проблемы:**
1. ❌ **Performance:** `setInterval` каждые 100ms создаёт много рендеров
2. ❌ **Accessibility:** Нет aria-live для screen readers
3. ⚠️ **UX:** Текст "Глубокий анализ" статичен, не отражает реальный этап

### 4.2 ThinkingStepsDisplay
**Файл:** `ThinkingPanel.tsx:90-165`

**Функциональность:**
- Показывает шаги рассуждения (PLANNING, DRAFTING, etc.)
- Collapsible при >3 шагов (UX-020)
- Анимация появления для каждого шага
- Live indicator (пульсирующая точка) для последнего шага

**Проблемы:**
1. ❌ **UX Gap:** Backend НЕ отправляет step events! Только `start` и `end`
2. ❌ **Dead Code:** `thinkingSteps` всегда пустой массив
3. ⚠️ **Lost Potential:** Красивый UI, который никогда не показывается

### 4.3 CollapsibleThink
**Файл:** `ThinkingPanel.tsx:200-251`

**Функциональность:**
- Collapsible панель с think content
- Copy to clipboard (UX-021)
- Показывается ПОСЛЕ генерации (не во время)

**Проблемы:**
1. ⚠️ **Timing:** Показывается только после `!isGenerating`, упущен момент
2. ❌ **Truncation:** Backend обрезает до 2000 chars без индикации в UI

### 4.4 ConfidenceBadge
**Файл:** `ThinkingPanel.tsx:261-301`

**Функциональность:**
- Gradient badge с уровнем уверенности
- Mini progress bar
- 5-уровневая цветовая шкала

**Проблемы:**
1. ❌ **Never Shows:** Backend не отправляет confidence events
2. ⚠️ **API Gap:** `lastConfidence` всегда null

---

## 5. Critical Issues (P0-P1)

### P0: ThinkingSteps никогда не отображаются

**Проблема:** Backend (`streaming.py`) отправляет только:
- `_meta: thinking_start`
- `_meta: thinking_end` (с duration_ms, think_content)

НО НЕ отправляет `step` events с name/content.

**Влияние:** Красивый UI компонент `ThinkingStepsDisplay` никогда не используется.

**Решение:**
```python
# В streaming.py - добавить парсинг структуры рассуждения
# Например, при обнаружении паттернов:
# "Planning: ..." → emit step event
# "Analyzing: ..." → emit step event
```

### P0: Confidence Score не работает

**Проблема:** API client ожидает `onConfidence` callback, но backend никогда не отправляет такие events.

**Решение:** Добавить confidence scoring в backend после генерации.

### P1: Performance Timer

**Проблема:** `setInterval` с 100ms в ThinkingIndicator создаёт ~600 рендеров в минуту.

**Решение:**
```typescript
// Использовать requestAnimationFrame или увеличить интервал до 500ms
// Или использовать CSS-only timer animation
```

---

## 6. UX Improvement Opportunities

### 6.1 Streaming Thinking Content (Real-time)

**Текущее:** Think content показывается только ПОСЛЕ завершения.

**Улучшение:** Показывать streaming think content во время генерации.

```typescript
// В useChat.ts - накапливать think_content в реальном времени
if (thinkingEvent.status === 'streaming') {
    setThinkContent(prev => prev + thinkingEvent.chunk);
}
```

**UX Impact:** Пользователь видит процесс мышления модели в реальном времени.

### 6.2 Thinking Phase Indicator

**Текущее:** Статичный текст "Глубокий анализ".

**Улучшение:** Динамические фазы на основе времени/контента:
- 0-2s: "Понимаю вопрос..."
- 2-5s: "Анализирую контекст..."
- 5-10s: "Глубокое рассуждение..."
- 10s+: "Сложная задача, думаю..."

### 6.3 Skeleton Loading для сообщения

**Текущее:** Пустой bubble для assistant message.

**Улучшение:** Skeleton анимация в bubble пока идёт thinking.

```tsx
{isThinking && !msg.content && (
    <div className="skeleton-text w-3/4 h-4 mb-2" />
    <div className="skeleton-text w-1/2 h-4" />
)}
```

### 6.4 Cancel Thinking

**Текущее:** Кнопка Stop работает, но нет визуального feedback.

**Улучшение:**
- Показать "Отмена..." состояние
- Fade-out анимация для ThinkingIndicator

### 6.5 Thinking History

**Текущее:** Think content доступен только для последнего сообщения.

**Улучшение:** Сохранять think_content в каждом Message объекте для истории.

---

## 7. Development Roadmap

### Phase 1: Quick Wins (1-2 дня)

1. **[P1]** Оптимизировать timer в ThinkingIndicator (500ms вместо 100ms)
2. **[P1]** Добавить aria-live для accessibility
3. **[P2]** Динамические фазы thinking на основе времени
4. **[P2]** Skeleton loading в message bubble

### Phase 2: Backend Integration (3-5 дней)

1. **[P0]** Добавить step parsing в streaming.py
2. **[P0]** Реализовать confidence scoring
3. **[P1]** Streaming think content в реальном времени
4. **[P1]** Сохранять think_content в Message

### Phase 3: Advanced UX (1 неделя)

1. **[P2]** Thinking visualization (graph/tree view)
2. **[P2]** Thinking search/filter
3. **[P3]** Thinking export (Markdown)
4. **[P3]** Comparative thinking (A/B responses)

---

## 8. Implementation Variants

### Variant A: Minimal Changes (Conservative)

```
Scope: Только frontend оптимизации
Effort: 1-2 дня
Impact: Улучшение производительности, accessibility

Changes:
- Timer optimization
- Dynamic phase text
- Aria-live attributes
- Skeleton loading
```

### Variant B: Full Integration (Recommended)

```
Scope: Frontend + Backend
Effort: 5-7 дней
Impact: Полностью рабочий Thinking UI

Changes:
- All Variant A changes
- Backend step parsing
- Confidence scoring
- Real-time think streaming
- Think history per message
```

### Variant C: Advanced Experience (Future)

```
Scope: Full rewrite + new features
Effort: 2-3 недели
Impact: Дифференцирующий UX

Changes:
- All Variant B changes
- Interactive thinking tree
- Thought branching visualization
- User annotations on thoughts
- Export/share thinking process
```

---

## 9. Technical Recommendations

### 9.1 Backend Changes (streaming.py)

```python
# Добавить парсинг шагов рассуждения
STEP_PATTERNS = [
    (r'Planning:', 'PLANNING'),
    (r'Analyzing:', 'ANALYZING'),
    (r'Considering:', 'THINKING'),
    (r'Verifying:', 'VERIFYING'),
]

# При обнаружении паттерна в think_content:
yield {
    "_meta": "thinking_step",
    "name": step_name,
    "content": step_content
}
```

### 9.2 Frontend Changes (useChat.ts)

```typescript
// Расширить Message type
interface Message {
    // ...existing
    thinkContent?: string;  // Сохранять для истории
    thinkingDuration?: number;
    confidenceScore?: number;
}
```

### 9.3 CSS Optimizations

```css
/* CSS-only timer (no JS intervals) */
@property --timer {
    syntax: '<number>';
    initial-value: 0;
    inherits: false;
}

.thinking-timer {
    animation: timer-count 60s linear infinite;
    counter-reset: timer var(--timer);
}

@keyframes timer-count {
    to { --timer: 60; }
}
```

---

## 10. Conclusion

Система Thinking UI в MAX AI имеет хорошую архитектурную основу, но страдает от:

1. **Disconnect между frontend и backend** — многие UI компоненты никогда не получают данные
2. **Неиспользуемый потенциал** — ThinkingStepsDisplay, ConfidenceBadge мёртвы
3. **Performance issues** — частые интервалы для timer

**Рекомендация:** Реализовать **Variant B** для полной интеграции, что даст значительное улучшение UX при умеренных усилиях.

---

## Appendix A: File References

| Component | File | Lines |
|-----------|------|-------|
| ThinkingIndicator | ThinkingPanel.tsx | 13-67 |
| ThinkingStepsDisplay | ThinkingPanel.tsx | 90-165 |
| CollapsibleThink | ThinkingPanel.tsx | 200-251 |
| ConfidenceBadge | ThinkingPanel.tsx | 261-301 |
| ThinkingPanel | ThinkingPanel.tsx | 319-379 |
| useChat thinking state | useChat.ts | 49-64 |
| streamChat handlers | useChat.ts | 162-195 |
| API ThinkingEvent | client.ts | 135-142 |
| Backend streaming | streaming.py | 27-209 |

## Appendix B: State Flow Diagram

```
User Input → sendMessage()
    │
    ↓
setIsGenerating(true)
setQueueStatus('inactive')
    │
    ↓ (SSE: queue_heartbeat)
setQueueStatus('waiting')
    │
    ↓ (SSE: thinking_start)
setIsThinking(true)
setThinkingStartTime(Date.now())
setQueueStatus('acquired')
    │
    ↓ (SSE: token)
setIsThinking(false) // ← Bug? Первый token сбрасывает thinking
appendToMessage(token)
    │
    ↓ (SSE: thinking_end)
setIsThinking(false)
setThinkContent(...)
    │
    ↓ (SSE: done)
setIsGenerating(false)
setQueueStatus('inactive')
```

## Appendix C: Known Bugs

### Bug #1: Premature Thinking Reset
**Location:** useChat.ts:140-142
```typescript
if (isThinking) {
    setIsThinking(false);
}
```
При первом token, isThinking сбрасывается, даже если think content ещё не закончился.

### Bug #2: ThinkContent Truncation без UI
**Location:** streaming.py:181
```python
"think_content": think_content[:2000]  # Limit for UI
```
Контент обрезается до 2000 символов, но UI не показывает индикатор обрезки.

---

## 11. Industry Benchmark: Современные стандарты 2024-2025

### 11.1 Claude Extended Thinking (Anthropic)

**Ключевые особенности:**
- **Toggle режим** — пользователь может включать/выключать extended thinking
- **Thinking Budget** — разработчики могут задавать "бюджет времени" на размышления
- **Visible Thought Process** — процесс мышления виден в сыром виде
- **Thinking Blocks** — структурированные сегменты chain-of-thought
- **Summarized Thinking** — краткая версия полного потока мыслей
- **Redacted Thinking** — шифрование потенциально вредного контента

**UX Flow:**
```
Content Block Start → Real-time Reasoning Render → Content Block End → Final Answer
```

**Источники:** [Claude's Extended Thinking](https://www.anthropic.com/news/visible-extended-thinking), [Building with Extended Thinking](https://docs.claude.com/en/docs/build-with-claude/extended-thinking)

### 11.2 ChatGPT o1 (OpenAI)

**Ключевые особенности:**
- **"Think" Button** — выделенная кнопка в prompt bar для активации reasoning модели
- **Thinking Section** — отображается перед ответом (step-by-step process)
- **Progress Bar** — для длительных запросов (o1 pro mode)
- **Notification System** — уведомления о ходе выполнения
- **Reasoning Effort** — `low | medium | high` контроль через API
- **Hidden reasoning_tokens** — отдельный счётчик для reasoning токенов

**UX Insight:** "Thinking section — это умный gimmick для пользователя, чтобы понять что что-то происходит пока он ждёт"

**Источники:** [Reasoning Models](https://platform.openai.com/docs/guides/reasoning), [Reasoning Best Practices](https://platform.openai.com/docs/guides/reasoning-best-practices)

### 11.3 UI/UX Тренды 2025

**Animation & Motion:**
- **Lottie animations** с условной логикой (реагируют на user input)
- **Rive animations** без кода для hover/pressed состояний
- **Motion Typography** — text transitions (fade, slide, transform)
- **Kinetic Typography** — для премиального ощущения

**AI Integration:**
- **Emotionally Intelligent Design** — адаптация к настроению пользователя
- **Predictive UX** — предугадывание поведения
- **Variable Fonts** — плавные переходы между устройствами

**Sustainability:**
- **Low-energy UI** — минимум ненужных анимаций
- **Performance-first** — быстрые, оптимизированные интерфейсы

**Источники:** [Future of UI/UX Design 2025](https://motiongility.com/future-of-ui-ux-design/), [UI Design Trends 2025](https://www.lummi.ai/blog/ui-design-trends-2025)

---

## 12. Variant D: Premium Experience (Максимальный)

Расширенный вариант, сочетающий лучшие практики Claude, ChatGPT o1 и современные UI/UX тренды 2025.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    VARIANT D: PREMIUM EXPERIENCE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Scope:     Complete redesign + Industry-leading features                │
│  Effort:    3-4 недели                                                   │
│  Impact:    Конкурентное преимущество, дифференцирующий UX               │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        НОВЫЕ КОМПОНЕНТЫ                         │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │                                                                  │    │
│  │  1. ThinkingModeToggle      — Claude-style toggle в header      │    │
│  │  2. ThinkingBudgetSlider    — Контроль "глубины" размышлений    │    │
│  │  3. LiveThinkingStream      — Real-time streaming think content │    │
│  │  4. ThinkingTimeline        — Visual timeline с phases          │    │
│  │  5. ThinkingTreeView        — Интерактивное дерево мыслей       │    │
│  │  6. ConfidenceMeter         — Animated gauge с breakdown        │    │
│  │  7. ReasoningTokenCounter   — Отдельный счётчик reasoning       │    │
│  │  8. ThinkingProgressBar     — Progress для длительных запросов  │    │
│  │  9. ThinkingSummary         — Краткое резюме размышлений        │    │
│  │  10. ThinkingExport         — Export в Markdown/JSON            │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      BACKEND ADDITIONS                           │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │                                                                  │    │
│  │  1. Streaming think chunks  — Incremental think content         │    │
│  │  2. Step detection          — Auto-parse PLANNING, ANALYZING    │    │
│  │  3. Confidence scoring      — Post-generation confidence        │    │
│  │  4. Reasoning token count   — Separate metric                   │    │
│  │  5. Thinking budget API     — max_thinking_tokens parameter     │    │
│  │  6. Thinking summarization  — LLM-based summary                 │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      ANIMATION SYSTEM                            │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │                                                                  │    │
│  │  • Framer Motion для orchestrated animations                    │    │
│  │  • Lottie для custom thinking indicator                         │    │
│  │  • CSS Houdini для performant timer                             │    │
│  │  • Spring physics для natural feel                              │    │
│  │  • Reduced motion support (a11y)                                │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.1 Feature Comparison Matrix

| Feature | Current | Variant C | Variant D |
|---------|---------|-----------|-----------|
| Basic thinking indicator | ✅ | ✅ | ✅ |
| Live timer | ✅ (buggy) | ✅ (fixed) | ✅ (CSS-only) |
| Thinking steps | ❌ (dead) | ✅ | ✅ + timeline |
| Real-time think stream | ❌ | ✅ | ✅ + formatting |
| Confidence badge | ❌ (dead) | ✅ | ✅ + breakdown |
| Think history per message | ❌ | ✅ | ✅ |
| Thinking tree view | ❌ | ✅ | ✅ + interactive |
| Thinking mode toggle | ❌ | ⚠️ partial | ✅ (header) |
| Thinking budget control | ❌ | ❌ | ✅ |
| Progress bar (long tasks) | ❌ | ❌ | ✅ |
| Reasoning token counter | ❌ | ❌ | ✅ |
| Thinking summary | ❌ | ❌ | ✅ |
| Export thinking | ❌ | ✅ | ✅ + formats |
| Lottie animations | ❌ | ❌ | ✅ |
| Framer Motion | ❌ | ⚠️ basic | ✅ |
| Accessibility (a11y) | ❌ | ✅ | ✅ + reduced motion |

---

## 13. Пошаговый план реализации Variant D

### PHASE 0: Подготовка и архитектура (2-3 дня)

#### Step 0.1: Установка зависимостей
```bash
# Frontend
npm install framer-motion lottie-react @radix-ui/react-slider @radix-ui/react-toggle
npm install -D @types/react-dom

# Опционально для advanced animations
npm install rive-react
```

#### Step 0.2: Создание структуры компонентов
```
frontend/src/components/thinking/
├── index.ts                    # Barrel export
├── ThinkingModeToggle.tsx      # Toggle в header
├── ThinkingBudgetSlider.tsx    # Slider для budget
├── LiveThinkingStream.tsx      # Real-time stream
├── ThinkingTimeline.tsx        # Visual timeline
├── ThinkingTreeView.tsx        # Tree visualization
├── ThinkingProgressBar.tsx     # Progress indicator
├── ThinkingSummary.tsx         # Summary card
├── ConfidenceMeter.tsx         # Animated gauge
├── ReasoningTokenCounter.tsx   # Token display
├── ThinkingExport.tsx          # Export modal
└── animations/
    ├── brain-thinking.json     # Lottie animation
    ├── progress-wave.json      # Progress animation
    └── confidence-gauge.json   # Gauge animation
```

#### Step 0.3: Типизация
```typescript
// frontend/src/types/thinking.ts

export interface ThinkingPhase {
    id: string;
    name: 'UNDERSTANDING' | 'PLANNING' | 'ANALYZING' | 'REASONING' | 'VERIFYING' | 'SYNTHESIZING';
    content: string;
    startTime: number;
    endTime?: number;
    tokens?: number;
}

export interface ThinkingState {
    isActive: boolean;
    mode: 'off' | 'standard' | 'extended';
    budget: number;  // max thinking tokens
    currentPhase: ThinkingPhase | null;
    phases: ThinkingPhase[];
    streamContent: string;
    summary: string | null;
    confidence: ConfidenceInfo | null;
    reasoningTokens: number;
    totalDuration: number;
}

export interface ConfidenceInfo {
    score: number;
    level: 'low' | 'medium' | 'high';
    factors: ConfidenceFactor[];
}

export interface ConfidenceFactor {
    name: string;
    score: number;
    description: string;
}

export interface ThinkingEvent {
    type: 'start' | 'phase' | 'chunk' | 'end' | 'confidence' | 'summary';
    data: any;
    timestamp: number;
}
```

---

### PHASE 1: Backend Foundation (3-4 дня)

#### Step 1.1: Расширение streaming.py для step detection

**Файл:** `src/core/lm/streaming.py`

```python
# Добавить после THINK_TAG_PATTERNS

THINKING_PHASES = [
    (r'(?:^|\n)\s*(?:Understanding|Понимаю)[:\s]', 'UNDERSTANDING'),
    (r'(?:^|\n)\s*(?:Planning|План|Планирую)[:\s]', 'PLANNING'),
    (r'(?:^|\n)\s*(?:Analyzing|Анализ|Анализирую)[:\s]', 'ANALYZING'),
    (r'(?:^|\n)\s*(?:Reasoning|Рассуждаю|Думаю)[:\s]', 'REASONING'),
    (r'(?:^|\n)\s*(?:Verifying|Проверяю|Проверка)[:\s]', 'VERIFYING'),
    (r'(?:^|\n)\s*(?:Synthesizing|Итог|Вывод)[:\s]', 'SYNTHESIZING'),
]

# В функции stream_response - добавить streaming think chunks
async def stream_response(...):
    # ... existing code ...

    # Внутри think block - emit chunks periodically
    if in_think_block and len(think_content) % 100 == 0:  # Every ~100 chars
        yield {
            "_meta": "thinking_chunk",
            "content": think_content[-100:],
            "total_chars": len(think_content)
        }

    # Detect phase changes
    for pattern, phase_name in THINKING_PHASES:
        if re.search(pattern, think_content[-200:], re.IGNORECASE):
            yield {
                "_meta": "thinking_phase",
                "name": phase_name,
                "content": extract_phase_content(think_content, pattern)
            }
```

#### Step 1.2: Добавление confidence scoring

**Файл:** `src/core/confidence.py` (новый)

```python
"""
Confidence Scoring System

Evaluates response confidence based on:
- Thinking depth and structure
- Source citations
- Hedging language detection
- Response coherence
"""

import re
from typing import Tuple, List, Dict

HEDGING_PHRASES = [
    r'\bвозможно\b', r'\bнаверное\b', r'\bможет быть\b',
    r'\bне уверен\b', r'\bпредположительно\b', r'\bвероятно\b',
    r'\bperhaps\b', r'\bmaybe\b', r'\bpossibly\b', r'\bmight\b',
]

CONFIDENCE_PHRASES = [
    r'\bточно\b', r'\bопределённо\b', r'\bбезусловно\b',
    r'\bdefinitely\b', r'\bcertainly\b', r'\bclearly\b',
]

def calculate_confidence(
    response: str,
    think_content: str | None = None,
    has_sources: bool = False
) -> Tuple[float, str, List[Dict]]:
    """
    Calculate confidence score for a response.

    Returns:
        (score, level, factors)
    """
    factors = []
    score = 0.5  # Base score

    # Factor 1: Thinking depth
    if think_content:
        think_score = min(len(think_content) / 2000, 1.0) * 0.2
        score += think_score
        factors.append({
            "name": "thinking_depth",
            "score": think_score,
            "description": f"Глубина размышлений: {len(think_content)} символов"
        })

    # Factor 2: Hedging language (negative)
    hedging_count = sum(
        len(re.findall(pattern, response, re.IGNORECASE))
        for pattern in HEDGING_PHRASES
    )
    if hedging_count > 0:
        hedge_penalty = min(hedging_count * 0.05, 0.2)
        score -= hedge_penalty
        factors.append({
            "name": "hedging_language",
            "score": -hedge_penalty,
            "description": f"Неуверенные формулировки: {hedging_count}"
        })

    # Factor 3: Confidence language (positive)
    confidence_count = sum(
        len(re.findall(pattern, response, re.IGNORECASE))
        for pattern in CONFIDENCE_PHRASES
    )
    if confidence_count > 0:
        conf_bonus = min(confidence_count * 0.03, 0.1)
        score += conf_bonus
        factors.append({
            "name": "confidence_language",
            "score": conf_bonus,
            "description": f"Уверенные формулировки: {confidence_count}"
        })

    # Factor 4: Sources
    if has_sources:
        score += 0.15
        factors.append({
            "name": "sources_cited",
            "score": 0.15,
            "description": "Указаны источники"
        })

    # Clamp score
    score = max(0.1, min(0.95, score))

    # Determine level
    if score >= 0.7:
        level = "high"
    elif score >= 0.4:
        level = "medium"
    else:
        level = "low"

    return score, level, factors
```

#### Step 1.3: API endpoint для thinking budget

**Файл:** `src/api/routers/chat.py` — добавить параметр

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: str = "auto"
    temperature: float = 0.7
    use_rag: bool = True
    thinking_mode: str = "standard"  # off | standard | extended
    thinking_budget: int = 4000       # NEW: max thinking tokens
    has_image: bool = False
```

---

### PHASE 2: Frontend Core Components (4-5 дней)

#### Step 2.1: useThinking hook

**Файл:** `frontend/src/hooks/useThinking.ts` (новый)

```typescript
/**
 * useThinking Hook — centralized thinking state management
 *
 * Manages all thinking-related state with proper typing and
 * performance optimizations.
 */
import { useState, useCallback, useRef, useMemo } from 'react';
import type { ThinkingState, ThinkingPhase, ThinkingEvent, ConfidenceInfo } from '../types/thinking';

const INITIAL_STATE: ThinkingState = {
    isActive: false,
    mode: 'standard',
    budget: 4000,
    currentPhase: null,
    phases: [],
    streamContent: '',
    summary: null,
    confidence: null,
    reasoningTokens: 0,
    totalDuration: 0,
};

export function useThinking() {
    const [state, setState] = useState<ThinkingState>(INITIAL_STATE);
    const startTimeRef = useRef<number>(0);
    const streamBufferRef = useRef<string>('');

    // Start thinking session
    const startThinking = useCallback(() => {
        startTimeRef.current = Date.now();
        streamBufferRef.current = '';
        setState(prev => ({
            ...INITIAL_STATE,
            mode: prev.mode,
            budget: prev.budget,
            isActive: true,
        }));
    }, []);

    // Handle thinking event from SSE
    const handleThinkingEvent = useCallback((event: ThinkingEvent) => {
        switch (event.type) {
            case 'phase':
                setState(prev => ({
                    ...prev,
                    currentPhase: {
                        id: `phase-${Date.now()}`,
                        name: event.data.name,
                        content: event.data.content,
                        startTime: Date.now(),
                    },
                    phases: prev.currentPhase
                        ? [...prev.phases, { ...prev.currentPhase, endTime: Date.now() }]
                        : prev.phases,
                }));
                break;

            case 'chunk':
                streamBufferRef.current += event.data.content;
                setState(prev => ({
                    ...prev,
                    streamContent: streamBufferRef.current,
                    reasoningTokens: event.data.total_chars,
                }));
                break;

            case 'end':
                setState(prev => ({
                    ...prev,
                    isActive: false,
                    totalDuration: Date.now() - startTimeRef.current,
                    currentPhase: prev.currentPhase
                        ? { ...prev.currentPhase, endTime: Date.now() }
                        : null,
                }));
                break;

            case 'confidence':
                setState(prev => ({
                    ...prev,
                    confidence: event.data,
                }));
                break;

            case 'summary':
                setState(prev => ({
                    ...prev,
                    summary: event.data.summary,
                }));
                break;
        }
    }, []);

    // Stop thinking (user cancel)
    const stopThinking = useCallback(() => {
        setState(prev => ({
            ...prev,
            isActive: false,
            totalDuration: Date.now() - startTimeRef.current,
        }));
    }, []);

    // Set thinking mode
    const setMode = useCallback((mode: ThinkingState['mode']) => {
        setState(prev => ({ ...prev, mode }));
    }, []);

    // Set thinking budget
    const setBudget = useCallback((budget: number) => {
        setState(prev => ({ ...prev, budget }));
    }, []);

    // Reset state
    const reset = useCallback(() => {
        setState(prev => ({
            ...INITIAL_STATE,
            mode: prev.mode,
            budget: prev.budget,
        }));
    }, []);

    // Computed values
    const progress = useMemo(() => {
        if (!state.isActive || state.budget === 0) return 0;
        return Math.min(state.reasoningTokens / state.budget, 1);
    }, [state.isActive, state.reasoningTokens, state.budget]);

    const elapsedTime = useMemo(() => {
        if (!state.isActive) return state.totalDuration;
        return Date.now() - startTimeRef.current;
    }, [state.isActive, state.totalDuration]);

    return {
        ...state,
        progress,
        elapsedTime,
        startThinking,
        stopThinking,
        handleThinkingEvent,
        setMode,
        setBudget,
        reset,
    };
}
```

#### Step 2.2: ThinkingModeToggle component

**Файл:** `frontend/src/components/thinking/ThinkingModeToggle.tsx`

```typescript
import { motion } from 'framer-motion';
import { Brain, Zap, Sparkles } from 'lucide-react';

interface ThinkingModeToggleProps {
    mode: 'off' | 'standard' | 'extended';
    onChange: (mode: 'off' | 'standard' | 'extended') => void;
    disabled?: boolean;
}

const MODES = [
    { id: 'off', icon: Zap, label: 'Быстро', color: 'zinc' },
    { id: 'standard', icon: Brain, label: 'Стандарт', color: 'indigo' },
    { id: 'extended', icon: Sparkles, label: 'Глубоко', color: 'purple' },
] as const;

export function ThinkingModeToggle({ mode, onChange, disabled }: ThinkingModeToggleProps) {
    return (
        <div className="flex items-center gap-1 bg-zinc-800/50 rounded-full p-1 border border-white/5">
            {MODES.map((m) => {
                const Icon = m.icon;
                const isActive = mode === m.id;

                return (
                    <motion.button
                        key={m.id}
                        onClick={() => onChange(m.id)}
                        disabled={disabled}
                        className={`
                            relative px-3 py-1.5 rounded-full text-xs font-medium
                            transition-colors flex items-center gap-1.5
                            ${isActive
                                ? `bg-${m.color}-500/20 text-${m.color}-400`
                                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'
                            }
                            disabled:opacity-50 disabled:cursor-not-allowed
                        `}
                        whileTap={{ scale: 0.95 }}
                        aria-pressed={isActive}
                        aria-label={`Режим: ${m.label}`}
                    >
                        <Icon size={14} />
                        <span className="hidden md:inline">{m.label}</span>

                        {isActive && (
                            <motion.div
                                layoutId="thinking-mode-indicator"
                                className={`absolute inset-0 bg-${m.color}-500/10 rounded-full -z-10`}
                                transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                            />
                        )}
                    </motion.button>
                );
            })}
        </div>
    );
}
```

#### Step 2.3: LiveThinkingStream component

**Файл:** `frontend/src/components/thinking/LiveThinkingStream.tsx`

```typescript
import { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

interface LiveThinkingStreamProps {
    content: string;
    isActive: boolean;
    maxHeight?: number;
}

export function LiveThinkingStream({
    content,
    isActive,
    maxHeight = 200
}: LiveThinkingStreamProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [expanded, setExpanded] = useState(false);
    const [copied, setCopied] = useState(false);
    const [autoScroll, setAutoScroll] = useState(true);

    // Auto-scroll to bottom when new content arrives
    useEffect(() => {
        if (autoScroll && containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [content, autoScroll]);

    // Detect manual scroll to disable auto-scroll
    const handleScroll = () => {
        if (!containerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
        setAutoScroll(isAtBottom);
    };

    const handleCopy = async () => {
        await navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (!content) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="relative bg-gradient-to-br from-purple-950/40 to-indigo-950/40
                       border border-purple-500/20 rounded-xl overflow-hidden"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-purple-500/10">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-purple-400 animate-pulse' : 'bg-zinc-600'}`} />
                    <span className="text-xs font-medium text-purple-300/80">
                        {isActive ? 'Мысли в реальном времени' : 'Процесс рассуждения'}
                    </span>
                </div>

                <div className="flex items-center gap-1">
                    <button
                        onClick={handleCopy}
                        className="p-1.5 rounded-md hover:bg-purple-500/20 text-purple-400/60 hover:text-purple-400 transition-colors"
                        title="Копировать"
                    >
                        {copied ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="p-1.5 rounded-md hover:bg-purple-500/20 text-purple-400/60 hover:text-purple-400 transition-colors"
                        title={expanded ? 'Свернуть' : 'Развернуть'}
                    >
                        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                </div>
            </div>

            {/* Content */}
            <div
                ref={containerRef}
                onScroll={handleScroll}
                className="overflow-y-auto transition-all duration-300"
                style={{ maxHeight: expanded ? '400px' : `${maxHeight}px` }}
            >
                <pre className="p-4 text-sm text-purple-200/70 whitespace-pre-wrap font-mono leading-relaxed">
                    {content}
                    {isActive && (
                        <motion.span
                            animate={{ opacity: [1, 0] }}
                            transition={{ duration: 0.5, repeat: Infinity }}
                            className="inline-block w-2 h-4 bg-purple-400 ml-0.5"
                        />
                    )}
                </pre>
            </div>

            {/* Gradient fade at bottom when scrollable */}
            {!expanded && content.length > 500 && (
                <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-purple-950/60 to-transparent pointer-events-none" />
            )}
        </motion.div>
    );
}
```

#### Step 2.4: ThinkingTimeline component

**Файл:** `frontend/src/components/thinking/ThinkingTimeline.tsx`

```typescript
import { motion } from 'framer-motion';
import type { ThinkingPhase } from '../../types/thinking';

const PHASE_ICONS: Record<string, string> = {
    UNDERSTANDING: '🔍',
    PLANNING: '📋',
    ANALYZING: '📊',
    REASONING: '🧠',
    VERIFYING: '✅',
    SYNTHESIZING: '✨',
};

const PHASE_LABELS: Record<string, string> = {
    UNDERSTANDING: 'Понимание',
    PLANNING: 'Планирование',
    ANALYZING: 'Анализ',
    REASONING: 'Рассуждение',
    VERIFYING: 'Проверка',
    SYNTHESIZING: 'Синтез',
};

interface ThinkingTimelineProps {
    phases: ThinkingPhase[];
    currentPhase: ThinkingPhase | null;
    isActive: boolean;
}

export function ThinkingTimeline({ phases, currentPhase, isActive }: ThinkingTimelineProps) {
    const allPhases = currentPhase ? [...phases, currentPhase] : phases;

    if (allPhases.length === 0) return null;

    return (
        <div className="space-y-2">
            {allPhases.map((phase, index) => {
                const isLast = index === allPhases.length - 1;
                const isCurrent = isLast && isActive;
                const duration = phase.endTime
                    ? ((phase.endTime - phase.startTime) / 1000).toFixed(1)
                    : null;

                return (
                    <motion.div
                        key={phase.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-start gap-3"
                    >
                        {/* Timeline line */}
                        <div className="flex flex-col items-center">
                            <div className={`
                                w-8 h-8 rounded-lg flex items-center justify-center text-lg
                                ${isCurrent
                                    ? 'bg-purple-500/30 ring-2 ring-purple-400/50'
                                    : 'bg-zinc-800/50'
                                }
                            `}>
                                {PHASE_ICONS[phase.name] || '💭'}
                            </div>
                            {!isLast && (
                                <div className="w-0.5 h-8 bg-zinc-700/50 my-1" />
                            )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 pb-4">
                            <div className="flex items-center gap-2">
                                <span className={`text-sm font-medium ${isCurrent ? 'text-purple-300' : 'text-zinc-400'}`}>
                                    {PHASE_LABELS[phase.name] || phase.name}
                                </span>
                                {isCurrent && (
                                    <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse" />
                                )}
                                {duration && (
                                    <span className="text-xs text-zinc-600">{duration}s</span>
                                )}
                            </div>
                            {phase.content && (
                                <p className="text-xs text-zinc-500 mt-1 line-clamp-2">
                                    {phase.content}
                                </p>
                            )}
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}
```

#### Step 2.5: ConfidenceMeter component

**Файл:** `frontend/src/components/thinking/ConfidenceMeter.tsx`

```typescript
import { motion } from 'framer-motion';
import type { ConfidenceInfo } from '../../types/thinking';

interface ConfidenceMeterProps {
    confidence: ConfidenceInfo;
    showBreakdown?: boolean;
}

export function ConfidenceMeter({ confidence, showBreakdown = true }: ConfidenceMeterProps) {
    const { score, level, factors } = confidence;
    const percent = Math.round(score * 100);

    const getColor = (s: number) => {
        if (s >= 0.7) return { bg: 'bg-emerald-500', text: 'text-emerald-400', glow: 'shadow-emerald-500/30' };
        if (s >= 0.4) return { bg: 'bg-yellow-500', text: 'text-yellow-400', glow: 'shadow-yellow-500/30' };
        return { bg: 'bg-red-500', text: 'text-red-400', glow: 'shadow-red-500/30' };
    };

    const colors = getColor(score);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-zinc-900/50 border border-zinc-700/50 rounded-xl p-4"
        >
            {/* Main gauge */}
            <div className="flex items-center gap-4">
                {/* Circular gauge */}
                <div className="relative w-16 h-16">
                    <svg className="w-full h-full -rotate-90">
                        {/* Background circle */}
                        <circle
                            cx="32"
                            cy="32"
                            r="28"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="6"
                            className="text-zinc-800"
                        />
                        {/* Progress circle */}
                        <motion.circle
                            cx="32"
                            cy="32"
                            r="28"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="6"
                            strokeLinecap="round"
                            className={colors.text}
                            strokeDasharray={`${2 * Math.PI * 28}`}
                            initial={{ strokeDashoffset: 2 * Math.PI * 28 }}
                            animate={{ strokeDashoffset: 2 * Math.PI * 28 * (1 - score) }}
                            transition={{ duration: 1, ease: 'easeOut' }}
                        />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span className={`text-lg font-bold ${colors.text}`}>{percent}%</span>
                    </div>
                </div>

                {/* Label */}
                <div>
                    <div className={`text-sm font-medium ${colors.text}`}>
                        {level === 'high' && 'Высокая уверенность'}
                        {level === 'medium' && 'Средняя уверенность'}
                        {level === 'low' && 'Низкая уверенность'}
                    </div>
                    <div className="text-xs text-zinc-500 mt-0.5">
                        На основе {factors.length} факторов
                    </div>
                </div>
            </div>

            {/* Breakdown */}
            {showBreakdown && factors.length > 0 && (
                <div className="mt-4 pt-4 border-t border-zinc-800 space-y-2">
                    {factors.map((factor, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                            <span className="text-zinc-400">{factor.description}</span>
                            <span className={factor.score >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                                {factor.score >= 0 ? '+' : ''}{Math.round(factor.score * 100)}%
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </motion.div>
    );
}
```

---

### PHASE 3: Integration & Polish (3-4 дня)

#### Step 3.1: Обновление useChat.ts для интеграции

**Изменения в:** `frontend/src/hooks/useChat.ts`

```typescript
// Добавить импорт
import { useThinking } from './useThinking';

// В функции useChat
export function useChat(options: UseChatOptions = {}) {
    // ... existing state ...

    // Интегрировать useThinking
    const thinking = useThinking();

    // В streamChat handlers - обновить
    (thinkingEvent) => {
        if (thinkingEvent.status === 'start') {
            thinking.startThinking();
        } else if (thinkingEvent.status === 'phase') {
            thinking.handleThinkingEvent({
                type: 'phase',
                data: { name: thinkingEvent.name, content: thinkingEvent.content },
                timestamp: Date.now()
            });
        } else if (thinkingEvent.status === 'chunk') {
            thinking.handleThinkingEvent({
                type: 'chunk',
                data: { content: thinkingEvent.content, total_chars: thinkingEvent.total_chars },
                timestamp: Date.now()
            });
        } else if (thinkingEvent.status === 'end') {
            thinking.handleThinkingEvent({
                type: 'end',
                data: { duration_ms: thinkingEvent.duration_ms },
                timestamp: Date.now()
            });
        }
    }

    // Return extended
    return {
        // ... existing returns ...
        thinking,  // NEW: expose thinking state
    };
}
```

#### Step 3.2: Обновление ChatTab для новых компонентов

**Изменения в:** `frontend/src/components/tabs/ChatTab.tsx`

```typescript
import { ThinkingModeToggle } from '../thinking/ThinkingModeToggle';
import { LiveThinkingStream } from '../thinking/LiveThinkingStream';
import { ThinkingTimeline } from '../thinking/ThinkingTimeline';
import { ConfidenceMeter } from '../thinking/ConfidenceMeter';

// В JSX
{/* Thinking Panel - redesigned */}
{thinking.isActive && (
    <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className="px-4 md:px-8"
    >
        <div className="max-w-2xl mx-auto space-y-4">
            {/* Timeline */}
            <ThinkingTimeline
                phases={thinking.phases}
                currentPhase={thinking.currentPhase}
                isActive={thinking.isActive}
            />

            {/* Live stream */}
            <LiveThinkingStream
                content={thinking.streamContent}
                isActive={thinking.isActive}
            />
        </div>
    </motion.div>
)}

{/* Confidence - after response */}
{!isGenerating && thinking.confidence && (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-4 md:px-8 max-w-2xl mx-auto"
    >
        <ConfidenceMeter confidence={thinking.confidence} />
    </motion.div>
)}
```

#### Step 3.3: CSS анимации и стили

**Добавить в:** `frontend/src/index.css`

```css
/* ============= PHASE 3: Thinking Animations ============= */

/* Smooth thinking panel transitions */
.thinking-panel-enter {
    opacity: 0;
    transform: translateY(-10px);
}

.thinking-panel-enter-active {
    opacity: 1;
    transform: translateY(0);
    transition: opacity 300ms ease-out, transform 300ms ease-out;
}

.thinking-panel-exit {
    opacity: 1;
}

.thinking-panel-exit-active {
    opacity: 0;
    transition: opacity 200ms ease-in;
}

/* Thinking indicator pulse */
@keyframes thinking-pulse {
    0%, 100% {
        box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.4);
    }
    50% {
        box-shadow: 0 0 0 10px rgba(139, 92, 246, 0);
    }
}

.thinking-pulse {
    animation: thinking-pulse 2s ease-in-out infinite;
}

/* Timeline connector animation */
@keyframes timeline-grow {
    from {
        height: 0;
    }
    to {
        height: 32px;
    }
}

.timeline-connector {
    animation: timeline-grow 300ms ease-out forwards;
}

/* Confidence meter fill */
@keyframes meter-fill {
    from {
        stroke-dashoffset: 175.93;
    }
}

/* Stream cursor blink */
@keyframes cursor-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}

.stream-cursor {
    animation: cursor-blink 1s step-end infinite;
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    .thinking-pulse,
    .timeline-connector,
    .stream-cursor {
        animation: none;
    }

    * {
        transition-duration: 0.01ms !important;
    }
}
```

#### Step 3.4: Accessibility improvements

**Добавить в соответствующие компоненты:**

```typescript
// ThinkingIndicator - aria-live region
<div
    role="status"
    aria-live="polite"
    aria-label={`MAX думает, прошло ${elapsedTime} секунд`}
>
    {/* ... existing content ... */}
</div>

// ThinkingTimeline - semantic list
<ol
    role="list"
    aria-label="Этапы рассуждения"
>
    {/* ... phases ... */}
</ol>

// ConfidenceMeter - accessible gauge
<div
    role="meter"
    aria-valuenow={percent}
    aria-valuemin={0}
    aria-valuemax={100}
    aria-label={`Уверенность: ${percent} процентов`}
>
    {/* ... gauge ... */}
</div>
```

---

### PHASE 4: Advanced Features (4-5 дней)

#### Step 4.1: ThinkingTreeView (интерактивное дерево)

**Файл:** `frontend/src/components/thinking/ThinkingTreeView.tsx`

```typescript
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronDown } from 'lucide-react';

interface ThinkingNode {
    id: string;
    label: string;
    content: string;
    children?: ThinkingNode[];
}

interface ThinkingTreeViewProps {
    root: ThinkingNode;
    onNodeSelect?: (node: ThinkingNode) => void;
}

function TreeNode({
    node,
    depth = 0,
    onSelect
}: {
    node: ThinkingNode;
    depth?: number;
    onSelect?: (node: ThinkingNode) => void;
}) {
    const [expanded, setExpanded] = useState(depth < 2);
    const hasChildren = node.children && node.children.length > 0;

    return (
        <div className="select-none">
            <motion.div
                className={`
                    flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer
                    hover:bg-zinc-800/50 transition-colors
                `}
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
                onClick={() => {
                    if (hasChildren) setExpanded(!expanded);
                    onSelect?.(node);
                }}
                whileHover={{ x: 2 }}
            >
                {hasChildren ? (
                    <motion.div
                        animate={{ rotate: expanded ? 90 : 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <ChevronRight size={14} className="text-zinc-500" />
                    </motion.div>
                ) : (
                    <div className="w-3.5 h-3.5 rounded-full bg-purple-500/30 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                    </div>
                )}
                <span className="text-sm text-zinc-300">{node.label}</span>
            </motion.div>

            <AnimatePresence>
                {expanded && hasChildren && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                    >
                        {node.children!.map(child => (
                            <TreeNode
                                key={child.id}
                                node={child}
                                depth={depth + 1}
                                onSelect={onSelect}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export function ThinkingTreeView({ root, onNodeSelect }: ThinkingTreeViewProps) {
    return (
        <div className="bg-zinc-900/50 border border-zinc-700/50 rounded-xl p-3">
            <div className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2 px-2">
                Дерево рассуждений
            </div>
            <TreeNode node={root} onSelect={onNodeSelect} />
        </div>
    );
}
```

#### Step 4.2: ThinkingExport component

**Файл:** `frontend/src/components/thinking/ThinkingExport.tsx`

```typescript
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, FileText, Code, X } from 'lucide-react';
import type { ThinkingState } from '../../types/thinking';

interface ThinkingExportProps {
    thinking: ThinkingState;
    messageContent: string;
    isOpen: boolean;
    onClose: () => void;
}

type ExportFormat = 'markdown' | 'json';

export function ThinkingExport({ thinking, messageContent, isOpen, onClose }: ThinkingExportProps) {
    const [format, setFormat] = useState<ExportFormat>('markdown');

    const generateMarkdown = () => {
        const lines = [
            '# Процесс рассуждения MAX AI',
            '',
            `**Дата:** ${new Date().toLocaleString()}`,
            `**Режим:** ${thinking.mode}`,
            `**Время размышлений:** ${(thinking.totalDuration / 1000).toFixed(1)}s`,
            '',
            '## Этапы рассуждения',
            '',
        ];

        thinking.phases.forEach((phase, i) => {
            const duration = phase.endTime
                ? ((phase.endTime - phase.startTime) / 1000).toFixed(1)
                : '?';
            lines.push(`### ${i + 1}. ${phase.name} (${duration}s)`);
            lines.push('');
            lines.push(phase.content);
            lines.push('');
        });

        if (thinking.streamContent) {
            lines.push('## Полный процесс мышления');
            lines.push('');
            lines.push('```');
            lines.push(thinking.streamContent);
            lines.push('```');
            lines.push('');
        }

        if (thinking.confidence) {
            lines.push('## Уверенность');
            lines.push('');
            lines.push(`**Оценка:** ${Math.round(thinking.confidence.score * 100)}% (${thinking.confidence.level})`);
            lines.push('');
        }

        lines.push('## Финальный ответ');
        lines.push('');
        lines.push(messageContent);

        return lines.join('\n');
    };

    const generateJSON = () => {
        return JSON.stringify({
            exportDate: new Date().toISOString(),
            thinking: {
                mode: thinking.mode,
                totalDuration: thinking.totalDuration,
                phases: thinking.phases,
                streamContent: thinking.streamContent,
                confidence: thinking.confidence,
            },
            response: messageContent,
        }, null, 2);
    };

    const handleDownload = () => {
        const content = format === 'markdown' ? generateMarkdown() : generateJSON();
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `thinking-export-${Date.now()}.${format === 'markdown' ? 'md' : 'json'}`;
        a.click();
        URL.revokeObjectURL(url);
        onClose();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    onClick={onClose}
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.95, opacity: 0 }}
                        onClick={e => e.stopPropagation()}
                        className="bg-zinc-900 border border-zinc-700 rounded-2xl p-6 max-w-md w-full"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-white">Экспорт рассуждений</h3>
                            <button onClick={onClose} className="text-zinc-500 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="space-y-3 mb-6">
                            <button
                                onClick={() => setFormat('markdown')}
                                className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-colors ${
                                    format === 'markdown'
                                        ? 'border-indigo-500 bg-indigo-500/10'
                                        : 'border-zinc-700 hover:border-zinc-600'
                                }`}
                            >
                                <FileText size={20} className={format === 'markdown' ? 'text-indigo-400' : 'text-zinc-500'} />
                                <div className="text-left">
                                    <div className="text-sm font-medium text-white">Markdown</div>
                                    <div className="text-xs text-zinc-500">Читаемый формат для документации</div>
                                </div>
                            </button>

                            <button
                                onClick={() => setFormat('json')}
                                className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-colors ${
                                    format === 'json'
                                        ? 'border-indigo-500 bg-indigo-500/10'
                                        : 'border-zinc-700 hover:border-zinc-600'
                                }`}
                            >
                                <Code size={20} className={format === 'json' ? 'text-indigo-400' : 'text-zinc-500'} />
                                <div className="text-left">
                                    <div className="text-sm font-medium text-white">JSON</div>
                                    <div className="text-xs text-zinc-500">Структурированные данные для анализа</div>
                                </div>
                            </button>
                        </div>

                        <button
                            onClick={handleDownload}
                            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-xl font-medium transition-colors"
                        >
                            <Download size={18} />
                            Скачать
                        </button>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
```

#### Step 4.3: ThinkingProgressBar для длительных запросов

**Файл:** `frontend/src/components/thinking/ThinkingProgressBar.tsx`

```typescript
import { motion } from 'framer-motion';

interface ThinkingProgressBarProps {
    progress: number;  // 0-1
    budget: number;
    used: number;
    isActive: boolean;
}

export function ThinkingProgressBar({ progress, budget, used, isActive }: ThinkingProgressBarProps) {
    if (!isActive) return null;

    return (
        <div className="w-full max-w-md">
            {/* Progress bar */}
            <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <motion.div
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress * 100}%` }}
                    transition={{ duration: 0.3 }}
                />
            </div>

            {/* Labels */}
            <div className="flex items-center justify-between mt-1.5 text-xs text-zinc-500">
                <span>{used.toLocaleString()} токенов</span>
                <span>{Math.round(progress * 100)}% бюджета</span>
                <span>из {budget.toLocaleString()}</span>
            </div>
        </div>
    );
}
```

---

### PHASE 5: Testing & Documentation (2-3 дня)

#### Step 5.1: Unit tests для hooks

**Файл:** `frontend/src/hooks/__tests__/useThinking.test.ts`

```typescript
import { renderHook, act } from '@testing-library/react';
import { useThinking } from '../useThinking';

describe('useThinking', () => {
    it('should initialize with default state', () => {
        const { result } = renderHook(() => useThinking());

        expect(result.current.isActive).toBe(false);
        expect(result.current.mode).toBe('standard');
        expect(result.current.phases).toHaveLength(0);
    });

    it('should start thinking session', () => {
        const { result } = renderHook(() => useThinking());

        act(() => {
            result.current.startThinking();
        });

        expect(result.current.isActive).toBe(true);
        expect(result.current.streamContent).toBe('');
    });

    it('should handle phase events', () => {
        const { result } = renderHook(() => useThinking());

        act(() => {
            result.current.startThinking();
            result.current.handleThinkingEvent({
                type: 'phase',
                data: { name: 'PLANNING', content: 'Planning the approach' },
                timestamp: Date.now(),
            });
        });

        expect(result.current.currentPhase?.name).toBe('PLANNING');
    });

    // ... more tests
});
```

#### Step 5.2: Storybook stories для компонентов

**Файл:** `frontend/src/components/thinking/LiveThinkingStream.stories.tsx`

```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { LiveThinkingStream } from './LiveThinkingStream';

const meta: Meta<typeof LiveThinkingStream> = {
    title: 'Thinking/LiveThinkingStream',
    component: LiveThinkingStream,
    parameters: {
        layout: 'centered',
    },
};

export default meta;
type Story = StoryObj<typeof LiveThinkingStream>;

export const Active: Story = {
    args: {
        content: 'Analyzing the user query...\n\nBreaking down into components:\n1. Main objective\n2. Context requirements\n3. Expected output format',
        isActive: true,
    },
};

export const Completed: Story = {
    args: {
        content: 'Full thinking process completed.\n\nConclusion: The approach is valid.',
        isActive: false,
    },
};

export const LongContent: Story = {
    args: {
        content: Array(50).fill('This is a line of thinking content.\n').join(''),
        isActive: true,
        maxHeight: 150,
    },
};
```

---

## 14. Checklist для реализации

### Pre-Development
- [ ] Установить зависимости (framer-motion, lottie-react, radix-ui)
- [ ] Создать структуру папок для thinking компонентов
- [ ] Определить TypeScript типы в `types/thinking.ts`
- [ ] Настроить Storybook для изолированной разработки

### Phase 1: Backend
- [ ] Расширить streaming.py для phase detection
- [ ] Добавить streaming think chunks
- [ ] Создать confidence.py модуль
- [ ] Добавить thinking_budget в API
- [ ] Написать unit tests для backend

### Phase 2: Frontend Core
- [ ] Создать useThinking hook
- [ ] Реализовать ThinkingModeToggle
- [ ] Реализовать LiveThinkingStream
- [ ] Реализовать ThinkingTimeline
- [ ] Реализовать ConfidenceMeter
- [ ] Написать unit tests для hooks

### Phase 3: Integration
- [ ] Интегрировать useThinking в useChat
- [ ] Обновить ChatTab с новыми компонентами
- [ ] Добавить CSS анимации
- [ ] Добавить aria-* атрибуты для a11y
- [ ] Протестировать reduced motion

### Phase 4: Advanced
- [ ] Реализовать ThinkingTreeView
- [ ] Реализовать ThinkingExport
- [ ] Реализовать ThinkingProgressBar
- [ ] Добавить Lottie анимации
- [ ] Интеграционное тестирование

### Phase 5: Polish
- [ ] Написать Storybook stories
- [ ] Провести UX тестирование
- [ ] Оптимизировать производительность
- [ ] Написать документацию
- [ ] Code review

---

## 15. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Backend не отправляет phase events | Высокая | Критическое | Fallback на time-based phases |
| Performance issues с частыми updates | Средняя | Высокое | Throttling, virtualization |
| Несовместимость с разными моделями | Средняя | Среднее | Graceful degradation |
| Большой bundle size от framer-motion | Низкая | Низкое | Tree shaking, lazy loading |

---

**Версия документа:** 2.0
**Обновлено:** 2025-12-15
**Следующий review:** После Phase 1
