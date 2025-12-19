import { useState, useEffect } from 'react';
import { ChevronDown, Loader2, Copy, Check } from 'lucide-react';
import type { ConfidenceInfo } from './types';

interface ThinkingIndicatorProps {
    isThinking: boolean;
    thinkingStartTime: number;
}

/**
 * Animated indicator showing AI reasoning process with live timer.
 */
export function ThinkingIndicator({ isThinking, thinkingStartTime }: ThinkingIndicatorProps) {
    const [thinkingElapsed, setThinkingElapsed] = useState(0);

    useEffect(() => {
        if (!isThinking) {
            setThinkingElapsed(0);
            return;
        }

        const interval = setInterval(() => {
            setThinkingElapsed((Date.now() - thinkingStartTime) / 1000);
        }, 100);

        return () => clearInterval(interval);
    }, [isThinking, thinkingStartTime]);

    if (!isThinking) return null;

    return (
        <div className="flex items-center gap-4 p-5 bg-gradient-to-r from-indigo-950/60 to-purple-950/60 
                    border border-indigo-500/30 rounded-2xl backdrop-blur-xl shadow-lg shadow-indigo-500/10
                    max-w-sm animate-in fade-in slide-in-from-left-4 duration-500">
            {/* Animated brain icon with spinner */}
            <div className="relative flex-shrink-0">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-600/30 to-purple-600/30 
                        flex items-center justify-center">
                    <span className="text-2xl">🧠</span>
                </div>
                {/* Spinning border */}
                <div className="absolute inset-0 rounded-full border-2 border-indigo-500/50 border-t-indigo-400 animate-spin"
                    style={{ animationDuration: '1.5s' }} />
                {/* Pulsing glow */}
                <div className="absolute inset-0 rounded-full bg-indigo-500/20 animate-ping"
                    style={{ animationDuration: '2s' }} />
            </div>

            {/* Text content */}
            <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-indigo-200">MAX думает</span>
                    <span className="flex gap-0.5">
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                    <span className="font-mono tabular-nums">{thinkingElapsed.toFixed(1)}s</span>
                    <span className="text-zinc-600">•</span>
                    <span className="text-purple-400/80">Глубокий анализ</span>
                </div>
            </div>
        </div>
    );
}

// Step icon mapping for beautiful visualization
const STEP_ICONS: Record<string, string> = {
    'PLANNING': '🔍',
    'DRAFTING': '📝',
    'EXECUTING': '⚡',
    'VERIFYING': '✅',
    'CRITIQUING': '🔬',
    'ANALYZING': '📊',
    'RESEARCHING': '📚',
    'THINKING': '💭',
};

interface ThinkingStepsDisplayProps {
    steps: Array<{ name: string; content: string }>;
    isThinking: boolean;
}

/**
 * Beautiful live display of thinking steps with animations.
 * UX-020: Collapsible when >3 steps
 */
