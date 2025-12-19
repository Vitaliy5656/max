/**
 * Models Hook — manages available models, selection, and modes.
 * 
 * FIX: Replaced hardcoded URLs with API_BASE constant.
 */
import { useState, useCallback } from 'react';
import * as api from '../api/client';

// FIX: Use relative path to leverage Vite proxy
const API_BASE = '/api';

export const MODEL_NAMES: Record<string, string> = {
    'auto': '🧠 Auto (Smart)',
    'gpt-oss-20b': '🔥 GPT-OSS 20B',
    'deepseek-r1-distill-llama-8b': '🚀 DeepSeek R1 8B',
    'ministral-3-14b-reasoning': '🤔 Ministral 14B Reasoning',
    'mistral-community-pixtral-12b': '👁️ Pixtral 12B Vision',
};

export const THINKING_MODES = [
    { id: 'fast' as const, icon: '⚡', label: 'Быстро', color: 'text-yellow-400', bgActive: 'bg-yellow-500/20' },
    { id: 'standard' as const, icon: '🧠', label: 'Обычно', color: 'text-indigo-400', bgActive: 'bg-indigo-500/20' },
    { id: 'deep' as const, icon: '🤔', label: 'Глубоко', color: 'text-purple-400', bgActive: 'bg-purple-500/20' },
];

export function useModels() {
    const [availableModels, setAvailableModels] = useState([
        'auto',
        'gpt-oss-20b',
        'deepseek-r1-distill-llama-8b',
        'ministral-3-14b-reasoning',
        'mistral-community-pixtral-12b',
    ]);
    const [selectedModel, setSelectedModel] = useState('auto');
    const [thinkingMode, setThinkingMode] = useState<'fast' | 'standard' | 'deep'>('standard');
    const [modelSelectionMode, setModelSelectionMode] = useState<'manual' | 'auto'>('manual');
    const [modelDropdownOpen, setModelDropdownOpen] = useState(false);

    const loadModels = useCallback(async () => {
        try {
            const modelResponse = await api.getModels();
            if (modelResponse.models && modelResponse.models.length > 0) {
                setAvailableModels(['auto', ...modelResponse.models]);
            }
        } catch {
            // Keep defaults if model fetch fails
        }
    }, []);

    // FIX: Use API_BASE instead of hardcoded localhost
    const loadModelSelectionMode = useCallback(async () => {
        try {
            const response = await fetch(`${API_BASE}/config/model_selection_mode`);
            if (response.ok) {
                const data = await response.json();
                setModelSelectionMode(data.mode as 'manual' | 'auto');
                return data.mode;
            }
        } catch {
            // Keep default 'manual' mode
        }
        return 'manual';
    }, []);

    // FIX: Use API_BASE and add rollback on error
    const updateModelSelectionMode = useCallback(async (mode: 'manual' | 'auto') => {
        const previousMode = modelSelectionMode;
        setModelSelectionMode(mode); // Optimistic update
        try {
            const response = await fetch(`${API_BASE}/config/model_selection_mode`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            });
            if (!response.ok) {
                // Rollback on error
                setModelSelectionMode(previousMode);
                console.error('Failed to update mode: Server returned', response.status);
            }
        } catch (error) {
            // Rollback on error
            setModelSelectionMode(previousMode);
            console.error('Failed to update mode:', error);
        }
    }, [modelSelectionMode]);

    const getModelDisplayName = useCallback((model: string) => {
        return MODEL_NAMES[model] || model;
    }, []);

    // ============= Provider Switching (Phase 8) =============
    const [provider, setProvider] = useState<'lmstudio' | 'gemini'>(() => {
        try {
            const stored = localStorage.getItem('llm_provider');
            return (stored === 'gemini' || stored === 'lmstudio') ? stored : 'lmstudio';
        } catch { return 'lmstudio'; }
    });

    const loadProvider = useCallback(async () => {
        try {
            const data = await api.getProvider();
            setProvider(data.provider);
        } catch {
            // Keep default
        }
    }, []);

    const updateProvider = useCallback(async (newProvider: 'lmstudio' | 'gemini') => {
        const previous = provider;
        setProvider(newProvider); // Optimistic
        localStorage.setItem('llm_provider', newProvider);
        try {
            const result = await api.setProvider(newProvider);
            if (!result.success) {
                setProvider(previous);
                localStorage.setItem('llm_provider', previous);
            }
        } catch {
            setProvider(previous);
            localStorage.setItem('llm_provider', previous);
        }
    }, [provider]);

    return {
        availableModels,
        selectedModel,
        setSelectedModel,
        thinkingMode,
        setThinkingMode,
        modelSelectionMode,
        setModelSelectionMode,
        modelDropdownOpen,
        setModelDropdownOpen,
        loadModels,
        loadModelSelectionMode,
        updateModelSelectionMode,
        getModelDisplayName,
        // Provider switching
        provider,
        loadProvider,
        updateProvider,
    };
}
