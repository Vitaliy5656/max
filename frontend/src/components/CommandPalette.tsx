/**
 * Command Palette Component
 * UX-002: Cmd+K / Ctrl+K command palette using cmdk library
 * 
 * Provides quick access to:
 * - Tab navigation
 * - Actions (new chat, clear memory)
 * - Settings
 */
import { useEffect, useState, useCallback } from 'react';
import { Command } from 'cmdk';
import {
    MessageSquare, FileText, Bot, LayoutTemplate, History, Search,
    Plus, Trash2, Sun, Moon, Beaker
} from 'lucide-react';

interface CommandPaletteProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onNavigate: (tab: 'chat' | 'rag' | 'research' | 'autogpt' | 'templates' | 'history') => void;
    onNewConversation: () => void;
    onClearMemory: () => void;
    onToggleDarkMode: () => void;
    darkMode: boolean;
}

const TAB_ITEMS = [
    { id: 'chat', label: 'Чат', icon: MessageSquare, shortcut: '1' },
    { id: 'rag', label: 'RAG / Документы', icon: FileText, shortcut: '2' },
    { id: 'research', label: 'Research Lab', icon: Beaker, shortcut: '3' },
    { id: 'autogpt', label: 'AutoGPT', icon: Bot, shortcut: '4' },
    { id: 'templates', label: 'Шаблоны', icon: LayoutTemplate, shortcut: '5' },
    { id: 'history', label: 'История', icon: History, shortcut: '6' },
] as const;

export function CommandPalette({
    open,
    onOpenChange,
    onNavigate,
    onNewConversation,
    onClearMemory,
    onToggleDarkMode,
    darkMode
}: CommandPaletteProps) {
    const [search, setSearch] = useState('');

    // Handle keyboard shortcut to open
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                onOpenChange(!open);
            }
            if (e.key === 'Escape' && open) {
                onOpenChange(false);
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [open, onOpenChange]);

    // Execute action and close
    const runAction = useCallback((action: () => void) => {
        action();
        onOpenChange(false);
        setSearch('');
    }, [onOpenChange]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-[100]">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={() => onOpenChange(false)}
            />

            {/* Command Dialog */}
            <div className="absolute left-1/2 top-[20%] -translate-x-1/2 w-full max-w-xl">
                <Command
                    className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden"
                    shouldFilter={true}
                >
                    {/* Search Input */}
                    <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800">
                        <Search size={18} className="text-zinc-500" />
                        <Command.Input
                            value={search}
                            onValueChange={setSearch}
                            placeholder="Поиск команд..."
                            className="flex-1 bg-transparent text-zinc-200 placeholder:text-zinc-500 focus:outline-none text-sm"
                            autoFocus
                        />
                        <kbd className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700">
                            ESC
                        </kbd>
                    </div>

                    {/* Command List */}
                    <Command.List className="max-h-80 overflow-y-auto p-2">
                        <Command.Empty className="py-6 text-center text-sm text-zinc-500">
                            Ничего не найдено
                        </Command.Empty>

                        {/* Navigation Group */}
                        <Command.Group heading="Навигация" className="mb-2">
                            {TAB_ITEMS.map((item) => (
                                <Command.Item
                                    key={item.id}
                                    value={`navigate ${item.label}`}
                                    onSelect={() => runAction(() => onNavigate(item.id as any))}
                                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-zinc-300 hover:bg-zinc-800 data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                                >
                                    <item.icon size={16} className="text-zinc-500" />
                                    <span className="flex-1">{item.label}</span>
                                    <kbd className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700">
                                        Ctrl+{item.shortcut}
                                    </kbd>
                                </Command.Item>
                            ))}
                        </Command.Group>

                        {/* Actions Group */}
                        <Command.Group heading="Действия" className="mb-2">
                            <Command.Item
                                value="new conversation chat"
                                onSelect={() => runAction(onNewConversation)}
                                className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-zinc-300 hover:bg-zinc-800 data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                            >
                                <Plus size={16} className="text-zinc-500" />
                                <span>Новый чат</span>
                            </Command.Item>
                            <Command.Item
                                value="clear memory delete"
                                onSelect={() => runAction(onClearMemory)}
                                className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-red-400 hover:bg-red-900/20 data-[selected=true]:bg-red-900/20"
                            >
                                <Trash2 size={16} />
                                <span>Очистить память</span>
                            </Command.Item>
                        </Command.Group>

                        {/* Settings Group */}
                        <Command.Group heading="Настройки">
                            <Command.Item
                                value="toggle theme dark light mode"
                                onSelect={() => runAction(onToggleDarkMode)}
                                className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-zinc-300 hover:bg-zinc-800 data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                            >
                                {darkMode ? <Sun size={16} className="text-zinc-500" /> : <Moon size={16} className="text-zinc-500" />}
                                <span>{darkMode ? 'Светлая тема' : 'Тёмная тема'}</span>
                            </Command.Item>
                        </Command.Group>
                    </Command.List>

                    {/* Footer */}
                    <div className="px-4 py-2 border-t border-zinc-800 flex items-center gap-4 text-[10px] text-zinc-600">
                        <span>↑↓ навигация</span>
                        <span>↵ выбрать</span>
                        <span>esc закрыть</span>
                    </div>
                </Command>
            </div>
        </div>
    );
}

export default CommandPalette;
