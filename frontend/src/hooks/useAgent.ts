/**
 * Agent Hook — manages AutoGPT agent state.
 * 
 * FIX: Added interval cleanup on unmount to prevent memory leak.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import * as api from '../api/client';

export interface UseAgentOptions {
    onLog?: (text: string, type?: 'info' | 'error' | 'growth') => void;
    onMetricsRefresh?: () => void;
}

export function useAgent(options: UseAgentOptions = {}) {
    const { onLog, onMetricsRefresh } = options;

    const [agentGoal, setAgentGoal] = useState('');
    const [agentRunning, setAgentRunning] = useState(false);
    const [agentSteps, setAgentSteps] = useState<api.AgentStep[]>([]);
    const [agentConfirmModal, setAgentConfirmModal] = useState(false);
    const [agentFailed, setAgentFailed] = useState(false);

    // FIX: Store interval ref for cleanup
    const pollIntervalRef = useRef<number | null>(null);

    // FIX: Cleanup interval on unmount to prevent memory leak
    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        };
    }, []);

    const requestAgent = useCallback(() => {
        if (!agentGoal.trim() || agentRunning) return;
        setAgentConfirmModal(true);
    }, [agentGoal, agentRunning]);

    const confirmAgent = useCallback(async () => {
        setAgentConfirmModal(false);
        if (!agentGoal.trim() || agentRunning) return;

        setAgentRunning(true);
        setAgentFailed(false);
        onLog?.('Автономный агент запущен', 'growth');

        try {
            await api.startAgent(agentGoal, 20);

            // FIX: Store interval ID in ref for cleanup
            pollIntervalRef.current = window.setInterval(async () => {
                try {
                    const status = await api.getAgentStatus();
                    setAgentSteps(status.steps);

                    if (!status.running) {
                        if (pollIntervalRef.current) {
                            clearInterval(pollIntervalRef.current);
                            pollIntervalRef.current = null;
                        }
                        setAgentRunning(false);

                        const hasFailed = status.steps?.some((s: { status: string }) => s.status === 'failed');
                        if (hasFailed) {
                            setAgentFailed(true);
                            onLog?.('Агент не выполнил задачу', 'error');
                        } else {
                            onLog?.('Агент выполнил задачу', 'growth');
                        }
                        onMetricsRefresh?.();
                    }
                } catch {
                    if (pollIntervalRef.current) {
                        clearInterval(pollIntervalRef.current);
                        pollIntervalRef.current = null;
                    }
                    setAgentRunning(false);
                    setAgentFailed(true);
                    onLog?.('Ошибка при проверке статуса агента', 'error');
                }
            }, 2000);
        } catch (error) {
            setAgentRunning(false);
            setAgentFailed(true);
            onLog?.('Ошибка запуска агента', 'error');
        }
    }, [agentGoal, agentRunning, onLog, onMetricsRefresh]);

    const cancelAgent = useCallback(() => {
        setAgentConfirmModal(false);
    }, []);

    // FIX: Add proper stop function that cancels backend task and clears interval
    const stopAgent = useCallback(async () => {
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
        }
        try {
            await api.stopAgent();
            onLog?.('Агент остановлен', 'info');
        } catch {
            onLog?.('Ошибка остановки агента', 'error');
        }
        setAgentRunning(false);
    }, [onLog]);

    return {
        agentGoal,
        setAgentGoal,
        agentRunning,
        agentSteps,
        agentConfirmModal,
        agentFailed,
        requestAgent,
        confirmAgent,
        cancelAgent,
        stopAgent, // FIX: Expose stop function
    };
}

