/**
 * Research Utilities
 * ARCH-014/015: Shared constants and functions for research components
 */

// Stage mapping for stepper
export const STAGES = [
    { key: 'planning', label: 'Planning', emoji: '📋' },
    { key: 'hunting', label: 'Hunting', emoji: '🎯' },
    { key: 'mining', label: 'Mining', emoji: '⛏️' },
    { key: 'polishing', label: 'Polishing', emoji: '💎' },
    { key: 'diploma', label: 'Diploma', emoji: '🎓' },
];

// Get current stage index from task
export function getStageIndex(stage: string): number {
    const idx = STAGES.findIndex(s => stage.toLowerCase().includes(s.key));
    return idx >= 0 ? idx : 0;
}

// Format ETA
export function formatETA(seconds?: number): string {
    if (!seconds || seconds <= 0) return '';
    if (seconds < 60) return `~${seconds}s`;
    const mins = Math.ceil(seconds / 60);
    return `~${mins} min`;
}
