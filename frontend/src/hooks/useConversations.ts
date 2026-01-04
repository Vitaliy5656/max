/**
 * Conversations Hook — manages conversation list and current selection.
 */
import { useState, useCallback } from 'react';
import * as api from '../api/client';

export function useConversations() {
    const [conversations, setConversations] = useState<api.Conversation[]>([]);
    const [conversationId, setConversationId] = useState<string | null>(null);

    const loadConversations = useCallback(async () => {
        try {
            const convs = await api.getConversations();
            setConversations(convs);
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    }, []);

    const createConversation = useCallback(async () => {
        const conv = await api.createConversation();
        setConversationId(conv.id);
        await loadConversations();
        return conv;
    }, [loadConversations]);

    const selectConversation = useCallback((id: string) => {
        setConversationId(id);
    }, []);

    return {
        conversations,
        conversationId,
        setConversationId,
        loadConversations,
        createConversation,
        selectConversation,
    };
}
