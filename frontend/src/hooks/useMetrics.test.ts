/**
 * Tests for useMetrics hook - simplified
 */
import { renderHook } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useMetrics } from './useMetrics';

describe('useMetrics', () => {
    describe('initial state', () => {
        it('should have default IQ score of 30', () => {
            const { result } = renderHook(() => useMetrics());
            expect(result.current.intelligence).toBe(30);
        });

        it('should have default empathy score of 30', () => {
            const { result } = renderHook(() => useMetrics());
            expect(result.current.empathy).toBe(30);
        });

        it('should expose loadMetrics function', () => {
            const { result } = renderHook(() => useMetrics());
            expect(typeof result.current.loadMetrics).toBe('function');
        });
    });
});
