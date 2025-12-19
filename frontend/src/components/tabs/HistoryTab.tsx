/**
 * HistoryTab - Conversation history/archive
 * ARCH-006: Extracted from App.tsx
 */

interface Conversation {
    id: string;
    title: string;
    message_count: number;
    updated_at: string;
}

interface HistoryTabProps {
    conversations: Conversation[];
    onSelectConversation: (id: string) => void;
    onSwitchToChat: () => void;
}

// GlassCard component (inline for simplicity)
function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={`bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl shadow-sm ${className}`}>
            {children}
        </div>
    );
}

export function HistoryTab({
    conversations,
    onSelectConversation,
    onSwitchToChat,
}: HistoryTabProps) {
    const handleSelect = (id: string) => {
        onSelectConversation(id);
        onSwitchToChat();
    };

    return (
        <div className="flex-1 overflow-y-auto p-6 animate-tab-in">
            <GlassCard className="p-6">
                <h3 className="text-lg font-semibold mb-4">📜 Архив разговоров</h3>
                <div className="space-y-2">
                    {conversations.length === 0 ? (
                        <p className="text-zinc-500 text-center py-8">Нет сохраненных разговоров</p>
                    ) : (
                        conversations.map(conv => (
                            <button
                                key={conv.id}
                                onClick={() => handleSelect(conv.id)}
                                className="w-full text-left p-4 bg-zinc-800/50 hover:bg-zinc-800 rounded-xl transition-colors"
                            >
                                <h4 className="font-medium mb-1">{conv.title}</h4>
                                <p className="text-xs text-zinc-500">{conv.message_count} сообщений</p>
                            </button>
                        ))
                    )}
                </div>
            </GlassCard>
        </div>
    );
}

export default HistoryTab;
