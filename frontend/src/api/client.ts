/**
 * API Client for MAX AI Backend
 */

const API_BASE = 'http://127.0.0.1:8000/api';

// ============= Types =============

export interface Conversation {
    id: string;
    title: string;
    updated_at: string;
    message_count: number;
}

export interface Message {
    id: number;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
    model_used?: string;
}

export interface Document {
    id: string;
    name: string;
    size: string;
    type: string;
    chunks: number;
    status: 'indexed' | 'processing';
}

export interface Template {
    id: string;
    name: string;
    category: string;
    content: string;
}

export interface MetricResult {
    score: number;
    level: number;
    progress: number;
    breakdown: Record<string, number>;
    trend: string;
    trend_value: number;
}

export interface Metrics {
    iq: MetricResult;
    empathy: MetricResult;
}

export interface Achievement {
    id: string;
    name: string;
    description: string;
    category: string;
    icon: string;
    progress: number;
    unlocked: boolean;
    unlocked_at?: string;
}

export interface AgentStep {
    id: number;
    action: string;
    title: string;
    desc: string;
    action_input?: Record<string, unknown> | string;  // Tool parameters
    result?: string;  // Execution result
    status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface AgentStatus {
    running: boolean;
    paused: boolean;
    goal: string;
    steps: AgentStep[];
}

// ============= API Functions =============

// Thinking Event (for reasoning models like DeepSeek R1)
export interface ThinkingEvent {
    status: 'start' | 'end';
    duration_ms?: number;
    chars_filtered?: number;
    think_content?: string;  // For Collapsible Think
}

// Confidence Event (scored after response)
export interface ConfidenceEvent {
    score: number;        // 0.0 - 1.0
    level: 'low' | 'medium' | 'high';
    factors: string[];
}

// Chat
export async function streamChat(
    message: string,
    conversationId?: string,
    model: string = 'auto',
    temperature: number = 0.7,
    useRag: boolean = true,
    thinkingMode: string = 'standard',  // NEW: fast/standard/deep
    hasImage: boolean = false,          // NEW: auto-activates vision
    onToken: (token: string) => void = () => { },
    onComplete: (data: any) => void = () => { },
    onError: (error: string) => void = () => { },  // Error callback
    onThinking?: (event: ThinkingEvent) => void,   // Thinking callback
    onConfidence?: (event: ConfidenceEvent) => void,  // Confidence callback
    onLoading?: (event: { model: string }) => void,   // Issue #6: Loading state callback
    abortSignal?: AbortSignal
): Promise<void> {
    const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message,
            conversation_id: conversationId,
            model,
            temperature,
            use_rag: useRag,
            thinking_mode: thinkingMode,
            has_image: hasImage,
        }),
        signal: abortSignal,
    });

    if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Server Error ${response.status}: ${errText || response.statusText}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    if (!reader) throw new Error('No response body');

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Split by newlines, but keep the last chunk if it's incomplete
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last incomplete line in buffer

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data: ')) continue;

            try {
                const data = JSON.parse(trimmed.slice(6));

                // Handle thinking events
                if (data.thinking && onThinking) {
                    onThinking({
                        status: data.thinking,
                        duration_ms: data.duration_ms,
                        chars_filtered: data.chars_filtered,
                        think_content: data.think_content
                    });
                } else if (data.confidence && onConfidence) {
                    // Handle confidence event
                    onConfidence({
                        score: data.score,
                        level: data.level,
                        factors: data.factors
                    });
                } else if (data.status === 'loading' && onLoading) {
                    // Issue #6 fix: Handle model loading event
                    onLoading({ model: data.model || '' });
                } else if (data.token) {
                    onToken(data.token);
                } else if (data.error) {
                    // Handle streaming errors from backend
                    console.error('Stream error from backend:', data.error);
                    onError(data.error);
                } else if (data.done) {
                    onComplete(data);
                }
            } catch (e) {
                console.warn('Failed to parse SSE message:', trimmed, e);
            }
        }
    }
}

// Conversations
export async function getConversations(limit: number = 50): Promise<Conversation[]> {
    const res = await fetch(`${API_BASE}/conversations?limit=${limit}`);
    return res.json();
}

export async function createConversation(title: string = 'Новый разговор'): Promise<{ id: string; title: string }> {
    const res = await fetch(`${API_BASE}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    });
    return res.json();
}

export async function getMessages(conversationId: string, limit: number = 100): Promise<Message[]> {
    const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages?limit=${limit}`);
    return res.json();
}

// Documents
export async function getDocuments(): Promise<Document[]> {
    const res = await fetch(`${API_BASE}/documents`);
    return res.json();
}

export async function uploadDocument(file: File): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/documents/upload`, {
        method: 'POST',
        body: formData,
    });
    return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
    await fetch(`${API_BASE}/documents/${docId}`, { method: 'DELETE' });
}

// Templates
export async function getTemplates(): Promise<Template[]> {
    const res = await fetch(`${API_BASE}/templates`);
    return res.json();
}

export async function createTemplate(name: string, prompt: string, category: string): Promise<{ id: string }> {
    const res = await fetch(`${API_BASE}/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, prompt, category }),
    });
    return res.json();
}

// Agent
export async function startAgent(goal: string, maxSteps: number = 20): Promise<{ run_id: string }> {
    const res = await fetch(`${API_BASE}/agent/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, max_steps: maxSteps }),
    });
    return res.json();
}

export async function getAgentStatus(): Promise<AgentStatus> {
    const res = await fetch(`${API_BASE}/agent/status`);
    return res.json();
}

export async function stopAgent(): Promise<void> {
    await fetch(`${API_BASE}/agent/stop`, { method: 'POST' });
}

// Metrics
export async function getMetrics(): Promise<Metrics> {
    const res = await fetch(`${API_BASE}/metrics`);
    return res.json();
}

export async function getAchievements(): Promise<Achievement[]> {
    const res = await fetch(`${API_BASE}/achievements`);
    return res.json();
}

// Feedback
export async function submitFeedback(messageId: number, rating: number): Promise<void> {
    await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, rating }),
    });
}

// Models
export async function getModels(): Promise<{ models: string[]; current: string }> {
    const res = await fetch(`${API_BASE}/models`);
    return res.json();
}

// Health
export async function checkHealth(): Promise<{ status: string; initialized: boolean }> {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
}

// Backup
export interface BackupStatus {
    status: string;
    last_backup: string | null;
    last_cloud_sync: string | null;
    cloud_synced: boolean;
    error?: string;
}

export async function getBackupStatus(): Promise<BackupStatus> {
    const res = await fetch(`${API_BASE}/backup/status`);
    return res.json();
}

export async function triggerBackup(): Promise<{ success: boolean }> {
    const res = await fetch(`${API_BASE}/backup/trigger`, { method: 'POST' });
    return res.json();
}
