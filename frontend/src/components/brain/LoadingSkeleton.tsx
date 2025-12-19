/// <reference path="../../types/three-jsx.d.ts" />
/**
 * LoadingSkeleton - Ghost spheres while brain map loads
 * 
 * Animated placeholder spheres arranged in a spiral pattern.
 */
import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export function LoadingSkeleton() {
    const groupRef = useRef<THREE.Group>(null);

    // Generate ghost positions in a spiral pattern
    const ghosts = useMemo(() =>
        Array.from({ length: 20 }, (_, i) => ({
            position: [
                Math.sin(i * 0.5) * (2 + i * 0.1),
                Math.cos(i * 0.3) * (2 + i * 0.1),
                Math.sin(i * 0.7) * (2 + i * 0.05)
            ] as [number, number, number],
            scale: 0.06 + Math.random() * 0.04,
            phase: i * 0.3  // Offset animation phase
        })), []);

    // Slow rotation
    useFrame((state) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = state.clock.elapsedTime * 0.1;
        }
    });

    return (
        <group ref={groupRef}>
            {ghosts.map((ghost, i) => (
                <GhostSphere
                    key={i}
                    position={ghost.position}
                    scale={ghost.scale}
                    phase={ghost.phase}
                />
            ))}
        </group>
    );
}

interface GhostSphereProps {
    position: [number, number, number];
    scale: number;
    phase: number;
}

function GhostSphere({ position, scale, phase }: GhostSphereProps) {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (meshRef.current) {
            // Pulsing opacity
            const opacity = 0.15 + Math.sin(state.clock.elapsedTime * 2 + phase) * 0.1;
            const material = meshRef.current.material as THREE.MeshStandardMaterial;
            material.opacity = opacity;
        }
    });

    return (
        <mesh ref={meshRef} position={position}>
            <sphereGeometry args={[scale, 8, 8]} />
            <meshStandardMaterial
                color="#38bdf8"
                emissive="#6366f1"
                emissiveIntensity={0.3}
                transparent
                opacity={0.5}
            />
        </mesh>
    );
}
