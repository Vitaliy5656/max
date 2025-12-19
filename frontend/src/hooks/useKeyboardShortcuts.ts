/**
 * useKeyboardShortcuts - Global keyboard shortcuts hook
 * UX-001: Implements keyboard navigation for better UX
 * 
 * Shortcuts:
 * - Ctrl+1-5: Switch between tabs
 * - Ctrl+K: Open command palette (TODO)
 * - Escape: Close modals
 */
import { useEffect, useCallback } from 'react';

export type TabType = 'chat' | 'rag' | 'research' | 'autogpt' | 'templates' | 'history';

interface UseKeyboardShortcutsOptions {
    onTabChange?: (tab: TabType) => void;
    onEscape?: () => void;
    onCommandPalette?: () => void;
    enabled?: boolean;
}

const TAB_SHORTCUTS: Record<string, TabType> = {
    '1': 'chat',
    '2': 'rag',
    '3': 'research',
    '4': 'autogpt',
    '5': 'templates',
    '6': 'history',
};

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}) {
    const { onTabChange, onEscape, onCommandPalette, enabled = true } = options;

    const handleKeyDown = useCallback((event: KeyboardEvent) => {
        if (!enabled) return;

        // Don't trigger if user is typing in an input
        const target = event.target as HTMLElement;
        const isTyping = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

        // Escape always works
        if (event.key === 'Escape') {
            onEscape?.();
            return;
        }

        // Ctrl/Cmd + K for command palette
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            onCommandPalette?.();
            return;
        }

        // Only process shortcuts when not typing
        if (isTyping) return;

        // Ctrl/Cmd + 1-6 for tab switching
        if ((event.ctrlKey || event.metaKey) && TAB_SHORTCUTS[event.key]) {
            event.preventDefault();
            onTabChange?.(TAB_SHORTCUTS[event.key]);
            return;
        }

        // Alt + 1-6 as alternative (more natural on Windows)
        if (event.altKey && TAB_SHORTCUTS[event.key]) {
            event.preventDefault();
            onTabChange?.(TAB_SHORTCUTS[event.key]);
            return;
        }
    }, [enabled, onTabChange, onEscape, onCommandPalette]);

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);
}

export default useKeyboardShortcuts;
