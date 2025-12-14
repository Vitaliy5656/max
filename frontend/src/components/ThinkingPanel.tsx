import { useState, useEffect } from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
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
 */
export function CollapsibleThink({ thinkContent, thinkExpanded, onToggleExpand }: CollapsibleThinkProps) {
    if (!thinkContent) return null;

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
                        animate-in fade-in slide-in-from-top-1 duration-200">
                    <pre className="text-xs text-purple-300/70 whitespace-pre-wrap font-mono leading-relaxed max-h-48 overflow-y-auto">
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
 */
export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
    if (!confidence) return null;

    const { score, level } = confidence;
    const percent = Math.round(score * 100);

    // Color based on confidence level
    const colors = {
        high: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        low: 'bg-red-500/20 text-red-400 border-red-500/30'
    };

    const emoji = level === 'high' ? '🟢' : level === 'medium' ? '🟡' : '🔴';
    const colorClass = colors[level] || colors.medium;

    return (
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium 
                     border ${colorClass} animate-in fade-in zoom-in-95 duration-300`}>
            <span>{emoji}</span>
            <span>{percent}% уверен</span>
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
    queueStatus
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
