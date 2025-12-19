/**
 * AgentTab - Autonomous Agent (Auto-GPT) interface
 * ARCH-004: Extracted from App.tsx
 */
import { Play, X, CheckCircle2, AlertTriangle, Loader2, RotateCw } from 'lucide-react';

interface AgentStep {
    id: number;
    action: string;
    title: string;
    desc: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
}

interface AgentState {
    agentGoal: string;
    setAgentGoal: (goal: string) => void;
    agentRunning: boolean;
    agentSteps: AgentStep[];
    agentFailed: boolean;
    agentConfirmModal: boolean;
    requestAgent: () => void;
    confirmAgent: () => void;
    cancelAgent: () => void;
    stopAgent: () => void;
}

interface AgentTabProps {
    agent: AgentState;
}

// GlassCard component (inline for simplicity)
function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={`bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl shadow-sm ${className}`}>
            {children}
        </div>
    );
}

export function AgentTab({ agent }: AgentTabProps) {
    return (
        <div className="flex-1 overflow-y-auto p-6 animate-tab-in">
            <GlassCard className="p-6">
                <h3 className="text-lg font-semibold mb-4">🤖 Автономный Агент</h3>

                {/* Goal Input */}
                <div className="mb-6">
                    <textarea
                        value={agent.agentGoal}
                        onChange={(e) => agent.setAgentGoal(e.target.value)}
                        placeholder="Опишите цель для агента..."
                        className="w-full bg-zinc-800/50 border border-white/10 rounded-xl p-4 text-sm resize-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50"
                        rows={3}
                    />
                </div>

                {/* Start/Stop Button */}
                {agent.agentRunning ? (
                    <button
                        onClick={agent.stopAgent}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-colors bg-red-600/20 text-red-400 hover:bg-red-600/30 border border-red-500/30"
                    >
                        <X size={18} />
                        Остановить агента
                    </button>
                ) : (
                    <button
                        onClick={agent.requestAgent}
                        disabled={!agent.agentGoal.trim()}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-colors bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Play size={18} />
                        Запустить агента
                    </button>
                )}

                {/* Steps */}
                {agent.agentSteps.length > 0 && (
                    <div className="mt-6 space-y-2">
                        <h4 className="text-sm font-medium text-zinc-400">Шаги:</h4>
                        {agent.agentSteps.map((step, idx) => (
                            <div key={step.id || idx} className="flex items-start gap-3 p-3 bg-zinc-800/30 rounded-lg">
                                {step.status === 'completed' ? (
                                    <CheckCircle2 size={18} className="text-emerald-400 mt-0.5" />
                                ) : step.status === 'failed' ? (
                                    <AlertTriangle size={18} className="text-red-400 mt-0.5" />
                                ) : (
                                    <Loader2 size={18} className="text-indigo-400 animate-spin mt-0.5" />
                                )}
                                <div>
                                    <p className="text-sm font-medium">{step.title || step.action}</p>
                                    {step.desc && <p className="text-xs text-zinc-500 mt-1">{step.desc}</p>}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Retry button */}
                {agent.agentFailed && !agent.agentRunning && (
                    <button
                        onClick={agent.confirmAgent}
                        className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 bg-amber-600/20 text-amber-400 border border-amber-500/30 rounded-xl hover:bg-amber-600/30"
                    >
                        <RotateCw size={16} />
                        Повторить
                    </button>
                )}
            </GlassCard>

            {/* Confirm Modal */}
            {agent.agentConfirmModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <GlassCard className="p-6 max-w-sm">
                        <h3 className="text-lg font-semibold mb-4">⚠️ Запустить агента?</h3>
                        <p className="text-zinc-400 mb-6">Агент будет выполнять действия автономно. Убедитесь, что цель сформулирована правильно.</p>
                        <div className="flex gap-3">
                            <button onClick={agent.cancelAgent} className="flex-1 px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700">Отмена</button>
                            <button onClick={agent.confirmAgent} className="flex-1 px-4 py-2 bg-indigo-600 rounded-lg hover:bg-indigo-500">Запустить</button>
                        </div>
                    </GlassCard>
                </div>
            )}
        </div>
    );
}

export default AgentTab;
