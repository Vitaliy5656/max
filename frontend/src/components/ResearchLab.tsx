/**
 * Research Lab Component
 * 
 * UI for managing research topics and viewing progress.
 * Features:
 * - Start new research with queue system
 * - View running tasks with 5-stage stepper
 * - Browse topics library with quality indicators
 * - View Topic Lens skills
 * - Research queue management
 */

import { useState, useMemo } from 'react';
import {
    Search, Plus, Trash2, RefreshCw, Brain, X, ChevronRight, Sparkles,
    // New icons for enhanced UI
    RotateCcw, Layers, Database, Globe, BarChart2, Clock,
    ChevronUp, ChevronDown, Pause, Play, List
} from 'lucide-react';
import { useResearch, type ResearchTask, type Topic, type QueueItem } from '../hooks/useResearch';

// Stage mapping for stepper
const STAGES = [
    { key: 'planning', label: 'Planning', emoji: '📋' },
    { key: 'hunting', label: 'Hunting', emoji: '🎯' },
    { key: 'mining', label: 'Mining', emoji: '⛏️' },
    { key: 'polishing', label: 'Polishing', emoji: '💎' },
    { key: 'diploma', label: 'Diploma', emoji: '🎓' },
];

// Get current stage index from task
function getStageIndex(stage: string): number {
    const idx = STAGES.findIndex(s => stage.toLowerCase().includes(s.key));
    return idx >= 0 ? idx : 0;
}

// Format ETA
function formatETA(seconds?: number): string {
    if (!seconds || seconds <= 0) return '';
    if (seconds < 60) return `~${seconds}s`;
    const mins = Math.ceil(seconds / 60);
    return `~${mins} min`;
}

// ============= NEW: Quality Bar =============
// FIX: Added tooltip explaining quality calculation
function QualityBar({ quality }: { quality: number }) {
    const percent = Math.round(quality * 100);
    const getColor = () => {
        if (quality >= 0.7) return 'bg-green-500';
        if (quality >= 0.4) return 'bg-yellow-500';
        return 'bg-red-500';
    };
    const getLabel = () => {
        if (quality >= 0.7) return 'Отлично';
        if (quality >= 0.4) return 'Хорошо';
        return 'Мало данных';
    };

    // FIX: Tooltip explaining quality calculation
    const tooltip = `Качество: ${percent}%\n• 70%+ = Отлично (достаточно данных)\n• 40-69% = Хорошо (можно дополнить)\n• <40% = Мало данных (нужно исследование)`;

    return (
        <div className="flex items-center gap-2" title={tooltip}>
            <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden cursor-help">
                <div className={`h-full ${getColor()} transition-all`} style={{ width: `${percent}%` }} />
            </div>
            <span className="text-[10px] text-zinc-500 font-mono w-16 text-right">{getLabel()}</span>
        </div>
    );
}

// ============= NEW: Stats Dashboard =============
// FIX: Added connectionStatus prop for real WebSocket state
function StatsDashboard({ stats, connectionStatus }: {
    stats: { totalTopics: number; totalChunks: number; completeCount: number; avgQuality: number };
    connectionStatus: 'connecting' | 'connected' | 'disconnected';
}) {
    // FIX: Dynamic status indicator based on WebSocket state
    const getStatusInfo = () => {
        switch (connectionStatus) {
            case 'connected': return { color: 'text-green-400', text: 'Подключено' };
            case 'connecting': return { color: 'text-yellow-400', text: 'Подключение...' };
            case 'disconnected': return { color: 'text-red-400', text: 'Отключено' };
        }
    };
    const statusInfo = getStatusInfo();

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center gap-2 text-zinc-500 mb-1">
                    <Layers size={14} />
                    <span className="text-[10px] uppercase font-bold">Топиков</span>
                </div>
                <div className="text-xl font-bold text-white">{stats.totalTopics}</div>
                <div className="text-[10px] text-zinc-600">{stats.completeCount} завершено</div>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center gap-2 text-zinc-500 mb-1">
                    <Database size={14} />
                    <span className="text-[10px] uppercase font-bold">Чанков</span>
                </div>
                <div className="text-xl font-bold text-white">{stats.totalChunks}</div>
                <div className="text-[10px] text-zinc-600">в базе знаний</div>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center gap-2 text-zinc-500 mb-1">
                    <BarChart2 size={14} />
                    <span className="text-[10px] uppercase font-bold">Качество</span>
                </div>
                <div className="text-xl font-bold text-white">{Math.round(stats.avgQuality * 100)}%</div>
                <div className="text-[10px] text-zinc-600">в среднем</div>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center gap-2 text-zinc-500 mb-1">
                    <Globe size={14} />
                    <span className="text-[10px] uppercase font-bold">Статус</span>
                </div>
                <div className={`text-xl font-bold ${statusInfo.color}`}>●</div>
                <div className="text-[10px] text-zinc-600">{statusInfo.text}</div>
            </div>
        </div>
    );
}

