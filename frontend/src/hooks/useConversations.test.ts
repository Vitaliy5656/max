/**
 * Tests for useConversations hook - simplified
 */
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useConversations } from './useConversations';

describe('useConversations', () => {
    describe('initial state', () => {
        it('should have empty conversations initially', () => {
            const { result } = renderHook(() => useConversations());
            expect(result.current.conversations).toEqual([]);
        });

        it('should have null conversationId initially', () => {
            const { result } = renderHook(() => useConversations());
            expect(result.current.conversationId).toBeNull();
        });
    });

    describe('conversationId', () => {
        it('should set conversation id', () => {
            const { result } = renderHook(() => useConversations());

            act(() => {
                result.current.setConversationId('conv-123');
            });

            expect(result.current.conversationId).toBe('conv-123');
        });

        it('should allow null conversation id', () => {
            const { result } = renderHook(() => useConversations());

            act(() => {
                result.current.setConversationId('conv-123');
            });

            act(() => {
                result.current.setConversationId(null);
            });

            expect(result.current.conversationId).toBeNull();
        });
    });

    describe('selectConversation', () => {
        it('should select conversation by id', () => {
            const { result } = renderHook(() => useConversations());

            act(() => {
                result.current.selectConversation('selected-conv');
            });

            expect(result.current.conversationId).toBe('selected-conv');
        });
    });

    describe('API functions', () => {
        it('should expose loadConversations function', () => {
            const { result } = renderHook(() => useConversations());
            expect(typeof result.current.loadConversations).toBe('function');
        });

        it('should expose createConversation function', () => {
            const { result } = renderHook(() => useConversations());
            expect(typeof result.current.createConversation).toBe('function');
        });
    });
});
