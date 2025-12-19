# 🧠 Brain Map Visualization — Implementation Plan v2.0

> **Цель:** Живая 3D визуализация knowledge graph как **фоновый слой** всего интерфейса.
> Brain всегда виден за frosted glass UI, реагирует на действия пользователя в реальном времени.

> [!IMPORTANT]
> Реализовать **ПОСЛЕ** основного Research Lab (Phase 1). Это отдельная задача.

---

## 🎯 Vision Statement

**Brain Map — это не отдельный экран, а живой организм на фоне.**

- Мозг **ВСЕГДА виден** за полупрозрачным интерфейсом (frosted glass effect)
- При вопросе — точки **загораются** (Query Spotlight)
- При ответе — видна **анимация мышления** (Thought Path)
- Кнопка `[🧠 Enter Brain]` → fullscreen режим для глубокого исследования

---

## 📐 Architecture: Layer System

```
┌──────────────────────────────────────────────────────────────────┐
│                     VISUAL LAYER STACK                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────┐  ┌─────────────────────────────────┐                │
│  │ SIDEBAR │  │         CHAT                    │   ●   ●       │
│  │ ░░░░░░░ │  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ ●   ●   ●     │
│  │ ░░░░░░░ │  │  backdrop-blur: 20px            │   ●━━━●       │
│  │ ░░░░░░░ │  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ ●       ●  ●  │
│  │ ░░░░░░░ │  │         messages                │    ●  ●       │
│  │ ░░░░░░░ │  │                                 │  ●    ●   ●   │
│  │ ░░[🧠]░ │  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │    ●━━━●━━●   │
│  └─────────┘  └─────────────────────────────────┘      ●   ●    │
│                                                   ●              │
│       ▲               ▲                              ▲           │
│   Layer 2         Layer 1                        Layer 0        │
│   z-20            z-10                           z-0            │
│   Sidebar         Chat                           BRAIN          │
│   Frosted         Frosted                        (3D WebGL)     │
└──────────────────────────────────────────────────────────────────┘
```

| Layer | Z-Index | Component | Effect |
|-------|---------|-----------|--------|
| 0 | `z-0` | 3D Brain Canvas | Fullscreen WebGL, always rendered |
| 1 | `z-10` | Chat Panel | `backdrop-blur-xl` + `bg-black/60` |
| 2 | `z-20` | Sidebar | `backdrop-blur-xl` + `bg-black/70` |
| 3 | `z-50` | Brain Mode UI | Fullscreen tools (when Enter Brain clicked) |

---

## 🔥 Feature List (Prioritized)

### Phase 1: Core (MVP)

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 1.1 | **Living Background** | Brain as fullscreen WebGL canvas behind frosted UI | P0 |
| 1.2 | **UMAP Projection** | 768D → 3D via `run_in_executor` (non-blocking) | P0 |
| 1.3 | **Hierarchical Levels** | Level 0 (topics) → Level 1 (clusters) → Level 2 (points) | P0 |
| 1.4 | **Enter Brain Mode** | Button to hide UI, show fullscreen brain with toolbar | P0 |
| 1.5 | **Constellation Lines** | Semantic connections between points | P1 |
| 1.6 | **Query Spotlight** | Points glow when relevant to current question | P1 |
| 1.7 | **Thought Path Replay** | Animate which points were used in answer | P1 |

### Phase 2: Advanced

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 2.1 | **Temporal Layer (4D)** | Timeline slider, playback of knowledge growth | P2 |
| 2.2 | **Decay Visualization** | Unused points → gray, with delete option | P2 |
| 2.3 | **Knowledge Gaps** | Detect and highlight empty areas between clusters | P2 |
| 2.4 | **Multi-Select + Batch** | Lasso selection, batch delete/archive/merge | P2 |

