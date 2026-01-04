import { useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface InputAreaProps {
    value: string;
    onChange: (value: string) => void;
    onSend: () => void;
    onStop: () => void;
    isGenerating: boolean;
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
 */
export function InputArea({ value, onChange, onSend, onStop, isGenerating }: InputAreaProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [value]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    };

    return (
        <div className="px-4 pb-6 pt-2 z-20">
            <div className="relative max-w-4xl mx-auto">
                <TextAreaContainer isGenerating={isGenerating}>
                    <textarea
                        ref={textareaRef}
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Спроси о чем угодно..."
                        className="w-full bg-transparent border-none text-zinc-200 placeholder:text-zinc-500 px-5 py-4 min-h-[56px] max-h-[200px] resize-none focus:ring-0 text-[15px]"
                        rows={1}
                    />
                    <div className="flex items-center justify-between px-3 pb-3">
                        <div className="flex items-center gap-1">
                            <span className="text-xs text-zinc-600">Shift+Enter для новой строки</span>
                        </div>
                        <button
                            onClick={isGenerating ? onStop : onSend}
                            disabled={!value.trim() && !isGenerating}
                            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all active:scale-90 ${value.trim() || isGenerating ? 'bg-indigo-600 text-white hover:bg-indigo-500' : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                                }`}
                        >
                            {isGenerating ? <div className="w-3 h-3 bg-white rounded-sm" /> : <Send size={16} />}
                        </button>
                    </div>
                </TextAreaContainer>
            </div>
        </div>
    );
}

export default InputArea;
