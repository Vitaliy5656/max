/**
 * Metrics Hook — manages IQ and Empathy scores.
 * 
 * FIX: Added onError callback for UI toast instead of console.error.
 */
import { useState, useCallback } from 'react';
import * as api from '../api/client';

export interface UseMetricsOptions {
    onError?: (message: string) => void;
}

export function useMetrics(options: UseMetricsOptions = {}) {
    const { onError } = options;
    const [intelligence, setIntelligence] = useState(30);
    const [empathy, setEmpathy] = useState(30);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadMetrics = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const metrics = await api.getMetrics();
            setIntelligence(metrics.iq.score);
            setEmpathy(metrics.empathy.score);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Не удалось загрузить метрики';
            setError(message);
            // FIX: Call onError callback for toast, but still log for debugging
            onError?.(message);
            console.error('Failed to load metrics:', err);
        } finally {
            setIsLoading(false);
        }
    }, [onError]);

    return {
        intelligence,
        empathy,
        loadMetrics,
        isLoading,
        error,
    };
}

