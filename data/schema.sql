-- Database schema for MAX AI Assistant.
--
-- Tables:
-- - conversations: Chat sessions
-- - messages: Individual messages
-- - memory_facts: Extracted facts for long-term memory
-- - documents: RAG document index
-- - document_chunks: RAG document chunks with embeddings
-- - autogpt_runs: Autonomous task runs
-- - autogpt_steps: Steps within autonomous runs
-- - user_profile: User preferences and habits
-- - feedback: User feedback on responses
-- - templates: Saved prompt templates

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls TEXT,  -- JSON array of tool calls
    tokens_used INTEGER DEFAULT 0,
    model_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

-- Memory Facts (Long-term memory)
CREATE TABLE IF NOT EXISTS memory_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    category TEXT,  -- 'personal', 'preference', 'project', 'general'
    embedding BLOB,  -- Vector embedding for semantic search
    source_message_id INTEGER REFERENCES messages(id),
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facts_category ON memory_facts(category);

-- RAG Documents
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT,
    file_type TEXT,  -- 'pdf', 'docx', 'txt', 'md'
    file_size INTEGER,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document Chunks (for RAG)
CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding BLOB,
    chunk_index INTEGER,
    tokens INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);

-- Auto-GPT Task Runs
CREATE TABLE IF NOT EXISTS autogpt_runs (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'paused', 'completed', 'failed')),
    max_steps INTEGER DEFAULT 20,
    current_step INTEGER DEFAULT 0,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Auto-GPT Steps
CREATE TABLE IF NOT EXISTS autogpt_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES autogpt_runs(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    action TEXT NOT NULL,
    action_input TEXT,  -- JSON
    result TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_steps_run ON autogpt_steps(run_id);

-- User Profile (Personalization)
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton
    name TEXT,
    preferences TEXT,  -- JSON: {verbosity, formality, humor, etc.}
    habits TEXT,       -- JSON: {frequent_queries, preferred_formats}
    dislikes TEXT,     -- JSON: things to avoid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default profile
INSERT OR IGNORE INTO user_profile (id, preferences, habits, dislikes) 
VALUES (1, '{}', '{}', '{}');

-- Feedback (for learning)
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER REFERENCES messages(id),
    rating INTEGER CHECK (rating IN (-1, 0, 1)),  -- -1: bad, 0: neutral, 1: good
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id);

-- Prompt Templates
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    prompt TEXT NOT NULL,
    category TEXT,
    use_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Search History
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    results_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_created ON search_history(created_at);

-- Conversation Summaries (for context compression)
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    messages_covered INTEGER,  -- Number of messages summarized
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- IQ & Empathy Metrics System Tables
-- ============================================================

-- Interaction Outcomes (per-message tracking for metrics)
CREATE TABLE IF NOT EXISTS interaction_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    was_correction BOOLEAN DEFAULT FALSE,    -- User corrected previous response
    implicit_positive BOOLEAN DEFAULT FALSE, -- "спасибо", "отлично", etc.
    implicit_negative BOOLEAN DEFAULT FALSE, -- "нет", "не то", etc.
    facts_in_context INTEGER DEFAULT 0,      -- Facts provided to model
    facts_referenced INTEGER DEFAULT 0,      -- Facts actually used in response
    style_prompt_length INTEGER DEFAULT 0,   -- Personalization applied
    response_time_ms INTEGER,                -- Response generation time
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outcomes_date ON interaction_outcomes(session_date);
CREATE INDEX IF NOT EXISTS idx_outcomes_message ON interaction_outcomes(message_id);

-- Daily Metrics Aggregates (for trend analysis)
CREATE TABLE IF NOT EXISTS daily_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE UNIQUE NOT NULL,
    total_interactions INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,       -- Positive feedback (explicit + implicit)
    negative_count INTEGER DEFAULT 0,       -- Negative feedback
    corrections_count INTEGER DEFAULT 0,    -- User corrections
    avg_context_utilization REAL DEFAULT 0, -- facts_referenced / facts_in_context
    iq_score REAL,                          -- Calculated IQ score
    empathy_score REAL,                     -- Calculated Empathy score
    breakdown_json TEXT,                    -- JSON with component scores
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_metrics(metric_date);

