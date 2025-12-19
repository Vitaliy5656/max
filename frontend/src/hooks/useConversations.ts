/**
 * Conversations Hook — manages conversation list and current selection.
 * 
 * FIX: Added error handling and loading state to prevent UI freeze.
 */
import { useState, useCallback } from 'react';
import * as api from '../api/client';

export function useConversations() {
    const [conversations, setConversations] = useState<api.Conversation[]>([]);
    const [conversationId, setConversationId] = useState<string | null>(null);
    // FIX: Add loading and error states
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadConversations = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const convs = await api.getConversations();
            setConversations(convs);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Не удалось загрузить разговоры';
            setError(message);
            console.error('Failed to load conversations:', err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // FIX: Wrap in try/catch to prevent UI freeze
    const createConversation = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const conv = await api.createConversation();
            setConversationId(conv.id);
            await loadConversations();
            return conv;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Не удалось создать разговор';
            setError(message);
            console.error('Failed to create conversation:', err);
            // Return a fallback to prevent undefined
            return null;
        } finally {
            setIsLoading(false);
        }
    }, [loadConversations]);

    const selectConversation = useCallback((id: string) => {
        setConversationId(id);
        setError(null); // Clear error when selecting
    }, []);

    // FIX: Add clearError function
    const clearError = useCallback(() => {
        setError(null);
    }, []);

    return {
        conversations,
        conversationId,
        setConversationId,
        loadConversations,
        createConversation,
        selectConversation,
        // FIX: Expose new states
        isLoading,
        error,
        clearError,
    };
}

