/**
 * ResearchStepper Component
 * ARCH-014: Extracted from ResearchLab.tsx
 * 
 * Displays the 5-stage research progress stepper
 */
import { ChevronRight } from 'lucide-react';
import { STAGES, getStageIndex } from './utils';
import type { ResearchTask } from '../../hooks/useResearch';

interface ResearchStepperProps {
    task: ResearchTask;
}

export function ResearchStepper({ task }: ResearchStepperProps) {
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

export default ResearchStepper;
