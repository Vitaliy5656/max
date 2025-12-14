"""
Agent (AutoGPT) Router for MAX AI API.

Endpoints:
- POST /api/agent/start
- GET /api/agent/status
- POST /api/agent/stop
"""
import asyncio

from fastapi import APIRouter, HTTPException

from src.api.schemas import AgentStartRequest

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Reference to global agent (set from main app)
_agent = None


def set_agent(agent):
    """Set the agent instance from main app."""
    global _agent
    _agent = agent


def get_agent():
    """Get the agent instance."""
    return _agent


async def _run_agent():
    """Background agent execution."""
    agent = get_agent()
    if agent:
        async for step in agent.run_generator():
            pass  # Steps are stored in DB


@router.post("/start")
async def start_agent(request: AgentStartRequest):
    """Start autonomous agent."""
    agent = get_agent()
    
    if not agent:
        raise HTTPException(500, "Agent not initialized")
    
    if agent.is_running():
        raise HTTPException(400, "Agent already running")
    
    run = await agent.set_goal(request.goal, request.max_steps)
    
    # Start in background
    asyncio.create_task(_run_agent())
    
    return {"run_id": run.id, "status": "running"}


@router.get("/status")
async def agent_status():
    """Get agent status and steps."""
    agent = get_agent()
    
    if not agent or not agent._current_run:
        return {"running": False, "steps": []}
    
    run = agent._current_run
    return {
        "running": agent.is_running(),
        "paused": agent.is_paused(),
        "goal": run.goal,
        "steps": [{
            "id": s.id,
            "action": s.action,
            "title": s.action,
            "desc": s.result[:100] if s.result else "",
            "status": s.status.value
        } for s in run.steps]
    }


@router.post("/stop")
async def stop_agent():
    """Stop agent execution."""
    agent = get_agent()
    
    if not agent:
        raise HTTPException(500, "Agent not initialized")
    
    await agent.cancel()
    return {"success": True}
