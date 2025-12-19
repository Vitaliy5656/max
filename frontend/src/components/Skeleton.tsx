/**
 * Skeleton Loading Component
 * 
 * Provides shimmer loading placeholders for better UX during async operations.
 */
import React from 'react';

interface SkeletonProps {
    className?: string;
    variant?: 'text' | 'title' | 'avatar' | 'button' | 'custom';
    width?: string | number;
    height?: string | number;
    count?: number;
}

/**
 * Individual skeleton line with shimmer animation
 */
function SkeletonLine({ className = '', variant = 'text', width, height }: Omit<SkeletonProps, 'count'>) {
    const variantClass = variant !== 'custom' ? `skeleton-${variant}` : '';
    const style: React.CSSProperties = {};

    if (width) style.width = typeof width === 'number' ? `${width}px` : width;
    if (height) style.height = typeof height === 'number' ? `${height}px` : height;

    return (
        <div
            className={`skeleton ${variantClass} ${className}`}
            style={style}
            aria-hidden="true"
        />
    );
}

/**
 * Skeleton component with optional multiple lines
 */
export function Skeleton({ count = 1, ...props }: SkeletonProps) {
    if (count === 1) {
        return <SkeletonLine {...props} />;
    }

    return (
        <div className="space-y-2">
            {Array.from({ length: count }).map((_, i) => (
                <SkeletonLine key={i} {...props} />
            ))}
        </div>
    );
}

/**
 * Card skeleton for loading states
 */
export function SkeletonCard({ className = '' }: { className?: string }) {
    return (
        <div className={`p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg ${className}`}>
            <div className="flex items-center gap-3 mb-3">
                <Skeleton variant="avatar" />
                <div className="flex-1 space-y-2">
                    <Skeleton variant="title" />
                    <Skeleton variant="text" width="40%" />
                </div>
            </div>
            <Skeleton count={3} />
        </div>
    );
}

/**
 * Message skeleton for chat loading
 */
export function SkeletonMessage({ isUser = false }: { isUser?: boolean }) {
    return (
        <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
            {!isUser && <Skeleton variant="avatar" />}
            <div className={`max-w-[60%] space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
                <Skeleton variant="custom" width="200px" height="60px" className="rounded-2xl" />
            </div>
            {isUser && <Skeleton variant="avatar" />}
        </div>
    );
}

export default Skeleton;
