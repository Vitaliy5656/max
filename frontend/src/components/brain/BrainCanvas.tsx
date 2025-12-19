/// <reference path="../../types/three-jsx.d.ts" />
console.log('[BrainCanvas] FILE LOADED - MODULE INITIALIZED');
/**
 * BrainCanvas - Main 3D brain visualization (Layer 0)
 * 
 * This component renders as a fullscreen background behind
 * the frosted glass UI. It's always visible but subtle.
 * 
 * Props allow highlighting specific points for:
 * - Query Spotlight (during typing)
 * - Thought Path (after answer)
 * - Decay (unused knowledge)
 */
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Suspense } from 'react';
import { BrainPoint, type BrainPointData } from './BrainPoint';
import { ConstellationLines, type Connection } from './ConstellationLines';
import { LoadingSkeleton } from './LoadingSkeleton';

interface BrainCanvasProps {
    points: BrainPointData[];
    connections: Connection[];
    isLoading: boolean;

    // Highlight states (point IDs)
    spotlightIds?: string[];
    thoughtPathIds?: string[];
    decayIds?: string[];

    // Brain Mode (fullscreen interactive)
    isInteractive?: boolean;
    onPointClick?: (point: BrainPointData) => void;
    onPointHover?: (point: BrainPointData | null) => void;

    // Show constellation lines
    showConnections?: boolean;
}

export function BrainCanvas({
    points,
    connections,
    isLoading,
    spotlightIds = [],
    thoughtPathIds = [],
    decayIds = [],
    isInteractive = false,
    onPointClick,
    onPointHover,
    showConnections = true
}: BrainCanvasProps) {
    // Create Set for O(1) lookups
    const spotlightSet = new Set(spotlightIds);
    const thoughtPathSet = new Set(thoughtPathIds);
    const decaySet = new Set(decayIds);

    return (
        <>

            <div
                className="fixed inset-0 z-0"
                style={{
                    pointerEvents: isInteractive ? 'auto' : 'none'
                }}
            >
                <Canvas
                    camera={{ position: [5, 5, 5], fov: 60 }}
                    dpr={[1, 2]}
                    gl={{ antialias: true, alpha: true }}
                    style={{ background: 'transparent' }}
                >
                    {/* Lighting */}
                    <ambientLight intensity={0.4} />
                    <pointLight position={[10, 10, 10]} intensity={0.6} />
                    <pointLight position={[-10, -10, -10]} intensity={0.2} />

                    {/* Camera controls (only in Brain Mode) */}
                    {isInteractive && (
                        <OrbitControls
                            enableDamping
                            dampingFactor={0.05}
                            minDistance={2}
                            maxDistance={20}
                        />
                    )}

                    {/* Content */}
                    <Suspense fallback={<LoadingSkeleton />}>
                        {isLoading ? (
                            <LoadingSkeleton />
                        ) : points.length === 0 ? (
                            /* Empty state - show subtle prompt */
                            <mesh position={[0, 0, 0]}>
                                <sphereGeometry args={[0.3, 16, 16]} />
                                <meshStandardMaterial color="#6366f1" emissive="#6366f1" emissiveIntensity={0.3} transparent opacity={0.5} />
                            </mesh>
                        ) : (
                            <>
                                {/* Constellation Lines */}
                                {showConnections && (
                                    <ConstellationLines
                                        connections={connections}
                                        points={points}
                                        visible={showConnections}
                                    />
                                )}

                                {/* Brain Points */}
                                {points.map((point) => (
                                    <BrainPoint
                                        key={point.id}
                                        point={point}
                                        isSpotlight={spotlightSet.has(point.id)}
                                        isThoughtPath={thoughtPathSet.has(point.id)}
                                        isDecayed={decaySet.has(point.id)}
                                        interactive={isInteractive}
                                        onClick={onPointClick}
                                        onHover={onPointHover}
                                    />
                                ))}
                            </>
                        )}
                    </Suspense>
                </Canvas>
            </div>
        </>
    );
}
