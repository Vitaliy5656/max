/**
 * ChatTab - Main chat interface component
 * ARCH-002: Extracted from App.tsx for better maintainability
 */
import { useRef, useEffect } from 'react';
import { MessageBubble } from '../MessageBubble';
import { ThinkingPanel } from '../ThinkingPanel';
import { InputArea } from '../InputArea';

interface Message {
    id: number;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: string;  // Optional to match actual usage
    model?: string;
}

interface ConfidenceInfo {
    score: number;
    level: 'low' | 'medium' | 'high';
    factors?: string[];  // Optional to match useChat.ts
}

interface ChatTabProps {
    // Chat state
    messages: Message[];
    input: string;
    setInput: (value: string) => void;
    isGenerating: boolean;
    // P2-001: Connection state for visual feedback
    isConnecting: boolean;

    // Thinking state
    isThinking: boolean;
    thinkingStartTime: number;
    thinkContent: string;
    thinkExpanded: boolean;
    toggleThinkExpanded: () => void;
    thinkingSteps: Array<{ name: string; content: string }>;

    // Other state
    lastConfidence: ConfidenceInfo | null;
    loadingModel: string | null;
    queueStatus: 'inactive' | 'waiting' | 'acquired';
    feedbackSent: Record<number, 'up' | 'down' | null>;

    // Actions
    onSendMessage: () => void;
    onStopGeneration: () => void;
    onCopy: (content: string) => void;
    onRegenerate: (messageId: number) => void;
    onFeedback: (messageId: number, rating: number) => void;
}

export function ChatTab({
    messages,
    input,
    setInput,
    isGenerating,
    isConnecting,
    isThinking,
    thinkingStartTime,
    thinkContent,
    thinkExpanded,
    toggleThinkExpanded,
    thinkingSteps,
    lastConfidence,
    loadingModel,
    queueStatus,
    feedbackSent,
    onSendMessage,
    onStopGeneration,
    onCopy,
    onRegenerate,
    onFeedback,
}: ChatTabProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isGenerating]);

    return (
        <div className="flex-1 flex flex-col overflow-hidden animate-tab-in">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-4">
                {messages.map(message => (
                    <MessageBubble
                        key={message.id}
                        message={message}
                        feedbackSent={feedbackSent}
                        onCopy={onCopy}
                        onRegenerate={onRegenerate}
                        onFeedback={onFeedback}
                    />
                ))}

                {/* Thinking Panel */}
                <ThinkingPanel
                    isThinking={isThinking}
                    thinkingStartTime={thinkingStartTime}
                    thinkContent={thinkContent}
                    thinkExpanded={thinkExpanded}
                    onToggleExpand={toggleThinkExpanded}
                    lastConfidence={lastConfidence}
                    loadingModel={loadingModel}
                    isGenerating={isGenerating}
                    queueStatus={queueStatus}
                    thinkingSteps={thinkingSteps}
                />

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <InputArea
                value={input}
                onChange={setInput}
                onSend={onSendMessage}
                onStop={onStopGeneration}
                isGenerating={isGenerating}
                isConnecting={isConnecting}
            />
        </div>
    );
}

export default ChatTab;
