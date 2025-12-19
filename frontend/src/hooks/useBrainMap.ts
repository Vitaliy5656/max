/**
 * useBrainMap - Hook for brain map data and state
 * 
 * Fetches brain map from API, manages loading/error states.
 */
import { useState, useEffect, useCallback } from 'react';
import type { BrainPointData } from '../components/brain/BrainPoint';
import type { Connection } from '../components/brain/ConstellationLines';

interface BrainMapData {
    points: BrainPointData[];
    connections: Connection[];
    level: number;
    count: number;
    temporal_range?: {
        min: string | null;
        max: string | null;
    };
    error?: string;
}

interface UseBrainMapResult {
    points: BrainPointData[];
    connections: Connection[];
    isLoading: boolean;
    error: string | null;
    level: number;
    temporalRange: { min: string | null; max: string | null };

    // Actions
    fetchBrainMap: (level?: number, topicId?: string) => Promise<void>;
    invalidateCache: () => Promise<void>;
}

export function useBrainMap(): UseBrainMapResult {
    const [points, setPoints] = useState<BrainPointData[]>([]);
    const [connections, setConnections] = useState<Connection[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [level, setLevel] = useState(0);
    const [temporalRange, setTemporalRange] = useState<{ min: string | null; max: string | null }>({ min: null, max: null });

    const fetchBrainMap = useCallback(async (newLevel: number = 0, topicId?: string) => {
        console.log('[BrainMap] Fetching brain map, level:', newLevel);
        setIsLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams({
                level: String(newLevel),
                include_connections: 'true'
            });

            if (topicId) {
                params.set('topic_id', topicId);
            }

            const url = `/api/research/brain-map?${params}`;
            console.log('[BrainMap] Fetching URL:', url);
            const response = await fetch(url);

            console.log('[BrainMap] Response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data: BrainMapData = await response.json();
            console.log('[BrainMap] Data received:', data);

            if (data.error) {
                // Not a fatal error - just means no data yet
                console.log('[BrainMap] API returned error:', data.error);
                setError(data.error);
                setPoints([]);
                setConnections([]);
            } else {
                console.log('[BrainMap] Points:', data.points?.length, 'Connections:', data.connections?.length);
                setPoints(data.points || []);
                setConnections(data.connections || []);
                setLevel(data.level);
                setTemporalRange(data.temporal_range || { min: null, max: null });
                setError(null);
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load brain map';
            console.error('[BrainMap] Fetch error:', message);
            setError(message);
            setPoints([]);
            setConnections([]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const invalidateCache = useCallback(async () => {
        try {
            await fetch('/api/research/brain-map/invalidate', { method: 'POST' });
            // Refetch after invalidation
            await fetchBrainMap(level);
        } catch (err) {
            console.error('Failed to invalidate brain map cache:', err);
        }
    }, [fetchBrainMap, level]);

    // Initial fetch on mount
    useEffect(() => {
        fetchBrainMap(0);
    }, [fetchBrainMap]);

    return {
        points,
        connections,
        isLoading,
        error,
        level,
        temporalRange,
        fetchBrainMap,
        invalidateCache
    };
}
