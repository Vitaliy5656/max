/**
 * SkillModal Component
 * ARCH-016: Extracted from ResearchLab.tsx
 * 
 * Modal for displaying Topic Lens skills
 */
import { Brain, X } from 'lucide-react';
import type { Topic } from '../../hooks/useResearch';

interface SkillModalProps {
    topic: Topic | null;
    onClose: () => void;
}

export function SkillModal({ topic, onClose }: SkillModalProps) {
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

export default SkillModal;
