import { useRef, useEffect, useState } from 'react';
import { Search, ChevronDown, Check, Sun, Moon, Menu, Trash2 } from 'lucide-react';
import type { ThinkingModeConfig } from './types';

interface HeaderProps {
    activeTab: 'chat' | 'rag' | 'autogpt' | 'templates' | 'history';
    onMenuClick: () => void;
    // Model selection
    selectedModel: string;
    availableModels: string[];
    modelNames: Record<string, string>;
    modelDropdownOpen: boolean;
    setModelDropdownOpen: (open: boolean) => void;
    onModelSelect: (model: string) => void;
    // Thinking modes
    thinkingMode: 'fast' | 'standard' | 'deep';
    thinkingModes: ThinkingModeConfig[];
    onThinkingModeChange: (mode: 'fast' | 'standard' | 'deep') => void;
    // Model selection mode
    modelSelectionMode: 'manual' | 'auto';
    onModelSelectionModeChange: (mode: 'manual' | 'auto') => void;
    // Search
    searchQuery: string;
    onSearchChange: (query: string) => void;
    // Backup
    backupStatus: 'synced' | 'syncing' | 'error' | 'unknown';
    // Theme
    darkMode: boolean;
    onToggleDarkMode: () => void;
}

const IconButton = ({ icon, tooltip, onClick, label }: { icon: React.ReactNode; tooltip?: string; onClick?: () => void; label?: string }) => (
    <div className="group relative flex items-center justify-center">
        <button
            onClick={onClick}
            className="p-2 rounded-lg transition-all duration-200 active:scale-95 text-zinc-400 hover:text-white hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            aria-label={label || tooltip}
        >
            {icon}
        </button>
        {tooltip && (
            <span className="absolute top-10 scale-0 transition-all duration-200 rounded-lg bg-zinc-800 px-3 py-1.5 text-xs font-medium text-white group-hover:scale-100 z-50 whitespace-nowrap border border-zinc-700 shadow-xl pointer-events-none">
                {tooltip}
            </span>
        )}
    </div>
);

/**
 * Header with model selector, thinking modes, and search.
 */
