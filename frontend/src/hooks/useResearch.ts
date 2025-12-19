/**
 * Research Lab Hook
 * 
 * State management and API calls for research functionality.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// Types
export interface ResearchTask {
    id: string;
    topic: string;
    description: string;
    max_pages: number;
    topic_id?: string;
    status: 'pending' | 'running' | 'complete' | 'cancelled' | 'failed';
    progress: number;
    stage: string;
    detail: string;
    eta_seconds?: number;
    started_at?: string;
    completed_at?: string;
    error?: string;
}

export interface Topic {
    id: string;
    name: string;
    description: string;
    chunk_count: number;
    skill?: string;
    status: string;
    created_at: string;
    // Computed/optional fields for enhanced UI
    quality?: number;       // Computed on frontend
    tags?: string[];        // Future backend support
    facts?: string[];       // Future: extracted from chunks
    sources?: { url: string; title: string }[];  // Future
}

export interface QueueItem {
    id: string;
    topic: string;
    description: string;
    max_pages: number;
    status: 'queued' | 'running' | 'paused';
    progress: number;
    paused: boolean;
    taskId?: string;  // Linked backend task when running
}

export interface SearchResult {
    id: string;
    content: string;
    distance: number;
    metadata: Record<string, any>;
}

interface UseResearchOptions {
    onTaskComplete?: (task: ResearchTask) => void;
    onTaskFailed?: (task: ResearchTask, error: string) => void;
}

const API_BASE = '/api/research';

export function useResearch(options?: UseResearchOptions) {
    const [topics, setTopics] = useState<Topic[]>([]);
    const [tasks, setTasks] = useState<ResearchTask[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    // FIX: Add WebSocket connection status for UI feedback
    const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);
    // FIX-008 & FIX-009: Track reconnect attempts for exponential backoff
    const reconnectAttemptRef = useRef(0);
    const MAX_RECONNECT_ATTEMPTS = 10;

    // Connect to WebSocket for real-time updates
    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${API_BASE}/ws/progress`;

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[Research] WebSocket connected');
            setError(null);
            setConnectionStatus('connected');
            reconnectAttemptRef.current = 0; // FIX-008: Reset on successful connect
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                if (message.type === 'initial_state' && message.running_tasks) {
                    setTasks(prev => {
                        const newTasks = [...prev];
                        for (const task of message.running_tasks) {
                            const idx = newTasks.findIndex(t => t.id === task.id);
                            if (idx >= 0) {
                                newTasks[idx] = task;
                            } else {
                                newTasks.push(task);
                            }
                        }
                        return newTasks;
                    });
                }

                if (message.type === 'research_progress' && message.data) {
                    const taskData = message.data as ResearchTask;

                    setTasks(prev => {
                        const idx = prev.findIndex(t => t.id === taskData.id);
                        if (idx >= 0) {
                            const updated = [...prev];
                            updated[idx] = taskData;
                            return updated;
                        }
                        return [...prev, taskData];
                    });

                    // Handle completion
                    if (taskData.status === 'complete') {
                        options?.onTaskComplete?.(taskData);
                        // Refresh topics list
                        fetchTopics();
                    }

                    if (taskData.status === 'failed') {
                        options?.onTaskFailed?.(taskData, taskData.error || 'Unknown error');
                    }
                }
            } catch (e) {
                console.error('[Research] WebSocket parse error:', e);
            }
        };

        ws.onclose = () => {
            console.log('[Research] WebSocket closed');
            setConnectionStatus('disconnected');

            // FIX-008 & FIX-009: Exponential backoff with max attempts
            if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
                const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttemptRef.current));
                console.log(`[Research] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})`);
                reconnectAttemptRef.current++;

                reconnectTimeoutRef.current = window.setTimeout(() => {
                    setConnectionStatus('connecting');
                    connectWebSocket();
                }, delay);
            } else {
                console.error('[Research] Max reconnect attempts reached, giving up');
                setError('Не удалось подключиться к серверу. Обновите страницу.');
            }
        };

        ws.onerror = (e) => {
            console.error('[Research] WebSocket error:', e);
        };

        wsRef.current = ws;
    }, [options]);

    // Cleanup on unmount
    useEffect(() => {
        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [connectWebSocket]);

    // Fetch topics
    const fetchTopics = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/topics`);
            if (!res.ok) throw new Error('Failed to fetch topics');
            const data = await res.json();
            setTopics(data);
        } catch (e) {
            console.error('[Research] Fetch topics error:', e);
            setError(e instanceof Error ? e.message : 'Unknown error');
        }
    }, []);

    // Fetch tasks
    const fetchTasks = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/tasks`);
            if (!res.ok) throw new Error('Failed to fetch tasks');
            const data = await res.json();
            setTasks(data);
        } catch (e) {
            console.error('[Research] Fetch tasks error:', e);
        }
    }, []);

    // Initial load
    useEffect(() => {
        fetchTopics();
        fetchTasks();
    }, [fetchTopics, fetchTasks]);

    // Start new research
    const startResearch = useCallback(async (topic: string, description: string, maxPages = 10) => {
        setIsLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, description, max_pages: maxPages })
            });

            if (!res.ok) {
                const data = await res.json();
                if (res.status === 409) {
                    throw new Error(data.detail || 'Research already in progress');
                }
                throw new Error(data.detail || 'Failed to start research');
            }

            const data = await res.json();

            // Add pending task
            setTasks(prev => [...prev, {
                id: data.task_id,
                topic,
                description,
                max_pages: maxPages,
                status: 'pending',
                progress: 0,
                stage: 'Starting...',
                detail: ''
            }]);

            return data.task_id;
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Unknown error';
            setError(message);
            throw e;
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Cancel research
    const cancelResearch = useCallback(async (taskId: string) => {
        if (!window.confirm('Cancel this research? Progress will be lost.')) {
            return false;
        }

        try {
            const res = await fetch(`${API_BASE}/cancel/${taskId}`, { method: 'POST' });
            if (!res.ok) throw new Error('Failed to cancel');

            setTasks(prev => prev.map(t =>
                t.id === taskId ? { ...t, status: 'cancelled' } : t
            ));

            return true;
        } catch (e) {
            console.error('[Research] Cancel error:', e);
            return false;
        }
    }, []);

    // Refresh topic
    const refreshTopic = useCallback(async (topicId: string, maxPages = 10) => {
        setIsLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/topics/${topicId}/refresh?max_pages=${maxPages}`, {
                method: 'POST'
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to refresh');
            }

            const data = await res.json();
            return data.task_id;
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Unknown error';
            setError(message);
            throw e;
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Delete topic
    const deleteTopic = useCallback(async (topicId: string) => {
        if (!window.confirm('Delete this topic and all its data?')) {
            return false;
        }

        try {
            const res = await fetch(`${API_BASE}/topics/${topicId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete');

            setTopics(prev => prev.filter(t => t.id !== topicId));
            return true;
        } catch (e) {
            console.error('[Research] Delete error:', e);
            return false;
        }
    }, []);

    // Search within topic
    const searchTopic = useCallback(async (topicId: string, query: string, topK = 5): Promise<SearchResult[]> => {
        try {
            const res = await fetch(`${API_BASE}/topics/${topicId}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, top_k: topK })
            });

            if (!res.ok) throw new Error('Search failed');

            const data = await res.json();
            return data.results || [];
        } catch (e) {
            console.error('[Research] Search error:', e);
            return [];
        }
    }, []);

    // Get topic skill
    const getTopicSkill = useCallback(async (topicId: string): Promise<string | null> => {
        try {
            const res = await fetch(`${API_BASE}/topics/${topicId}/skill`);
            if (!res.ok) return null;

            const data = await res.json();
            return data.skill || null;
        } catch {
            return null;
        }
    }, []);

    // ============================================
    // RESEARCH QUEUE SYSTEM
    // ============================================
    const MAX_CONCURRENT_SLOTS = 2;
    const QUEUE_STORAGE_KEY = 'research_queue';

    // Queue state with localStorage persistence
    const [researchQueue, setResearchQueue] = useState<QueueItem[]>(() => {
        try {
            const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    });

    // Persist queue to localStorage
    useEffect(() => {
        try {
            localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(researchQueue));
        } catch (e) {
            console.error('[Research] Failed to persist queue:', e);
        }
    }, [researchQueue]);

    // Auto-start next queued item when slot frees up
    useEffect(() => {
        const runningCount = researchQueue.filter(q => q.status === 'running' && !q.paused).length;
        const nextQueued = researchQueue.find(q => q.status === 'queued');

        if (runningCount < MAX_CONCURRENT_SLOTS && nextQueued) {
            // Start next item
            (async () => {
                try {
                    const taskId = await startResearch(
                        nextQueued.topic,
                        nextQueued.description,
                        nextQueued.max_pages
                    );
                    setResearchQueue(curr => curr.map(q =>
                        q.id === nextQueued.id
                            ? { ...q, status: 'running' as const, taskId }
                            : q
                    ));
                } catch (e) {
                    console.error('[Research] Auto-start failed:', e);
                    // Remove failed item from queue
                    setResearchQueue(curr => curr.filter(q => q.id !== nextQueued.id));
                }
            })();
        }
    }, [researchQueue, startResearch]);

    // Sync queue with running tasks (update progress, detect completion)
    useEffect(() => {
        setResearchQueue(curr => curr.map(qItem => {
            if (qItem.status !== 'running' || !qItem.taskId) return qItem;

            const task = tasks.find(t => t.id === qItem.taskId);
            if (!task) return qItem;

            // Update progress
            if (task.status === 'complete' || task.status === 'cancelled' || task.status === 'failed') {
                // Remove completed from queue
                return null as any;
            }

            return { ...qItem, progress: task.progress };
        }).filter(Boolean));
    }, [tasks]);

    // Add to queue
    const addToQueue = useCallback((topic: string, description: string, maxPages = 10) => {
        const newItem: QueueItem = {
            id: Math.random().toString(36).substr(2, 9),
            topic,
            description,
            max_pages: maxPages,
            status: 'queued',
            progress: 0,
            paused: false
        };
        setResearchQueue(curr => [...curr, newItem]);
        return newItem.id;
    }, []);

    // Remove from queue
    const removeFromQueue = useCallback(async (id: string) => {
        const item = researchQueue.find(q => q.id === id);
        if (item?.status === 'running' && item.taskId) {
            // Cancel backend task first
            await cancelResearch(item.taskId);
        }
        setResearchQueue(curr => curr.filter(q => q.id !== id));
    }, [researchQueue, cancelResearch]);

    // Pause queue item (cancels backend if running)
    const pauseQueueItem = useCallback(async (id: string) => {
        const item = researchQueue.find(q => q.id === id);
        if (item?.status === 'running' && item.taskId) {
            await cancelResearch(item.taskId);
        }
        setResearchQueue(curr => curr.map(q =>
            q.id === id ? { ...q, status: 'paused' as const, paused: true, taskId: undefined } : q
        ));
    }, [researchQueue, cancelResearch]);

    // Resume queue item
    const resumeQueueItem = useCallback((id: string) => {
        setResearchQueue(curr => curr.map(q =>
            q.id === id ? { ...q, status: 'queued' as const, paused: false } : q
        ));
    }, []);

    // Move up in queue
    const moveQueueUp = useCallback((id: string) => {
        setResearchQueue(curr => {
            const queued = curr.filter(q => q.status === 'queued');
            const others = curr.filter(q => q.status !== 'queued');
            const idx = queued.findIndex(q => q.id === id);
            if (idx <= 0) return curr;
            [queued[idx - 1], queued[idx]] = [queued[idx], queued[idx - 1]];
            return [...others, ...queued];
        });
    }, []);

    // Move down in queue
    const moveQueueDown = useCallback((id: string) => {
        setResearchQueue(curr => {
            const queued = curr.filter(q => q.status === 'queued');
            const others = curr.filter(q => q.status !== 'queued');
            const idx = queued.findIndex(q => q.id === id);
            if (idx < 0 || idx >= queued.length - 1) return curr;
            [queued[idx], queued[idx + 1]] = [queued[idx + 1], queued[idx]];
            return [...others, ...queued];
        });
    }, []);

    // Re-research topic (add to queue)
    const reResearchTopic = useCallback((topic: Topic) => {
        return addToQueue(`${topic.name} (дополнение)`, topic.description, 10);
    }, [addToQueue]);

    // ============================================
    // COMPUTED VALUES
    // ============================================

    // Calculate quality for topics (frontend-computed)
    const calculateQuality = (topic: Topic): number => {
        const hasSkill = topic.skill && topic.skill.length > 100;
        const chunksScore = Math.min(topic.chunk_count / 50, 1);
        return hasSkill ? chunksScore * 0.7 + 0.3 : chunksScore * 0.5;
    };

    // Enrich topics with computed quality
    const enrichedTopics = topics.map(t => ({
        ...t,
        quality: t.quality ?? calculateQuality(t)
    }));

    const runningTasks = tasks.filter(t => t.status === 'running' || t.status === 'pending');
    const completedTopics = enrichedTopics.filter(t => t.status === 'complete');
    const incompleteTopics = enrichedTopics.filter(t => t.status !== 'complete');

    // Stats computed
    const stats = {
        totalTopics: enrichedTopics.length,
        totalChunks: enrichedTopics.reduce((acc, t) => acc + t.chunk_count, 0),
        completeCount: completedTopics.length,
        avgQuality: enrichedTopics.length > 0
            ? enrichedTopics.reduce((acc, t) => acc + (t.quality || 0), 0) / enrichedTopics.length
            : 0
    };

    // Activity feed from completed/failed tasks
    const activityFeed = tasks
        .filter(t => t.status === 'complete' || t.status === 'failed')
        .slice(-10)
        .reverse()
        .map(t => ({
            topic: t.topic,
            action: t.status as 'complete' | 'failed',
            time: t.completed_at ? new Date(t.completed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : ''
        }));

    return {
        // State
        topics: enrichedTopics,
        tasks,
        runningTasks,
        completedTopics,
        incompleteTopics,
        isLoading,
        error,
        stats,
        activityFeed,
        connectionStatus, // FIX: Expose WebSocket status for UI

        // Queue
        researchQueue,
        maxConcurrentSlots: MAX_CONCURRENT_SLOTS,
        addToQueue,
        removeFromQueue,
        pauseQueueItem,
        resumeQueueItem,
        moveQueueUp,
        moveQueueDown,
        reResearchTopic,

        // Actions
        startResearch,
        cancelResearch,
        refreshTopic,
        deleteTopic,
        searchTopic,
        getTopicSkill,
        fetchTopics,
        fetchTasks
    };
}
