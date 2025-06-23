// src/declarations.d.ts
/// <reference types="react" />

import type { ReactThreeFiber } from '@react-three/fiber';

declare global {
  namespace JSX {
    // Для R3F v8 геометрії, матеріали, світло, mesh тощо описані тут
    interface IntrinsicElements extends ReactThreeFiber['intrinsicElements'] {}
  }
}
