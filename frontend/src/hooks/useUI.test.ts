/**
 * Tests for useUI hook
 */
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useUI } from './useUI';

describe('useUI', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    describe('initial state', () => {
        it('should have correct initial values', () => {
            const { result } = renderHook(() => useUI());

            expect(result.current.activeTab).toBe('chat');
            expect(result.current.sidebarOpen).toBe(true);
            expect(result.current.darkMode).toBe(true);
            expect(result.current.systemLogs).toEqual([]);
        });
    });

    describe('activeTab', () => {
        it('should change active tab', () => {
            const { result } = renderHook(() => useUI());

            act(() => {
                result.current.setActiveTab('rag');
            });

            expect(result.current.activeTab).toBe('rag');
        });

        it('should accept all valid tab values', () => {
            const { result } = renderHook(() => useUI());
            const tabs: Array<'chat' | 'rag' | 'autogpt' | 'templates' | 'history'> =
                ['chat', 'rag', 'autogpt', 'templates', 'history'];

            tabs.forEach(tab => {
                act(() => {
                    result.current.setActiveTab(tab);
                });
                expect(result.current.activeTab).toBe(tab);
            });
        });
    });

    describe('sidebar', () => {
        it('should toggle sidebar', () => {
            const { result } = renderHook(() => useUI());

            expect(result.current.sidebarOpen).toBe(true);

            act(() => {
                result.current.toggleSidebar();
            });

            expect(result.current.sidebarOpen).toBe(false);

            act(() => {
                result.current.toggleSidebar();
            });

            expect(result.current.sidebarOpen).toBe(true);
        });

        it('should set sidebar directly', () => {
            const { result } = renderHook(() => useUI());

            act(() => {
                result.current.setSidebarOpen(false);
            });

            expect(result.current.sidebarOpen).toBe(false);
        });
    });

    describe('darkMode', () => {
        it('should toggle dark mode', () => {
            const { result } = renderHook(() => useUI());

            expect(result.current.darkMode).toBe(true);

            act(() => {
                result.current.toggleDarkMode();
            });

            expect(result.current.darkMode).toBe(false);
        });
    });

    describe('addLog', () => {
        it('should add log entries', () => {
            const { result } = renderHook(() => useUI());

            act(() => {
                result.current.addLog('Test message', 'info');
            });

            expect(result.current.systemLogs).toHaveLength(1);
            expect(result.current.systemLogs[0].text).toBe('Test message');
            expect(result.current.systemLogs[0].type).toBe('info');
        });

        it('should add multiple log entries', () => {
            const { result } = renderHook(() => useUI());

            act(() => {
                result.current.addLog('First', 'info');
                result.current.addLog('Second', 'error');
                result.current.addLog('Third', 'growth');
            });

            expect(result.current.systemLogs).toHaveLength(3);
        });

        it('should use default type info', () => {
            const { result } = renderHook(() => useUI());

            act(() => {
                result.current.addLog('Default type');
            });

            expect(result.current.systemLogs[0].type).toBe('info');
        });
    });
});
