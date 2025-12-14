"""
Auto-Learning for Semantic Router.

Automatically learns from conversations to improve routing accuracy.
When LLM Router classifies a message (because Semantic Router wasn't confident),
and user doesn't give negative feedback, the example is added to training data.

Flow:
    1. Semantic Router fails (low confidence)
    2. LLM Router classifies → intent
    3. Wait for user feedback window (5 min)
    4. If no negative feedback → add to Semantic Router
    5. Persist to training file for next restart
"""
import asyncio
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Set
from dataclasses import dataclass

from .semantic_router import get_semantic_router
from .observer import get_routing_observer, FeedbackType
from ..logger import log


# Path for learned examples (separate from bootstrap)
LEARNED_DATA_PATH = Path("data/learned_examples.yaml")

# Minimum confidence for LLM result to be auto-learned
MIN_LLM_CONFIDENCE = 0.7

# Wait time before considering example "approved" (no negative feedback)
FEEDBACK_WINDOW_MINUTES = 5

# Max examples to learn per session (prevent runaway)
MAX_LEARNED_PER_SESSION = 100

# Intents safe for auto-learning
SAFE_INTENTS = {
    "greeting", "goodbye", "question", "coding", "creative",
    "math", "translation", "search", "psychology", "vision"
}

# Intents requiring explicit approval
NEEDS_APPROVAL_INTENTS = {"system_cmd", "privacy_unlock", "task"}


@dataclass
class PendingExample:
    """Example waiting for feedback window."""
    trace_id: str
    message: str
    intent: str
    topic: Optional[str]
    timestamp: datetime
    confidence: float


