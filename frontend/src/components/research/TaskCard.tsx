/**
 * TaskCard Component
 * ARCH-014: Extracted from ResearchLab.tsx
 * 
 * Displays a running research task with stepper and progress bar
 */
import { X } from 'lucide-react';
import { ResearchStepper } from './ResearchStepper';
import { formatETA } from './utils';
import type { ResearchTask } from '../../hooks/useResearch';

interface TaskCardProps {
    task: ResearchTask;
    onCancel: (id: string) => void;
}

export function TaskCard({ task, onCancel }: TaskCardProps) {
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

export default TaskCard;
