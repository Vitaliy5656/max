/**
 * useResearchWebSocket - WebSocket connection management for Research module
 * ARCH-018: Extracted from useResearch.ts
 * 
 * Handles:
 * - WebSocket connection lifecycle
 * - Exponential backoff reconnection (FIX-008, FIX-009)
 * - Real-time research progress updates
 */
import { useState, useEffect, useCallback, useRef } from 'react';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export interface ResearchProgressMessage {
    type: 'initial_state' | 'research_progress';
    running_tasks?: any[];
    data?: any;
}

export interface UseResearchWebSocketOptions {
    apiBase: string;
    onMessage?: (message: ResearchProgressMessage) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onMaxRetriesReached?: () => void;
}

const MAX_RECONNECT_ATTEMPTS = 10;

export function useResearchWebSocket(options: UseResearchWebSocketOptions) {
    const { apiBase, onMessage, onConnect, onDisconnect, onMaxRetriesReached } = options;

    const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);
    const reconnectAttemptRef = useRef(0);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${apiBase}/ws/progress`;

        setConnectionStatus('connecting');
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[ResearchWS] Connected');
            setError(null);
            setConnectionStatus('connected');
            reconnectAttemptRef.current = 0;
            onConnect?.();
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data) as ResearchProgressMessage;
                onMessage?.(message);
            } catch (e) {
                console.error('[ResearchWS] Parse error:', e);
            }
        };

        ws.onclose = () => {
            console.log('[ResearchWS] Closed');
            setConnectionStatus('disconnected');
            onDisconnect?.();

            // Exponential backoff reconnection
            if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
                const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttemptRef.current));
                console.log(`[ResearchWS] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})`);
                reconnectAttemptRef.current++;

                reconnectTimeoutRef.current = window.setTimeout(() => {
                    connect();
                }, delay);
            } else {
                console.error('[ResearchWS] Max reconnect attempts reached');
                setError('Не удалось подключиться к серверу. Обновите страницу.');
                onMaxRetriesReached?.();
            }
        };

        ws.onerror = (e) => {
            console.error('[ResearchWS] Error:', e);
        };

        wsRef.current = ws;
    }, [apiBase, onMessage, onConnect, onDisconnect, onMaxRetriesReached]);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
    }, []);

    // Auto-connect on mount
    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return {
        connectionStatus,
        error,
        connect,
        disconnect,
        isConnected: connectionStatus === 'connected',
    };
}

export default useResearchWebSocket;
