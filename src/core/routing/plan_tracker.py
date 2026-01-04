"""
Plan Progress Tracker for MAX AI.

Tracks and streams plan execution progress to the UI.
Shows steps like "thinking" indicators in chat.

Features:
    - Plan creation with steps
    - Step-by-step progress tracking
    - Streaming updates to UI
    - Estimated time per step
"""
import asyncio
import time
import json
from typing import Optional, Dict, Any, List, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from ..logger import log


class StepStatus(Enum):
    """Status of a plan step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    
    # Timing
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    estimated_ms: int = 1000
    
    # Result
    result: Optional[str] = None
    error: Optional[str] = None
    
    # Icon for UI
    icon: str = "📋"
    
    @property
    def elapsed_ms(self) -> float:
        if not self.started_at:
            return 0
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "elapsed_ms": self.elapsed_ms,
            "estimated_ms": self.estimated_ms,
            "icon": self.icon,
            "result": self.result,
            "error": self.error
        }


@dataclass  
class Plan:
    """A plan with multiple steps."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    
    # Status
    current_step_index: int = 0
    status: str = "created"  # created, running, completed, failed
    
    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    @property
    def current_step(self) -> Optional[PlanStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    @property
    def progress_percent(self) -> int:
        if not self.steps:
            return 0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return int(completed / len(self.steps) * 100)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "status": self.status,
            "progress_percent": self.progress_percent
        }


class PlanProgressTracker:
    """
    Tracks plan execution and streams updates to UI.
    
    Usage:
        tracker = PlanProgressTracker()
        plan = tracker.create_plan("Write a function", [
            {"title": "Analyze request", "icon": "🔍"},
            {"title": "Write code", "icon": "💻"},
            {"title": "Test code", "icon": "✅"}
        ])
        
        async for update in tracker.execute(plan, my_executor):
            # Stream update to UI
            yield update
    """
    
    def __init__(self):
        self._active_plans: Dict[str, Plan] = {}
        log.debug("PlanProgressTracker initialized")
    
    def create_plan(
        self,
        goal: str,
        steps: List[Dict[str, Any]]
    ) -> Plan:
        """
        Create a new plan with steps.
        
        Args:
            goal: What the plan aims to achieve
            steps: List of step configs with title, description, icon, estimated_ms
        """
        plan_steps = []
        for step_config in steps:
            plan_steps.append(PlanStep(
                title=step_config.get("title", "Step"),
                description=step_config.get("description", ""),
                icon=step_config.get("icon", "📋"),
                estimated_ms=step_config.get("estimated_ms", 1000)
            ))
        
        plan = Plan(goal=goal, steps=plan_steps)
        self._active_plans[plan.id] = plan
        
        log.debug(f"Created plan {plan.id}: {len(plan.steps)} steps")
        return plan
    
    async def execute(
        self,
        plan: Plan,
        step_executor: Optional[Callable] = None
    ) -> AsyncIterator[Dict]:
        """
        Execute plan and yield progress updates.
        
        Yields:
            Progress updates as dicts for SSE streaming
        """
        plan.status = "running"
        plan.started_at = time.time()
        
        # Yield plan start
        yield self._format_update("plan_start", plan)
        
        for i, step in enumerate(plan.steps):
            plan.current_step_index = i
            
            # Start step
            step.status = StepStatus.RUNNING
            step.started_at = time.time()
            
            yield self._format_update("step_start", plan, step)
            
            try:
                # Execute step if executor provided
                if step_executor:
                    result = await step_executor(step)
                    step.result = result
                else:
                    # Simulate step execution
                    await asyncio.sleep(step.estimated_ms / 1000)
                    step.result = "OK"
                
                step.status = StepStatus.COMPLETED
                step.completed_at = time.time()
                
                yield self._format_update("step_complete", plan, step)
                
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                step.completed_at = time.time()
                
                yield self._format_update("step_failed", plan, step)
                
                # Don't stop on failure, continue to next step
                log.warn(f"Step failed: {step.title} - {e}")
        
        # Plan complete
        plan.status = "completed"
        plan.completed_at = time.time()
        
        yield self._format_update("plan_complete", plan)
    
    def _format_update(
        self,
        event_type: str,
        plan: Plan,
        step: Optional[PlanStep] = None
    ) -> Dict:
        """Format update for SSE streaming."""
        update = {
            "type": event_type,
            "plan_id": plan.id,
            "progress_percent": plan.progress_percent,
            "timestamp": time.time()
        }
        
        if step:
            update["step"] = step.to_dict()
        
        if event_type == "plan_start":
            update["goal"] = plan.goal
            update["total_steps"] = len(plan.steps)
            update["steps_preview"] = [
                {"title": s.title, "icon": s.icon}
                for s in plan.steps
            ]
        
        if event_type == "plan_complete":
            total_time = (plan.completed_at - plan.started_at) * 1000 if plan.completed_at else 0
            update["total_time_ms"] = total_time
            update["completed_steps"] = sum(
                1 for s in plan.steps if s.status == StepStatus.COMPLETED
            )
        
        return update
    
    def get_active_plan(self, plan_id: str) -> Optional[Plan]:
        """Get active plan by ID."""
        return self._active_plans.get(plan_id)
    
    def format_for_sse(self, update: Dict) -> str:
        """Format update for Server-Sent Events."""
        return f"data: {json.dumps(update, ensure_ascii=False)}\n\n"


# Preset plan templates
PLAN_TEMPLATES = {
    "coding": [
        {"title": "Анализ требований", "icon": "🔍", "estimated_ms": 500},
        {"title": "Написание кода", "icon": "💻", "estimated_ms": 3000},
        {"title": "Проверка синтаксиса", "icon": "✅", "estimated_ms": 500},
    ],
    "search": [
        {"title": "Формулировка запроса", "icon": "📝", "estimated_ms": 300},
        {"title": "Поиск информации", "icon": "🔎", "estimated_ms": 2000},
        {"title": "Обработка результатов", "icon": "📊", "estimated_ms": 500},
    ],
    "task": [
        {"title": "Декомпозиция задачи", "icon": "📋", "estimated_ms": 500},
        {"title": "Выполнение шагов", "icon": "⚙️", "estimated_ms": 5000},
        {"title": "Проверка результата", "icon": "✓", "estimated_ms": 500},
    ],
    "analysis": [
        {"title": "Сбор данных", "icon": "📥", "estimated_ms": 1000},
        {"title": "Анализ", "icon": "🧠", "estimated_ms": 3000},
        {"title": "Формирование выводов", "icon": "📈", "estimated_ms": 1000},
    ],
}


def get_plan_template(intent: str) -> List[Dict]:
    """Get plan template for intent."""
    return PLAN_TEMPLATES.get(intent, PLAN_TEMPLATES["task"])


# Global instance
_tracker: Optional[PlanProgressTracker] = None


def get_plan_tracker() -> PlanProgressTracker:
    """Get or create global tracker."""
    global _tracker
    if _tracker is None:
        _tracker = PlanProgressTracker()
    return _tracker


async def create_and_track_plan(
    goal: str,
    intent: str = "task",
    executor: Optional[Callable] = None
) -> AsyncIterator[Dict]:
    """
    Quick helper to create and execute a plan.
    
    Usage in chat.py:
        if route.intent == "task":
            async for update in create_and_track_plan(message, "task"):
                yield f"data: {json.dumps({'plan': update})}\n\n"
    """
    tracker = get_plan_tracker()
    template = get_plan_template(intent)
    plan = tracker.create_plan(goal, template)
    
    async for update in tracker.execute(plan, executor):
        yield update
