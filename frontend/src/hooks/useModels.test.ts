/**
 * Tests for useModels hook
 */
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useModels, THINKING_MODES, MODEL_NAMES } from './useModels';

// Mock the API client
vi.mock('../../api/client', () => ({
    getModels: vi.fn().mockResolvedValue({ models: ['model1', 'model2'] }),
    getModelSelectionMode: vi.fn().mockResolvedValue({ mode: 'manual' }),
    setModelSelectionMode: vi.fn().mockResolvedValue({ success: true }),
}));

describe('useModels', () => {
    describe('initial state', () => {
        it('should have correct initial values', () => {
            const { result } = renderHook(() => useModels());

            expect(result.current.selectedModel).toBe('auto');
            expect(result.current.thinkingMode).toBe('standard');
            expect(result.current.modelSelectionMode).toBe('manual');
            expect(result.current.modelDropdownOpen).toBe(false);
        });

        it('should have default available models', () => {
            const { result } = renderHook(() => useModels());

            expect(result.current.availableModels).toContain('auto');
            expect(result.current.availableModels.length).toBeGreaterThan(0);
        });
    });

    describe('selectedModel', () => {
        it('should change selected model', () => {
            const { result } = renderHook(() => useModels());

            act(() => {
                result.current.setSelectedModel('gpt-oss-20b');
            });

            expect(result.current.selectedModel).toBe('gpt-oss-20b');
        });
    });

    describe('thinkingMode', () => {
        it('should change thinking mode', () => {
            const { result } = renderHook(() => useModels());

            act(() => {
                result.current.setThinkingMode('deep');
            });

            expect(result.current.thinkingMode).toBe('deep');
        });

        it('should accept all valid thinking modes', () => {
            const { result } = renderHook(() => useModels());
            const modes: Array<'fast' | 'standard' | 'deep'> = ['fast', 'standard', 'deep'];

            modes.forEach(mode => {
                act(() => {
                    result.current.setThinkingMode(mode);
                });
                expect(result.current.thinkingMode).toBe(mode);
            });
        });
    });

    describe('modelDropdownOpen', () => {
        it('should toggle dropdown', () => {
            const { result } = renderHook(() => useModels());

            expect(result.current.modelDropdownOpen).toBe(false);

            act(() => {
                result.current.setModelDropdownOpen(true);
            });

            expect(result.current.modelDropdownOpen).toBe(true);
        });
    });

    describe('getModelDisplayName', () => {
        it('should return display name for known models', () => {
            const { result } = renderHook(() => useModels());

            expect(result.current.getModelDisplayName('auto')).toContain('Auto');
        });

        it('should return model id for unknown models', () => {
            const { result } = renderHook(() => useModels());

            expect(result.current.getModelDisplayName('unknown-model')).toBe('unknown-model');
        });
    });
});

describe('THINKING_MODES constant', () => {
    it('should have 3 modes', () => {
        expect(THINKING_MODES).toHaveLength(3);
    });

    it('should have correct structure', () => {
        THINKING_MODES.forEach(mode => {
            expect(mode).toHaveProperty('id');
            expect(mode).toHaveProperty('icon');
            expect(mode).toHaveProperty('label');
            expect(mode).toHaveProperty('color');
            expect(mode).toHaveProperty('bgActive');
        });
    });

    it('should include fast, standard, deep', () => {
        const ids = THINKING_MODES.map(m => m.id);
        expect(ids).toContain('fast');
        expect(ids).toContain('standard');
        expect(ids).toContain('deep');
    });
});

describe('MODEL_NAMES constant', () => {
    it('should have auto key', () => {
        expect(MODEL_NAMES).toHaveProperty('auto');
    });

    it('should return display names as strings', () => {
        Object.values(MODEL_NAMES).forEach(name => {
            expect(typeof name).toBe('string');
        });
    });
});