### Phase 3: Polish

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 3.1 | **Annotations** | User tags/notes on points (#important, #verify) | P3 |
| 3.2 | **Export** | Screenshot, video recording of exploration | P3 |
| 3.3 | **Search in Brain** | Text search → zoom to matching points | P3 |

---

## 🎬 UX Flows

### Flow 1: Normal Chat Mode

```
1. User opens app
2. Brain renders on Layer 0 (subtle, softly pulsing)
3. Sidebar + Chat render on top with frosted glass
4. User can see brain "breathing" behind the text
5. Brain is NOT interactive in this mode (click-through)
```

### Flow 2: Query Spotlight (во время вопроса)

```
1. User types question in chat
2. As they type, brain points start to glow based on semantic similarity
3. When send → bright pulse animation
4. During streaming response → Thought Path lights up
5. After response → glow fades, path remains visible briefly
```

### Flow 3: Enter Brain Mode

```
1. User clicks [🧠 Enter Brain] button (in sidebar)
2. Animation sequence:
   a. Sidebar slides LEFT (300ms)
   b. Chat panel fades + scales to center (400ms)
   c. Brain points EXPLODE outward from center (500ms)
   d. Toolbar slides DOWN from top (300ms)
   e. Timeline appears at BOTTOM (300ms)
3. Brain is now INTERACTIVE:
   - OrbitControls (drag to rotate, scroll to zoom)
   - Click point → show details panel
   - Click centroid → drill down to cluster
   - Lasso select → batch actions
4. [← Exit] button → reverse animation, back to chat
```

### Flow 4: Temporal Playback

```
1. In Brain Mode, timeline visible at bottom
2. Drag slider → brain shows state at that date
3. Play button → animate knowledge growth over time
4. Points fade in as they were created
5. Constellation lines animate connections forming
```

---

## 🛠 Technical Implementation

### Dependencies

```txt
# Backend (requirements.txt)
umap-learn>=0.5.0        # Dimensionality reduction

# Frontend (package.json)
@react-three/fiber       # React wrapper for Three.js
@react-three/drei        # OrbitControls, helpers
three                    # 3D engine
```

---

### Backend: src/core/research/brain_map.py

```python
"""
Brain Map Generator

Converts ChromaDB embeddings to 3D projections via UMAP.
All heavy computation runs in executor to avoid blocking event loop.
"""
import asyncio
import json
import pickle
import umap
import numpy as np
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from .storage import research_storage

# Cache paths
REDUCER_CACHE = Path("data/research/umap_reducer.pkl")
PROJECTION_CACHE = Path("data/research/brain_map_cache.json")
MAX_POINTS_PER_LEVEL = 100

# Topic colors (deterministic hash)
COLORS = ["#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"]

def _topic_color(topic_name: str) -> str:
    return COLORS[hash(topic_name) % len(COLORS)]


async def generate_brain_map(
    level: int = 0,
    topic_id: Optional[str] = None,
    force_recompute: bool = False,
    include_connections: bool = True,
    min_connection_strength: float = 0.7
) -> dict:
    """
    Generate hierarchical brain map with optional constellation lines.
    
    Args:
        level: 0 = topics, 1 = clusters, 2 = all points
        topic_id: Filter to specific topic (for level > 0)
        force_recompute: Ignore cache
        include_connections: Add constellation lines (semantic similarity)
        min_connection_strength: Threshold for connection visibility
    
    Returns:
        {
            "points": [...],
            "connections": [...],  # If include_connections
            "level": int,
            "count": int,
            "temporal_range": {"min": "2024-01-01", "max": "2024-12-15"}
        }
    """
    # ... (implementation as in original, plus new fields)


async def get_query_spotlight(query: str, top_k: int = 10) -> List[str]:
    """
    Given a query, return IDs of most relevant points for spotlight effect.
    Called during chat streaming to highlight relevant knowledge.
    """
    # Semantic search across all collections
    # Return point IDs with relevance scores for glow intensity


async def record_thought_path(point_ids: List[str], conversation_id: str):
    """
    Record which points were used in generating an answer.
    Called after chat completion to enable Thought Path replay.
    """
    # Store in data/research/thought_paths/{conversation_id}.json


async def get_knowledge_gaps() -> List[dict]:
    """
    Analyze embedding space for sparse regions between dense clusters.
    Returns suggested research topics to fill gaps.
    """
    # Clustering + gap detection algorithm


async def get_decay_candidates(days_unused: int = 30) -> List[str]:
    """
    Return point IDs that haven't been used in thought paths for N days.
    """
    # Query thought_paths, find unused points
```

---

### Backend: API Endpoints (add to research.py)

```python
@router.get("/brain-map")
async def get_brain_map(
    level: int = Query(default=0, ge=0, le=2),
    topic_id: Optional[str] = None,
    include_connections: bool = True,
    force_recompute: bool = False
) -> dict:
    """Get 3D brain map projection with constellation lines."""
    from src.core.research.brain_map import generate_brain_map
    return await generate_brain_map(level, topic_id, force_recompute, include_connections)


@router.get("/brain-map/spotlight")
async def get_spotlight(query: str) -> List[str]:
    """Get point IDs to highlight for a query (Query Spotlight)."""
    from src.core.research.brain_map import get_query_spotlight
    return await get_query_spotlight(query)


@router.get("/brain-map/thought-path/{conversation_id}")
async def get_thought_path(conversation_id: str) -> List[str]:
    """Get point IDs used in a conversation's answers (Thought Path)."""
    # Return stored thought path


@router.get("/brain-map/gaps")
async def get_gaps() -> List[dict]:
    """Get knowledge gap suggestions."""
    from src.core.research.brain_map import get_knowledge_gaps
    return await get_knowledge_gaps()


@router.get("/brain-map/decay")
async def get_decay(days: int = 30) -> List[str]:
    """Get unused point IDs for decay visualization."""
    from src.core.research.brain_map import get_decay_candidates
    return await get_decay_candidates(days)


@router.post("/brain-map/invalidate")
async def invalidate_brain_map():
    """Force cache invalidation."""
    from src.core.research.brain_map import invalidate_cache
    await invalidate_cache()
    return {"status": "cache invalidated"}


@router.delete("/brain-map/points")
async def delete_points(point_ids: List[str]):
    """Batch delete points (for decay cleanup)."""
    # Delete from ChromaDB collections
```

---

### Frontend: Component Structure

```
frontend/src/
├── components/
│   ├── brain/
│   │   ├── BrainCanvas.tsx        # Fullscreen WebGL canvas (Layer 0)
│   │   ├── BrainPoint.tsx         # Individual 3D point
│   │   ├── ConstellationLines.tsx # Connection lines between points
│   │   ├── BrainModeUI.tsx        # Toolbar when in Brain Mode
│   │   ├── PointDetails.tsx       # Selected point info panel
│   │   ├── Timeline.tsx           # Temporal layer slider
│   │   └── LoadingSkeleton.tsx    # Ghost spheres while loading
│   ├── BrainCore.tsx              # [🧠 Enter Brain] button in sidebar
│   └── ...
├── hooks/
│   ├── useBrainMap.ts             # Brain map state & API
│   ├── useBrainMode.ts            # Enter/exit brain mode
│   ├── useQuerySpotlight.ts       # Highlight during typing
│   └── useThoughtPath.ts          # Replay after response
└── ...
```

---

### Frontend: BrainCanvas.tsx (Layer 0)

```tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useBrainMap } from '../hooks/useBrainMap';
import { useBrainMode } from '../hooks/useBrainMode';
import { BrainPoint } from './brain/BrainPoint';
import { ConstellationLines } from './brain/ConstellationLines';

interface BrainCanvasProps {
  spotlightIds?: string[];      // Query Spotlight
  thoughtPathIds?: string[];    // Thought Path
  decayIds?: string[];          // Gray unused points
}

export function BrainCanvas({ spotlightIds, thoughtPathIds, decayIds }: BrainCanvasProps) {
  const { points, connections, isLoading } = useBrainMap();
  const { isInBrainMode } = useBrainMode();
  
  return (
    <div className="fixed inset-0 z-0">
      <Canvas camera={{ position: [5, 5, 5], fov: 60 }}>
        <ambientLight intensity={0.3} />
        <pointLight position={[10, 10, 10]} intensity={0.6} />
        
        {/* Only enable controls in Brain Mode */}
        {isInBrainMode && (
          <OrbitControls enableDamping dampingFactor={0.05} />
        )}
        
        {/* Constellation Lines */}
        <ConstellationLines connections={connections} />
        
        {/* Points */}
        {points.map((point) => (
          <BrainPoint
            key={point.id}
            point={point}
            isSpotlight={spotlightIds?.includes(point.id)}
            isThoughtPath={thoughtPathIds?.includes(point.id)}
            isDecayed={decayIds?.includes(point.id)}
            interactive={isInBrainMode}
          />
        ))}
      </Canvas>
    </div>
  );
}
```

---

### Frontend: App Layout Integration

```tsx
// App.tsx structure
function App() {
  const { spotlightIds } = useQuerySpotlight();
  const { thoughtPathIds } = useThoughtPath();
  const { decayIds } = useDecay();
  const { isInBrainMode, enterBrain, exitBrain } = useBrainMode();
  
  return (
    <div className="relative min-h-screen">
      {/* Layer 0: Brain Background (always rendered) */}
      <BrainCanvas 
        spotlightIds={spotlightIds}
        thoughtPathIds={thoughtPathIds}
        decayIds={decayIds}
      />
      
      {/* Layer 1 & 2: UI (hidden in Brain Mode) */}
      {!isInBrainMode && (
        <>
          {/* Sidebar - Layer 2 */}
          <Sidebar 
            className="bg-black/70 backdrop-blur-xl"
            onEnterBrain={enterBrain}
          />
          
          {/* Chat - Layer 1 */}
          <ChatPanel className="bg-black/60 backdrop-blur-xl" />
        </>
      )}
      
      {/* Layer 3: Brain Mode UI (shown only in Brain Mode) */}
      {isInBrainMode && (
        <BrainModeUI onExit={exitBrain} />
      )}
    </div>
  );
}
```

---

### CSS: Frosted Glass Effect

```css
/* globals.css */
.frosted-panel {
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.frosted-panel-dark {
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(24px) saturate(120%);
  -webkit-backdrop-filter: blur(24px) saturate(120%);
}

/* Brain Mode transition */
.brain-enter-animation {
  animation: brain-explode 500ms ease-out forwards;
}

@keyframes brain-explode {
  from {
    transform: scale(0.8);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
```

---

## 📁 Files Summary

```
Backend:
├── src/core/research/brain_map.py         # UMAP + spotlight + gaps + decay
└── src/api/routers/research.py            # +6 endpoints

Frontend:
├── src/components/brain/
│   ├── BrainCanvas.tsx                    # Main 3D canvas (Layer 0)
│   ├── BrainPoint.tsx                     # Individual point with states
│   ├── ConstellationLines.tsx             # Connection lines
│   ├── BrainModeUI.tsx                    # Fullscreen toolbar
│   ├── PointDetails.tsx                   # Selected point panel
│   ├── Timeline.tsx                       # Temporal slider
│   └── LoadingSkeleton.tsx                # Loading state
├── src/components/BrainCore.tsx           # Enter Brain button
├── src/hooks/
│   ├── useBrainMap.ts                     # API + state
│   ├── useBrainMode.ts                    # Mode switching
│   ├── useQuerySpotlight.ts               # Real-time highlight
│   ├── useThoughtPath.ts                  # Post-answer replay
│   └── useDecay.ts                        # Unused points
└── src/App.tsx                            # Layer integration

Data:
├── data/research/umap_reducer.pkl         # Cached UMAP model
├── data/research/brain_map_cache.json     # Cached projections
└── data/research/thought_paths/           # Per-conversation paths
```

---

## ✅ Verification Checklist

### Phase 1 (MVP)

- [ ] Brain Canvas renders behind UI
- [ ] Frosted glass effect works on Sidebar + Chat
- [ ] UMAP projection runs in executor (non-blocking)
- [ ] Hierarchical levels 0→1→2 работают
- [ ] Enter Brain Mode animation
- [ ] Exit Brain Mode animation
- [ ] OrbitControls only active in Brain Mode
- [ ] Constellation lines visible
- [ ] Query Spotlight highlights during typing
- [ ] Thought Path animates after response

### Phase 2

- [ ] Timeline slider shows temporal data
- [ ] Playback animation works
- [ ] Decay points are gray
- [ ] Delete decay points works
- [ ] Knowledge gaps highlighted
- [ ] Multi-select with lasso
- [ ] Batch delete/archive

### Phase 3

- [ ] Annotations saved per point
- [ ] Filter by tags
- [ ] Export screenshot
- [ ] Search → zoom to point

---

## 🔮 Future Enhancements

| Feature | Priority | Notes |
|---------|----------|-------|
| VR Mode (WebXR) | 🟡 | Walk inside your brain |
| Voice narration | 🟢 | "This cluster contains 47 facts about..." |
| Shared brains | 🔴 | Collaborative knowledge spaces |
| Import external | 🟢 | Import from Notion, Obsidian |
| Point clustering labels | 🟡 | Auto-generated cluster names |

---

## 📝 Context for Future Sessions

**Что было обсуждено:**

1. Brain Map — не отдельный экран, а **живой фон** всего интерфейса
2. UI компоненты (Sidebar, Chat) имеют **frosted glass** эффект поверх мозга
3. Мозг реагирует на действия: **Query Spotlight** (подсвечивает при вопросе), **Thought Path** (показывает путь мышления)
4. Кнопка **[🧠 Enter Brain]** открывает fullscreen режим с тулбаром
5. **Temporal Layer** — 4D timeline для просмотра роста знаний
6. **Decay** — серые неиспользуемые точки с возможностью удаления
7. **Knowledge Gaps** — подсветка пустых областей с рекомендациями
8. **Constellation Lines** — связи между семантически близкими точками

**Ключевые технические решения:**

- Layer 0 (z-0): WebGL Canvas — всегда рендерится
- Layer 1-2 (z-10, z-20): UI с `backdrop-blur`
- UMAP в `run_in_executor` — не блокирует event loop
- Cache reducer для стабильных проекций

**Реализовывать после:** Research Lab Phase 1 (storage, worker, basic UI)
