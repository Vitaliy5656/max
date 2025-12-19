/**
 * RagTab - Knowledge Base (RAG) management component
 * ARCH-003: Extracted from App.tsx
 */
import { Plus, FileText, Trash2 } from 'lucide-react';

interface Document {
    id: string;
    name: string;
    size: string;
    type: string;
    chunks: number;
    status: 'indexed' | 'processing';
}

interface DeleteModalState {
    isOpen: boolean;
    docId: string;
    docName: string;
}

interface RagTabProps {
    documents: Document[];
    isUploading: boolean;
    deleteModal: DeleteModalState;
    setDeleteModal: (state: DeleteModalState) => void;
    onUploadDocument: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onDeleteDocument: () => void;
}

// GlassCard component (inline for simplicity)
function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={`bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl shadow-sm ${className}`}>
            {children}
        </div>
    );
}

export function RagTab({
    documents,
    isUploading,
    deleteModal,
    setDeleteModal,
    onUploadDocument,
    onDeleteDocument,
}: RagTabProps) {
    return (
        <div className="flex-1 overflow-y-auto p-6 animate-tab-in">
            <GlassCard className="p-6">
                <h3 className="text-lg font-semibold mb-4">📚 База Знаний (RAG)</h3>

                {/* Upload */}
                <div className="mb-6">
                    <label className="flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600/20 border border-indigo-500/30 rounded-xl cursor-pointer hover:bg-indigo-600/30 transition-colors">
                        <Plus size={18} />
                        <span>{isUploading ? 'Загрузка...' : 'Загрузить документ'}</span>
                        <input
                            type="file"
                            className="hidden"
                            onChange={onUploadDocument}
                            accept=".pdf,.docx,.txt,.md"
                        />
                    </label>
                </div>

                {/* Documents List */}
                <div className="space-y-2">
                    {documents.length === 0 ? (
                        <p className="text-zinc-500 text-center py-8">Нет загруженных документов</p>
                    ) : (
                        documents.map(doc => (
                            <div key={doc.id} className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                                <div className="flex items-center gap-3">
                                    <FileText size={18} className="text-indigo-400" />
                                    <span className="text-sm">{doc.name}</span>
                                </div>
                                <button
                                    onClick={() => setDeleteModal({ isOpen: true, docId: doc.id, docName: doc.name })}
                                    className="p-2 text-zinc-500 hover:text-red-400 transition-colors"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </GlassCard>

            {/* Delete Modal */}
            {deleteModal.isOpen && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <GlassCard className="p-6 max-w-sm">
                        <h3 className="text-lg font-semibold mb-4">Удалить документ?</h3>
                        <p className="text-zinc-400 mb-6">"{deleteModal.docName}" будет удален безвозвратно.</p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setDeleteModal({ isOpen: false, docId: '', docName: '' })}
                                className="flex-1 px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={onDeleteDocument}
                                className="flex-1 px-4 py-2 bg-red-600 rounded-lg hover:bg-red-500"
                            >
                                Удалить
                            </button>
                        </div>
                    </GlassCard>
                </div>
            )}
        </div>
    );
}

export default RagTab;
