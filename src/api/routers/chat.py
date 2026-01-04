"""
Chat Router for MAX AI API.

Endpoints:
- POST /api/chat
- GET /api/conversations
- POST /api/conversations
- GET /api/conversations/{id}/messages
"""
import asyncio
import json
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.memory import memory
from src.core.lm import lm_client, ThinkingMode
from src.core.rag import rag
from src.core.user_profile import user_profile
from src.core.metrics import metrics_engine
from src.core.adaptation import prompt_builder
from src.core.tools import tools as tools_manager, TOOLS
from src.core.logger import log
from src.core.confidence import confidence_scorer
from src.core.routing import get_smart_router, get_privacy_guard

router = APIRouter(prefix="/api", tags=["chat"])

# ============= Pydantic Models =============

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: str = "auto"
    temperature: float = 0.7
    use_rag: bool = True
    thinking_mode: str = "standard"  # fast/standard/deep
    has_image: bool = False

class ConversationCreate(BaseModel):
    title: str = "Новый разговор"

# ============= Helpers =============

def _log_task_exception(task: asyncio.Task):
    """Log exceptions from fire-and-forget tasks."""
    try:
        exc = task.exception()
        if exc:
            log.error(f"[Background Task Error] {type(exc).__name__}: {exc}")
    except asyncio.CancelledError:
        pass

# ============= Endpoints =============

