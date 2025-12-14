/**
 * Agent Hook — manages AutoGPT agent state.
 */
import { useState, useCallback } from 'react';
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

            const pollInterval = setInterval(async () => {
                try {
                    const status = await api.getAgentStatus();
                    setAgentSteps(status.steps);

                    if (!status.running) {
                        clearInterval(pollInterval);
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
                    clearInterval(pollInterval);
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
    };
}