export function Header({
    activeTab,
    onMenuClick,
    selectedModel,
    availableModels,
    modelNames,
    modelDropdownOpen,
    setModelDropdownOpen,
    onModelSelect,
    thinkingMode,
    thinkingModes,
    onThinkingModeChange,
    modelSelectionMode,
    onModelSelectionModeChange,
    searchQuery,
    onSearchChange,
    backupStatus,
    darkMode,
    onToggleDarkMode
}: HeaderProps) {
    const modelDropdownRef = useRef<HTMLDivElement>(null);

    // Close model dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
                setModelDropdownOpen(false);
            }
        };
        if (modelDropdownOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [modelDropdownOpen, setModelDropdownOpen]);

    return (
        <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-white/5 bg-[#09090b]/80 backdrop-blur-xl z-10 sticky top-0">
            <div className="flex items-center gap-3">
                <button onClick={onMenuClick} className="lg:hidden p-2 -ml-2 text-zinc-400 hover:text-white rounded-lg">
                    <Menu size={20} />
                </button>

                {activeTab === 'chat' ? (
                    <div className="relative" ref={modelDropdownRef}>
                        <button
                            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                            className="flex items-center gap-2 cursor-pointer px-2 py-1.5 rounded-lg hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                            aria-label="Выбрать модель"
                            aria-expanded={modelDropdownOpen}
                        >
                            <span className="text-lg font-semibold text-white/90">MAX AI</span>
                            <span className="text-zinc-600">/</span>
                            <div className="flex items-center gap-2 text-sm text-zinc-300">
                                <span>{modelNames[selectedModel] || selectedModel}</span>
                                <ChevronDown size={14} className={`text-zinc-500 transition-transform ${modelDropdownOpen ? 'rotate-180' : ''}`} />
                            </div>
                        </button>
                        {modelDropdownOpen && (
                            <div className="absolute top-full left-0 mt-2 w-48 bg-zinc-900 border border-white/10 rounded-xl shadow-xl z-50 overflow-hidden">
                                {availableModels.map(model => (
                                    <button
                                        key={model}
                                        onClick={() => { onModelSelect(model); setModelDropdownOpen(false); }}
                                        className={`w-full px-4 py-2.5 text-left text-sm hover:bg-white/5 transition-colors flex items-center justify-between
                      ${selectedModel === model ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-300'}`}
                                    >
                                        {modelNames[model] || model}
                                        {selectedModel === model && <Check size={14} />}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ) : (
                    <h2 className="text-lg font-semibold text-white/90">
                        {activeTab === 'rag' && 'База Знаний'}
                        {activeTab === 'autogpt' && 'Автономный Агент'}
                        {activeTab === 'templates' && 'Галерея Шаблонов'}
                        {activeTab === 'history' && 'Архив Событий'}
                    </h2>
                )}
            </div>

            {/* Thinking Mode Selector */}
            {activeTab === 'chat' && (
                <div className="flex items-center gap-3">
                    {/* Thinking Modes */}
                    <div className="flex items-center gap-1 bg-zinc-800/50 rounded-full p-1">
                        {thinkingModes.map(mode => (
                            <button
                                key={mode.id}
                                onClick={() => onThinkingModeChange(mode.id)}
                                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${thinkingMode === mode.id
                                    ? `${mode.bgActive} ${mode.color} shadow-md`
                                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'}`}
                                title={mode.label}
                            >
                                <span>{mode.icon}</span>
                                <span className="hidden md:inline">{mode.label}</span>
                            </button>
                        ))}
                    </div>

                    {/* Model Selection Mode Toggle */}
                    <div className="flex items-center gap-1 bg-zinc-800/50 rounded-full p-1 border border-white/5">
                        <button
                            onClick={() => onModelSelectionModeChange('manual')}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 ${modelSelectionMode === 'manual'
                                ? 'bg-emerald-500/20 text-emerald-400 shadow-md'
                                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'}`}
                            title="Ручной режим: модель не меняется при переключении thinking modes"
                        >
                            <span>🎯</span>
                            <span className="hidden lg:inline">Ручной</span>
                        </button>
                        <button
                            onClick={() => onModelSelectionModeChange('auto')}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 ${modelSelectionMode === 'auto'
                                ? 'bg-indigo-500/20 text-indigo-400 shadow-md'
                                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'}`}
                            title="Авто режим: thinking modes автоматически выбирают оптимальную модель"
                        >
                            <span>🧠</span>
                            <span className="hidden lg:inline">Авто</span>
                        </button>
                    </div>
                </div>
            )}

            <div className="flex items-center gap-3">
                <div className="relative hidden md:flex group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={15} />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        placeholder="Поиск..."
                        className="w-64 bg-zinc-900/50 border border-white/5 rounded-lg py-1.5 pl-9 pr-4 text-sm text-zinc-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-zinc-600"
                        aria-label="Поиск по разговорам"
                    />
                </div>

                {/* Backup Status Indicator */}
                <div className="hidden md:flex items-center gap-1.5 text-xs px-2 py-1 rounded-md bg-zinc-800/50">
                    {backupStatus === 'synced' && (
                        <>
                            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-emerald-400">☁️ Синхронизировано</span>
                        </>
                    )}
                    {backupStatus === 'syncing' && (
                        <>
                            <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                            <span className="text-yellow-400">⏳ Синхронизация...</span>
                        </>
                    )}
                    {backupStatus === 'error' && (
                        <>
                            <span className="w-2 h-2 rounded-full bg-red-500" />
                            <span className="text-red-400">⚠️ Ошибка</span>
                        </>
                    )}
                    {backupStatus === 'unknown' && (
                        <>
                            <span className="w-2 h-2 rounded-full bg-zinc-500" />
                            <span className="text-zinc-500">💾 Локально</span>
                        </>
                    )}
                </div>

                {/* Clear Memory Button */}
                <IconButton
                    icon={<Trash2 size={18} />}
                    tooltip="Очистить память"
                    label="Очистить всю память"
                    onClick={async () => {
                        if (window.confirm('⚠️ Очистить ВСЮ память?\n\nБудут удалены:\n• Все разговоры\n• Все сообщения\n• Все факты о вас\n\nЭто действие необратимо!')) {
                            try {
                                const response = await fetch('/api/memory/clear', { method: 'DELETE' });
                                if (response.ok) {
                                    alert('✅ Память очищена! Обновите страницу.');
                                    window.location.reload();
                                } else {
                                    alert('❌ Ошибка при очистке памяти');
                                }
                            } catch (error) {
                                alert(`❌ Ошибка: ${error}`);
                            }
                        }
                    }}
                />

                <IconButton
                    icon={darkMode ? <Sun size={18} /> : <Moon size={18} />}
                    tooltip={darkMode ? "Светлая тема" : "Тёмная тема"}
                    label="Переключить тему"
                    onClick={onToggleDarkMode}
                />
            </div>
        </header>
    );
}

export default Header;
