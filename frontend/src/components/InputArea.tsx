import { useRef, useEffect } from 'react';
import { Send, Square, Paperclip, AtSign, Loader2 } from 'lucide-react';

interface InputAreaProps {
    value: string;
    onChange: (value: string) => void;
    onSend: () => void;
    onStop: () => void;
    isGenerating: boolean;
    /** P2-001: Show connecting state before first token */
    isConnecting?: boolean;
}

const TextAreaContainer = ({ children, isGenerating }: { children: React.ReactNode; isGenerating: boolean }) => (
    <div className={`relative bg-zinc-900/90 backdrop-blur-xl border transition-all duration-300 rounded-[2rem] shadow-2xl overflow-hidden ${isGenerating ? 'border-indigo-500/30 ring-1 ring-indigo-500/10' : 'border-white/10 hover:border-white/20'
        }`}
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }} // Handle iOS Home Bar
    >
        {children}
    </div>
);

/**
 * Chat input area with auto-resize textarea and send/stop buttons.
 * 
 * FIX: Added tooltips and aria-labels for accessibility.
 * P2-001: Added isConnecting state for visual feedback.
 */
export function InputArea({ value, onChange, onSend, onStop, isGenerating, isConnecting = false }: InputAreaProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [value]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Enter or Ctrl+Enter to send (UX-001)
        // P2-001: Block sending while connecting
        if (e.key === 'Enter' && !e.shiftKey && !isConnecting) {
            e.preventDefault();
            onSend();
        }
    };

    // P2-001: Enhanced button states
    const getButtonState = () => {
        if (isConnecting) {
            return { label: 'Подключение к серверу...', icon: 'connecting' };
        }
        if (isGenerating) {
            return { label: 'Остановить генерацию', icon: 'stop' };
        }
        return { label: 'Отправить сообщение', icon: 'send' };
    };

    const buttonState = getButtonState();
    const isDisabled = (!value.trim() && !isGenerating) || isConnecting;

    // Render button icon based on state
    const renderButtonIcon = () => {
        switch (buttonState.icon) {
            case 'connecting':
                return <Loader2 size={16} className="animate-spin" />;
            case 'stop':
                return <Square size={12} fill="currentColor" />;
            default:
                return <Send size={16} />;
        }
    };

    return (
        <div className="px-4 pb-6 pt-2 z-20">
            <div className="relative max-w-4xl mx-auto">
                <TextAreaContainer isGenerating={isGenerating || isConnecting}>
                    <textarea
                        ref={textareaRef}
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={isConnecting ? "Подключение..." : "Спроси о чем угодно... (/ для команд)"}
                        className="w-full bg-transparent border-none text-zinc-200 placeholder:text-zinc-500 px-5 py-4 min-h-[56px] max-h-[200px] resize-none focus:ring-0 focus:outline-none text-[15px]"
                        rows={1}
                        aria-label="Поле ввода сообщения"
                        disabled={isConnecting}
                    />
                    <div className="flex items-center justify-between px-3 pb-3">
                        <div className="flex items-center gap-1">
                            {/* UX-023: File attachment button */}
                            <button
                                type="button"
                                className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
                                title="Прикрепить файл"
                                aria-label="Прикрепить файл"
                                onClick={() => {
                                    // TODO: Implement file picker
                                    alert('📎 Функция прикрепления файлов в разработке');
                                }}
                            >
                                <Paperclip size={16} />
                            </button>
                            {/* UX-024: @mention button */}
                            <button
                                type="button"
                                className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
                                title="Упомянуть документ (@)"
                                aria-label="Упомянуть документ"
                                onClick={() => {
                                    onChange(value + '@');
                                }}
                            >
                                <AtSign size={16} />
                            </button>
                            <span className="text-xs text-zinc-600 ml-1">
                                {isConnecting ? '⏳ Ожидание сервера...' : 'Shift+Enter для новой строки'}
                            </span>
                        </div>
                        {/* FIX: Added tooltip, aria-label, and focus styles */}
                        {/* P2-001: Enhanced with connecting state */}
                        <button
                            onClick={isGenerating ? onStop : onSend}
                            disabled={isDisabled}
                            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all active:scale-90 focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-900 focus:outline-none ${isConnecting
                                    ? 'bg-amber-600 text-white cursor-wait'
                                    : value.trim() || isGenerating
                                        ? 'bg-indigo-600 text-white hover:bg-indigo-500 focus:ring-indigo-500'
                                        : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                                }`}
                            title={buttonState.label}
                            aria-label={buttonState.label}
                        >
                            {renderButtonIcon()}
                        </button>
                    </div>
                </TextAreaContainer>
            </div>
        </div>
    );
}

export default InputArea;

