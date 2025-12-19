/**
 * TemplatesTab - Prompt templates management
 * ARCH-005: Extracted from App.tsx
 */

interface Template {
    id: string;
    name: string;
    content: string;
    category: string;
}

interface TemplatesTabProps {
    templates: Template[];
    filteredTemplates: Template[];
    tplCategory: string;
    setTplCategory: (category: string) => void;
    onUseTemplate: (template: Template) => void;
}

// GlassCard component (inline for simplicity)
function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={`bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl shadow-sm ${className}`}>
            {children}
        </div>
    );
}

export function TemplatesTab({
    templates,
    filteredTemplates,
    tplCategory,
    setTplCategory,
    onUseTemplate,
}: TemplatesTabProps) {
    // Get unique categories
    const categories = ['All', ...new Set(templates.map(t => t.category))];

    return (
        <div className="flex-1 overflow-y-auto p-6 animate-tab-in">
            <GlassCard className="p-6">
                <h3 className="text-lg font-semibold mb-4">📋 Шаблоны промптов</h3>

                {/* Category Filter */}
                <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                    {categories.map(cat => (
                        <button
                            key={cat}
                            onClick={() => setTplCategory(cat)}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${tplCategory === cat
                                    ? 'bg-indigo-600 text-white'
                                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                                }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>

                {/* Templates Grid */}
                <div className="grid gap-3">
                    {filteredTemplates.length === 0 ? (
                        <p className="text-zinc-500 text-center py-8">Нет шаблонов</p>
                    ) : (
                        filteredTemplates.map(tpl => (
                            <button
                                key={tpl.id}
                                onClick={() => onUseTemplate(tpl)}
                                className="text-left p-4 bg-zinc-800/50 hover:bg-zinc-800 rounded-xl transition-colors"
                            >
                                <h4 className="font-medium mb-1">{tpl.name}</h4>
                                <p className="text-xs text-zinc-500 line-clamp-2">{tpl.content}</p>
                            </button>
                        ))
                    )}
                </div>
            </GlassCard>
        </div>
    );
}

export default TemplatesTab;
