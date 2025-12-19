/**
 * useResearchQueue - Queue management for Research module
 * ARCH-017: Extracted from useResearch.ts
 * 
 * Handles:
 * - Queue state with localStorage persistence
 * - Auto-start when slots free up
 * - Pause/Resume/Move operations
 * - MAX_CONCURRENT_SLOTS limit
 */
import { useState, useEffect, useCallback } from 'react';

export interface QueueItem {
    id: string;
    topic: string;
    description: string;
    max_pages: number;
    status: 'queued' | 'running' | 'paused';
    progress: number;
    paused: boolean;
    taskId?: string;
}

export interface ResearchTask {
    id: string;
    status: 'pending' | 'running' | 'complete' | 'cancelled' | 'failed';
    progress: number;
}

interface UseResearchQueueOptions {
    maxConcurrentSlots?: number;
    storageKey?: string;
    tasks: ResearchTask[];
    onStartResearch: (topic: string, description: string, maxPages: number) => Promise<string>;
    onCancelResearch: (taskId: string) => Promise<boolean>;
}

const DEFAULT_MAX_SLOTS = 2;
const DEFAULT_STORAGE_KEY = 'research_queue';

export function useResearchQueue(options: UseResearchQueueOptions) {
    const {
        maxConcurrentSlots = DEFAULT_MAX_SLOTS,
        storageKey = DEFAULT_STORAGE_KEY,
        tasks,
        onStartResearch,
        onCancelResearch,
    } = options;

    // Queue state with localStorage persistence
    const [queue, setQueue] = useState<QueueItem[]>(() => {
        try {
            const stored = localStorage.getItem(storageKey);
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    });

    // Persist queue to localStorage
    useEffect(() => {
        try {
            localStorage.setItem(storageKey, JSON.stringify(queue));
        } catch (e) {
            console.error('[ResearchQueue] Failed to persist:', e);
        }
    }, [queue, storageKey]);

    // Auto-start next queued item when slot frees up
    useEffect(() => {
        const runningCount = queue.filter(q => q.status === 'running' && !q.paused).length;
        const nextQueued = queue.find(q => q.status === 'queued');

        if (runningCount < maxConcurrentSlots && nextQueued) {
            (async () => {
                try {
                    const taskId = await onStartResearch(
                        nextQueued.topic,
                        nextQueued.description,
                        nextQueued.max_pages
                    );
                    setQueue(curr => curr.map(q =>
                        q.id === nextQueued.id
                            ? { ...q, status: 'running' as const, taskId }
                            : q
                    ));
                } catch (e) {
                    console.error('[ResearchQueue] Auto-start failed:', e);
                    setQueue(curr => curr.filter(q => q.id !== nextQueued.id));
                }
            })();
        }
    }, [queue, maxConcurrentSlots, onStartResearch]);

    // Sync queue with running tasks
    useEffect(() => {
        setQueue(curr => curr.map(qItem => {
            if (qItem.status !== 'running' || !qItem.taskId) return qItem;

            const task = tasks.find(t => t.id === qItem.taskId);
            if (!task) return qItem;

            if (task.status === 'complete' || task.status === 'cancelled' || task.status === 'failed') {
                return null as any;
            }

            return { ...qItem, progress: task.progress };
        }).filter(Boolean));
    }, [tasks]);

    // Add to queue
    const addToQueue = useCallback((topic: string, description: string, maxPages = 10): string => {
        const newItem: QueueItem = {
            id: Math.random().toString(36).substr(2, 9),
            topic,
            description,
            max_pages: maxPages,
            status: 'queued',
            progress: 0,
            paused: false
        };
        setQueue(curr => [...curr, newItem]);
        return newItem.id;
    }, []);

    // Remove from queue
    const removeFromQueue = useCallback(async (id: string) => {
        const item = queue.find(q => q.id === id);
        if (item?.status === 'running' && item.taskId) {
            await onCancelResearch(item.taskId);
        }
        setQueue(curr => curr.filter(q => q.id !== id));
    }, [queue, onCancelResearch]);

    // Pause queue item
    const pauseItem = useCallback(async (id: string) => {
        const item = queue.find(q => q.id === id);
        if (item?.status === 'running' && item.taskId) {
            await onCancelResearch(item.taskId);
        }
        setQueue(curr => curr.map(q =>
            q.id === id ? { ...q, status: 'paused' as const, paused: true, taskId: undefined } : q
        ));
    }, [queue, onCancelResearch]);

    // Resume queue item
    const resumeItem = useCallback((id: string) => {
        setQueue(curr => curr.map(q =>
            q.id === id ? { ...q, status: 'queued' as const, paused: false } : q
        ));
    }, []);

    // Move up in queue
    const moveUp = useCallback((id: string) => {
        setQueue(curr => {
            const queued = curr.filter(q => q.status === 'queued');
            const others = curr.filter(q => q.status !== 'queued');
            const idx = queued.findIndex(q => q.id === id);
            if (idx <= 0) return curr;
            [queued[idx - 1], queued[idx]] = [queued[idx], queued[idx - 1]];
            return [...others, ...queued];
        });
    }, []);

    // Move down in queue
    const moveDown = useCallback((id: string) => {
        setQueue(curr => {
            const queued = curr.filter(q => q.status === 'queued');
            const others = curr.filter(q => q.status !== 'queued');
            const idx = queued.findIndex(q => q.id === id);
            if (idx < 0 || idx >= queued.length - 1) return curr;
            [queued[idx], queued[idx + 1]] = [queued[idx + 1], queued[idx]];
            return [...others, ...queued];
        });
    }, []);

    // Clear completed items
    const clearCompleted = useCallback(() => {
        setQueue(curr => curr.filter(q => q.status !== 'queued' && q.status !== 'paused'));
    }, []);

    return {
        queue,
        maxSlots: maxConcurrentSlots,
        runningCount: queue.filter(q => q.status === 'running').length,
        queuedCount: queue.filter(q => q.status === 'queued').length,
        addToQueue,
        removeFromQueue,
        pauseItem,
        resumeItem,
        moveUp,
        moveDown,
        clearCompleted,
    };
}

export default useResearchQueue;
