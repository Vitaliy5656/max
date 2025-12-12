"""
FastAPI REST API for MAX AI Assistant.

Provides endpoints for React frontend:
- Chat with streaming (SSE)
- Documents (RAG)
- Auto-GPT agent
- Templates
- Metrics (IQ/Empathy)
"""
import asyncio
import json
from typing import Optional, AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import MAX core modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.memory import memory
from src.core.lm_client import lm_client
from src.core.rag import rag
from src.core.templates import templates
from src.core.autogpt import RunStatus  # Keep enum, use ReflectiveAgent
from src.core.agent_v2 import ReflectiveAgent
from src.core.user_profile import user_profile
from src.core.metrics import metrics_engine
from src.core.adaptation import initialize_adaptation, prompt_builder
from src.core.backup import backup_manager
# AI Next Gen modules
from src.core.embedding_service import embedding_service
from src.core.semantic_router import semantic_router
from src.core.context_primer import context_primer
from src.core.self_reflection import self_reflection, initialize_self_reflection
from src.core.confidence import confidence_scorer
from src.core.error_memory import error_memory  # P1: Integrate orphan module

# ============= FastAPI App =============

app = FastAPI(
    title="MAX AI API",
    description="REST API for MAX AI Assistant React frontend",
    version="1.0.0"
)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],  # P2 fix: Explicit methods
    allow_headers=["*"],
)

# Global state
_initialized = False
_current_conversation_id: Optional[str] = None
_autogpt_agent: Optional[ReflectiveAgent] = None  # P1: Use ReflectiveAgent with verification
_agent_lock = asyncio.Lock()  # P1 fix: Lock for singleton race condition


def _log_task_exception(task: asyncio.Task):
    """Log exceptions from fire-and-forget tasks (P1 fix)."""
    try:
        exc = task.exception()
        if exc:
            print(f"[Background Task Error] {type(exc).__name__}: {exc}", flush=True)
    except asyncio.CancelledError:
        pass


# ============= Pydantic Models =============

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: str = "auto"
    temperature: float = 0.7
    use_rag: bool = True
    thinking_mode: str = "standard"  # fast/standard/deep
    has_image: bool = False  # Auto-activates vision mode


class ConversationCreate(BaseModel):
    title: str = "Новый разговор"


class TemplateCreate(BaseModel):
    name: str
    prompt: str
    category: str = "general"


class AgentStartRequest(BaseModel):
    goal: str
    max_steps: int = 20
    use_internet: bool = True
    use_files: bool = False


class FeedbackRequest(BaseModel):
    message_id: int
    rating: int  # 1 = positive, -1 = negative


# ============= Startup =============

@app.on_event("startup")
async def startup():
    """Initialize all subsystems."""
    global _initialized, _autogpt_agent
    
    if _initialized:
        return
    
    await memory.initialize()
    await user_profile.initialize(memory._db)
    await rag.initialize(memory._db)
    await templates.initialize(memory._db)
    await metrics_engine.initialize(memory._db)
    await initialize_adaptation(memory._db)
    
    # AI Next Gen: Initialize semantic routing and context priming
    await embedding_service.initialize(lm_client)
    await semantic_router.initialize(lm_client, embedding_service)
    await context_primer.initialize(memory._db, embedding_service)
    await initialize_self_reflection(memory._db)
    
    # P1: Initialize error_memory for learning from mistakes
    await error_memory.initialize(memory._db, embedding_service)
    
    # P1: Use ReflectiveAgent (adds verification step to AutoGPT)
    _autogpt_agent = ReflectiveAgent(memory._db)
    await _autogpt_agent.initialize(memory._db)
    
    _initialized = True
    print("✅ AI Next Gen modules initialized (SemanticRouter, ContextPrimer, SelfReflection, ErrorMemory, ReflectiveAgent)", flush=True)


@app.on_event("shutdown")
async def shutdown():
    """Cleanup and spawn backup on exit."""
    print("📦 Spawning backup worker before shutdown...")
    backup_manager.spawn_backup_worker()
    await memory.close()


# ============= Backup Endpoints =============

@app.get("/api/backup/status")
async def get_backup_status():
    """Get current backup status."""
    return backup_manager.get_status()


@app.get("/api/backup/list")
async def list_backups():
    """List recent backups."""
    return backup_manager.list_backups()


@app.post("/api/backup/trigger")
async def trigger_backup():
    """Manually trigger a backup."""
    success = backup_manager.spawn_backup_worker()
    return {"success": success}


