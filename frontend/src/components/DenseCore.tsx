import { BrainCircuit } from 'lucide-react';

interface DenseCoreProps {
    intelligence: number;
    empathy: number;
}

/**
 * DenseCore - Visual representation of AI IQ and EQ metrics.
 * Features animated orbital rings showing progress.
 */
export function DenseCore({ intelligence, empathy }: DenseCoreProps) {
    const size = 200;
    const center = size / 2;

    // IQ Orbit (Outer)
    const rIQ = size / 2 - 10;
    const cIQ = 2 * Math.PI * rIQ;
    const oIQ = cIQ - (intelligence / 100) * cIQ;

    // EQ Orbit (Inner)
    const rEQ = size / 2 - 28;
    const cEQ = 2 * Math.PI * rEQ;
    const oEQ = cEQ - (empathy / 100) * cEQ;

    return (
        <div className="relative flex items-center justify-center py-6" style={{ width: size, height: size }}>

            {/* THE DENSE CORE */}
            <div className="absolute z-10 flex items-center justify-center">
                {/* Layer 1: The Mass */}
                <div
                    className="w-28 h-28 rounded-full bg-[#050505] shadow-[inset_0_0_40px_rgba(0,0,0,1)] border border-white/5 relative z-20 animate-solid-pulse"
                >
                    {/* Glossy Reflection */}
                    <div
                        className="absolute top-0 left-0 w-full h-full rounded-full opacity-20"
                        style={{ background: 'radial-gradient(circle at 35% 35%, rgba(255,255,255,0.15), transparent 50%)' }}
                    />
                </div>

                {/* Layer 2: Energy Glow */}
                <div className="absolute inset-0 w-28 h-28 rounded-full bg-indigo-900/40 blur-xl z-10 animate-inner-glow" />

                {/* Layer 3: Aura */}
                <div className="absolute w-36 h-36 bg-indigo-950/20 rounded-full blur-2xl z-0" />
            </div>

            {/* TWO ORBITS */}
            <svg className="absolute inset-0 w-full h-full z-30 pointer-events-none drop-shadow-[0_0_10px_rgba(0,0,0,0.8)]">
                <defs>
                    <linearGradient id="grad_iq" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#3b82f6" />
                    </linearGradient>
                    <linearGradient id="grad_eq" x1="100%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#f43f5e" />
                        <stop offset="100%" stopColor="#fbbf24" />
                    </linearGradient>
                </defs>

                {/* Orbit 1: IQ */}
                <g className="animate-orbit-iq">
                    <circle cx={center} cy={center} r={rIQ} stroke="rgba(255,255,255,0.03)" strokeWidth={1} fill="none" />
                    <circle
                        cx={center} cy={center} r={rIQ}
                        stroke="url(#grad_iq)" strokeWidth={2} fill="none"
                        strokeDasharray={cIQ} strokeDashoffset={oIQ} strokeLinecap="round"
                        className="transition-all duration-1000 ease-out opacity-90"
                    />
                    <circle cx={center} cy={center - rIQ} r={2} fill="#818cf8" className="animate-pulse" />
                </g>

                {/* Orbit 2: EQ */}
                <g className="animate-orbit-eq">
                    <circle cx={center} cy={center} r={rEQ} stroke="rgba(255,255,255,0.03)" strokeWidth={1} fill="none" />
                    <circle
                        cx={center} cy={center} r={rEQ}
                        stroke="url(#grad_eq)" strokeWidth={2} fill="none"
                        strokeDasharray={cEQ} strokeDashoffset={oEQ} strokeLinecap="round"
                        className="transition-all duration-1000 ease-out opacity-90"
                    />
                    <circle cx={center} cy={center - rEQ} r={2} fill="#fb7185" className="animate-pulse" />
                </g>
            </svg>

            {/* Central Symbol */}
            <div className="absolute z-40 flex items-center justify-center opacity-40 mix-blend-screen pointer-events-none">
                <BrainCircuit size={32} className="text-indigo-200" strokeWidth={1} />
            </div>

            {/* Data Labels */}
            <div className="absolute -bottom-8 w-full flex justify-between px-10 text-[9px] font-mono text-zinc-600 uppercase tracking-widest">
                <div className="flex flex-col items-center">
                    <span className="text-indigo-500/80 mb-0.5">{Math.round(intelligence)}%</span>
                    <span>IQ</span>
                </div>
                <div className="flex flex-col items-center">
                    <span className="text-rose-500/80 mb-0.5">{Math.round(empathy)}%</span>
                    <span>EQ</span>
                </div>
            </div>
        </div>
    );
}