export function ThinkingStepsDisplay({ steps, isThinking }: ThinkingStepsDisplayProps) {
    const [expanded, setExpanded] = useState(false);

    if (!isThinking || steps.length === 0) return null;

    // UX-020: Show only last 3 steps unless expanded
    const visibleSteps = expanded ? steps : steps.slice(-3);
    const hiddenCount = steps.length - 3;

    return (
        <div className="mt-3 space-y-2 max-w-2xl">
            {/* Show expand button if there are hidden steps */}
            {!expanded && hiddenCount > 0 && (
                <button
                    onClick={() => setExpanded(true)}
                    className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 px-2 py-1 bg-purple-950/30 rounded-md border border-purple-500/20"
                >
                    <span>Показать ещё {hiddenCount} шагов</span>
                </button>
            )}

            {visibleSteps.map((step, index) => {
                const actualIndex = expanded ? index : steps.length - 3 + index;
                const icon = STEP_ICONS[step.name.toUpperCase()] || '💭';
                const isLatest = actualIndex === steps.length - 1;

                return (
                    <div
                        key={actualIndex}
                        className={`flex items-start gap-3 p-4 rounded-xl transition-all duration-300
                            ${isLatest
                                ? 'bg-gradient-to-r from-purple-950/50 to-indigo-950/50 border border-purple-500/30'
                                : 'bg-zinc-900/30 border border-zinc-700/20 opacity-70'}
                            animate-in fade-in slide-in-from-left-2`}
                        style={{ animationDelay: `${index * 100}ms` }}
                    >
                        {/* Step icon */}
                        <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center
                            ${isLatest ? 'bg-purple-500/20' : 'bg-zinc-800/50'}`}>
                            <span className="text-xl">{icon}</span>
                        </div>

                        {/* Step content - full text visible */}
                        <div className="flex-1 min-w-0">
                            <div className={`text-xs font-bold uppercase tracking-wider mb-1
                                ${isLatest ? 'text-purple-400' : 'text-zinc-500'}`}>
                                {step.name}
                            </div>
                            <div className={`text-sm leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto
                                ${isLatest ? 'text-zinc-200' : 'text-zinc-400'}`}>
                                {step.content}
                            </div>
                        </div>

                        {/* Live indicator for latest step */}
                        {isLatest && (
                            <div className="flex-shrink-0 mt-1">
                                <div className="w-2.5 h-2.5 bg-purple-400 rounded-full animate-pulse shadow-lg shadow-purple-500/50" />
                            </div>
                        )}
                    </div>
                );
            })}

            {/* Collapse button when expanded */}
            {expanded && steps.length > 3 && (
                <button
                    onClick={() => setExpanded(false)}
                    className="text-xs text-zinc-500 hover:text-zinc-400 flex items-center gap-1 px-2 py-1"
                >
                    Свернуть
                </button>
            )}
        </div>
    );
}

interface ModelLoadingIndicatorProps {
    loadingModel: string | null;
}

/**
 * Shows model name when hot-swapping models.
 */
export function ModelLoadingIndicator({ loadingModel }: ModelLoadingIndicatorProps) {
    if (!loadingModel) return null;

    return (
        <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-amber-950/60 to-orange-950/60 
                    border border-amber-500/30 rounded-xl backdrop-blur-xl
                    max-w-xs animate-in fade-in slide-in-from-left-4 duration-300">
            <Loader2 size={20} className="text-amber-400 animate-spin" />
            <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium text-amber-200">Загрузка модели</span>
                <span className="text-xs text-amber-400/70 truncate max-w-[180px]">{loadingModel}</span>
            </div>
        </div>
    );
}

interface CollapsibleThinkProps {
    thinkContent: string;
    thinkExpanded: boolean;
    onToggleExpand: () => void;
}

/**
 * Collapsible panel showing AI's internal reasoning process.
 * UX-021: Added copy button for think content
 */
export function CollapsibleThink({ thinkContent, thinkExpanded, onToggleExpand }: CollapsibleThinkProps) {
    const [copied, setCopied] = useState(false);

    if (!thinkContent) return null;

    const handleCopy = async (e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await navigator.clipboard.writeText(thinkContent);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    return (
        <div className="mb-4 animate-in fade-in slide-in-from-top-2 duration-300">
            <button
                onClick={onToggleExpand}
                className="flex items-center gap-2 px-3 py-2 bg-purple-950/40 hover:bg-purple-950/60 
                   border border-purple-500/20 rounded-lg transition-all group w-full"
            >
                <span className="text-purple-400">🧠</span>
                <span className="text-sm text-purple-300/80">Процесс рассуждения</span>
                <ChevronDown
                    size={14}
                    className={`text-purple-400/60 ml-auto transition-transform duration-200 
                     ${thinkExpanded ? 'rotate-180' : ''}`}
                />
            </button>

            {thinkExpanded && (
                <div className="mt-2 p-4 bg-purple-950/20 border border-purple-500/10 rounded-lg
                        animate-in fade-in slide-in-from-top-1 duration-200 relative">
                    {/* UX-021: Copy button */}
                    <button
                        onClick={handleCopy}
                        className="absolute top-2 right-2 p-1.5 rounded-md bg-purple-900/30 
                                 hover:bg-purple-900/50 text-purple-400 transition-colors"
                        title="Скопировать"
                    >
                        {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                    </button>
                    <pre className="text-xs text-purple-300/70 whitespace-pre-wrap font-mono leading-relaxed max-h-48 overflow-y-auto pr-8">
                        {thinkContent}
                    </pre>
                </div>
            )}
        </div>
    );
}

interface ConfidenceBadgeProps {
    confidence: ConfidenceInfo | null;
}

/**
 * Badge showing AI's confidence level in the response.
 * UX-022: Enhanced with gradient confidence visualization
 */
export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
    if (!confidence) return null;

    const { score, level } = confidence;
    const percent = Math.round(score * 100);

    // UX-022: Gradient colors based on exact score (not just 3 levels)
    const getGradientColor = (s: number) => {
        if (s >= 0.8) return 'from-emerald-500/30 to-emerald-400/10 border-emerald-500/30 text-emerald-400';
        if (s >= 0.6) return 'from-lime-500/30 to-lime-400/10 border-lime-500/30 text-lime-400';
        if (s >= 0.4) return 'from-yellow-500/30 to-yellow-400/10 border-yellow-500/30 text-yellow-400';
        if (s >= 0.2) return 'from-orange-500/30 to-orange-400/10 border-orange-500/30 text-orange-400';
        return 'from-red-500/30 to-red-400/10 border-red-500/30 text-red-400';
    };

    const getEmoji = (s: number) => {
        if (s >= 0.8) return '🟢';
        if (s >= 0.6) return '🟡';
        if (s >= 0.4) return '🟠';
        return '🔴';
    };

    const gradientClass = getGradientColor(score);
    const emoji = getEmoji(score);

    return (
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium 
                     border bg-gradient-to-r ${gradientClass} animate-in fade-in zoom-in-95 duration-300`}
            title={`Уровень уверенности: ${level} (${percent}%)`}>
            <span>{emoji}</span>
            <span>{percent}% уверен</span>
            {/* Mini progress bar */}
            <div className="w-12 h-1.5 bg-zinc-800 rounded-full overflow-hidden ml-1">
                <div
                    className="h-full bg-current transition-all duration-500"
                    style={{ width: `${percent}%` }}
                />
            </div>
        </div>
    );
}

interface ThinkingPanelProps {
    isThinking: boolean;
    thinkingStartTime: number;
    thinkContent: string;
    thinkExpanded: boolean;
    onToggleExpand: () => void;
    lastConfidence: ConfidenceInfo | null;
    loadingModel: string | null;
    isGenerating: boolean;
    queueStatus?: 'inactive' | 'waiting' | 'acquired';
    thinkingSteps?: Array<{ name: string; content: string }>;
}

/**
 * Combined panel for all AI status indicators.
 */
export function ThinkingPanel({
    isThinking,
    thinkingStartTime,
    thinkContent,
    thinkExpanded,
    onToggleExpand,
    lastConfidence,
    loadingModel,
    isGenerating,
    queueStatus,
    thinkingSteps = []
}: ThinkingPanelProps) {
    return (
        <>
            {/* Queue Status */}
            {queueStatus === 'waiting' && (
                <div className="pl-12 md:pl-14 mb-2">
                    <div className="flex items-center gap-3 p-3 bg-zinc-900/40 border border-zinc-700/50 rounded-xl max-w-xs animate-pulse">
                        <div className="w-2 h-2 bg-yellow-500 rounded-full animate-ping" />
                        <span className="text-sm text-zinc-400">Ожидание слота...</span>
                    </div>
                </div>
            )}
            {/* Show thinking indicator when model is thinking (reasoning) */}
            {isThinking && (
                <div className="pl-12 md:pl-14">
                    <ThinkingIndicator isThinking={isThinking} thinkingStartTime={thinkingStartTime} />
                    {/* Live Thinking Steps */}
                    <ThinkingStepsDisplay steps={thinkingSteps} isThinking={isThinking} />
                </div>
            )}

            {/* Show model loading indicator */}
            {loadingModel && (
                <div className="pl-12 md:pl-14">
                    <ModelLoadingIndicator loadingModel={loadingModel} />
                </div>
            )}

            {/* Collapsible Think Block - shows after response if thinking occurred */}
            {!isGenerating && thinkContent && (
                <div className="pl-12 md:pl-14 max-w-2xl">
                    <CollapsibleThink
                        thinkContent={thinkContent}
                        thinkExpanded={thinkExpanded}
                        onToggleExpand={onToggleExpand}
                    />
                </div>
            )}

            {/* Confidence Badge - shows after response */}
            {!isGenerating && lastConfidence && (
                <div className="pl-12 md:pl-14 mt-2">
                    <ConfidenceBadge confidence={lastConfidence} />
                </div>
            )}
        </>
    );
}

export default ThinkingPanel;
