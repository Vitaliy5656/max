/**
 * API Client for MAX AI Backend
 * 
 * FIX-002: API_BASE now reads from env variable
 * FIX-003: Added retry logic for 5xx errors
 * FIX-004: Added request timeout constant
 */

// FIX-002: Use environment variable with fallback to relative path (Vite proxy)
const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL)
    || '/api';

// FIX-004: Default timeout for requests (30 seconds)
export const DEFAULT_TIMEOUT = 30000;

// FIX-003: Retry utility for transient errors
export async function fetchWithRetry(
    url: string,
    options: RequestInit,
    maxRetries = 3,
    baseDelay = 1000
): Promise<Response> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            const response = await fetch(url, options);

            // Retry on 5xx server errors
            if (response.status >= 500 && attempt < maxRetries - 1) {
                const delay = baseDelay * Math.pow(2, attempt);
                console.warn(`Server error ${response.status}, retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                continue;
            }

            return response;
        } catch (error) {
            lastError = error instanceof Error ? error : new Error(String(error));

            // Only retry on network errors, not on abort
            if (lastError.name === 'AbortError') {
                throw lastError;
            }

            if (attempt < maxRetries - 1) {
                const delay = baseDelay * Math.pow(2, attempt);
                console.warn(`Network error, retrying in ${delay}ms...`, lastError.message);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    throw lastError || new Error('Request failed after retries');
}

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
    status: 'start' | 'end' | 'step';  // 'step' for intermediate thinking steps
    duration_ms?: number;
    chars_filtered?: number;
    think_content?: string;  // For Collapsible Think
    name?: string;           // Step name (PLANNING, DRAFTING, etc.)
    content?: string;        // Step description
}

// Confidence Event (scored after response)
export interface ConfidenceEvent {
    score: number;        // 0.0 - 1.0
    level: 'low' | 'medium' | 'high';
    factors: string[];
}

// Queue Status Event
export interface QueueEvent {
    status: 'waiting' | 'acquired';
    position?: number;
}

// Chat
// P0-001 FIX: Added timeout support and proper network error handling
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
    onQueueStatus?: (event: QueueEvent) => void,      // NEW: Queue status callback
    abortSignal?: AbortSignal
): Promise<void> {
    // P0-001: Create timeout controller (30 seconds)
    const timeoutController = new AbortController();
    const timeoutId = setTimeout(() => timeoutController.abort(), DEFAULT_TIMEOUT);

    // Combine user abort signal with timeout
    const combinedController = new AbortController();

    // Listen to both signals
    const abortHandler = () => combinedController.abort();
    timeoutController.signal.addEventListener('abort', abortHandler);
    abortSignal?.addEventListener('abort', abortHandler);

    try {
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
            signal: combinedController.signal,
        });

        // Clear timeout since we got a response
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errText = await response.text();
            const errorMessage = `Ошибка сервера ${response.status}: ${errText || response.statusText}`;
            onError(errorMessage);
            throw new Error(errorMessage);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        if (!reader) {
            const errorMessage = 'Нет ответа от сервера';
            onError(errorMessage);
            throw new Error(errorMessage);
        }

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

                    // Handle meta events (Queue & Pulse)
                    if (data._meta) {
                        if (data._meta === 'queue_heartbeat' && onQueueStatus) {
                            onQueueStatus({ status: 'waiting' });
                        } else if (data._meta === 'thinking_start' && onThinking) {
                            onThinking({ status: 'start' });
                        } else if (data._meta === 'thinking_end' && onThinking) {
                            onThinking({
                                status: 'end',
                                duration_ms: data.duration_ms,
                                chars_filtered: data.chars_filtered,
                                think_content: data.think_content
                            });
                        }
                        // 'pulse' is currently just a keep-alive, no UI action needed yet
                        // except maybe resetting a connection timeout timer if we had one.
                        // FIX-001: Use continue instead of return to process remaining messages
                        continue;
                    }

                    // Handle thinking events (Legacy/Direct format if backend sends it)
                    if (data.thinking && onThinking) {
                        onThinking({
                            status: data.thinking,
                            duration_ms: data.duration_ms,
                            chars_filtered: data.chars_filtered,
                            think_content: data.think_content,
                            name: data.name,           // Step name (e.g., "PLANNING")
                            content: data.content      // Step description
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
    } catch (error) {
        // P0-001 & P1-001: Proper network error handling
        clearTimeout(timeoutId);

        if (error instanceof Error) {
            if (error.name === 'AbortError') {
                // Check if it was timeout or user abort
                if (timeoutController.signal.aborted && !abortSignal?.aborted) {
                    const timeoutMessage = 'Сервер не отвечает (таймаут 30 секунд). Проверьте подключение к LM Studio.';
                    onError(timeoutMessage);
                    throw new Error(timeoutMessage);
                }
                // User cancelled - re-throw without onError (handled in useChat)
                throw error;
            }

            // Network errors (Connection Refused, etc.)
            let userMessage = 'Ошибка сети';
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                userMessage = 'Не удалось подключиться к серверу. Проверьте что backend запущен.';
            } else if (error.message.includes('ECONNREFUSED')) {
                userMessage = 'Сервер недоступен (Connection Refused). Запустите backend.';
            } else {
                userMessage = `Ошибка: ${error.message}`;
            }

            onError(userMessage);
            throw new Error(userMessage);
        }

        const unknownError = 'Неизвестная ошибка при отправке сообщения';
        onError(unknownError);
        throw new Error(unknownError);
    } finally {
        // Cleanup listeners
        timeoutController.signal.removeEventListener('abort', abortHandler);
        abortSignal?.removeEventListener('abort', abortHandler);
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

// FIX: Upload with progress callback for progress bar UI
export function uploadDocumentWithProgress(
    file: File,
    onProgress: (percent: number) => void
): Promise<Document> {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                onProgress(percent);
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    resolve(JSON.parse(xhr.responseText));
                } catch {
                    reject(new Error('Invalid response'));
                }
            } else {
                reject(new Error(`Upload failed: ${xhr.status}`));
            }
        });

        xhr.addEventListener('error', () => reject(new Error('Network error')));
        xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')));

        xhr.open('POST', `${API_BASE}/documents/upload`);
        xhr.send(formData);
    });
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

// UX-013: Message edit
export async function editMessage(messageId: number, content: string): Promise<{ status: string; message_id: number; content: string }> {
    const res = await fetch(`${API_BASE}/messages/${messageId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    });
    if (!res.ok) {
        throw new Error(`Failed to edit message: ${res.status}`);
    }
    return res.json();
}

// ============= Provider Switching (Phase 8) =============

export interface ProviderInfo {
    provider: 'lmstudio' | 'gemini';
    available: string[];
}

export async function getProvider(): Promise<ProviderInfo> {
    const res = await fetch(`${API_BASE}/provider`);
    return res.json();
}

export async function setProvider(provider: 'lmstudio' | 'gemini'): Promise<{ success: boolean; provider: string }> {
    const res = await fetch(`${API_BASE}/provider`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
    });
    return res.json();
}

// Model Selection Mode
export async function getModelSelectionMode(): Promise<{ mode: string }> {
    const res = await fetch(`${API_BASE}/config/model_selection_mode`);
    return res.json();
}

export async function setModelSelectionMode(mode: 'manual' | 'auto'): Promise<{ success: boolean; mode: string }> {
    const res = await fetch(`${API_BASE}/config/model_selection_mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
    });
    return res.json();
}

