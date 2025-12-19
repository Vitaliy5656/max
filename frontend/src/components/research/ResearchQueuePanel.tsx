/**
 * ResearchQueuePanel - Queue management for research tasks
 * ARCH-013: Extracted from ResearchLab.tsx
 */
import { List, Clock, Pause, Play, X, ChevronUp, ChevronDown } from 'lucide-react';

export interface QueueItem {
    id: string;
    topic: string;
    description: string;
    max_pages: number;
    status: 'queued' | 'running' | 'paused';
    progress: number;
    paused: boolean;
    taskId?: string;
}

interface ResearchQueuePanelProps {
    queue: QueueItem[];
    maxSlots: number;
    onMoveUp: (id: string) => void;
    onMoveDown: (id: string) => void;
    onCancel: (id: string) => void;
    onPause: (id: string) => void;
    onResume: (id: string) => void;
}

export function ResearchQueuePanel({
    queue,
    maxSlots,
    onMoveUp,
    onMoveDown,
    onCancel,
    onPause,
    onResume
}: ResearchQueuePanelProps) {
    const activeItems = queue.filter(q => q.status === 'running');
    const queuedItems = queue.filter(q => q.status === 'queued');
    const pausedItems = queue.filter(q => q.status === 'paused');

    if (queue.length === 0) return null;

    return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg overflow-hidden h-fit">
            {/* Header */}
            <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between bg-zinc-800/30">
                <div className="flex items-center gap-2">
                    <List size={14} className="text-indigo-400" />
                    <span className="text-xs font-bold uppercase tracking-wide text-zinc-300">Очередь</span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-mono">
                    <span className="text-indigo-400">{activeItems.length}</span>
                    <span>/</span>
                    <span>{maxSlots}</span>
                </div>
            </div>

            {/* Active Tasks */}
            {activeItems.length > 0 && (
                <div className="p-3 border-b border-zinc-800/50">
                    <div className="text-[10px] uppercase font-bold text-green-500 mb-2 flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        Активно ({activeItems.length})
                    </div>
                    <div className="space-y-2">
                        {activeItems.map(item => (
                            <div key={item.id} className="bg-zinc-800/50 rounded-lg p-2">
                                <div className="text-xs font-medium text-white truncate mb-1">{item.topic}</div>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 h-1 bg-zinc-700 rounded-full overflow-hidden">
                                        <div className="h-full bg-indigo-500 transition-all" style={{ width: `${item.progress * 100}%` }} />
                                    </div>
                                    <span className="text-[10px] text-zinc-500">{Math.round(item.progress * 100)}%</span>
                                    <button onClick={() => onPause(item.id)} className="p-1 hover:bg-zinc-700 rounded" title="Пауза">
                                        <Pause size={12} />
                                    </button>
                                    <button onClick={() => onCancel(item.id)} className="p-1 hover:bg-red-900/30 text-zinc-400 hover:text-red-400 rounded" title="Отменить">
                                        <X size={12} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Paused Tasks */}
            {pausedItems.length > 0 && (
                <div className="p-3 border-b border-zinc-800/50">
                    <div className="text-[10px] uppercase font-bold text-yellow-500 mb-2">На паузе ({pausedItems.length})</div>
                    <div className="space-y-1">
                        {pausedItems.map(item => (
                            <div key={item.id} className="flex items-center gap-2 bg-zinc-800/30 rounded p-2">
                                <div className="flex-1 text-xs text-zinc-400 truncate">{item.topic}</div>
                                <button onClick={() => onResume(item.id)} className="p-1 hover:bg-zinc-700 rounded text-yellow-500" title="Продолжить">
                                    <Play size={12} />
                                </button>
                                <button onClick={() => onCancel(item.id)} className="p-1 hover:bg-red-900/30 text-zinc-400 hover:text-red-400 rounded" title="Удалить">
                                    <X size={12} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Queued Tasks */}
            {queuedItems.length > 0 && (
                <div className="p-3">
                    <div className="text-[10px] uppercase font-bold text-zinc-500 mb-2 flex items-center gap-1">
                        <Clock size={10} />
                        В очереди ({queuedItems.length})
                    </div>
                    <div className="space-y-1">
                        {queuedItems.map((item, index) => (
                            <div key={item.id} className="flex items-center gap-2 bg-zinc-800/30 rounded p-2 group">
                                <span className="text-[10px] text-zinc-600 font-mono w-4">{index + 1}.</span>
                                <div className="flex-1 text-xs text-zinc-400 truncate">{item.topic}</div>
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => onMoveUp(item.id)} disabled={index === 0}
                                        className="p-1 hover:bg-zinc-700 rounded disabled:opacity-30" title="Выше">
                                        <ChevronUp size={12} />
                                    </button>
                                    <button onClick={() => onMoveDown(item.id)} disabled={index === queuedItems.length - 1}
                                        className="p-1 hover:bg-zinc-700 rounded disabled:opacity-30" title="Ниже">
                                        <ChevronDown size={12} />
                                    </button>
                                    <button onClick={() => onCancel(item.id)}
                                        className="p-1 hover:bg-red-900/30 text-zinc-400 hover:text-red-400 rounded" title="Удалить">
                                        <X size={12} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default ResearchQueuePanel;