// ============= NEW: Activity Feed =============
function ActivityFeed({ activities }: { activities: { topic: string; action: string; time: string }[] }) {
    if (activities.length === 0) return null;

    return (
        <div className="bg-zinc-900/30 border border-zinc-800 rounded-lg p-3 mb-6">
            <h3 className="text-[10px] uppercase font-bold text-zinc-500 mb-2 flex items-center gap-2">
                <Clock size={12} />
                Недавняя активность
            </h3>
            <div className="flex flex-wrap gap-3">
                {activities.map((item, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                        <span className={`w-1.5 h-1.5 rounded-full ${item.action === 'complete' ? 'bg-green-500' : 'bg-red-500'
                            }`} />
                        <span className="text-zinc-400">{item.topic}</span>
                        <span className="text-zinc-600">{item.time}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ============= NEW: Research Queue Panel =============
function ResearchQueuePanel({
    queue,
    maxSlots,
    onMoveUp,
    onMoveDown,
    onCancel,
    onPause,
    onResume
}: {
    queue: QueueItem[];
    maxSlots: number;
    onMoveUp: (id: string) => void;
    onMoveDown: (id: string) => void;
    onCancel: (id: string) => void;
    onPause: (id: string) => void;
    onResume: (id: string) => void;
}) {
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

// ============= Sub-components =============

function ResearchStepper({ task }: { task: ResearchTask }) {
    const currentIndex = getStageIndex(task.stage);

    return (
        <div className="flex items-center gap-1 text-xs">
            {STAGES.map((stage, idx) => {
                const isActive = idx === currentIndex;
                const isComplete = idx < currentIndex;

                return (
                    <div key={stage.key} className="flex items-center">
                        <div
                            className={`
                                flex items-center gap-1 px-2 py-1 rounded transition-all
                                ${isActive ? 'bg-indigo-600 text-white' : ''}
                                ${isComplete ? 'bg-indigo-900/30 text-indigo-300' : ''}
                                ${!isActive && !isComplete ? 'text-zinc-500' : ''}
                            `}
                        >
                            <span>{stage.emoji}</span>
                            <span className="hidden md:inline">{stage.label}</span>
                        </div>
                        {idx < STAGES.length - 1 && (
                            <ChevronRight size={12} className="text-zinc-600 mx-1" />
                        )}
                    </div>
                );
            })}
        </div>
    );
}

function TaskCard({ task, onCancel }: { task: ResearchTask; onCancel: (id: string) => void }) {
    const eta = formatETA(task.eta_seconds);

    return (
        <div className="bg-zinc-900/50 rounded-lg p-4 border border-zinc-800">
            <div className="flex justify-between items-start mb-3">
                <div>
                    <h3 className="font-medium text-white">{task.topic}</h3>
                    <p className="text-xs text-zinc-500 mt-1">{task.description || 'No description'}</p>
                </div>
                <button
                    onClick={() => onCancel(task.id)}
                    className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                    title="Cancel research"
                >
                    <X size={16} />
                </button>
            </div>

            <ResearchStepper task={task} />

            <div className="mt-3 flex items-center justify-between text-xs text-zinc-400">
                <span>{task.detail || task.stage}</span>
                {eta && <span className="text-indigo-400">{eta}</span>}
            </div>

            {/* Progress bar */}
            <div className="mt-2 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div
                    className="h-full bg-indigo-500 transition-all duration-500"
                    style={{ width: `${task.progress * 100}%` }}
                />
            </div>
        </div>
    );
}

function TopicCard({
    topic,
    onDelete,
    onRefresh,
    onViewSkill,
    onReResearch
}: {
    topic: Topic;
    onDelete: (id: string) => void;
    onRefresh: (id: string) => void;
    onViewSkill: (topic: Topic) => void;
    onReResearch: (topic: Topic) => void;
}) {
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

            {/* FIX: Action buttons always visible (reduced opacity) for accessibility */}
            <div className="mt-3 flex items-center justify-between">
                <div className="flex items-center gap-1 opacity-60 group-hover:opacity-100 transition-opacity">
                    {topic.skill && (
                        <button
                            onClick={() => onViewSkill(topic)}
                            className="text-zinc-500 hover:text-indigo-400 p-1.5 transition-colors focus:ring-2 focus:ring-indigo-500 focus:outline-none rounded"
                            title="Посмотреть Topic Lens"
                            aria-label="Посмотреть Topic Lens"
                        >
                            <Sparkles size={16} />
                        </button>
                    )}
                    <button
                        onClick={() => onRefresh(topic.id)}
                        className="text-zinc-500 hover:text-blue-400 p-1.5 transition-colors focus:ring-2 focus:ring-blue-500 focus:outline-none rounded"
                        title="Обновить"
                        aria-label="Обновить топик"
                    >
                        <RefreshCw size={16} />
                    </button>
                    <button
                        onClick={() => onDelete(topic.id)}
                        className="text-zinc-500 hover:text-red-400 p-1.5 transition-colors focus:ring-2 focus:ring-red-500 focus:outline-none rounded"
                        title="Удалить"
                        aria-label="Удалить топик"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
}

// FIX: Translated to Russian for locale consistency
function EmptyState({ onStart }: { onStart: () => void }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="text-6xl mb-4">📚</div>
            <h3 className="text-xl font-medium text-white mb-2">Ваша библиотека знаний пуста</h3>
            <p className="text-zinc-400 mb-6 max-w-md">
                Начните первое исследование, чтобы расширить экспертизу MAX в любой теме
            </p>
            <button
                onClick={onStart}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
            >
                <Plus size={18} />
                Новое исследование
            </button>
        </div>
    );
}

function SkillModal({ topic, onClose }: { topic: Topic | null; onClose: () => void }) {
    if (!topic) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
            <div className="bg-zinc-900 rounded-lg p-6 max-w-lg w-full mx-4 border border-zinc-700">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-2">
                        <Brain className="text-indigo-400" size={24} />
                        <h2 className="text-lg font-medium text-white">Topic Lens: {topic.name}</h2>
                    </div>
                    <button onClick={onClose} className="text-zinc-500 hover:text-white">
                        <X size={20} />
                    </button>
                </div>
                <div className="bg-zinc-800/50 rounded-lg p-4 text-sm text-zinc-300 leading-relaxed">
                    {topic.skill || 'No skill generated yet'}
                </div>
                <p className="text-xs text-zinc-500 mt-4">
                    This skill is injected into MAX's system prompt when discussing {topic.name}.
                </p>
            </div>
        </div>
    );
}

function CelebrationModal({ task, onClose }: { task: ResearchTask | null; onClose: () => void }) {
    if (!task) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
            <div className="bg-zinc-900 rounded-lg p-8 max-w-md w-full mx-4 border border-zinc-700 text-center">
                <div className="text-6xl mb-4">🎉</div>
                <h2 className="text-2xl font-bold text-white mb-2">Research Complete!</h2>
                <p className="text-indigo-400 text-lg mb-4">{task.topic}</p>
                <p className="text-zinc-400 text-sm mb-6">
                    MAX has gained new expertise. The Topic Lens is now active.
                </p>
                <button
                    onClick={onClose}
                    className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
                >
                    Awesome!
                </button>
            </div>
        </div>
    );
}

// ============= Main Component =============

export function ResearchLab() {
    const [showNewForm, setShowNewForm] = useState(false);
    const [newTopic, setNewTopic] = useState('');
    const [newDescription, setNewDescription] = useState('');
    const [maxPages, setMaxPages] = useState(10);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
    const [completedTask, setCompletedTask] = useState<ResearchTask | null>(null);
    // UX-007: Topic sort option
    const [sortBy, setSortBy] = useState<'date' | 'name' | 'quality'>('date');
    // UX-008: Topic status filter
    const [statusFilter, setStatusFilter] = useState<'all' | 'complete' | 'incomplete'>('all');

    const {
        topics,
        runningTasks,
        error,
        stats,
        activityFeed,
        connectionStatus, // FIX: Get WebSocket status
        // Queue
        researchQueue,
        maxConcurrentSlots,
        addToQueue,
        removeFromQueue,
        pauseQueueItem,
        resumeQueueItem,
        moveQueueUp,
        moveQueueDown,
        reResearchTopic,
        // Actions
        cancelResearch,
        refreshTopic,
        deleteTopic,
        getTopicSkill
    } = useResearch({
        onTaskComplete: (task) => setCompletedTask(task)
    });

    // UX-006/007/008: Filtered and sorted topics
    const filteredTopics = useMemo(() => {
        let result = topics;

        // UX-006: Search filter
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            result = result.filter(t =>
                t.name.toLowerCase().includes(q) ||
                t.description.toLowerCase().includes(q)
            );
        }

        // UX-008: Status filter
        if (statusFilter !== 'all') {
            result = result.filter(t => t.status === statusFilter);
        }

        // UX-007: Sort
        result = [...result].sort((a, b) => {
            switch (sortBy) {
                case 'name':
                    return a.name.localeCompare(b.name);
                case 'quality':
                    return (b.quality ?? 0) - (a.quality ?? 0);
                case 'date':
                default:
                    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
            }
        });

        return result;
    }, [topics, searchQuery, statusFilter, sortBy]);



    // Handle view skill
    const handleViewSkill = async (topic: Topic) => {
        if (topic.skill) {
            setSelectedTopic(topic);
        } else {
            const skill = await getTopicSkill(topic.id);
            if (skill) {
                setSelectedTopic({ ...topic, skill });
            }
        }
    };

    return (
        <div className="h-full flex flex-col bg-zinc-950 text-white">
            {/* Header */}
            <div className="shrink-0 border-b border-zinc-800 p-4">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Brain className="text-indigo-400" size={28} />
                        <h1 className="text-xl font-semibold">Research Lab</h1>
                    </div>
                    <button
                        onClick={() => setShowNewForm(true)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm transition-colors"
                    >
                        <Plus size={16} />
                        New Research
                    </button>
                </div>

                {/* Search */}
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                    <input
                        type="text"
                        placeholder="Search topics..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm focus:outline-none focus:border-zinc-700"
                    />
                </div>

                {/* UX-007/008: Sort and Filter controls */}
                <div className="flex items-center gap-2 mt-3">
                    {/* Status Filter */}
                    <div className="flex items-center gap-1 bg-zinc-900 rounded-lg p-1 border border-zinc-800">
                        {(['all', 'complete', 'incomplete'] as const).map((status) => (
                            <button
                                key={status}
                                onClick={() => setStatusFilter(status)}
                                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${statusFilter === status
                                        ? 'bg-indigo-600 text-white'
                                        : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                                    }`}
                            >
                                {status === 'all' ? 'Все' : status === 'complete' ? 'Готово' : 'В процессе'}
                            </button>
                        ))}
                    </div>

                    {/* Sort Dropdown */}
                    <select
                        value={sortBy}
                        onChange={e => setSortBy(e.target.value as 'date' | 'name' | 'quality')}
                        className="bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-zinc-700"
                    >
                        <option value="date">По дате</option>
                        <option value="name">По имени</option>
                        <option value="quality">По качеству</option>
                    </select>
                </div>
            </div>

            {/* Content Container with Queue Sidebar */}
            <div className="flex-1 flex overflow-hidden">
                {/* Main Content */}
                <div className="flex-1 overflow-y-auto p-4 space-y-6">
                    {/* Stats Dashboard */}
                    <StatsDashboard stats={stats} connectionStatus={connectionStatus} />

                    {/* Activity Feed */}
                    <ActivityFeed activities={activityFeed} />

                    {/* Running tasks */}
                    {runningTasks.length > 0 && (
                        <section>
                            <h2 className="text-sm font-medium text-zinc-400 mb-3">
                                Running Research ({runningTasks.length})
                            </h2>
                            <div className="space-y-3">
                                {runningTasks.map(task => (
                                    <TaskCard
                                        key={task.id}
                                        task={task}
                                        onCancel={cancelResearch}
                                    />
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Error */}
                    {error && (
                        <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Topics library */}
                    <section>
                        <h2 className="text-sm font-medium text-zinc-400 mb-3">
                            Knowledge Library ({filteredTopics.length})
                        </h2>

                        {filteredTopics.length === 0 && runningTasks.length === 0 ? (
                            <EmptyState onStart={() => setShowNewForm(true)} />
                        ) : filteredTopics.length === 0 ? (
                            <p className="text-zinc-500 text-sm">No topics match your search</p>
                        ) : (
                            <div className="grid gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                                {filteredTopics.map(topic => (
                                    <TopicCard
                                        key={topic.id}
                                        topic={topic}
                                        onDelete={deleteTopic}
                                        onRefresh={refreshTopic}
                                        onViewSkill={handleViewSkill}
                                        onReResearch={reResearchTopic}
                                    />
                                ))}
                            </div>
                        )}
                    </section>
                </div>

                {/* Queue Sidebar */}
                {researchQueue.length > 0 && (
                    <aside className="w-72 shrink-0 border-l border-zinc-800 bg-zinc-950 overflow-y-auto p-3">
                        <ResearchQueuePanel
                            queue={researchQueue}
                            maxSlots={maxConcurrentSlots}
                            onMoveUp={moveQueueUp}
                            onMoveDown={moveQueueDown}
                            onCancel={removeFromQueue}
                            onPause={pauseQueueItem}
                            onResume={resumeQueueItem}
                        />
                    </aside>
                )}
            </div>

            {/* New Research Form Modal */}
            {showNewForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
                    <div className="bg-zinc-900 rounded-lg p-6 max-w-md w-full mx-4 border border-zinc-700">
                        <h2 className="text-lg font-medium mb-4">New Research</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1">Topic *</label>
                                <input
                                    type="text"
                                    value={newTopic}
                                    onChange={e => setNewTopic(e.target.value)}
                                    placeholder="e.g. Python async programming"
                                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500"
                                    autoFocus
                                />
                            </div>

                            <div>
                                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                                <textarea
                                    value={newDescription}
                                    onChange={e => setNewDescription(e.target.value)}
                                    placeholder="What should MAX learn about this topic?"
                                    rows={3}
                                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 resize-none"
                                />
                            </div>

                            <div>
                                <label className="block text-sm text-zinc-400 mb-1">Max Pages: {maxPages}</label>
                                <input
                                    type="range"
                                    min={5}
                                    max={30}
                                    value={maxPages}
                                    onChange={e => setMaxPages(Number(e.target.value))}
                                    className="w-full accent-indigo-500"
                                />
                                <p className="text-xs text-zinc-500 mt-1">
                                    More pages = deeper research, but takes longer
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowNewForm(false)}
                                className="px-4 py-2 text-zinc-400 hover:text-white transition-colors"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={() => {
                                    addToQueue(newTopic, newDescription, maxPages);
                                    setShowNewForm(false);
                                    setNewTopic('');
                                    setNewDescription('');
                                    setMaxPages(10);
                                }}
                                disabled={!newTopic.trim()}
                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                <Plus size={16} />
                                В очередь
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Skill Modal */}
            <SkillModal topic={selectedTopic} onClose={() => setSelectedTopic(null)} />

            {/* Celebration Modal */}
            <CelebrationModal task={completedTask} onClose={() => setCompletedTask(null)} />
        </div>
    );
}
