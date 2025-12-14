/**
 * Chat Hook — manages chat state and message handling.
 * 
 * Extracted from App.tsx to reduce component complexity.
 */
import { useState, useRef, useCallback } from 'react';
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
    const [input, setInput] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);

    // Thinking state
    const [isThinking, setIsThinking] = useState(false);
    const [thinkingStartTime, setThinkingStartTime] = useState(0);
    const [thinkContent, setThinkContent] = useState('');
    const [thinkExpanded, setThinkExpanded] = useState(false);

    // Confidence state
    const [lastConfidence, setLastConfidence] = useState<ConfidenceInfo | null>(null);

    // Model loading state
    const [loadingModel, setLoadingModel] = useState<string | null>(null);

    // Queue state
    const [queueStatus, setQueueStatus] = useState<'inactive' | 'waiting' | 'acquired'>('inactive');

    // Abort controller for canceling requests
    const abortControllerRef = useRef<AbortController | null>(null);

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
        setQueueStatus('inactive'); // Reset initially, but client might set to waiting immediately

        const assistantId = Date.now() + 1;
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            timestamp: formatTime(),
            model: selectedModel
        }]);

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
                    // Start of token means we acquired slot
                    setQueueStatus('acquired');
                    if (isThinking) {
                        setIsThinking(false);
                    }
                    setMessages(prev => prev.map(msg =>
                        msg.id === assistantId
                            ? { ...msg, content: msg.content + token }
                            : msg
                    ));
                },
                (data) => {
                    onConversationIdChange?.(data.conversation_id);
                    onLog?.('Ответ сгенерирован', 'growth');
                    onMetricsRefresh?.();
                },
                (error) => {
                    onLog?.(`Ошибка стрима: ${error}`, 'error');
                    setMessages(prev => prev.map(msg =>
                        msg.id === assistantId
                            ? { ...msg, content: msg.content + `\n\n⚠️ ${error}` }
                            : msg
                    ));
                },
                (thinkingEvent) => {
                    setQueueStatus('acquired'); // Thinking means we have slot
                    if (thinkingEvent.status === 'start') {
                        setIsThinking(true);
                        setThinkingStartTime(Date.now());
                        setThinkContent('');
                        setThinkExpanded(false);
                        onLog?.('🧠 MAX думает...', 'info');
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
        } catch (error: any) {
            if (error.name === 'AbortError') {
                onLog?.('Генерация остановлена пользователем', 'info');
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantId
                        ? { ...msg, content: msg.content + ' [Прервано]' }
                        : msg
                ));
            } else {
                onLog?.('Ошибка генерации', 'error');
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantId
                        ? { ...msg, content: `Ошибка: ${error.message || 'не удалось получить ответ'}` }
                        : msg
                ));
            }
        } finally {
            setIsGenerating(false);
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
        isThinking,
        thinkingStartTime,
        thinkContent,
        thinkExpanded,
        setThinkExpanded,
        lastConfidence,
        loadingModel,
        queueStatus,

        // Actions
        sendMessage,
        stopGeneration,
        clearMessages,
        loadMessages,
        toggleThinkExpanded,
    };
}
