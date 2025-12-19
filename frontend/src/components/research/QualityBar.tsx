/**
 * QualityBar - Visual quality indicator for research topics
 * ARCH-009: Extracted from ResearchLab.tsx
 */

interface QualityBarProps {
    quality: number;
}

export function QualityBar({ quality }: QualityBarProps) {
    const percent = Math.round(quality * 100);

    const getColor = () => {
        if (quality >= 0.7) return 'bg-green-500';
        if (quality >= 0.4) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    const getLabel = () => {
        if (quality >= 0.7) return 'Отлично';
        if (quality >= 0.4) return 'Хорошо';
        return 'Мало данных';
    };

    const tooltip = `Качество: ${percent}%\n• 70%+ = Отлично (достаточно данных)\n• 40-69% = Хорошо (можно дополнить)\n• <40% = Мало данных (нужно исследование)`;

    return (
        <div className="flex items-center gap-2" title={tooltip}>
            <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden cursor-help">
                <div className={`h-full ${getColor()} transition-all`} style={{ width: `${percent}%` }} />
            </div>
            <span className="text-[10px] text-zinc-500 font-mono w-16 text-right">{getLabel()}</span>
        </div>
    );
}

export default QualityBar;