-- Fact Effectiveness (track which facts help)
CREATE TABLE IF NOT EXISTS fact_effectiveness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id INTEGER REFERENCES memory_facts(id) ON DELETE CASCADE,
    times_used INTEGER DEFAULT 0,
    positive_outcomes INTEGER DEFAULT 0,    -- Used and got 👍
    negative_outcomes INTEGER DEFAULT 0,    -- Used and got 👎
    effectiveness_score REAL GENERATED ALWAYS AS (
        CASE WHEN times_used > 0 
        THEN CAST(positive_outcomes AS REAL) / times_used 
        ELSE 0.5 END
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_fact_eff_score ON fact_effectiveness(effectiveness_score DESC);

-- Correction Log (learn from user corrections)
CREATE TABLE IF NOT EXISTS correction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_message_id INTEGER REFERENCES messages(id),
    correction_message_id INTEGER REFERENCES messages(id),
    original_response TEXT,                 -- What we said wrong
    user_correction TEXT,                   -- User's correction
    extracted_pattern TEXT,                 -- LLM-extracted "what was wrong"
    category TEXT,                          -- 'style', 'content', 'format', 'misunderstanding'
    applied_count INTEGER DEFAULT 0,        -- How many times we used this learning
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_correction_category ON correction_log(category);

-- Success Patterns (replicate good responses)
CREATE TABLE IF NOT EXISTS success_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER REFERENCES messages(id),
    response_summary TEXT,                  -- Brief description of successful response
    extracted_pattern TEXT,                 -- LLM-extracted "what worked"
    category TEXT,                          -- 'style', 'format', 'depth', 'approach'
    relevance_context TEXT,                 -- When to apply this pattern
    applied_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_success_category ON success_patterns(category);

-- Achievements (gamification)
CREATE TABLE IF NOT EXISTS achievements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,                          -- 'iq', 'empathy', 'general'
    icon TEXT,                              -- Emoji or icon name for UI
    threshold_type TEXT,                    -- 'count', 'streak', 'percentage', 'milestone'
    threshold_value REAL,
    current_value REAL DEFAULT 0,
    unlocked_at TIMESTAMP,                  -- NULL = not unlocked
    notified BOOLEAN DEFAULT FALSE          -- Has user been notified?
);

-- Insert default achievements
INSERT OR IGNORE INTO achievements (id, name, description, category, icon, threshold_type, threshold_value) VALUES
    ('first_chat', 'Первый контакт', 'Начните общение с MAX', 'general', '👋', 'count', 1),
    ('first_thank', 'Благодарность', 'Получите первый положительный отзыв', 'iq', '👍', 'count', 1),
    ('streak_3', 'Точность x3', '3 дня подряд без негативных отзывов', 'iq', '🎯', 'streak', 3),
    ('no_corrections', 'Идеальный день', 'День без единой коррекции', 'iq', '✨', 'milestone', 1),
    ('memory_10', 'Память', 'Запомнено 10 фактов о вас', 'empathy', '🧠', 'count', 10),
    ('memory_50', 'Глубокая память', 'Запомнено 50 фактов', 'empathy', '📚', 'count', 50),
    ('week_together', 'Неделя вместе', '7 дней активного общения', 'general', '📅', 'count', 7),
    ('month_together', 'Месяц вместе', '30 дней активного общения', 'general', '🗓️', 'count', 30),
    ('adaptation_10', 'Адаптация', 'Ошибок стало на 10% меньше', 'iq', '📈', 'percentage', 10),
    ('adaptation_50', 'Полная адаптация', 'Ошибок стало на 50% меньше', 'iq', '🚀', 'percentage', 50),
    ('habit_5', 'Наблюдатель', 'Отслежено 5 привычек', 'empathy', '👁️', 'count', 5),
    ('anticipation', 'Предвосхищение', 'Предложение принято 10 раз', 'empathy', '🔮', 'count', 10);

-- ============================================================
-- AI Next Gen Modules Tables
-- ============================================================

-- Verification Logs (ReflectiveAgent)
-- Tracks verification results for AutoGPT steps
CREATE TABLE IF NOT EXISTS verification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id INTEGER REFERENCES autogpt_steps(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'partial', 'skip')),
    critique TEXT,                              -- What went wrong (if fail/partial)
    suggestion TEXT,                            -- How to fix it
    confidence REAL DEFAULT 0.0,                -- Verification confidence 0.0-1.0
    retry_count INTEGER DEFAULT 0,              -- How many retries were needed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_verification_step ON verification_logs(step_id);
CREATE INDEX IF NOT EXISTS idx_verification_status ON verification_logs(status);

-- Error Memory (ErrorMemory module)
-- Vector-based memory of past errors for avoiding repetition
CREATE TABLE IF NOT EXISTS error_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_pattern TEXT NOT NULL,                -- What the error looked like
    wrong_action TEXT NOT NULL,                 -- What MAX did wrong
    correct_action TEXT NOT NULL,               -- What should have been done
    context_summary TEXT,                       -- Summarized context when error occurred
    embedding BLOB,                             -- Vector embedding for similarity search
    occurrences INTEGER DEFAULT 1,              -- How many times this error pattern occurred
    last_recalled TIMESTAMP,                    -- Last time this error was used to warn
    source_correction_id INTEGER REFERENCES correction_log(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_occurrences ON error_memory(occurrences DESC);

