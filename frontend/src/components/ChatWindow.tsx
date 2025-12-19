import { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { ThinkingPanel } from './ThinkingPanel';
import type { Message, ConfidenceInfo } from './types';

interface ChatWindowProps {
    messages: Message[];
    feedbackSent: Record<number, 'up' | 'down' | null>;
    onFeedback: (messageId: number, rating: number) => void;
    onRegenerate: (messageId: number) => void;
    onCopy: (content: string) => void;
    // Thinking state
    isGenerating: boolean;
    isThinking: boolean;
    thinkingStartTime: number;
    thinkContent: string;
    thinkExpanded: boolean;
    onToggleThinkExpand: () => void;
    lastConfidence: ConfidenceInfo | null;
    loadingModel: string | null;
    thinkingSteps?: Array<{ name: string; content: string }>;
}

/**
 * Main chat window displaying message list with auto-scroll.
 */
export function ChatWindow({
    messages,
    feedbackSent,
    onFeedback,
    onRegenerate,
    onCopy,
    isGenerating,
    isThinking,
    thinkingStartTime,
    thinkContent,
    thinkExpanded,
    onToggleThinkExpand,
    lastConfidence,
    loadingModel,
    thinkingSteps = []
}: ChatWindowProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isGenerating]);

    return (
        <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="space-y-4 pb-4">
                {messages.map((msg) => (
                    <MessageBubble
                        key={msg.id}
                        message={msg}
                        feedbackSent={feedbackSent}
                        onFeedback={onFeedback}
                        onRegenerate={onRegenerate}
                        onCopy={onCopy}
                    />
                ))}

                {/* ThinkingPanel with all status indicators */}
                <ThinkingPanel
                    isThinking={isThinking}
                    thinkingStartTime={thinkingStartTime}
                    thinkContent={thinkContent}
                    thinkExpanded={thinkExpanded}
                    onToggleExpand={onToggleThinkExpand}
                    lastConfidence={lastConfidence}
                    loadingModel={loadingModel}
                    isGenerating={isGenerating}
                    thinkingSteps={thinkingSteps}
                />

                {/* Show simple generating indicator when generating but not thinking */}
                {isGenerating && !isThinking && messages[messages.length - 1]?.role === 'assistant' && !messages[messages.length - 1]?.content && (
                    <div className="pl-12 md:pl-14">
                        <div className="flex items-center gap-2 p-3 text-zinc-500 text-sm">
                            <div className="w-4 h-4 border-2 border-zinc-600 border-t-indigo-400 rounded-full animate-spin" />
                            <span>Генерация...</span>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} className="h-4" />
            </div>
        </div>
    );
}

export default ChatWindow;
