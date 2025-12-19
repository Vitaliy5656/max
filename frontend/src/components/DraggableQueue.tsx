/**
 * Draggable Queue Component
 * UX-009: Drag-and-drop reordering for research queue using @dnd-kit
 */
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, X, Play, Pause } from 'lucide-react';

export interface DraggableQueueItem {
    id: string;
    topic: string;
    status: 'queued' | 'running' | 'paused';
    progress?: number;
}

interface DraggableQueueProps {
    items: DraggableQueueItem[];
    onReorder: (items: DraggableQueueItem[]) => void;
    onRemove: (id: string) => void;
    onPause?: (id: string) => void;
    onResume?: (id: string) => void;
}

// Single sortable item
function SortableItem({
    item,
    onRemove,
    onPause,
    onResume
}: {
    item: DraggableQueueItem;
    onRemove: (id: string) => void;
    onPause?: (id: string) => void;
    onResume?: (id: string) => void;
}) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: item.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`flex items-center gap-2 p-2.5 rounded-lg border transition-colors ${isDragging
                ? 'bg-indigo-900/30 border-indigo-500/50'
                : 'bg-zinc-800/50 border-zinc-700/50 hover:border-zinc-600'
                }`}
        >
            {/* Drag Handle */}
            <button
                {...attributes}
                {...listeners}
                className="p-1 cursor-grab active:cursor-grabbing text-zinc-500 hover:text-zinc-300"
                title="Перетащить"
            >
                <GripVertical size={14} />
            </button>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="text-sm text-zinc-200 truncate">{item.topic}</div>
                <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${item.status === 'running' ? 'bg-green-900/30 text-green-400' :
                        item.status === 'paused' ? 'bg-yellow-900/30 text-yellow-400' :
                            'bg-zinc-700 text-zinc-400'
                        }`}>
                        {item.status === 'running' ? '▶ Running' :
                            item.status === 'paused' ? '⏸ Paused' : 'Queued'}
                    </span>
                    {item.progress !== undefined && (
                        <div className="flex-1 h-1 bg-zinc-700 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-indigo-500 transition-all"
                                style={{ width: `${item.progress * 100}%` }}
                            />
                        </div>
                    )}
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1">
                {item.status === 'paused' && onResume && (
                    <button
                        onClick={() => onResume(item.id)}
                        className="p-1.5 text-yellow-500 hover:bg-yellow-900/30 rounded"
                        title="Продолжить"
                    >
                        <Play size={12} />
                    </button>
                )}
                {item.status === 'running' && onPause && (
                    <button
                        onClick={() => onPause(item.id)}
                        className="p-1.5 text-zinc-400 hover:bg-zinc-700 rounded"
                        title="Пауза"
                    >
                        <Pause size={12} />
                    </button>
                )}
                <button
                    onClick={() => onRemove(item.id)}
                    className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-900/20 rounded"
                    title="Удалить"
                >
                    <X size={12} />
                </button>
            </div>
        </div>
    );
}

export function DraggableQueue({
    items,
    onReorder,
    onRemove,
    onPause,
    onResume
}: DraggableQueueProps) {
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;

        if (over && active.id !== over.id) {
            const oldIndex = items.findIndex((item) => item.id === active.id);
            const newIndex = items.findIndex((item) => item.id === over.id);
            const newItems = arrayMove(items, oldIndex, newIndex);
            onReorder(newItems);
        }
    };

    if (items.length === 0) {
        return (
            <div className="text-center py-8 text-zinc-500 text-sm">
                Очередь пуста
            </div>
        );
    }

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
        >
            <SortableContext items={items} strategy={verticalListSortingStrategy}>
                <div className="space-y-2">
                    {items.map((item) => (
                        <SortableItem
                            key={item.id}
                            item={item}
                            onRemove={onRemove}
                            onPause={onPause}
                            onResume={onResume}
                        />
                    ))}
                </div>
            </SortableContext>
        </DndContext>
    );
}

export default DraggableQueue;