# ============= Chat Endpoints =============

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with streaming response (SSE)."""
    # DIRECT PRINT - guaranteed visibility
    print("\n" + "="*60, flush=True)
    print(f">>> CHAT REQUEST RECEIVED: {request.message[:50]}...", flush=True)
    print(f">>> Model: {request.model}, Mode: {request.thinking_mode}", flush=True)
    print("="*60, flush=True)
    
    from src.core.logger import log
    
    global _current_conversation_id
    
    # Start request tracing
    log.request_start(request.message, request.model, request.thinking_mode)
    
    # Get or create conversation
    conv_id = request.conversation_id
    is_new_conv = False
    
    if not conv_id:
        conv = await memory.create_conversation("Новый разговор")
        conv_id = conv.id
        is_new_conv = True
        print(f">>> Created conversation: {conv_id}", flush=True)
        log.api("Created new conversation", id=conv_id)
    _current_conversation_id = conv_id
    
    # Add user message
    await memory.add_message(conv_id, "user", request.message)
    print(">>> User message saved", flush=True)
    log.api("User message saved to memory")
    
    # Track interaction (Background task with exception handler - P1 fix)
    task = asyncio.create_task(user_profile.track_interaction(request.message))
    task.add_done_callback(_log_task_exception)
    
    # P1 Fix: Auto-generate title if new conversation
    async def _update_title():
        try:
            # Simple heuristic for now: first 40 chars
            # Future: Use LLM to summarize
            smart_title = request.message[:40].strip()
            if len(request.message) > 40:
                smart_title += "..."
            
            await memory._db.execute(
                "UPDATE conversations SET title = ? WHERE id = ? AND title = 'Новый разговор'",
                (smart_title, conv_id)
            )
            await memory._db.commit()
            log.api(f"Auto-updated title to: {smart_title}")
        except Exception as e:
            log.error(f"Failed to update title: {e}")

    if is_new_conv:
        asyncio.create_task(_update_title())
    
    # Get context
    context = await memory.get_smart_context(conv_id)
    log.api("Context retrieved", messages=len(context))
    
    # RAG augmentation
    if request.use_rag:
        rag_context = await rag.get_context_for_query(request.message, max_tokens=1000)
        if rag_context:
            context.insert(0, {
                "role": "system",
                "content": f"Релевантные документы:\n{rag_context}"
            })
            log.api("RAG context added", chars=len(rag_context))
    
    # Build adaptive prompt
    style_prompt = await prompt_builder.build_adaptive_prompt(request.message)
    if style_prompt:
        context.insert(0, {"role": "system", "content": style_prompt})
        log.api("Adaptive prompt injected")
    
    async def generate() -> AsyncGenerator[str, None]:
        """Stream tokens as SSE."""
        full_response = ""
        error_occurred = False
        sse_count = 0
        
        log.api("Starting SSE generator")
        
        try:
            # Convert string to ThinkingMode enum
            from src.core.lm_client import ThinkingMode
            try:
                thinking_mode = ThinkingMode(request.thinking_mode)
            except ValueError:
                thinking_mode = ThinkingMode.STANDARD
                log.warn(f"Invalid thinking_mode '{request.thinking_mode}', using STANDARD")
            
            log.api("Calling lm_client.chat()", mode=thinking_mode.value)
            
            # P2 Fix: Resolve model and handle loading state
            target_model = request.model
            
            # Smart model resolution for "auto":
            # 1. Check if any model is already loaded in LM Studio
            # 2. If yes - use it (no hot-swap needed!)
            # 3. If no - use config default for the thinking mode
            if target_model == "auto" or not target_model:
                # First check if LM Studio has a model loaded
                loaded_model = await lm_client.get_loaded_model()
                if loaded_model:
                    target_model = loaded_model
                    log.api(f"Auto-selected already loaded model: {target_model}")
                else:
                    # No model loaded, use config default
                    mode_config = lm_client.get_mode_config(thinking_mode)
                    target_model = mode_config.model
                    log.api(f"Auto-selected config model: {target_model}")
            
            # Check if we need to load (Hot-swap)
            # We use local check first to avoid IPC if possible, but ensure_model_loaded is safe
            if lm_client.current_model != target_model:
                log.api(f"Model switch needed: {lm_client.current_model} -> {target_model}")
                sse_loading = json.dumps({'status': 'loading', 'model': target_model})
                yield f"data: {sse_loading}\n\n"
                
                success = await lm_client.ensure_model_loaded(target_model)
                if not success:
                    error_msg = f"Failed to load model: {target_model}"
                    log.error(error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

            async for chunk in await lm_client.chat(
                messages=context + [{"role": "user", "content": request.message}],
                temperature=request.temperature,
                model=target_model,  # Explicitly pass resolved model
                thinking_mode=thinking_mode,
                has_image=request.has_image,
                stream=True
            ):
                sse_count += 1
                
                # Check if chunk is metadata dict (thinking events)
                if isinstance(chunk, dict) and "_meta" in chunk:
                    meta_type = chunk["_meta"]
                    if meta_type == "thinking_start":
                        log.api("🧠 Thinking started")
                        yield f"data: {json.dumps({'thinking': 'start'})}\n\n"
                    elif meta_type == "thinking_end":
                        duration = chunk.get("duration_ms", 0)
                        chars = chunk.get("chars_filtered", 0)
                        think_content = chunk.get("think_content", "")
                        log.api(f"🧠 Thinking ended", duration_ms=duration, chars_filtered=chars)
                        yield f"data: {json.dumps({'thinking': 'end', 'duration_ms': duration, 'chars_filtered': chars, 'think_content': think_content})}\n\n"
                    continue
                
                # Check for error in chunk
                if chunk.startswith("\n[Error:"):
                    error_occurred = True
                    full_response += chunk
                    log.error(f"Error chunk received: {chunk}")
                    yield f"data: {json.dumps({'error': chunk.strip()})}\n\n"
                    break
                
                full_response += chunk
                
                # SSE format
                sse_data = json.dumps({'token': chunk})
                log.sse_yield("token", len(chunk))
                yield f"data: {sse_data}\n\n"
                
        except asyncio.CancelledError:
            log.warn("Client disconnected (Stop Generation)")
            full_response += " [Interrupted]"
            # Don't yield here, channel is closed
            
        except Exception as e:
            log.error(f"Generate exception: {type(e).__name__}: {e}")
            import traceback
            log.error(f"Traceback:\n{traceback.format_exc()}")
            error_msg = f"\n[System Error: {str(e)}]"
            full_response += error_msg
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        finally:
            # P0 CRITICAL FIX: Guaranteed save even on disconnect
            if full_response:
                try:
                    saved_msg = await memory.add_message(
                        conv_id, "assistant", full_response,
                        model_used=lm_client.current_model or "unknown"
                    )
                    log.api("Response saved to memory (guaranteed)", msg_id=saved_msg.id, chars=len(full_response))
                    
                    # Record metrics
                    await metrics_engine.record_interaction_outcome(
                        message_id=saved_msg.id,
                        user_message=request.message,
                        facts_in_context=len(context),
                        style_prompt_length=len(style_prompt) if style_prompt else 0
                    )
                    
                    # Send done signal if we can
                    if not error_occurred:
                        done_data = {'done': True, 'message_id': saved_msg.id, 'conversation_id': conv_id}
                        yield f"data: {json.dumps(done_data)}\n\n"
                        
                        # Score confidence
                        try:
                            confidence_result = confidence_scorer.score_response(full_response)
                            confidence_data = {
                                'confidence': True,
                                'score': confidence_result.score,
                                'level': confidence_result.level.value,
                                'factors': confidence_result.factors
                            }
                            yield f"data: {json.dumps(confidence_data)}\n\n"
                        except Exception:
                            pass
                            
                except Exception as save_err:
                     log.error(f"FATAL: Failed to save response to DB: {save_err}")

        log.request_end(sse_count, len(full_response), 0)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/api/conversations")
async def list_conversations(limit: int = 50):
    """List recent conversations with message counts."""
    convs = await memory.list_conversations(limit=limit)
    result = []
    for c in convs:
        # P1 fix: Add message_count to match frontend interface
        messages = await memory.get_messages(c.id, limit=1000)
        result.append({
            "id": c.id,
            "title": c.title,
            "updated_at": c.updated_at,
            "message_count": len(messages)
        })
    return result


@app.post("/api/conversations")
async def create_conversation(data: ConversationCreate):
    """Create new conversation."""
    conv = await memory.create_conversation(data.title)
    return {"id": conv.id, "title": conv.title}


@app.get("/api/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, limit: int = 100):
    """Get messages for a conversation."""
    messages = await memory.get_messages(conv_id, limit=limit)
    return [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at,
        "model_used": m.model_used
    } for m in messages]


# ============= Documents (RAG) Endpoints =============

@app.get("/api/documents")
async def list_documents():
    """List all indexed documents."""
    docs = await rag.list_documents()
    return [{
        "id": str(d.id),
        "name": d.filename,
        "size": f"{d.chunk_count * 500} chars",  # Approximate
        "type": d.filename.split(".")[-1] if "." in d.filename else "txt",
        "chunks": d.chunk_count,
        "status": "indexed"
    } for d in docs]


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a document."""
    import tempfile
    import os
    
    # Save to temp file (Streamed)
    temp_path = os.path.join(tempfile.gettempdir(), file.filename)
    # Optimization: Read in chunks to avoid memory spike
    with open(temp_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)
    
    try:
        # Index document
        doc = await rag.add_document(temp_path)
        return {"id": str(doc.id), "name": doc.filename, "status": "indexed"}
    finally:
        # P1 fix: Cleanup temp file to prevent disk leak
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document."""
    await rag.remove_document(doc_id)
    return {"success": True}


# ============= Auto-GPT Endpoints =============

@app.post("/api/agent/start")
async def start_agent(request: AgentStartRequest):
    """Start autonomous agent."""
    global _autogpt_agent
    
    if _autogpt_agent.is_running():
        raise HTTPException(400, "Agent already running")
    
    run = await _autogpt_agent.set_goal(request.goal, request.max_steps)
    
    # Start in background
    asyncio.create_task(_run_agent())
    
    return {"run_id": run.id, "status": "running"}


async def _run_agent():
    """Background agent execution."""
    global _autogpt_agent
    async for step in _autogpt_agent.run_generator():
        pass  # Steps are stored in DB


@app.get("/api/agent/status")
async def agent_status():
    """Get agent status and steps."""
    global _autogpt_agent
    
    if not _autogpt_agent or not _autogpt_agent._current_run:
        return {"running": False, "steps": []}
    
    run = _autogpt_agent._current_run
    return {
        "running": _autogpt_agent.is_running(),
        "paused": _autogpt_agent.is_paused(),
        "goal": run.goal,
        "steps": [{
            "id": s.id,
            "action": s.action,
            "title": s.action,
            "desc": s.result[:100] if s.result else "",
            "status": s.status.value
        } for s in run.steps]
    }


@app.post("/api/agent/stop")
async def stop_agent():
    """Stop agent execution."""
    global _autogpt_agent
    await _autogpt_agent.cancel()
    return {"success": True}


# ============= Templates Endpoints =============

@app.get("/api/templates")
async def list_templates():
    """List all templates."""
    tpls = await templates.list_all()
    return [{
        "id": t.id,
        "name": t.name,
        "category": t.category or "general",
        "content": t.prompt
    } for t in tpls]


@app.post("/api/templates")
async def create_template(data: TemplateCreate):
    """Create a new template."""
    tpl_id = await templates.save(data.name, data.prompt, data.category)
    return {"id": tpl_id, "name": data.name}


# ============= Metrics Endpoints =============

@app.get("/api/metrics")
async def get_metrics():
    """Get current IQ and Empathy scores."""
    iq = await metrics_engine.calculate_iq()
    empathy = await metrics_engine.calculate_empathy()
    
    return {
        "iq": iq.to_dict(),
        "empathy": empathy.to_dict()
    }


@app.get("/api/metrics/proof")
async def get_adaptation_proof():
    """Get adaptation proof (Day 1 vs Day 30)."""
    proof = await metrics_engine.get_adaptation_proof()
    return proof


@app.get("/api/achievements")
async def get_achievements():
    """Get all achievements."""
    achievements = await metrics_engine.get_achievements()
    return [a.to_dict() for a in achievements]


@app.post("/api/feedback")
async def submit_feedback(data: FeedbackRequest):
    """Submit feedback on a message."""
    # Record to interaction_outcomes
    is_positive = data.rating > 0
    is_negative = data.rating < 0
    
    await metrics_engine.record_interaction_outcome(
        message_id=data.message_id,
        user_message="[explicit feedback]",
        detected_positive=is_positive,
        detected_negative=is_negative
    )
    
    return {"success": True}


# ============= Models Endpoint =============

@app.get("/api/models")
async def get_models():
    """Get available LLM models."""
    # P1 Fix: Use async and sync state
    models = await lm_client.get_available_models()
    # Force sync state from LM Studio
    current = await lm_client.sync_state()
    
    return {
        "models": models,
        "current": current,
        "smart_routing": True
    }


# ============= Health Check =============

@app.get("/api/health/cognitive")
async def cognitive_health():
    """Get cognitive system health (AI Next Gen modules)."""
    try:
        iq = await metrics_engine.calculate_iq()
        cache_stats = context_primer.get_cache_stats()
        embedding_stats = embedding_service.get_stats()
        
        return {
            "iq_today": iq.score,
            "context_cache": cache_stats,
            "embedding_cache": embedding_stats,
            "semantic_routing": True,
            "context_priming": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "semantic_routing": False,
            "context_priming": False
        }


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "initialized": _initialized}


# ============= Run Server =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
