"""
Research Lab API Router

Endpoints for research management, topic browsing, and real-time progress.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from src.core.research.storage import research_storage, TopicInfo
from src.core.research.worker import research_worker
from src.core.research.parser import DualParser


router = APIRouter(prefix="/api/research", tags=["Research Lab"])


# Request/Response Models
class StartResearchRequest(BaseModel):
    """Request to start new research."""
    topic: str
    description: str = ""
    max_pages: int = 10


class StartResearchResponse(BaseModel):
    """Response with task ID."""
    task_id: str
    message: str


class TopicResponse(BaseModel):
    """Topic information."""
    id: str
    name: str
    description: str
    chunk_count: int
    skill: Optional[str]
    status: str
    created_at: str


class SearchRequest(BaseModel):
    """Search request."""
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    """Search result item."""
    id: str
    content: str
    distance: float
    metadata: dict


# Endpoints

@router.post("/start", response_model=StartResearchResponse)
async def start_research(request: StartResearchRequest):
    """
    Start new research on a topic.
    
    Returns task_id for progress tracking.
    Returns 409 if topic already being researched.
    """
    try:
        task_id = await research_worker.start(
            topic=request.topic,
            description=request.description,
            max_pages=request.max_pages
        )
        
        return StartResearchResponse(
            task_id=task_id,
            message=f"Research started for: {request.topic}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get current status of a research task."""
    status = research_worker.get_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


@router.post("/cancel/{task_id}")
async def cancel_research(task_id: str):
    """Cancel running research task."""
    result = await research_worker.cancel(task_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found or already completed")
    
    return {"message": "Task cancelled", "task_id": task_id}


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(default=None, description="Filter by status")
):
    """List all research tasks."""
    if status == "running":
        return research_worker.get_running_tasks()
    
    return research_worker.get_all_tasks()


@router.get("/topics", response_model=list[TopicResponse])
async def list_topics():
    """List all research topics."""
    topics = await research_storage.list_topics()
    
    return [
        TopicResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            chunk_count=t.chunk_count,
            skill=t.skill,
            status=t.status,
            created_at=t.created_at
        )
        for t in topics
    ]


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    """Get topic details."""
    topic = await research_storage.get_topic(topic_id)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return TopicResponse(
        id=topic.id,
        name=topic.name,
        description=topic.description,
        chunk_count=topic.chunk_count,
        skill=topic.skill,
        status=topic.status,
        created_at=topic.created_at
    )


@router.get("/topics/{topic_id}/skill")
async def get_topic_skill(topic_id: str):
    """Get Topic Lens (skill prompt) for a topic."""
    skill = await research_storage.get_skill(topic_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return {"topic_id": topic_id, "skill": skill}


@router.post("/topics/{topic_id}/refresh")
async def refresh_topic(
    topic_id: str,
    max_pages: int = Query(default=10, ge=1, le=50)
):
    """
    Refresh topic with new research.
    
    Adds new data to EXISTING topic (doesn't create duplicate).
    """
    topic = await research_storage.get_topic(topic_id)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    try:
        task_id = await research_worker.start_refresh(
            topic_id=topic_id,
            topic=topic.name,
            description=topic.description,
            max_pages=max_pages
        )
        
        return {
            "task_id": task_id,
            "message": f"Refresh started for: {topic.name}",
            "topic_id": topic_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/{topic_id}/search")
async def search_topic(topic_id: str, request: SearchRequest):
    """Semantic search within a topic."""
    topic = await research_storage.get_topic(topic_id)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    results = await research_storage.search(
        topic_id=topic_id,
        query=request.query,
        top_k=request.top_k
    )
    
    return {
        "topic_id": topic_id,
        "query": request.query,
        "results": results
    }


@router.delete("/topics/{topic_id}")
async def delete_topic(topic_id: str):
    """Delete a topic and all its data."""
    result = await research_storage.delete_topic(topic_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return {"message": "Topic deleted", "topic_id": topic_id}


@router.get("/parser-stats")
async def get_parser_stats():
    """Get parser comparison statistics."""
    parser = DualParser()
    return parser.get_stats()


@router.get("/skills")
async def get_all_skills():
    """Get all Topic Lens skills for router integration."""
    return await research_storage.get_all_skills()


# ============================================================================
# Brain Map Endpoints
# ============================================================================

@router.get("/brain-map")
async def get_brain_map(
    level: int = Query(default=0, ge=0, le=2, description="0=topics, 1=clusters, 2=points"),
    topic_id: Optional[str] = Query(default=None, description="Filter to specific topic"),
    include_connections: bool = Query(default=True, description="Include constellation lines"),
    force_recompute: bool = Query(default=False, description="Ignore cache")
):
    """
    Get 3D brain map projection via UMAP.
    
    Returns points with x,y,z coordinates and optional connection lines.
    First call may take 5-10 seconds for UMAP computation.
    """
    from src.core.research.brain_map import generate_brain_map
    return await generate_brain_map(
        level=level,
        topic_id=topic_id,
        force_recompute=force_recompute,
        include_connections=include_connections
    )


@router.get("/brain-map/spotlight")
async def get_spotlight(
    query: str = Query(..., description="Query to find relevant points"),
    top_k: int = Query(default=10, ge=1, le=50)
):
    """Get point IDs to highlight for Query Spotlight effect."""
    from src.core.research.brain_map import get_query_spotlight
    return await get_query_spotlight(query, top_k)


@router.post("/brain-map/invalidate")
async def invalidate_brain_map():
    """Force cache invalidation. Call after new research completes."""
    from src.core.research.brain_map import invalidate_cache
    await invalidate_cache()
    return {"status": "cache_invalidated"}


# WebSocket for real-time progress
@router.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """
    WebSocket endpoint for real-time research progress.
    
    Messages format:
    {
        "type": "research_progress",
        "task_id": "...",
        "data": {
            "status": "running",
            "stage": "hunting",
            "detail": "Searching: python async patterns...",
            "progress": 0.35,
            "eta_seconds": 120
        }
    }
    """
    await websocket.accept()
    await research_worker.add_websocket(websocket)
    
    try:
        # Send current running tasks on connect
        running = research_worker.get_running_tasks()
        if running:
            await websocket.send_text(json.dumps({
                "type": "initial_state",
                "running_tasks": running
            }))
        
        # Keep connection alive
        while True:
            try:
                # Wait for any message (keepalive ping)
                data = await websocket.receive_text()
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                break
                
    finally:
        research_worker.remove_websocket(websocket)
