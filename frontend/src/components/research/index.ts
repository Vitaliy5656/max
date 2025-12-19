/**
 * Research Components Index
 * ARCH-008: Centralized exports for all research sub-components
 * 
 * These components are extracted from ResearchLab.tsx for better maintainability.
 * Usage: import { QualityBar, StatsDashboard, TaskCard } from './research';
 */

// Components
export { QualityBar } from './QualityBar';
export { StatsDashboard } from './StatsDashboard';
export { ActivityFeed } from './ActivityFeed';
export { ResearchQueuePanel } from './ResearchQueuePanel';
export { ResearchStepper } from './ResearchStepper';
export { TaskCard } from './TaskCard';
export { TopicCard } from './TopicCard';
export { SkillModal } from './SkillModal';
export { CelebrationModal } from './CelebrationModal';

// Types
export type { QueueItem } from './ResearchQueuePanel';

// Utilities
export { STAGES, getStageIndex, formatETA } from './utils';

