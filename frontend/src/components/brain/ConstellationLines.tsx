/// <reference path="../../types/three-jsx.d.ts" />
/**
 * ConstellationLines - Semantic connections between brain points
 * 
 * Renders lines between semantically similar points.
 * Line opacity based on connection strength.
 */
import { useMemo } from 'react';
import { Line } from '@react-three/drei';
import type { BrainPointData } from './BrainPoint';

export interface Connection {
    from: string;
    to: string;
    strength: number;
}

interface ConstellationLinesProps {
    connections: Connection[];
    points: BrainPointData[];
    visible?: boolean;
}

export function ConstellationLines({
    connections,
    points,
    visible = true
}: ConstellationLinesProps) {
    // Build point lookup map
    const pointMap = useMemo(() => {
        const map = new Map<string, BrainPointData>();
        points.forEach(p => map.set(p.id, p));
        return map;
    }, [points]);

    // Generate line segments
    const lines = useMemo(() => {
        if (!visible) return [];

        return connections
            .map(conn => {
                const fromPoint = pointMap.get(conn.from);
                const toPoint = pointMap.get(conn.to);

                if (!fromPoint || !toPoint) return null;

                return {
                    points: [
                        [fromPoint.x, fromPoint.y, fromPoint.z] as [number, number, number],
                        [toPoint.x, toPoint.y, toPoint.z] as [number, number, number]
                    ],
                    // Blend colors of connected points
                    color: fromPoint.color,
                    opacity: conn.strength * 0.5  // Max 50% opacity
                };
            })
            .filter(Boolean) as {
                points: [number, number, number][];
                color: string;
                opacity: number
            }[];
    }, [connections, pointMap, visible]);

    if (!visible || lines.length === 0) {
        return null;
    }

    return (
        <group>
            {lines.map((line, i) => (
                <Line
                    key={`${connections[i]?.from}-${connections[i]?.to}`}
                    points={line.points}
                    color={line.color}
                    lineWidth={1}
                    transparent
                    opacity={line.opacity}
                />
            ))}
        </group>
    );
}
