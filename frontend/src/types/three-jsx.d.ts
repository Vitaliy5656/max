// Global ambient module declaration to extend JSX for Three.js
// This file should be automatically included since it's in src/
import type { ThreeElements } from '@react-three/fiber';

declare module 'react' {
    namespace JSX {
        interface IntrinsicElements extends ThreeElements { }
    }
}
