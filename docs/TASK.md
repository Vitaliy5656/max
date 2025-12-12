# MAX AI Assistant - Task List

## Этап 0: Visionary Check & Risk Assessment

- [x] Анализ требований и API LM Studio
- [x] Оценка рисков (security, performance)

## Этап 1: Архитектура

- [x] Создание implementation_plan.md
- [x] Выбор и утверждение фич (17 штук)

## Этап 2: Базовая инфраструктура

- [x] Python venv + requirements.txt (13 зависимостей)
- [x] Структура папок

## Этап 3: Core Backend

- [x] config.py
- [x] lm_client.py (Model Switcher, Smart Routing, TTL)
- [x] memory.py (Session, Summary, Facts, Cross-Session)
- [x] user_profile.py (Mood, Style, Feedback)
- [x] tools.py (14 инструментов)
- [x] web_search.py
- [x] archives.py (ZIP/RAR)
- [x] rag.py (PDF/DOCX документы)
- [x] autogpt.py (автономные задачи)
- [x] templates.py (8 дефолтных шаблонов)

## Этап 4: UI (Gradio)

- [x] app.py (7 вкладок: Чат, RAG, AutoGPT, Шаблоны, История, Настройки, Помощь)
- [x] run.py

## Этап 5: Верификация

- [x] Все импорты проверены
- [ ] Функциональный тест с LM Studio
