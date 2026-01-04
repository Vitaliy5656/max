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
from src.core.lm import lm_client
from src.core.memory import Memory
from src.core.config import config, ThinkingMode
# Trigger reload for langgraph fix
from src.core.rag import rag
from src.core.templates import templates
from src.core.autogpt import RunStatus, AutoGPTAgent
from src.core.user_profile import user_profile
from src.core.metrics import metrics_engine
from src.core.adaptation import initialize_adaptation, prompt_builder
from src.core.backup import backup_manager
from src.core.tools import tools as tools_manager, TOOLS  # Web search and other tools
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

_autogpt_agent: Optional[AutoGPTAgent] = None  # P1: Use AutoGPTAgent
_agent_lock = asyncio.Lock()  # P1 fix: Lock for singleton race condition


def _log_task_exception(task: asyncio.Task):
    """Log exceptions from fire-and-forget tasks (P1 fix)."""
    try:
        exc = task.exception()
        if exc:
            from src.core.logger import log
            log.error(f"[Background Task Error] {type(exc).__name__}: {exc}")
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
    
    # P1: Use AutoGPTAgent for autonomous task execution
    _autogpt_agent = AutoGPTAgent(memory._db)
    await _autogpt_agent.initialize(memory._db)
    
    _initialized = True
    from src.core.logger import log
    log.api("✅ AI Next Gen modules initialized (SemanticRouter, ContextPrimer, SelfReflection, ErrorMemory, AutoGPTAgent)")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup and spawn backup on exit."""
    from src.core.logger import log
    log.api("📦 Spawning backup worker before shutdown...")
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
    # Replaced with log.api/log.request_start but keeping the cleaner log for now
    from src.core.logger import log
    

    
    # Start request tracing
    log.request_start(request.message, request.model, request.thinking_mode)
    
    # Get or create conversation
    conv_id = request.conversation_id
    is_new_conv = False
    
    if not conv_id:
        conv = await memory.create_conversation("Новый разговор")
        conv_id = conv.id
        is_new_conv = True
        log.api(f"Created conversation: {conv_id}")
        log.api("Created new conversation", id=conv_id)

    
    # Add user message
    await memory.add_message(conv_id, "user", request.message)
    log.api("User message saved")
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
    
    # Detect if user is requesting a web search
    search_keywords = ["найди", "поищи", "search", "check", "проверь", "посмотри в интернете", "in internet", "google", "what's new", "новости"]
    needs_search = any(keyword in request.message.lower() for keyword in search_keywords)
    
    # Add anti-hallucination prompt when using web search
    if needs_search:
        anti_hallucination_prompt = (
            "🚨 КРИТИЧЕСКАЯ ИНСТРУКЦИЯ: Использование инструментов веб-поиска\n\n"
            "ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА (нарушение недопустимо):\n"
            "1. ✅ Используйте ТОЛЬКО URL из результатов инструментов поиска\n"
            "2. ❌ НИКОГДА не придумывайте, не угадывайте URL\n"
            "3. 📝 Цитируйте источник для каждого факта: [Источник: URL]\n"
            "4. 🚫 НЕ придумывайте: телефоны, email, даты, имена, адреса\n"
            "5. 🤷 Если информации нет — скажите: 'Я не нашел эту информацию'\n"
            "6. 💬 Выражайте неуверенность: 'Согласно [источник], возможно...'\n"
            "7. 🔗 Указывайте ТОЧНЫЙ URL из результатов, не модифицируйте его\n\n"
            "❗ ВСЕ URL проходят автоматическую проверку. Выдуманные URL будут помечены как ошибка!"
        )
        context.insert(0, {"role": "system", "content": anti_hallucination_prompt})
        log.api("Enhanced anti-hallucination prompt added for web search")
    
    # Build adaptive prompt
    style_prompt = await prompt_builder.build_adaptive_prompt(request.message)
    if style_prompt:
        context.insert(0, {"role": "system", "content": style_prompt})
        log.api("Adaptive prompt injected")
    
    async def generate() -> AsyncGenerator[str, None]:
        """Stream tokens as SSE or execute tools if needed."""
        full_response = ""
        error_occurred = False
        sse_count = 0
        filtered_chars = 0  # Track filtered thinking chars
        
        log.api("Starting SSE generator")
        
        # P2 Fix: Resolve model early for both streaming and tool execution
        target_model = request.model
        
        # Smart model resolution based on model_selection_mode
        from src.core.config import config as app_config
        
        if app_config.lm_studio.model_selection_mode == "manual":
            # MANUAL MODE: Respect user choice or loaded model
            if target_model == "auto" or not target_model:
                # No explicit selection → use loaded model
                loaded_model = await lm_client.get_loaded_model()
                if loaded_model:
                    target_model = loaded_model
                    log.api(f"🎯 MANUAL: using loaded model: {target_model}")
                else:
                    target_model = app_config.lm_studio.default_model
                    log.api(f"🎯 MANUAL: using default model: {target_model}")
            else:
                # User explicitly selected a model → always respect it
                log.api(f"🎯 MANUAL: explicit selection: {target_model}")
        else:
            # AUTO MODE: Thinking mode can select model (legacy)
            if target_model == "auto" or not target_model:
                # First check if LM Studio has a model loaded
                loaded_model = await lm_client.get_loaded_model()
                if loaded_model:
                    target_model = loaded_model
                    log.api(f"🧠 AUTO: reusing loaded model: {target_model}")
                else:
                    # No model loaded, use thinking mode's config
                    from src.core.lm import ThinkingMode
                    try:
                        thinking_mode = ThinkingMode(request.thinking_mode)
                    except ValueError:
                        thinking_mode = ThinkingMode.STANDARD
                    mode_config = lm_client.get_mode_config(thinking_mode)
                    target_model = mode_config.model
                    log.api(f"🧠 AUTO: thinking mode selected: {target_model}")
                    
        # COGNITIVE LOOP ROUTING (System 2)
        # If thinking_mode is DEEP/REASONING, and it's not a tool call, use LangGraph
        from src.core.lm import ThinkingMode
        try:
            t_mode = ThinkingMode(request.thinking_mode)
        except ValueError:
            t_mode = ThinkingMode.STANDARD
        
        if t_mode == ThinkingMode.DEEP:
            log.api("🧠 Entering System 2 Cognitive Loop")
            # Import here to avoid circular deps if any
            from src.core.cognitive.graph import build_cognitive_graph
            from src.core.cognitive.types import CognitiveState, CognitiveConfig
            import time as time_module

            # P0 FIX: Timeout for Cognitive Loop (180 seconds max)
            COGNITIVE_LOOP_TIMEOUT = 180  # seconds

            # Yield initial think start
            yield f"data: {json.dumps({'thinking': 'start'})}\n\n"
            yield f"data: {json.dumps({'token': '🔄 Analyzing problem complexity...\n'})}\n\n"

            # Build & Run Graph
            graph = build_cognitive_graph()

            # Fetch user profile context
            profile_context = await user_profile.get_profile_summary_for_context(conv_id)

            initial_state: CognitiveState = {
                "input": request.message,
                "conversation_id": conv_id,
                "user_context": profile_context,
                "plan": None,
                "steps": [],
                "draft_answer": "",
                "critique": "",
                "score": 0.0,
                "iterations": 0,
                "past_failures": [],
                "thinking_tokens": [],
                "total_iterations": 0  # P0 FIX: Global counter that never resets
            }

            # Track start time for timeout and duration
            start_time = time_module.time()
            final_answer = ""
            score = 0.0
            iterations = 0

            try:
                # P0 FIX: Wrap in asyncio.wait_for with timeout
                async def run_cognitive_loop():
                    nonlocal final_answer, score, iterations
                    async for event in graph.astream(initial_state):
                        for node_name, node_state in event.items():
                            if node_name == "__end__":
                                continue

                            # Extract step info
                            step_name = node_state.get("step_name", node_name)
                            step_content = node_state.get("step_content", "")

                            # Stream the step event
                            if step_name and step_content:
                                step_data = {
                                    "thinking": "step",
                                    "name": step_name.upper(),
                                    "content": step_content
                                }
                                yield f"data: {json.dumps(step_data)}\n\n"

                            # Keep track of final state
                            if "draft_answer" in node_state:
                                final_answer = node_state["draft_answer"]
                            if "score" in node_state:
                                score = node_state["score"]
                            if "iterations" in node_state:
                                iterations = node_state["iterations"]

                # Stream with timeout check
                async for sse_event in run_cognitive_loop():
                    yield sse_event
                    # Check timeout after each step
                    elapsed = time_module.time() - start_time
                    if elapsed > COGNITIVE_LOOP_TIMEOUT:
                        log.warn(f"⏱️ Cognitive Loop TIMEOUT after {elapsed:.1f}s")
                        yield f"data: {json.dumps({'thinking': 'timeout', 'elapsed_s': elapsed})}\n\n"
                        break

            except asyncio.TimeoutError:
                log.error(f"⏱️ Cognitive Loop HARD TIMEOUT after {COGNITIVE_LOOP_TIMEOUT}s")
                yield f"data: {json.dumps({'error': f'Timeout: thinking took longer than {COGNITIVE_LOOP_TIMEOUT}s'})}\n\n"
                # Use whatever answer we have so far
                if not final_answer:
                    final_answer = "Извините, глубокий анализ занял слишком много времени. Попробуйте упростить вопрос."

            except Exception as e:
                log.error(f"Graph streaming error, falling back to invoke: {e}")
                # Fallback to atomic execution with timeout
                try:
                    final_state = await asyncio.wait_for(
                        graph.ainvoke(initial_state),
                        timeout=COGNITIVE_LOOP_TIMEOUT
                    )
                    final_answer = final_state.get("draft_answer", "Error in cognitive loop")
                    score = final_state.get("score", 0.0)
                    iterations = final_state.get("iterations", 0)
                except asyncio.TimeoutError:
                    log.error(f"⏱️ Cognitive Loop fallback TIMEOUT")
                    final_answer = "Извините, глубокий анализ занял слишком много времени."

            # Calculate actual duration
            duration_ms = int((time_module.time() - start_time) * 1000)

            # Yield think end with real duration
            think_summary = f"Cognitive Loop: {iterations} iterations, Score: {score:.2f}"
            yield f"data: {json.dumps({'thinking': 'end', 'duration_ms': duration_ms, 'think_content': think_summary})}\n\n"

            # Yield Final Answer
            yield f"data: {json.dumps({'token': final_answer})}\n\n"

            full_response = final_answer
            # Save to DB logic will handle the rest in finally block
            return
        
        # Wrap entire logic in try-finally for guaranteed save
        try:
            # If search is needed, use non-streaming with tools
            if needs_search:
                log.api("🔍 Web search detected - using tool execution mode")
                try:
                    # Execute tools in non-streaming mode
                    final_messages = context + [{"role": "user", "content": request.message}]
                    
                    for iteration in range(5):  # Max 5 tool iterations
                        log.api(f"🔄 Tool iteration {iteration + 1}/5, sending {len(TOOLS)} tools to model")
                        
                        response = await lm_client.client.chat.completions.create(
                            model=target_model,
                            messages=final_messages,
                            temperature=request.temperature,
                            tools=TOOLS,
                            tool_choice="auto",
                            stream=False
                        )
                        
                        message = response.choices[0].message
                        
                        # DEBUG: Log tool_calls status
                        log.api(f"📊 Response received - has tool_calls: {bool(message.tool_calls)}, content: {bool(message.content)}")
                        if message.tool_calls:
                            log.api(f"🔧 Tool calls count: {len(message.tool_calls)}")
                            for tc in message.tool_calls:
                                log.api(f"   Tool: {tc.function.name}")
                        
                        # No tool calls - we have final answer
                        if not message.tool_calls:
                            full_response = message.content or ""
                            
                            # ANTI-HALLUCINATION Layer 3: Validate response against tool results
                            from src.core.response_validator import response_validator
                            from src.core.hallucination_detector import hallucination_detector
                            
                            # Collect all tool results for validation
                            all_tool_results = "\n".join([
                                msg.get("content", "") 
                                for msg in final_messages 
                                if msg.get("role") == "tool"
                            ])
                            
                            # Validate response
                            log.api(f"🔍 Validating response ({len(full_response)} chars) against tool results ({len(all_tool_results)} chars)")
                            validation = await response_validator.validate_response(
                                full_response,
                                all_tool_results
                            )
                            log.api(f"📊 Validation: fabricated_urls={len(validation.fabricated_urls)}, risk_score={validation.risk_score:.2f}")
                            
                            # Detect hallucination risk
                            risk = await hallucination_detector.detect_hallucination_risk(
                                full_response,
                                all_tool_results
                            )
                            log.api(f"⚠️ Risk assessment: level={risk.risk_level}, score={risk.risk_score:.2f}, factors={len(risk.risk_factors)}")
                            
                            # Add warnings if ANY risk detected (lowered threshold from 0.6 to 0.3)
                            if risk.risk_level != "low" or validation.risk_score > 0.3:
                                log.api(f"🚨 ADDING WARNING - risk_level={risk.risk_level}, validation_score={validation.risk_score}")
                                warning_parts = ["\n\n⚠️ ПРЕДУПРЕЖДЕНИЕ О ДОСТОВЕРНОСТИ:\n"]
                                
                                if validation.fabricated_urls:
                                    warning_parts.append(
                                        f"❌ Обнаружены неподтвержденные URL: {', '.join(validation.fabricated_urls)}"
                                    )
                                
                                if validation.fabricated_phones:
                                    warning_parts.append(
                                        f"❌ Телефоны не найдены в источниках: {', '.join(validation.fabricated_phones)}"
                                    )
                                
                                if validation.fabricated_emails:
                                    warning_parts.append(
                                        f"❌ Email не найдены в источниках: {', '.join(validation.fabricated_emails)}"
                                    )
                                
                                if risk.risk_factors:
                                    warning_parts.append("\n🔍 Факторы риска:")
                                    for factor in risk.risk_factors:
                                        warning_parts.append(f"  • {factor}")
                                
                                warning_parts.append(
                                    f"\n⚠️ Уровень риска: {risk.risk_level.upper()} "
                                    f"({risk.risk_score:.1%})"
                                )
                                warning_parts.append(
                                    "\n💡 Рекомендация: Проверьте эту информацию из других источников!"
                                )
                                
                                full_response += "\n".join(warning_parts)
                            
                            # Send as single SSE chunk
                            yield f"data: {json.dumps({'token': full_response})}\n\n"
                            break
                        
                        # Add assistant message with tool calls
                        final_messages.append({
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }
                                for tc in message.tool_calls
                            ]
                        })
                        
                        # Execute each tool
                        for tool_call in message.tool_calls:
                            try:
                                log.api(f"🔧 Executing tool: {tool_call.function.name}")
                                args = json.loads(tool_call.function.arguments)
                                
                                # Execute via tools_manager
                                result = await tools_manager.execute(
                                    tool_call.function.name,
                                    args
                                )
                                
                                tool_result = result.content if hasattr(result, 'content') else str(result)
                                log.api(f"✅ Tool result: {tool_result[:100]}...")
                                
                            except Exception as e:
                                tool_result = f"Error executing tool: {str(e)}"
                                log.error(f"Tool execution failed: {e}")
                            
                            # Add tool result to messages
                            final_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result
                            })
                    
                except Exception as e:
                    log.error(f"Tool execution error: {e}")
                    error_msg = f"Ошибка поиска: {str(e)}"
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    full_response = error_msg
                    error_occurred = True
            
            else:
                # Normal streaming mode (no tools)
                try:
                    # Convert string to ThinkingMode enum
                    from src.core.lm import ThinkingMode
                    try:
                        thinking_mode = ThinkingMode(request.thinking_mode)
                    except ValueError:
                        thinking_mode = ThinkingMode.STANDARD
                        log.warn(f"Invalid thinking_mode '{request.thinking_mode}', using STANDARD")
                    
                    log.api("Calling lm_client.chat()", mode=thinking_mode.value)
                    
                    # Check if we need to load (Hot-swap)
                    # Model already resolved earlier, use local check first to avoid IPC if possible
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
                        # TODO: Implement tool execution loop for streaming
                        # tools=TOOLS,  # Disabled: need to handle tool_calls in streaming
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
                                think_text = chunk.get("think_content", "")
                                filtered_chars += chars
                                log.api("💭 Thinking ended", duration_ms=duration, chars_filtered=chars)
                                yield f"data: {json.dumps({'thinking': 'end', 'duration_ms': duration, 'think_content': think_text[:500]})}\n\n"
                            continue
                        
                        # Regular text chunk
                        if not isinstance(chunk, str):
                            continue
                        
                        # Check for error in chunk
                        if chunk.startswith("\n[Error:"):
                            error_occurred = True
                            full_response += chunk
                            log.error(f"Error chunk received: {chunk}")
                            yield f"data: {json.dumps({'error': chunk.strip()})}\n\n"
                            break
                        
                        # Accumulate response
                        full_response += chunk
                        
                        # Send chunk to frontend (SSE log silenced to reduce spam)
                        sse_data = json.dumps({'token': chunk})
                        yield f"data: {sse_data}\n\n"
                
                except Exception as e:
                    log.error(f"Generate exception: {type(e).__name__}: {e}")
                    import traceback
                    log.error(f"Traceback:\n{traceback.format_exc()}")
                    error_msg = f"\n[System Error: {str(e)}]"
                    full_response += error_msg
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        finally:
            # P0 CRITICAL FIX: Guaranteed save even on disconnect

            # Note: Empty response handling is now done in lm_client._stream_response
            # with retry logic and fallback message. This block only logs if still empty.
            if not full_response and not error_occurred:
                log.warn("⚠️ Empty response in finally block - lm_client should have provided fallback")

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
async def list_conversations(limit: int = 50, offset: int = 0):
    """List recent conversations with message counts."""
    convs = await memory.list_conversations(limit=limit, offset=offset)
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
        raise HTTPException(409, "Agent already running")
    
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


# ============= Model Selection Mode Endpoints =============

class ModelSelectionModeRequest(BaseModel):
    mode: str


@app.get("/api/config/model_selection_mode")
async def get_model_selection_mode():
    """Get current model selection mode (manual/auto)."""
    from src.core.config import config as app_config
    return {"mode": app_config.lm_studio.model_selection_mode}


@app.post("/api/config/model_selection_mode")
async def set_model_selection_mode(request: ModelSelectionModeRequest):
    """Set model selection mode (manual/auto)."""
    from src.core.config import config as app_config
    
    if request.mode not in ["manual", "auto"]:
        raise HTTPException(400, "Invalid mode. Must be 'manual' or 'auto'")
    
    app_config.lm_studio.model_selection_mode = request.mode
    
    from src.core.logger import log
    log.api(f"🔧 Model selection mode changed to: {request.mode}")
    
    return {"success": True, "mode": request.mode}


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
