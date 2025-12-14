import {
    MessageSquare, FileText, Bot, LayoutTemplate, Plus, Cpu,
    History, ChevronRight, X, MessageCircle
} from 'lucide-react';
import { DenseCore } from './DenseCore';
import { SynapticStream } from './SynapticStream';
import type { LogEntry } from './SynapticStream';
import type * as api from '../api/client';

interface SidebarProps {
    activeTab: 'chat' | 'rag' | 'autogpt' | 'templates' | 'history';
    setActiveTab: (tab: 'chat' | 'rag' | 'autogpt' | 'templates' | 'history') => void;
    sidebarOpen: boolean;
    setSidebarOpen: (open: boolean) => void;
    isMobile: boolean;
    conversations: api.Conversation[];
    conversationId: string | null;
    setConversationId: (id: string) => void;
    onNewConversation: () => void;
    intelligence: number;
    empathy: number;
    systemLogs: LogEntry[];
}

const NavItem = ({ icon, label, active, onClick, collapsed }: {
    icon: React.ReactNode;
    label: string;
    active: boolean;
    onClick: () => void;
    collapsed?: boolean
}) => (
    <button
        onClick={onClick}
        className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group focus:outline-none focus:ring-2 focus:ring-indigo-500/50 ${active ? 'bg-zinc-800 text-white font-medium' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
            }`}
        aria-label={collapsed ? label : undefined}
        title={collapsed ? label : undefined}
    >
        <div className={`flex items-center justify-center transition-colors ${active ? 'text-indigo-400' : 'group-hover:text-indigo-300'}`}>
            {icon}
        </div>
        {!collapsed && <span className="text-sm truncate flex-1 text-left">{label}</span>}
    </button>
);

/**
 * Sidebar navigation with conversation history and tools.
 */
export function Sidebar({
    activeTab,
    setActiveTab,
    sidebarOpen,
    setSidebarOpen,
    isMobile,
    conversations,
    setConversationId,
    onNewConversation,
    intelligence,
    empathy,
    systemLogs
}: SidebarProps) {
    return (
        <>
            {/* Mobile Overlay */}
            {isMobile && sidebarOpen && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30" onClick={() => setSidebarOpen(false)} />
            )}

            {/* Sidebar */}
            <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        ${sidebarOpen ? 'w-80 translate-x-0' : 'w-20 -translate-x-full lg:translate-x-0'} 
        bg-[#09090b] border-r border-white/5 flex flex-col transition-all duration-500
      `}>
                {/* Header */}
                <div className="h-16 flex items-center justify-between px-6 border-b border-white/5 shrink-0">
                    <div className="flex items-center">
                        <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-[0_0_15px_rgba(79,70,229,0.4)]">
                            <Cpu size={20} className="text-white" />
                        </div>
                        {sidebarOpen && <span className="ml-3 font-bold text-xl tracking-tight text-white">MAX <span className="text-zinc-500 font-normal">AI</span></span>}
                    </div>
                    {sidebarOpen && <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-zinc-500 hover:text-white"><X size={20} /></button>}
                </div>

                {/* Chat & History */}
                <div className="flex-1 flex flex-col overflow-y-auto py-4 px-3 gap-1">
                    <NavItem icon={<Plus size={18} />} label="Новый чат" active={false} onClick={onNewConversation} collapsed={!sidebarOpen} />
                    <NavItem icon={<MessageSquare size={18} />} label="Текущий чат" active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} collapsed={!sidebarOpen} />

                    {sidebarOpen && conversations.length > 0 && (
                        <div className="mt-6 mb-2 px-2 flex items-center justify-between">
                            <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider">Недавние диалоги</span>
                            <span className="text-[10px] text-zinc-700 bg-zinc-900 px-1.5 py-0.5 rounded-md border border-white/5">{conversations.length}</span>
                        </div>
                    )}

                    <div className="space-y-0.5">
                        {conversations.slice(0, 5).map(chat => (
                            <button
                                key={chat.id}
                                onClick={() => { setConversationId(chat.id); setActiveTab('chat'); }}
                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group text-left hover:bg-zinc-900/50"
                            >
                                <MessageCircle size={16} className="text-zinc-500 group-hover:text-zinc-300" />
                                {sidebarOpen && (
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm text-zinc-400 group-hover:text-zinc-200 truncate">{chat.title}</div>
                                        <div className="text-[10px] text-zinc-600 truncate">{chat.message_count} сообщ.</div>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Tools */}
                <div className="shrink-0 bg-[#09090b] border-t border-white/5 flex flex-col">
                    <div className="px-3 py-4 space-y-1">
                        {sidebarOpen && <div className="px-2 mb-2 text-[10px] font-bold text-zinc-600 uppercase tracking-wider">Инструменты</div>}
                        <NavItem icon={<FileText size={18} />} label="База знаний (RAG)" active={activeTab === 'rag'} onClick={() => setActiveTab('rag')} collapsed={!sidebarOpen} />
                        <NavItem icon={<Bot size={18} />} label="Авто-агент" active={activeTab === 'autogpt'} onClick={() => setActiveTab('autogpt')} collapsed={!sidebarOpen} />
                        <NavItem icon={<LayoutTemplate size={18} />} label="Шаблоны" active={activeTab === 'templates'} onClick={() => setActiveTab('templates')} collapsed={!sidebarOpen} />
                        <NavItem icon={<History size={18} />} label="Архив" active={activeTab === 'history'} onClick={() => setActiveTab('history')} collapsed={!sidebarOpen} />
                    </div>

                    {!sidebarOpen && (
                        <button onClick={() => setSidebarOpen(true)} className="w-full flex items-center justify-center p-4 text-zinc-600 hover:text-white border-t border-white/5">
                            <ChevronRight size={18} />
                        </button>
                    )}

                    {/* The Living Core */}
                    {sidebarOpen && (
                        <div className="p-4 pt-2 border-t border-white/5 flex flex-col items-center">
                            <SynapticStream logs={systemLogs} />
                            <DenseCore intelligence={intelligence} empathy={empathy} />
                        </div>
                    )}
                </div>
            </aside>
        </>
    );
}

export default Sidebar;
