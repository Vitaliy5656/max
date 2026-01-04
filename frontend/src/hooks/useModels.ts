/**
 * Models Hook — manages available models, selection, and modes.
 */
import { useState, useCallback } from 'react';
import * as api from '../api/client';

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

    const loadModelSelectionMode = useCallback(async () => {
        try {
            const response = await fetch('http://localhost:8000/api/config/model_selection_mode');
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

    const updateModelSelectionMode = useCallback(async (mode: 'manual' | 'auto') => {
        setModelSelectionMode(mode);
        try {
            await fetch('http://localhost:8000/api/config/model_selection_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            });
        } catch (error) {
            console.error('Failed to update mode:', error);
        }
    }, []);

    const getModelDisplayName = useCallback((model: string) => {
        return MODEL_NAMES[model] || model;
    }, []);

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
    };
}
