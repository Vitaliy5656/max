/**
 * StatsDashboard - Overview statistics for research module
 * ARCH-010: Extracted from ResearchLab.tsx
 */
import { Layers, Database, BarChart2, Globe } from 'lucide-react';

interface Stats {
    totalTopics: number;
    totalChunks: number;
    completeCount: number;
    avgQuality: number;
}

interface StatsDashboardProps {
    stats: Stats;
    connectionStatus: 'connecting' | 'connected' | 'disconnected';
}

export function StatsDashboard({ stats, connectionStatus }: StatsDashboardProps) {
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

export default StatsDashboard;