@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with streaming response (SSE)."""
    
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
    
    # Track interaction (Background task)
    task = asyncio.create_task(user_profile.track_interaction(request.message))
    task.add_done_callback(_log_task_exception)
    
    # Auto-generate title if new conversation
    async def _update_title():
        try:
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
    
    # =========================================
    # SmartRouter: Intelligent Routing Decision
    # =========================================
    smart_router = get_smart_router()
    route = await smart_router.route(request.message)
    
    log.api(f"SmartRouter: intent={route.intent}, source={route.routing_source}, "
            f"prompt={route.prompt_name}, {route.routing_time_ms:.1f}ms")
    
    # Handle speculative responses (greetings)
    if route.speculative_response and route.intent in {"greeting", "privacy_unlock"}:
        # Fast path: return instant response
        async def speculative_generate():
            response = route.speculative_response
            yield f"data: {json.dumps({'token': response})}\n\n"
            
            # Save to memory
            saved_msg = await memory.add_message(conv_id, "assistant", response)
            yield f"data: {json.dumps({'done': True, 'message_id': saved_msg.id, 'conversation_id': conv_id})}\n\n"
        
        return StreamingResponse(
            speculative_generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    
    # Override request params with SmartRouter decisions
    effective_temperature = route.temperature if route.temperature else request.temperature
    effective_use_rag = route.use_rag if route.use_rag is not None else request.use_rag
    
    # Get context
    context = await memory.get_smart_context(conv_id)
    log.api("Context retrieved", messages=len(context))
    
    # Detect if user is requesting a web search
    search_keywords = ["найди", "поищи", "search", "check", "проверь", "посмотри в интернете", "in internet", "google", "what's new", "новости"]
    needs_search = any(keyword in request.message.lower() for keyword in search_keywords)

    # =========================================================================
    # SYSTEM PROMPT CONSTRUCTION
    # Merge all system instructions into a single message to avoid "Strict Alternation" errors.
    # =========================================================================
    system_prompts = []
    
    # 0. Base Identity from external file (editable by user)
    from pathlib import Path
    base_prompt_path = Path(__file__).parent.parent.parent.parent / "data" / "system_prompt.txt"
    if base_prompt_path.exists():
        try:
            base_prompt = base_prompt_path.read_text(encoding="utf-8").strip()
            if base_prompt:
                system_prompts.append(base_prompt)
                log.api("Base system prompt loaded from file")
        except Exception as e:
            log.warn(f"Failed to load system_prompt.txt: {e}")
    
    # 1. SmartRouter prompt (if available, augments base prompt)
    if route.system_prompt:
        system_prompts.append(route.system_prompt)
        log.api(f"SmartRouter prompt selected: {route.prompt_name}")
    
    # 2. Adaptive Prompt (Style/Tone)
    style_prompt = await prompt_builder.build_adaptive_prompt(request.message)
    if style_prompt:
        system_prompts.append(style_prompt)
        log.api("Adaptive prompt added")

    # 3. Anti-hallucination for Search
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
        system_prompts.append(anti_hallucination_prompt)
        log.api("Anti-hallucination prompt added")

    # 4. RAG Context
    if effective_use_rag:
        rag_context = await rag.get_context_for_query(request.message, max_tokens=1000)
        if rag_context:
            system_prompts.append(f"Relevant documents:\n{rag_context}")
            log.api("RAG context added", chars=len(rag_context))

    # Insert Consolidated System Message
    if system_prompts:
        consolidated_system_content = "\n\n---\n\n".join(system_prompts)
        
        # Check if history already starts with system message
        if context and context[0].get("role") == "system":
            # Append to existing system message
            context[0]["content"] = consolidated_system_content + "\n\n" + context[0]["content"]
        else:
            # Insert new system message at start
            context.insert(0, {
                "role": "system",
                "content": consolidated_system_content
            })
        log.api("Consolidated system prompt injected")
    
    async def generate() -> AsyncGenerator[str, None]:
        """Stream tokens as SSE or execute tools if needed."""
        full_response = ""
        error_occurred = False
        sse_count = 0
        filtered_chars = 0
        
        log.api("Starting SSE generator")
        
        target_model = request.model
        
        # Smart model resolution
        from src.core.config import config as app_config
        
        if app_config.lm_studio.model_selection_mode == "manual":
            if target_model == "auto" or not target_model:
                loaded_model = await lm_client.get_loaded_model()
                if loaded_model:
                    target_model = loaded_model
                    log.api(f"🎯 MANUAL: using loaded model: {target_model}")
                else:
                    target_model = app_config.lm_studio.default_model
                    log.api(f"🎯 MANUAL: using default model: {target_model}")
            else:
                log.api(f"🎯 MANUAL: explicit selection: {target_model}")
        else:
            if target_model == "auto" or not target_model:
                loaded_model = await lm_client.get_loaded_model()
                if loaded_model:
                    target_model = loaded_model
                    log.api(f"🧠 AUTO: reusing loaded model: {target_model}")
                else:
                    try:
                        thinking_mode = ThinkingMode(request.thinking_mode)
                    except ValueError:
                        thinking_mode = ThinkingMode.STANDARD
                    mode_config = lm_client.get_mode_config(thinking_mode)
                    target_model = mode_config.model
                    log.api(f"🧠 AUTO: thinking mode selected: {target_model}")
                    
        # COGNITIVE LOOP ROUTING (System 2)
        try:
            t_mode = ThinkingMode(request.thinking_mode)
        except ValueError:
            t_mode = ThinkingMode.STANDARD
        
        if t_mode == ThinkingMode.DEEP:
            log.api("🧠 Entering System 2 Cognitive Loop")
            from src.core.cognitive.graph import build_cognitive_graph
            from src.core.cognitive.types import CognitiveState
            
            yield f"data: {json.dumps({'thinking': 'start'})}\n\n"
            yield f"data: {json.dumps({'token': '🔄 Analyzing problem complexity...\n'})}\n\n"
            
            graph = build_cognitive_graph()
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
                "thinking_tokens": []
            }
            
            try:
                final_answer = ""
                # Use astream manual loop
                async for event in graph.astream(initial_state):
                    for node_name, node_state in event.items():
                        if node_name == "__end__":
                            continue
                            
                        step_name = node_state.get("step_name", node_name)
                        step_content = node_state.get("step_content", "")
                        
                        if step_name and step_content:
                            step_data = {
                                "thinking": "step", 
                                "name": step_name.upper(), 
                                "content": step_content
                            }
                            yield f"data: {json.dumps(step_data)}\n\n"
                            
                        if "draft_answer" in node_state:
                            final_answer = node_state["draft_answer"]
                        if "score" in node_state:
                            score = node_state["score"]
                        if "iterations" in node_state:
                            iterations = node_state["iterations"]
                            
            except Exception as e:
                log.error(f"Graph streaming error, falling back to invoke: {e}")
                final_state = await graph.ainvoke(initial_state)
                final_answer = final_state.get("draft_answer", "Error in cognitive loop")
                score = final_state.get("score", 0.0)
                iterations = final_state.get("iterations", 0)

            think_summary = f"Cognitive Loop: {iterations} iterations, Score: {score:.2f}"
            yield f"data: {json.dumps({'thinking': 'end', 'duration_ms': 0, 'think_content': think_summary})}\n\n"
            yield f"data: {json.dumps({'token': final_answer})}\n\n"
            full_response = final_answer
            return
        
        # Plan Progress UI (Visual Thinking for Standard Mode)
        if route.intent in {"task", "coding", "search", "analysis"} and t_mode != ThinkingMode.DEEP:
            log.api(f"🧠 Starting Plan Progress UI for intent: {route.intent}")
            from src.core.routing.plan_tracker import create_and_track_plan
            
            yield f"data: {json.dumps({'thinking': 'start'})}\n\n"
            
            try:
                async for update in create_and_track_plan(request.message, route.intent):
                    step = update.get("step", {})
                    
                    if update["type"] == "step_start":
                        step_content = step.get('description') or "Processing..."
                        yield f"data: {json.dumps({
                            'thinking': 'step', 
                            'name': step.get('title', 'Step').upper(), 
                            'content': f"{step.get('icon', '•')} {step_content}"
                        })}\n\n"
                        
                yield f"data: {json.dumps({'thinking': 'end', 'duration_ms': 0, 'think_content': 'Plan verified'})}\n\n"
            except Exception as e:
                log.error(f"Plan tracker error: {e}")
                yield f"data: {json.dumps({'thinking': 'end', 'duration_ms': 0, 'think_content': 'Planning skipped'})}\n\n"
        
        # STANDARD API CALL
        try:
            # Helper for strict message alternation (System -> User -> Assistant -> User...)
            def safe_context_merge(history_context, current_message):
                merged = []
                
                # 1. System message (always first)
                if history_context and history_context[0].get("role") == "system":
                    # Make a deep copy to avoid modifying original context
                    merged.append(history_context[0].copy())
                    start_idx = 1
                else:
                    start_idx = 0
                
                # 2. CRITICAL FIX: First non-system message MUST be user
                #    Skip any leading assistant messages (orphaned greetings, edge cases)
                non_system_msgs = list(history_context[start_idx:])
                while non_system_msgs and non_system_msgs[0].get("role") == "assistant":
                    log.api(f"⚠️ Skipping orphaned assistant message before first user")
                    non_system_msgs = non_system_msgs[1:]
                
                # 3. Process history (now guaranteed to start with user or be empty)
                for msg in non_system_msgs:
                    role = msg.get("role")
                    content = msg.get("content", "")
                    
                    if not merged:
                        merged.append(msg.copy())
                        continue
                    
                    last_msg = merged[-1]
                    
                    # Merge consecutive same-role messages
                    if last_msg.get("role") == role:
                        last_msg["content"] += f"\n\n{content}"
                    # Handle system messages in middle of history (convert to user note)
                    elif role == "system":
                        if last_msg.get("role") == "user":
                            last_msg["content"] += f"\n\n[System Note: {content}]"
                        else:
                            # Create new user message for system note
                            merged.append({"role": "user", "content": f"[System Note: {content}]"})
                    else:
                        merged.append(msg.copy())
                
                # 3. Add current user message
                if merged and merged[-1].get("role") == "user":
                    merged[-1]["content"] += f"\n\n{current_message}"
                else:
                    merged.append({"role": "user", "content": current_message})
                    
                return merged

            final_messages = safe_context_merge(context, request.message)

            # DEBUG: Log message structure
            log.api(f"📋 Message structure BEFORE sanitization (context): {len(context)} messages")
            for i, m in enumerate(context):
                log.api(f"   [{i}] role={m.get('role')}, len={len(m.get('content', ''))}")
            
            log.api(f"📋 Message structure AFTER sanitization: {len(final_messages)} messages")
            for i, m in enumerate(final_messages):
                log.api(f"   [{i}] role={m.get('role')}, len={len(m.get('content', ''))}")

            if needs_search:
                log.api("🔍 Web search detected - using tool execution mode")
                try:
                    # final_messages is already prepared by safe_context_merge
                    
                    for iteration in range(5):
                        log.api(f"🔄 Tool iteration {iteration + 1}/5, sending {len(TOOLS)} tools to model")
                        
                        response = await lm_client.client.chat.completions.create(
                            model=target_model,
                            messages=final_messages,
                            temperature=effective_temperature,
                            tools=TOOLS,
                            tool_choice="auto",
                            stream=False
                        )
                        
                        message = response.choices[0].message
                        log.api(f"📊 Response received - has tool_calls: {bool(message.tool_calls)}, content: {bool(message.content)}")
                        
                        if message.tool_calls:
                            log.api(f"🔧 Tool calls count: {len(message.tool_calls)}")
                            for tc in message.tool_calls:
                                log.api(f"   Tool: {tc.function.name}")
                        
                        if not message.tool_calls:
                            full_response = message.content or ""
                            
                            from src.core.response_validator import response_validator
                            from src.core.hallucination_detector import hallucination_detector
                            
                            all_tool_results = "\n".join([msg.get("content", "") for msg in final_messages if msg.get("role") == "tool"])
                            
                            log.api(f"🔍 Validating response ({len(full_response)} chars)")
                            validation = await response_validator.validate_response(full_response, all_tool_results)
                            risk = await hallucination_detector.detect_hallucination_risk(full_response, all_tool_results)
                            log.api(f"⚠️ Risk assessment: level={risk.risk_level}, score={risk.risk_score:.2f}")
                            
                            if risk.risk_level != "low" or validation.risk_score > 0.3:
                                log.api("🚨 ADDING WARNING")
                                warning_parts = ["\n\n⚠️ ПРЕДУПРЕЖДЕНИЕ О ДОСТОВЕРНОСТИ:\n"]
                                if validation.fabricated_urls:
                                    warning_parts.append(f"❌ Обнаружены неподтвержденные URL: {', '.join(validation.fabricated_urls)}")
                                full_response += "\n".join(warning_parts)
                            
                            yield f"data: {json.dumps({'token': full_response})}\n\n"
                            break
                        
                        final_messages.append({
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                                } for tc in message.tool_calls
                            ]
                        })
                        
                        for tool_call in message.tool_calls:
                            try:
                                log.api(f"🔧 Executing tool: {tool_call.function.name}")
                                args = json.loads(tool_call.function.arguments)
                                result = await tools_manager.execute(tool_call.function.name, args)
                                tool_result = result.content if hasattr(result, 'content') else str(result)
                                log.api(f"✅ Tool result: {tool_result[:100]}...")
                            except Exception as e:
                                tool_result = f"Error executing tool: {str(e)}"
                                log.error(f"Tool execution failed: {e}")
                            
                            final_messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})
                    
                except Exception as e:
                    log.error(f"Tool execution error: {e}")
                    error_msg = f"Ошибка поиска: {str(e)}"
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    full_response = error_msg
                    error_occurred = True
            
            else:
                # Normal Streaming
                try:
                    try:
                        thinking_mode = ThinkingMode(request.thinking_mode)
                    except ValueError:
                        thinking_mode = ThinkingMode.STANDARD
                        log.warn(f"Invalid thinking_mode '{request.thinking_mode}', using STANDARD")
                    
                    log.api("Calling lm_client.chat()", mode=thinking_mode.value)
                    
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
                        messages=final_messages,
                        temperature=effective_temperature,
                        model=target_model,
                        thinking_mode=thinking_mode,
                        has_image=request.has_image,
                        stream=True
                    ):
                        sse_count += 1
                        
                        if isinstance(chunk, dict) and "_meta" in chunk:
                            meta_type = chunk["_meta"]
                            if meta_type == "thinking_start":
                                yield f"data: {json.dumps({'thinking': 'start'})}\n\n"
                            elif meta_type == "thinking_end":
                                duration = chunk.get("duration_ms", 0)
                                chars = chunk.get("chars_filtered", 0)
                                think_text = chunk.get("think_content", "")
                                filtered_chars += chars
                                yield f"data: {json.dumps({'thinking': 'end', 'duration_ms': duration, 'think_content': think_text[:500]})}\n\n"
                            continue
                        
                        if not isinstance(chunk, str):
                            continue
                        
                        if chunk.startswith("\n[Error:"):
                            error_occurred = True
                            full_response += chunk
                            log.error(f"Error chunk received: {chunk}")
                            yield f"data: {json.dumps({'error': chunk.strip()})}\n\n"
                            break
                        
                        full_response += chunk
                        sse_data = json.dumps({'token': chunk})
                        yield f"data: {sse_data}\n\n"
                
                except Exception as e:
                    log.error(f"Generate exception: {type(e).__name__}: {e}")
                    error_msg = f"\n[System Error: {str(e)}]"
                    full_response += error_msg
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        finally:
            # Check for empty response (P0 Fix)
            if not full_response and not error_occurred:
                 error_msg = "\n[Error: Model returned no content]"
                 full_response = error_msg
                 log.error(f"⚠️ Empty response detected in finally block, injecting error: {error_msg}")
                 yield f"data: {json.dumps({'error': error_msg})}\n\n"

            if full_response:
                try:
                    saved_msg = await memory.add_message(
                        conv_id, "assistant", full_response,
                        model_used=lm_client.current_model or "unknown"
                    )
                    log.api("Response saved to memory", msg_id=saved_msg.id)
                    
                    await metrics_engine.record_interaction_outcome(
                        message_id=saved_msg.id,
                        user_message=request.message,
                        facts_in_context=len(context),
                        style_prompt_length=len(style_prompt) if style_prompt else 0
                    )
                    
                    if not error_occurred:
                        done_data = {'done': True, 'message_id': saved_msg.id, 'conversation_id': conv_id}
                        yield f"data: {json.dumps(done_data)}\n\n"
                        
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

@router.get("/conversations")
async def list_conversations(limit: int = 50, offset: int = 0):
    """List recent conversations."""
    convs = await memory.list_conversations(limit=limit, offset=offset)
    result = []
    for c in convs:
        messages = await memory.get_messages(c.id, limit=1000)
        result.append({
            "id": c.id,
            "title": c.title,
            "updated_at": c.updated_at,
            "message_count": len(messages)
        })
    return result

@router.post("/conversations")
async def create_conversation(data: ConversationCreate):
    """Create new conversation."""
    conv = await memory.create_conversation(data.title)
    return {"id": conv.id, "title": conv.title}

@router.get("/conversations/{conv_id}/messages")
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

@router.delete("/memory/clear")
async def clear_all_memory():
    """Clear all memory: conversations, messages, and facts. For debugging."""
    log.api("🗑️ Clearing all memory...")
    
    try:
        # Clear all tables
        await memory._db.execute("DELETE FROM messages")
        await memory._db.execute("DELETE FROM conversation_summaries")
        await memory._db.execute("DELETE FROM conversations")
        await memory._db.execute("DELETE FROM memory_facts")
        await memory._db.commit()
        
        log.api("✅ All memory cleared successfully")
        return {"status": "ok", "message": "All memory cleared"}
    except Exception as e:
        log.error(f"Failed to clear memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
