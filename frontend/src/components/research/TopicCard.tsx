/**
 * TopicCard Component
 * ARCH-015: Extracted from ResearchLab.tsx
 * 
 * Displays a research topic with quality bar and action buttons
 */
import { Trash2, RefreshCw, Brain, RotateCcw } from 'lucide-react';
import { QualityBar } from './QualityBar';
import type { Topic } from '../../hooks/useResearch';

interface TopicCardProps {
    topic: Topic;
    onDelete: (id: string) => void;
    onRefresh: (id: string) => void;
    onViewSkill: (topic: Topic) => void;
    onReResearch: (topic: Topic) => void;
}

export function TopicCard({
    topic,
    onDelete,
    onRefresh,
    onViewSkill,
    onReResearch
}: TopicCardProps) {
    const quality = topic.quality ?? 0.5;
    const needsMoreResearch = quality < 0.7 || topic.status !== 'complete';

    return (
        <div className="group bg-zinc-900/50 rounded-lg p-4 border border-zinc-800 hover:border-zinc-700 transition-colors relative">
            {/* Re-research button */}
            <button
                onClick={() => onReResearch(topic)}
                className={`absolute top-3 right-3 p-2 rounded-lg transition-all flex items-center gap-1 focus:ring-2 focus:ring-indigo-500 focus:outline-none
                    ${needsMoreResearch
                        ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 border border-yellow-500/30'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-300 opacity-50 group-hover:opacity-100'
                    }`}
                title="Дополнить исследование"
                aria-label="Дополнить исследование"
            >
                <RotateCcw size={14} />
                {needsMoreResearch && <span className="text-[10px] font-bold">+</span>}
            </button>

            <div className="flex justify-between items-start pr-12">
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <h3 className="font-medium text-white">{topic.name}</h3>
                        <span className={`
                            text-[10px] px-1.5 py-0.5 rounded
                            ${topic.status === 'complete' ? 'bg-green-900/30 text-green-400' : ''}
                            ${topic.status === 'incomplete' ? 'bg-yellow-900/30 text-yellow-400' : ''}
                            ${topic.status === 'failed' ? 'bg-red-900/30 text-red-400' : ''}
                        `}>
                            {topic.status}
                        </span>
                    </div>
                    <p className="text-xs text-zinc-500 mt-1">
                        {topic.chunk_count} chunks • {new Date(topic.created_at).toLocaleDateString()}
                    </p>
                </div>
            </div>

            {/* Quality Bar */}
            <div className="mt-3">
                <QualityBar quality={quality} />
            </div>

            {/* FIX: Action buttons always visible for accessibility */}
            <div className="mt-3 flex items-center gap-2">
                <button
                    onClick={() => onViewSkill(topic)}
                    className="flex items-center gap-1.5 text-xs bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 px-2.5 py-1.5 rounded-lg transition-colors focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    aria-label="Просмотреть Lens Skill"
                >
                    <Brain size={12} />
                    <span>Lens Skill</span>
                </button>
                <button
                    onClick={() => onRefresh(topic.id)}
                    className="p-1.5 text-zinc-500 hover:text-indigo-400 transition-colors rounded focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    title="Обновить"
                    aria-label="Обновить топик"
                >
                    <RefreshCw size={14} />
                </button>
                <button
                    onClick={() => onDelete(topic.id)}
                    className="p-1.5 text-zinc-500 hover:text-red-400 transition-colors rounded focus:ring-2 focus:ring-red-500 focus:outline-none"
                    title="Удалить"
                    aria-label="Удалить топик"
                >
                    <Trash2 size={14} />
                </button>
            </div>
        </div>
    );
}

export default TopicCard;
