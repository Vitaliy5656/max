/**
 * Chat Hook — manages chat state and message handling.
 * 
 * Extracted from App.tsx to reduce component complexity.
 * FIX: Added tokenCount and tokensPerSecond for generation stats.
 * UX-012: Chat draft persistence added.
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import * as api from '../api/client';

export interface Message {
    id: number;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
    model?: string;
}

export interface ConfidenceInfo {
    score: number;
    level: 'low' | 'medium' | 'high';
}

export interface UseChatOptions {
    onLog?: (text: string, type?: 'info' | 'error' | 'growth' | 'empathy') => void;
    onMetricsRefresh?: () => void;
}

export function useChat(options: UseChatOptions = {}) {
    const { onLog, onMetricsRefresh } = options;

    // Core state
    const [messages, setMessages] = useState<Message[]>([
        { id: 1, role: 'system', content: 'Привет! Я MAX. Мои нейронные связи готовы к работе. Чем займемся?', timestamp: formatTime(), model: 'System' }
    ]);
    // UX-012: Chat input draft with localStorage persistence
    const [input, setInput] = useState(() => {
        try {
            return localStorage.getItem('chat_draft') || '';
        } catch { return ''; }
    });
    const [isGenerating, setIsGenerating] = useState(false);
    // P2-001: Track connection state (before first token)
    const [isConnecting, setIsConnecting] = useState(false);

    // FIX: Token counter state for generation stats
    const [tokenCount, setTokenCount] = useState(0);
    const [tokensPerSecond, setTokensPerSecond] = useState(0);
    const generationStartRef = useRef<number>(0);

    // Thinking state
    const [isThinking, setIsThinking] = useState(false);
    const [thinkingStartTime, setThinkingStartTime] = useState(0);
    const [thinkContent, setThinkContent] = useState('');
    const [thinkExpanded, setThinkExpanded] = useState(() => {
        try {
            return localStorage.getItem('think_expanded') === 'true';
        } catch { return false; }
    });
    const [thinkingSteps, setThinkingSteps] = useState<Array<{ name: string; content: string }>>([]);

    // Confidence state
    const [lastConfidence, setLastConfidence] = useState<ConfidenceInfo | null>(null);

    // Model loading state
    const [loadingModel, setLoadingModel] = useState<string | null>(null);

    // Queue state
    const [queueStatus, setQueueStatus] = useState<'inactive' | 'waiting' | 'acquired'>('inactive');

    // Abort controller for canceling requests
    const abortControllerRef = useRef<AbortController | null>(null);

    // UX-012: Sync chat draft to localStorage
    useEffect(() => {
        try {
            if (input) {
                localStorage.setItem('chat_draft', input);
            } else {
                localStorage.removeItem('chat_draft');
            }
        } catch { /* ignore storage errors */ }
    }, [input]);

    // UX-025: Persist thinkExpanded preference
    useEffect(() => {
        try {
            localStorage.setItem('think_expanded', String(thinkExpanded));
        } catch { /* ignore */ }
    }, [thinkExpanded]);


    function formatTime() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    const sendMessage = useCallback(async (
        conversationId: string | null,
        selectedModel: string,
        thinkingMode: 'fast' | 'standard' | 'deep',
        onConversationIdChange?: (id: string) => void
    ) => {
        if (!input.trim() || isGenerating) return;

        const userMessage: Message = {
            id: Date.now(),
            role: 'user',
            content: input,
            timestamp: formatTime()
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsGenerating(true);
        setIsConnecting(true); // P2-001: Show connecting state
        setQueueStatus('inactive'); // Reset initially, but client might set to waiting immediately

        // FIX: Reset token stats for new generation
        setTokenCount(0);
        setTokensPerSecond(0);
        generationStartRef.current = Date.now();

        // P0-002 FIX: Don't create assistant message until first token
        // This prevents empty bubbles on errors
        let assistantId: number | null = null;
        let firstTokenReceived = false;

        // Helper to ensure assistant message exists
        const ensureAssistantMessage = () => {
            if (!assistantId) {
                assistantId = Date.now() + 1;
                setMessages(prev => [...prev, {
                    id: assistantId!,
                    role: 'assistant',
                    content: '',
                    timestamp: formatTime(),
                    model: selectedModel
                }]);
            }
            return assistantId;
        };

        abortControllerRef.current = new AbortController();

        try {
            await api.streamChat(
                userMessage.content,
                conversationId ?? undefined,
                selectedModel,
                0.7,
                true,
                thinkingMode,
                false, // hasImage
                (token) => {
                    // P0-002: Create message on first token
                    if (!firstTokenReceived) {
                        firstTokenReceived = true;
                        setIsConnecting(false); // P2-001: Connected, got first token
                        ensureAssistantMessage();
                    }

                    // FIX-005: Correct token counting and rate calculation
                    setTokenCount(prev => {
                        const newCount = prev + 1;
                        const elapsed = (Date.now() - generationStartRef.current) / 1000;
                        if (elapsed > 0.1) { // Avoid division by tiny numbers
                            setTokensPerSecond(Math.round(newCount / elapsed));
                        }
                        return newCount;
                    });
                    // Start of token means we acquired slot
                    setQueueStatus('acquired');
                    if (isThinking) {
                        setIsThinking(false);
                    }

                    const currentId = assistantId;
                    if (currentId) {
                        setMessages(prev => prev.map(msg =>
                            msg.id === currentId
                                ? { ...msg, content: msg.content + token }
                                : msg
                        ));
                    }
                },
                (data) => {
                    onConversationIdChange?.(data.conversation_id);
                    onLog?.('Ответ сгенерирован', 'growth');
                    onMetricsRefresh?.();
                },
                (error) => {
                    // P0-002: If no tokens received yet, just log the error
                    // Don't create empty message with error
                    if (!firstTokenReceived) {
                        onLog?.(`❌ ${error}`, 'error');
                    } else if (assistantId) {
                        // Tokens were received, append error to message
                        const currentId = assistantId;
                        setMessages(prev => prev.map(msg =>
                            msg.id === currentId
                                ? { ...msg, content: msg.content + `\n\n⚠️ ${error}` }
                                : msg
                        ));
                        onLog?.(`Ошибка стрима: ${error}`, 'error');
                    }
                },
                (thinkingEvent) => {
                    setQueueStatus('acquired'); // Thinking means we have slot
                    if (thinkingEvent.status === 'start') {
                        setIsThinking(true);
                        setThinkingStartTime(Date.now());
                        setThinkContent('');
                        setThinkExpanded(false);
                        setThinkingSteps([]); // Clear previous steps
                        onLog?.('🧠 MAX думает...', 'info');
                    } else if (thinkingEvent.status === 'step') {
                        // Live step update
                        if (thinkingEvent.name && thinkingEvent.content) {
                            setThinkingSteps(prev => [...prev, {
                                name: thinkingEvent.name!,
                                content: thinkingEvent.content!
                            }]);
                        }
                    } else if (thinkingEvent.status === 'end') {
                        setIsThinking(false);
                        if (thinkingEvent.think_content) {
                            setThinkContent(thinkingEvent.think_content);
                        }
                        const durationSec = ((thinkingEvent.duration_ms || 0) / 1000).toFixed(1);
                        onLog?.(`🧠 Обдумал за ${durationSec}s`, 'growth');
                    }
                },
                (confidenceEvent) => {
                    setLastConfidence({
                        score: confidenceEvent.score,
                        level: confidenceEvent.level
                    });
                    const emoji = confidenceEvent.level === 'high' ? '🟢' : confidenceEvent.level === 'medium' ? '🟡' : '🔴';
                    onLog?.(`${emoji} Уверенность: ${Math.round(confidenceEvent.score * 100)}%`, 'growth');
                },
                (loadingEvent) => {
                    if (loadingEvent.model) {
                        setLoadingModel(loadingEvent.model);
                        onLog?.(`🔄 Загрузка модели: ${loadingEvent.model}...`, 'info');
                    }
                },
                (queueEvent) => {
                    // Handle queue status
                    if (queueEvent.status === 'waiting') {
                        setQueueStatus('waiting');
                        onLog?.('⏳ Ожидание слота...', 'info');
                    } else if (queueEvent.status === 'acquired') {
                        setQueueStatus('acquired');
                    }
                },
                abortControllerRef.current.signal
            );
        } catch (error: unknown) {
            const err = error as Error;

            if (err.name === 'AbortError') {
                onLog?.('Генерация остановлена пользователем', 'info');
                if (assistantId) {
                    const currentId = assistantId;
                    setMessages(prev => prev.map(msg =>
                        msg.id === currentId
                            ? { ...msg, content: msg.content + ' [Прервано]' }
                            : msg
                    ));
                }
            } else {
                // P0-002: Better error handling
                const errorMessage = err.message || 'Не удалось получить ответ';

                if (!firstTokenReceived) {
                    // No tokens received - error already logged in onError callback
                    // Don't create assistant message, just ensure the error is visible
                    onLog?.(`❌ ${errorMessage}`, 'error');
                } else if (assistantId) {
                    // Tokens were received, show error in message
                    const currentId = assistantId;
                    setMessages(prev => prev.map(msg =>
                        msg.id === currentId
                            ? { ...msg, content: msg.content + `\n\n⚠️ ${errorMessage}` }
                            : msg
                    ));
                }
            }
        } finally {
            setIsGenerating(false);
            setIsConnecting(false); // P2-001: Reset connecting state
            setIsThinking(false);
            setLoadingModel(null);
            setQueueStatus('inactive');
            abortControllerRef.current = null;
        }
    }, [input, isGenerating, isThinking, onLog, onMetricsRefresh]);

    const stopGeneration = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            onLog?.('Остановка генерации...', 'info');
        }
    }, [onLog]);

    const clearMessages = useCallback(() => {
        setMessages([
            { id: 1, role: 'system', content: 'Новый разговор начат. Чем могу помочь?', timestamp: formatTime(), model: 'System' }
        ]);
    }, []);

    const loadMessages = useCallback(async (conversationId: string) => {
        try {
            const msgs = await api.getMessages(conversationId);
            if (msgs.length > 0) {
                setMessages(msgs.map(m => ({
                    id: m.id,
                    role: m.role,
                    content: m.content,
                    timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    model: m.model_used
                })));
                onLog?.('История загружена', 'info');
            } else {
                clearMessages();
            }
        } catch (error) {
            console.error('Failed to load messages:', error);
            onLog?.('Ошибка загрузки истории', 'error');
        }
    }, [clearMessages, onLog]);

    const toggleThinkExpanded = useCallback(() => {
        setThinkExpanded(prev => !prev);
    }, []);

    return {
        // State
        messages,
        setMessages,
        input,
        setInput,
        isGenerating,
        isConnecting, // P2-001: Expose connecting state
        isThinking,
        thinkingStartTime,
        thinkContent,
        thinkExpanded,
        setThinkExpanded,
        thinkingSteps,
        lastConfidence,
        loadingModel,
        queueStatus,
        // FIX: Expose token stats for UI
        tokenCount,
        tokensPerSecond,

        // Actions
        sendMessage,
        stopGeneration,
        clearMessages,
        loadMessages,
        toggleThinkExpanded,
    };
}
