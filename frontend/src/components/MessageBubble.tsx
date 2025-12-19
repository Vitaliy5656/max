import { Copy, RotateCw, ThumbsUp, ThumbsDown, Check, Cpu } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Message } from './types';

interface MessageBubbleProps {
    message: Message;
    feedbackSent: Record<number, 'up' | 'down' | null>;
    onFeedback: (messageId: number, rating: number) => void;
    onRegenerate: (messageId: number) => void;
    onCopy: (content: string) => void;
}

const ActionBtn = ({ icon, onClick, label }: { icon: React.ReactNode; onClick?: () => void; label: string }) => (
    <button
        onClick={onClick}
        className="p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 rounded-md transition-colors active:scale-90 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
        aria-label={label}
        title={label}
    >
        {icon}
    </button>
);

/**
 * Individual message bubble with actions for assistant messages.
 */
export function MessageBubble({ message, feedbackSent, onFeedback, onRegenerate, onCopy }: MessageBubbleProps) {
    const msg = message;

    return (
        <div className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {/* Avatar - only for assistant */}
            {msg.role !== 'user' && (
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 
                      bg-gradient-to-br from-indigo-600 to-violet-700 shadow-lg shadow-indigo-500/30">
                    <Cpu size={16} className="text-white" />
                </div>
            )}

            <div className={`flex flex-col max-w-[75%] md:max-w-[70%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {/* Message bubble */}
                <div className={`
          px-5 py-3.5 rounded-2xl shadow-lg
          ${msg.role === 'user'
                        ? 'bg-gradient-to-br from-indigo-600 to-indigo-500 text-white rounded-tr-md'
                        : 'bg-zinc-800/80 backdrop-blur-sm border border-zinc-700/50 text-zinc-100 rounded-tl-md'
                    }
        `}>
                    <div className={`text-[15px] leading-relaxed ${msg.role === 'user' ? 'text-white' : 'text-zinc-100'} prose prose-invert prose-sm max-w-none`}>
                        <ReactMarkdown
                            components={{
                                // Style inline code
                                code: ({ children }) => (
                                    <code className="bg-zinc-700/50 px-1.5 py-0.5 rounded text-indigo-300 text-sm">
                                        {children}
                                    </code>
                                ),
                                // Style code blocks
                                pre: ({ children }) => (
                                    <pre className="bg-zinc-900/80 p-3 rounded-lg overflow-x-auto my-2 border border-zinc-700/50">
                                        {children}
                                    </pre>
                                ),
                                // Style bold
                                strong: ({ children }) => (
                                    <strong className="font-semibold text-white">{children}</strong>
                                ),
                                // Style links
                                a: ({ children, href }) => (
                                    <a href={href} target="_blank" rel="noopener noreferrer"
                                        className="text-indigo-400 hover:text-indigo-300 underline">
                                        {children}
                                    </a>
                                ),
                            }}
                        >
                            {msg.content}
                        </ReactMarkdown>
                    </div>
                </div>

                {/* Metadata row */}
                <div className="flex items-center gap-2 mt-1.5 px-2">
                    <span className="text-[11px] text-zinc-500">{msg.timestamp}</span>
                    {msg.model && msg.role === 'assistant' && (
                        <>
                            <span className="text-[11px] text-zinc-700">•</span>
                            <span className="text-[11px] text-zinc-600">{msg.model}</span>
                        </>
                    )}
                </div>

                {/* Action buttons - only for assistant */}
                {msg.role === 'assistant' && msg.content && (
                    <div className="flex items-center gap-1 mt-2 -ml-1">
                        <ActionBtn icon={<Copy size={14} />} onClick={() => onCopy(msg.content)} label="Копировать" />
                        <ActionBtn icon={<RotateCw size={14} />} onClick={() => onRegenerate(msg.id)} label="Перегенерировать" />
                        <div className="h-3 w-[1px] bg-zinc-700 mx-1" />
                        <button
                            onClick={() => onFeedback(msg.id, 1)}
                            aria-label="Нравится"
                            title="Нравится"
                            className={`p-1.5 rounded-md transition-all duration-200 active:scale-90 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 ${feedbackSent[msg.id] === 'up'
                                ? 'text-emerald-400 bg-emerald-500/20'
                                : 'text-zinc-500 hover:text-emerald-400 hover:bg-zinc-800'
                                }`}
                        >
                            {feedbackSent[msg.id] === 'up' ? <Check size={14} /> : <ThumbsUp size={14} />}
                        </button>
                        <button
                            onClick={() => onFeedback(msg.id, -1)}
                            aria-label="Не нравится"
                            title="Не нравится"
                            className={`p-1.5 rounded-md transition-all duration-200 active:scale-90 focus:outline-none focus:ring-2 focus:ring-red-500/50 ${feedbackSent[msg.id] === 'down'
                                ? 'text-red-400 bg-red-500/20'
                                : 'text-zinc-500 hover:text-red-400 hover:bg-zinc-800'
                                }`}
                        >
                            {feedbackSent[msg.id] === 'down' ? <Check size={14} /> : <ThumbsDown size={14} />}
                        </button>
                    </div>
                )}
            </div>

            {/* Avatar - only for user */}
            {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 
                      bg-zinc-800 border border-zinc-700 shadow-lg">
                    <span className="text-xs font-bold text-zinc-400">VM</span>
                </div>
            )}
        </div>
    );
}

export default MessageBubble;
