import { useRef, useEffect } from 'react';
import { Activity } from 'lucide-react';

export interface LogEntry {
    id: number;
    text: string;
    type: 'info' | 'growth' | 'empathy' | 'error';
    time: string;
}

interface SynapticStreamProps {
    logs: LogEntry[];
}

/**
 * SynapticStream - Real-time activity log display.
 */
export function SynapticStream({ logs }: SynapticStreamProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
            if (scrollHeight - scrollTop - clientHeight < 100) {
                scrollRef.current.scrollTo({ top: scrollHeight, behavior: 'smooth' });
            }
        }
    }, [logs]);

    return (
        <div className="flex flex-col w-full h-48 relative group px-2 mb-4">

            {/* Header */}
            <div className="flex items-center justify-between px-3 mb-1 opacity-30">
                <span className="text-[9px] font-mono uppercase tracking-widest text-zinc-500">Синапс</span>
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
            </div>

            {/* Content */}
            <div className="relative flex-1 stream-mask overflow-hidden rounded-xl bg-white/[0.01]">
                <div
                    ref={scrollRef}
                    className="absolute inset-0 overflow-y-auto dark-scroll px-3 py-4 space-y-3"
                >
                    {logs.length === 0 && (
                        <div className="h-full flex flex-col items-center justify-center opacity-10">
                            <Activity size={24} strokeWidth={1} />
                        </div>
                    )}

                    {logs.map((log) => {
                        const isGrowth = log.type === 'growth';
                        const isEmpathy = log.type === 'empathy';
                        const isError = log.type === 'error';

                        let dotColor = 'bg-zinc-800';
                        let textColor = 'text-zinc-600';

                        if (isGrowth) { dotColor = 'bg-indigo-600'; textColor = 'text-indigo-300/70'; }
                        if (isEmpathy) { dotColor = 'bg-rose-600'; textColor = 'text-rose-300/70'; }
                        if (isError) { dotColor = 'bg-red-900'; textColor = 'text-red-400/60'; }

                        return (
                            <div key={log.id} className="flex gap-3 items-start animate-in slide-in-from-bottom-2 fade-in duration-700">
                                <div className={`mt-1.5 w-1 h-1 rounded-full shrink-0 transition-colors duration-500 ${dotColor}`} />
                                <div className="flex-1 min-w-0">
                                    <p className={`text-[10px] leading-snug font-medium transition-colors duration-500 ${textColor}`}>
                                        {log.text}
                                    </p>
                                    <span className="text-[8px] font-mono text-zinc-800 block mt-0.5">{log.time}</span>
                                </div>
                            </div>
                        );
                    })}
                    <div className="h-4" />
                </div>
            </div>
        </div>
    );
}
