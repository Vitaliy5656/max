/**
 * CelebrationModal Component
 * ARCH-016: Extracted from ResearchLab.tsx
 * 
 * Modal displayed when research completes
 */
import type { ResearchTask } from '../../hooks/useResearch';

interface CelebrationModalProps {
    task: ResearchTask | null;
    onClose: () => void;
}

export function CelebrationModal({ task, onClose }: CelebrationModalProps) {
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

export default CelebrationModal;
