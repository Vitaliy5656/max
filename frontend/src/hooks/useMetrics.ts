/**
 * Metrics Hook — manages IQ and Empathy scores.
 */
import { useState, useCallback } from 'react';
import * as api from '../api/client';

export function useMetrics() {
    const [intelligence, setIntelligence] = useState(30);
    const [empathy, setEmpathy] = useState(30);

    const loadMetrics = useCallback(async () => {
        try {
            const metrics = await api.getMetrics();
            setIntelligence(metrics.iq.score);
            setEmpathy(metrics.empathy.score);
        } catch (error) {
            console.error('Failed to load metrics:', error);
        }
    }, []);

    return {
        intelligence,
        empathy,
        loadMetrics,
    };
}