class AutoLearner:
    """
    Automatic learning from conversations.
    
    Strategy:
        - When LLM classifies (Semantic wasn't confident)
        - Wait for feedback window
        - If no negative feedback → add to Semantic Router
        - Persist for next session
    """
    
    def __init__(self):
        self._pending: Dict[str, PendingExample] = {}
        self._learned_count = 0
        self._session_examples: List[Dict] = []
        self._processed_traces: Set[str] = set()
        
        # Background task for processing
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        log.debug("AutoLearner initialized")
    
    def start(self) -> None:
        """Start background learning task."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._learning_loop())
        log.debug("AutoLearner started")
    
    def stop(self) -> None:
        """Stop background learning."""
        self._running = False
        if self._task:
            self._task.cancel()
    
    async def _learning_loop(self) -> None:
        """Background loop that processes pending examples."""
        while self._running:
            try:
                await self._process_pending()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"AutoLearner error: {e}")
                await asyncio.sleep(60)
    
    async def _process_pending(self) -> None:
        """Process pending examples past feedback window."""
        now = datetime.now()
        window = timedelta(minutes=FEEDBACK_WINDOW_MINUTES)
        observer = get_routing_observer()
        
        to_remove = []
        
        for trace_id, example in self._pending.items():
            # Check if feedback window passed
            if now - example.timestamp < window:
                continue
            
            to_remove.append(trace_id)
            
            # Check for negative feedback
            trace = observer.get_trace(trace_id)
            if trace and trace.user_feedback in {
                FeedbackType.BAD.value,
                FeedbackType.WRONG_INTENT.value
            }:
                log.debug(f"Skipping {trace_id}: negative feedback")
                continue
            
            # Add to semantic router
            await self._learn_example(example)
        
        for trace_id in to_remove:
            del self._pending[trace_id]
    
    def queue_for_learning(
        self,
        trace_id: str,
        message: str,
        intent: str,
        confidence: float,
        topic: Optional[str] = None
    ) -> bool:
        """
        Queue an example for potential learning.
        
        Called when LLM Router classifies (not Semantic).
        
        Returns True if queued.
        """
        # Check limits
        if self._learned_count >= MAX_LEARNED_PER_SESSION:
            return False
        
        # Check if already processed
        if trace_id in self._processed_traces:
            return False
        
        # Check confidence
        if confidence < MIN_LLM_CONFIDENCE:
            log.debug(f"Skipping {trace_id}: low confidence ({confidence:.2f})")
            return False
        
        # Check intent safety
        if intent in NEEDS_APPROVAL_INTENTS:
            log.debug(f"Skipping {trace_id}: intent {intent} needs approval")
            return False
        
        if intent.lower() not in SAFE_INTENTS:
            log.debug(f"Skipping {trace_id}: unknown intent {intent}")
            return False
        
        # Queue it
        self._pending[trace_id] = PendingExample(
            trace_id=trace_id,
            message=message,
            intent=intent.lower(),
            topic=topic,
            timestamp=datetime.now(),
            confidence=confidence
        )
        
        self._processed_traces.add(trace_id)
        log.debug(f"Queued for learning: {trace_id} -> {intent}")
        
        return True
    
    async def _learn_example(self, example: PendingExample) -> None:
        """Add example to semantic router and persist."""
        router = get_semantic_router()
        
        # Add to runtime index
        router.add_example(
            text=example.message,
            intent=example.intent,
            topic=example.topic
        )
        
        self._learned_count += 1
        self._session_examples.append({
            "text": example.message,
            "intent": example.intent,
            "topic": example.topic,
            "learned_at": datetime.now().isoformat()
        })
        
        log.debug(
            f"Learned: '{example.message[:30]}...' -> {example.intent} "
            f"(total: {self._learned_count})"
        )
        
        # Persist to file
        await self._persist_example(example)
    
    async def _persist_example(self, example: PendingExample) -> None:
        """Persist learned example to YAML file."""
        try:
            LEARNED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing
            data = {}
            if LEARNED_DATA_PATH.exists():
                with open(LEARNED_DATA_PATH, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
            
            # Add new example
            intent = example.intent.upper()
            if intent not in data:
                data[intent] = []
            
            if example.message not in data[intent]:
                data[intent].append(example.message)
            
            # Save
            with open(LEARNED_DATA_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            
        except Exception as e:
            log.error(f"Failed to persist learned example: {e}")
    
    def force_learn(self, message: str, intent: str, topic: Optional[str] = None) -> None:
        """
        Force-learn an example immediately (for manual correction).
        
        Used when user provides explicit feedback.
        """
        router = get_semantic_router()
        router.add_example(text=message, intent=intent, topic=topic)
        
        self._learned_count += 1
        log.debug(f"Force-learned: '{message[:30]}...' -> {intent}")
        
        # Fire-and-forget persist
        asyncio.create_task(self._persist_example(PendingExample(
            trace_id="manual",
            message=message,
            intent=intent,
            topic=topic,
            timestamp=datetime.now(),
            confidence=1.0
        )))
    
    def get_stats(self) -> Dict:
        """Get learning statistics."""
        return {
            "learned_this_session": self._learned_count,
            "pending_examples": len(self._pending),
            "processed_traces": len(self._processed_traces),
            "max_per_session": MAX_LEARNED_PER_SESSION,
            "feedback_window_minutes": FEEDBACK_WINDOW_MINUTES,
        }
    
    def load_learned_examples(self) -> int:
        """Load previously learned examples into semantic router."""
        if not LEARNED_DATA_PATH.exists():
            return 0
        
        try:
            with open(LEARNED_DATA_PATH, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            router = get_semantic_router()
            count = 0
            
            for intent, phrases in data.items():
                for phrase in phrases:
                    router.add_example(text=phrase, intent=intent.lower())
                    count += 1
            
            log.debug(f"Loaded {count} learned examples from {LEARNED_DATA_PATH}")
            return count
            
        except Exception as e:
            log.error(f"Failed to load learned examples: {e}")
            return 0


# Global instance
_auto_learner: Optional[AutoLearner] = None


def get_auto_learner() -> AutoLearner:
    """Get or create global AutoLearner."""
    global _auto_learner
    if _auto_learner is None:
        _auto_learner = AutoLearner()
    return _auto_learner


async def initialize_auto_learning() -> None:
    """Initialize and start auto-learning."""
    learner = get_auto_learner()
    
    # Load previously learned examples
    count = learner.load_learned_examples()
    
    # Start background learning
    learner.start()
    
    log.debug(f"Auto-learning initialized ({count} previous examples loaded)")
