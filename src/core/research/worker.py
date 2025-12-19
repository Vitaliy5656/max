"""
Research Worker Module

Background task management for research operations.

Features:
- Async task execution with progress tracking
- WebSocket broadcast for real-time updates
- Task persistence for crash recovery
- Duplicate research prevention (409 Conflict)
- Zombie cleanup on startup
"""

import asyncio
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Callable, Any
from uuid import uuid4

from .agent import research_agent
from .storage import research_storage


# Configuration
ACTIVE_TASKS_FILE = Path("data/research/active_tasks.json")
LOG_DIR = Path("data/research/logs")


@dataclass
class ResearchTask:
    """Represents a research task."""
    id: str
    topic: str
    description: str
    max_pages: int
    topic_id: Optional[str] = None
    status: str = "pending"  # pending | running | complete | cancelled | failed
    progress: float = 0.0
    stage: str = ""
    detail: str = ""
    eta_seconds: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ResearchWorker:
    """
    Manages background research tasks.
    
    Features:
    - Prevents duplicate research on same topic
    - Tracks progress for WebSocket updates
    - Persists tasks for crash recovery
    """
    
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._progress: dict[str, ResearchTask] = {}
        self._websockets: list[Any] = []
        self._logger = logging.getLogger("research_worker")
        self._lock = asyncio.Lock()
    
    async def start(
        self,
        topic: str,
        description: str,
        max_pages: int = 10
    ) -> str:
        """
        Start new research task.
        
        Returns task_id on success.
        Raises HTTPException(409) if topic already being researched.
        """
        async with self._lock:
            # Check for duplicate research
            for task_id, progress in self._progress.items():
                if progress.topic.lower() == topic.lower() and progress.status == "running":
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=409,
                        detail=f"Research already in progress for topic: {topic}"
                    )
            
            task_id = str(uuid4())
            
            # Create task info
            task_info = ResearchTask(
                id=task_id,
                topic=topic,
                description=description,
                max_pages=max_pages,
                status="pending",
                started_at=datetime.now().isoformat()
            )
            self._progress[task_id] = task_info
            
            # Save to file for persistence
            self._save_tasks()
            
            # Create async task
            task = asyncio.create_task(self._run_research(task_id, topic, description, max_pages))
            self._tasks[task_id] = task
            
            return task_id
    
    async def start_refresh(
        self,
        topic_id: str,
        topic: str,
        description: str,
        max_pages: int = 10
    ) -> str:
        """
        Start refresh for existing topic.
        Adds new data to existing topic instead of creating new one.
        """
        async with self._lock:
            # Check for duplicate
            for tid, progress in self._progress.items():
                if progress.topic_id == topic_id and progress.status == "running":
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=409,
                        detail=f"Refresh already in progress for this topic"
                    )
            
            task_id = str(uuid4())
            
            task_info = ResearchTask(
                id=task_id,
                topic=topic,
                description=description,
                max_pages=max_pages,
                topic_id=topic_id,
                status="pending",
                started_at=datetime.now().isoformat()
            )
            self._progress[task_id] = task_info
            self._save_tasks()
            
            # Create task for refresh
            task = asyncio.create_task(
                self._run_refresh(task_id, topic_id, topic, description, max_pages)
            )
            self._tasks[task_id] = task
            
            return task_id
    
    async def cancel(self, task_id: str) -> bool:
        """
        Cancel running research task.
        
        Returns True if cancelled, False if task not found or already done.
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            
            if not task:
                return False
            
            # Check if already done
            if task.done():
                return False
            
            task.cancel()
            
            # Update progress
            if task_id in self._progress:
                self._progress[task_id].status = "cancelled"
                self._progress[task_id].completed_at = datetime.now().isoformat()
                self._save_tasks()
            
            await self._broadcast(task_id, {
                "type": "cancelled",
                "task_id": task_id
            })
            
            return True
    
    def get_status(self, task_id: str) -> Optional[dict]:
        """Get current task status."""
        if task_id not in self._progress:
            return None
        
        return asdict(self._progress[task_id])
    
    def get_all_tasks(self) -> list[dict]:
        """Get all tasks."""
        return [asdict(t) for t in self._progress.values()]
    
    def get_running_tasks(self) -> list[dict]:
        """Get only running tasks."""
        return [
            asdict(t) for t in self._progress.values()
            if t.status in ("pending", "running")
        ]
    
    async def add_websocket(self, websocket):
        """Add WebSocket for progress updates."""
        self._websockets.append(websocket)
    
    def remove_websocket(self, websocket):
        """Remove WebSocket."""
        if websocket in self._websockets:
            self._websockets.remove(websocket)
    
    async def cleanup_zombies(self):
        """
        Clean up zombie tasks on startup.
        Called from app lifespan.
        """
        try:
            if ACTIVE_TASKS_FILE.exists():
                data = json.loads(ACTIVE_TASKS_FILE.read_text())
                
                for task_id, task_data in data.items():
                    if task_data.get("status") in ("pending", "running"):
                        # Mark as failed/incomplete
                        task_data["status"] = "incomplete"
                        task_data["error"] = "Server restarted"
                        task_data["completed_at"] = datetime.now().isoformat()
                
                ACTIVE_TASKS_FILE.write_text(json.dumps(data, indent=2))
                self._logger.info(f"Cleaned up {len(data)} zombie tasks")
                
        except Exception as e:
            self._logger.error(f"Error cleaning zombies: {e}")
    
    async def _run_research(
        self,
        task_id: str,
        topic: str,
        description: str,
        max_pages: int
    ):
        """Execute research task."""
        try:
            self._update_progress(task_id, "running", "Starting research", 0.0)
            
            async def progress_callback(stage: str, detail: str, progress: float):
                self._update_progress(task_id, "running", stage, progress, detail)
                await self._broadcast(task_id, self.get_status(task_id))
            
            topic_id = await research_agent.research(
                topic=topic,
                description=description,
                max_pages=max_pages,
                progress_callback=progress_callback
            )
            
            # Update with topic_id
            self._progress[task_id].topic_id = topic_id
            self._update_progress(task_id, "complete", "Research complete", 1.0)
            
            await self._broadcast(task_id, self.get_status(task_id))
            
        except asyncio.CancelledError:
            self._update_progress(task_id, "cancelled", "Research cancelled", 0)
            await self._broadcast(task_id, self.get_status(task_id))
            
        except Exception as e:
            self._logger.error(f"Research failed: {e}")
            self._update_progress(task_id, "failed", "Research failed", 0)
            self._progress[task_id].error = str(e)
            await self._broadcast(task_id, self.get_status(task_id))
    
    async def _run_refresh(
        self,
        task_id: str,
        topic_id: str,
        topic: str,
        description: str,
        max_pages: int
    ):
        """Execute refresh task."""
        try:
            self._update_progress(task_id, "running", "Starting refresh", 0.0)
            
            async def progress_callback(stage: str, detail: str, progress: float):
                self._update_progress(task_id, "running", stage, progress, detail)
                await self._broadcast(task_id, self.get_status(task_id))
            
            await research_agent.research_into_existing(
                topic_id=topic_id,
                topic=topic,
                description=description,
                max_pages=max_pages,
                progress_callback=progress_callback
            )
            
            self._update_progress(task_id, "complete", "Refresh complete", 1.0)
            await self._broadcast(task_id, self.get_status(task_id))
            
        except asyncio.CancelledError:
            self._update_progress(task_id, "cancelled", "Refresh cancelled", 0)
            await self._broadcast(task_id, self.get_status(task_id))
            
        except Exception as e:
            self._logger.error(f"Refresh failed: {e}")
            self._update_progress(task_id, "failed", "Refresh failed", 0)
            self._progress[task_id].error = str(e)
            await self._broadcast(task_id, self.get_status(task_id))
    
    def _update_progress(
        self,
        task_id: str,
        status: str,
        stage: str,
        progress: float,
        detail: str = ""
    ):
        """Update task progress."""
        if task_id not in self._progress:
            return
        
        task = self._progress[task_id]
        task.status = status
        task.stage = stage
        task.progress = progress
        task.detail = detail
        
        # Estimate ETA based on progress
        if progress > 0 and progress < 1 and task.started_at:
            try:
                started = datetime.fromisoformat(task.started_at)
                elapsed = (datetime.now() - started).total_seconds()
                estimated_total = elapsed / progress
                task.eta_seconds = int(estimated_total - elapsed)
            except Exception:
                pass
        
        if status in ("complete", "cancelled", "failed"):
            task.completed_at = datetime.now().isoformat()
            task.eta_seconds = 0
        
        self._save_tasks()
    
    async def _broadcast(self, task_id: str, data: dict):
        """Broadcast update to all websockets."""
        message = json.dumps({
            "type": "research_progress",
            "task_id": task_id,
            "data": data
        })
        
        dead_sockets = []
        
        for ws in self._websockets:
            try:
                await ws.send_text(message)
            except Exception:
                dead_sockets.append(ws)
        
        # Remove dead sockets
        for ws in dead_sockets:
            self.remove_websocket(ws)
    
    def _save_tasks(self):
        """Save tasks to file for persistence."""
        try:
            ACTIVE_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                task_id: asdict(task)
                for task_id, task in self._progress.items()
            }
            
            ACTIVE_TASKS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            self._logger.error(f"Error saving tasks: {e}")
    
    def _load_tasks(self):
        """Load tasks from file."""
        try:
            if ACTIVE_TASKS_FILE.exists():
                data = json.loads(ACTIVE_TASKS_FILE.read_text())
                for task_id, task_data in data.items():
                    self._progress[task_id] = ResearchTask(**task_data)
        except Exception as e:
            self._logger.error(f"Error loading tasks: {e}")


# Global instance
research_worker = ResearchWorker()
