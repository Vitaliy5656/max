/**
 * ActivityFeed - Recent activity display for research module
 * ARCH-011: Extracted from ResearchLab.tsx
 */
import { Clock } from 'lucide-react';

interface Activity {
    topic: string;
    action: string;
    time: string;
}

interface ActivityFeedProps {
    activities: Activity[];
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
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

export default ActivityFeed;
