/// <reference path="../../types/three-jsx.d.ts" />
/**
 * BrainPoint - Individual 3D point in the brain map
 * 
 * States:
 * - Default: normal color, small size
 * - Spotlight: glowing (relevant to current query)
 * - ThoughtPath: pulsing (used in answer)
 * - Decayed: gray, faded (unused knowledge)
 * - Hovered: enlarged + emissive glow (Brain Mode only)
 */
import { useState, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import type { Mesh } from 'three';

export interface BrainPointData {
    id: string;
    x: number;
    y: number;
    z: number;
    topic: string;
    topic_id: string;
    text: string;
    color: string;
    point_count?: number;
    is_centroid?: boolean;
    created_at?: string;
}

interface BrainPointProps {
    point: BrainPointData;
    isSpotlight?: boolean;
    isThoughtPath?: boolean;
    isDecayed?: boolean;
    interactive?: boolean;
    onClick?: (point: BrainPointData) => void;
    onHover?: (point: BrainPointData | null) => void;
}

export function BrainPoint({
    point,
    isSpotlight = false,
    isThoughtPath = false,
    isDecayed = false,
    interactive = false,
    onClick,
    onHover
}: BrainPointProps) {
    const meshRef = useRef<Mesh>(null);
    const [hovered, setHovered] = useState(false);

    // Base size (centroids are larger)
    const baseSize = point.is_centroid ? 0.15 : 0.05;

    // Determine visual state
    const getColor = () => {
        if (isDecayed) return '#404040';  // Gray for unused
        if (isSpotlight) return '#fbbf24';  // Gold for spotlight
        if (isThoughtPath) return '#22d3ee';  // Cyan for thought path
        return point.color;
    };

    const getEmissive = () => {
        if (hovered && interactive) return point.color;
        if (isSpotlight) return '#fbbf24';
        if (isThoughtPath) return '#22d3ee';
        return '#000000';
    };

    const getEmissiveIntensity = () => {
        if (hovered && interactive) return 0.4;
        if (isSpotlight) return 0.6;
        if (isThoughtPath) return 0.3;
        return 0;
    };

    const getOpacity = () => {
        if (isDecayed) return 0.3;
        return 1.0;
    };

    // Animation for spotlight/thought path pulsing
    useFrame((state) => {
        if (meshRef.current) {
            // Gentle pulse for spotlight
            if (isSpotlight) {
                const scale = baseSize * (1 + Math.sin(state.clock.elapsedTime * 3) * 0.2);
                meshRef.current.scale.setScalar(scale / baseSize);
            } else if (isThoughtPath) {
                // Slower pulse for thought path
                const scale = baseSize * (1 + Math.sin(state.clock.elapsedTime * 2) * 0.1);
                meshRef.current.scale.setScalar(scale / baseSize);
            } else {
                // Reset scale
                const targetScale = hovered && interactive ? 1.5 : 1.0;
                meshRef.current.scale.lerp(
                    { x: targetScale, y: targetScale, z: targetScale },
                    0.1
                );
            }
        }
    });

    const handleClick = () => {
        if (interactive && onClick) {
            onClick(point);
        }
    };

    const handlePointerOver = () => {
        if (interactive) {
            setHovered(true);
            onHover?.(point);
            document.body.style.cursor = 'pointer';
        }
    };

    const handlePointerOut = () => {
        setHovered(false);
        onHover?.(null);
        document.body.style.cursor = 'auto';
    };

    return (
        <mesh
            ref={meshRef}
            position={[point.x, point.y, point.z]}
            onClick={handleClick}
            onPointerOver={handlePointerOver}
            onPointerOut={handlePointerOut}
        >
            <sphereGeometry args={[baseSize, 16, 16]} />
            <meshStandardMaterial
                color={getColor()}
                emissive={getEmissive()}
                emissiveIntensity={getEmissiveIntensity()}
                transparent={isDecayed}
                opacity={getOpacity()}
            />
        </mesh>
    );
}
