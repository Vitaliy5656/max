"""
LM Studio API Client with Model Switching & Smart Routing.

Features:
- OpenAI-compatible API client
- Model switching via CLI (lms load/unload)
- Smart routing based on task type
- Auto-unload TTL
- Streaming support
- Reasoning mode with thinking time
"""
import asyncio
import json
import time as import_time
from typing import AsyncIterator, Optional, Any
from dataclasses import dataclass
from enum import Enum
import httpx
from openai import AsyncOpenAI

from .config import config
from .safe_shell import safe_shell
from .logger import log


class TaskType(Enum):
    """Type of task for smart routing."""
    REASONING = "reasoning"  # Complex thinking, chain-of-thought
    VISION = "vision"        # Image analysis
    QUICK = "quick"          # Fast simple responses
    DEFAULT = "default"      # General purpose


class ThinkingMode(Enum):
    """User-selectable thinking depth modes."""
    FAST = "fast"           # Quick responses, minimal reasoning
    STANDARD = "standard"   # Balanced quality/speed
    DEEP = "deep"           # Chain-of-thought, detailed analysis
    VISION = "vision"       # Auto-activated for images


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    id: str
    object: str = "model"
    owned_by: str = "lmstudio"
    
    
class LMStudioClient:
    """
    Client for LM Studio's OpenAI-compatible API.

    Supports:
    - Chat completions with streaming
    - Model switching via CLI
    - Smart routing based on task
    - Auto-unload after TTL
    - Rate limiting (P2 fix)
    """

    # P2 fix: Rate limiting configuration
    MIN_REQUEST_INTERVAL = 0.1  # seconds between requests

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or config.lm_studio.base_url
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key="not-needed"  # LM Studio doesn't require API key
        )
        self._current_model: Optional[str] = None
        self._last_used: float = 0
        self._unload_task: Optional[asyncio.Task] = None
        # P2 fix: Rate limiting via semaphore
        self._request_semaphore = asyncio.Semaphore(config.lm_studio.max_concurrent_requests)
        self._last_request_time: float = 0
        
        # P0 Fix: Race Condition Lock
        self._lock = asyncio.Lock()
        
        # Cache for available models
        self._available_models_cache: list[str] = []
        self._last_scan_time: float = 0
        self._scan_ttl: int = 60  # Cache model list for 60s
    
    @property
    def current_model(self) -> Optional[str]:
        """Get currently set model name."""
        return self._current_model
    
    async def get_available_models(self, force_refresh: bool = False) -> list[str]:
        """Get list of available model keys (smart scan)."""
        import time
        now = time.monotonic()
        
        # Use cache if fresh
        if not force_refresh and self._available_models_cache and (now - self._last_scan_time < self._scan_ttl):
            return self._available_models_cache
            
        log.lm("🔍 Scanning for models via CLI...")
        
        # Try CLI first (Real data)
        real_models = await self._scan_models_cli()
        if real_models:
            self._available_models_cache = real_models
            self._last_scan_time = now
            return real_models
            
        # Fallback to config (Legacy/Safe mode)
        log.warn("CLI scan failed, using config fallback")
        return [
            config.lm_studio.default_model,
            config.lm_studio.reasoning_model,
            config.lm_studio.quick_model,
            config.lm_studio.vision_model,
        ]
        
    async def _scan_models_cli(self) -> list[str]:
        """Run 'lms ls' to get real models."""
        try:
            result = await safe_shell.execute("lms ls", timeout=30.0)
            
            if result.return_code != 0:
                return []
                
            lines = result.stdout.splitlines()
            models = []
            for line in lines:
                line = line.strip()
                # Skip headers or decorative lines if any
                if not line or line.startswith("SIZE") or line.startswith("Downloaded"):
                    continue
                # Simple heuristic: assume model key is the first contiguous string
                # or the whole line if it looks like a model ID
                parts = line.split()
                if parts:
                    # In newer LMS CLI, the first column is often the model key/path
                    models.append(parts[0])
            
            return models
        except Exception as e:
            log.error(f"Error scanning models: {e}")
            return []

    async def list_models(self) -> list[ModelInfo]:
        """Get list of available models from LM Studio API (Legacy)."""
        try:
            response = await self.client.models.list()
            return [
                ModelInfo(id=model.id, object=model.object, owned_by=model.owned_by)
                for model in response.data
            ]
        except Exception as e:
            log.error(f"Error listing models API: {e}")
            return []
    
    async def sync_state(self) -> Optional[str]:
        """Refreshes local state from actual LM Studio status."""
        try:
            # Check via API first (Most reliable for "what responds to API")
            loaded = await self.get_loaded_model()
            if loaded:
                if self._current_model != loaded:
                    log.lm(f"🧩 State healing: {self._current_model} -> {loaded}")
                    self._current_model = loaded
                return loaded
                
            # If API returns nothing, maybe nothing is loaded.
            # We could verify with 'lms ps' but API is the authority for the client.
            self._current_model = None
            return None
        except Exception:
            return None

    async def get_loaded_model(self) -> Optional[str]:
        """Get currently loaded model (API check)."""
        try:
            # Fast check
            models = await self.list_models()
            return models[0].id if models else None
        except:
            return None
    
    async def load_model(self, model_key: str, ttl: Optional[int] = None) -> bool:
        """Safe thread-locked model loading."""
        async with self._lock:
            # Double check inside lock
            loaded = await self.get_loaded_model()
            if loaded == model_key:
                self._current_model = model_key
                return True
                
            log.lm(f"🔄 Loading model: {model_key}...")
            
            try:
                cmd = f"lms load {model_key}"
                if ttl:
                    cmd += f" --ttl {ttl}"

                result = await safe_shell.execute(cmd, timeout=120.0)

                if result.return_code == 0:
                    self._current_model = model_key
                    log.lm(f"✓ Model loaded: {model_key}")
                    # Force a quick API check to confirm
                    await asyncio.sleep(0.5) 
                    await self.get_loaded_model() 
                    return True
                else:
                    log.error(f"✗ Failed to load model: {result.stderr}")
                    return False
            except Exception as e:
                log.error(f"✗ Error loading model: {e}")
                return False

    async def unload_model(self, model_key: Optional[str] = None) -> bool:
        """Safe thread-locked unload."""
        async with self._lock:
            try:
                if model_key:
                    cmd = f"lms unload {model_key}"
                else:
                    cmd = "lms unload --all"

                result = await safe_shell.execute(cmd, timeout=30.0)

                if result.return_code == 0:
                    if not model_key or model_key == self._current_model:
                        self._current_model = None
                    log.lm(f"✓ Model unloaded")
                    return True
                return False
            except Exception as e:
                log.error(f"✗ Error unloading model: {e}")
                return False
    
    async def ensure_model_loaded(self, required_model: str) -> bool:
        """
        Hot-swap: ensure the required model is loaded (Thread-safe).
        
        Smart matching: if loaded model contains required model name, 
        consider it a match (e.g., 'mistralai/ministral-3b' matches 'ministral-3b').
        """
        # Fast optimistic check outside lock (Performance)
        if self._current_model == required_model:
            return True
        
        # Lock for mutation
        async with self._lock:
            # Re-check state after acquiring lock (Double-Checked Locking)
            current = await self.get_loaded_model()
            
            # Exact match
            if current == required_model:
                self._current_model = required_model
                return True
            
            # Fuzzy match: if current model contains the required model name
            # e.g., "mistralai/ministral-3b" contains "ministral-3b"
            if current and required_model:
                req_lower = required_model.lower()
                cur_lower = current.lower()
                if req_lower in cur_lower or cur_lower.endswith(req_lower):
                    log.lm(f"✓ Model already loaded (fuzzy match): {current}")
                    self._current_model = current  # Use actual loaded model
                    return True
            
            # If ANY model is loaded and we're not explicitly switching, use it
            if current and (required_model == "auto" or not required_model):
                log.lm(f"✓ Using currently loaded model: {current}")
                self._current_model = current
                return True
            
            log.lm(f"🔄 Hot-swap needed: {current or 'none'} → {required_model}")
            
            # Unload current model if different and exists
            if current:
                # Direct CLI unload to be safe (using SafeShell for Windows)
                await safe_shell.execute(f"lms unload {current}", timeout=30.0)
            
            # Load required model
            success = await self._load_model_impl(required_model, ttl=config.lm_studio.auto_unload_ttl)
            return success
            
    async def _load_model_impl(self, model_key: str, ttl: Optional[int] = None) -> bool:
        """Internal load implementation without lock (uses SafeShell for Windows)."""
        try:
            cmd = f"lms load {model_key}"
            if ttl:
                cmd += f" --ttl {ttl}"

            result = await safe_shell.execute(cmd, timeout=120.0)

            if result.return_code == 0:
                self._current_model = model_key
                log.lm(f"✓ Model loaded: {model_key}")
                return True
            else:
                log.error(f"✗ Failed to load model: {result.stderr}")
                return False
        except Exception as e:
            log.error(f"✗ Error in _load_model_impl: {e}")
            return False

    def get_mode_config(self, thinking_mode: ThinkingMode):
        """Get configuration for a thinking mode."""
        from .config import ThinkingModeConfig
        mode_config = config.lm_studio.thinking_modes.get(thinking_mode.value)
        if mode_config:
            return mode_config
        # Fallback to standard
        return config.lm_studio.thinking_modes["standard"]
    
    async def get_model_for_task(self, task_type: TaskType) -> str:
        """Smart routing: get best model for task type."""
        # Use available models if cached, else use config defaults
        # Only do a quick check if we have cache, don't force scan
        available = await self.get_available_models(force_refresh=False)
        
        # TODO: Implement sophisticated matching against 'available'
        # For now, sticking to config defaults but logging intent
        if task_type == TaskType.VISION:
            return config.lm_studio.vision_model
        elif task_type == TaskType.REASONING:
            return config.lm_studio.reasoning_model
        elif task_type == TaskType.QUICK:
            return config.lm_studio.quick_model
        else:
            return config.lm_studio.default_model
    
    def detect_task_type(self, message: str, has_image: bool = False) -> TaskType:
        """Auto-detect task type from message content."""
        if has_image:
            return TaskType.VISION
        
        # Keywords for reasoning tasks
        reasoning_keywords = [
            "почему", "объясни", "проанализируй", "сравни", "подумай",
            "рассуждай", "логика", "вывод", "докажи", "аргумент",
            "why", "explain", "analyze", "compare", "think", "reason"
        ]
        
        # Keywords for quick tasks
        quick_keywords = [
            "да или нет", "кратко", "быстро", "одним словом",
            "yes or no", "briefly", "quick", "short"
        ]
        
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in quick_keywords):
            return TaskType.QUICK
        
        if any(kw in message_lower for kw in reasoning_keywords):
            return TaskType.REASONING
        
        # Issue #4 fix: Additional heuristics beyond keywords
        # 1. Multiple question marks suggest complex inquiry
        question_marks = message.count('?')
        if question_marks >= 2:
            return TaskType.REASONING
        
        # 2. Math symbols often need reasoning
        has_math = any(c in message for c in ['=', '+', '*', '/', '^', '√', '∫', 'π'])
        if has_math and len(message) > 30:
            return TaskType.REASONING
        
        # 3. Question with significant length
        if question_marks >= 1 and len(message) > 100:
            return TaskType.REASONING
        
        # Default based on message length
        if len(message) > 200:
            return TaskType.REASONING
        
        return TaskType.DEFAULT
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_type: Optional[TaskType] = None,
        thinking_mode: ThinkingMode = ThinkingMode.STANDARD,  # NEW
        has_image: bool = False,  # NEW: Auto-detect vision
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str] | str:
        """
        Send chat completion request with thinking mode support.
        
        Args:
            messages: OpenAI-format messages list
            model: Model to use (overrides thinking_mode if specified)
            stream: Enable streaming response
            temperature: Sampling temperature (overrides mode config)
            max_tokens: Maximum tokens to generate (overrides mode config)
            task_type: Task type for smart routing (legacy)
            thinking_mode: User-selected thinking depth
            has_image: If True, auto-switch to VISION mode
            tools: Function tools for tool calling
            
        Returns:
            Async iterator of chunks if streaming, else complete response
        """
        # Auto-activate Vision mode if image present
        if has_image:
            thinking_mode = ThinkingMode.VISION
            log.lm("👁️ Vision mode auto-activated (image detected)")
        
        # Get mode configuration
        mode_config = self.get_mode_config(thinking_mode)
        
        # Model Selection Logic based on mode
        if config.lm_studio.model_selection_mode == "manual":
            # MANUAL MODE: Thinking modes do NOT change model
            # Only apply temperature and token limits
            if not model:
                # No explicit model → use currently loaded or default
                loaded = await self.get_loaded_model()
                model = loaded if loaded else config.lm_studio.default_model
                log.lm(f"🎯 MANUAL mode: using {'loaded' if loaded else 'default'} model: {model}")
            else:
                log.lm(f"🎯 MANUAL mode: explicit model selection: {model}")
            
            # Apply only thinking parameters (not model)
            if temperature is None:
                temperature = mode_config.temperature
            if max_tokens is None:
                max_tokens = mode_config.max_tokens
        else:
            # AUTO MODE: Thinking modes select optimal model (legacy behavior)
            if not model:
                model = mode_config.model
                log.lm(f"🧠 AUTO mode: thinking mode selected model: {model}")
            
            if temperature is None:
                temperature = mode_config.temperature
            if max_tokens is None:
                max_tokens = mode_config.max_tokens
        
        # Inject system prompt suffix for thinking mode (Chain-of-Thought)
        if mode_config.system_prompt_suffix:
            messages = self._inject_thinking_prompt(messages, mode_config.system_prompt_suffix)
        
        # Apply thinking time for DEEP mode
        if thinking_mode == ThinkingMode.DEEP and config.lm_studio.min_thinking_time > 0:
            await asyncio.sleep(config.lm_studio.min_thinking_time)
        
        params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        params.update(kwargs)

        # STATE BUG FIX: Track which model is being used
        self._current_model = model

        if stream:
            # P0 Fix: Wrap streaming with SlotManager
            return self._stream_with_slots(params, priority=SlotPriority.STANDARD)
        else:
            # P2 fix: Apply rate limiting AND SlotManager
            # Note: For non-streaming, we just wait for slot
            async with self._request_semaphore:
                await self._enforce_rate_limit()
                
                # Acquire slot (blocking)
                # Since we can't yield "heartbeats" in a non-async-gen function effectively here without changing return type,
                # we assume non-streaming is fast enough or handled by upper layer.
                # BUT for consistency, we should use slot_manager. 
                # However, acquire_slot is an async generator.
                # Simplified: Just blocking wait for now (User mostly uses streaming).
                
                # TODO: Implement proper slot acquisition for non-streaming if needed.
                # For now, bypassing slots for non-streaming system calls (usually fast/low priority)
                
                response = await self.client.chat.completions.create(**params)
                return response.choices[0].message.content or ""

    async def _stream_with_slots(self, params: dict, priority: Any) -> AsyncIterator[str]:
        """Stream response with Slot management (Heartbeats)."""
        from .parallel import slot_manager, SlotPriority
        
        request_id = f"req_{int(import_time.time()*1000)}"
        
        try:
            # 1. Acquire Slot (Yields heartbeats while waiting)
            async for status in slot_manager.acquire_slot(request_id, priority):
                if status == "waiting":
                    yield {"_meta": "queue_heartbeat"}
                elif status == "acquired":
                    break
            
            # 2. Add Request Header for Tracking (Optional)
            # params["extra_headers"] = {"X-Request-ID": request_id}
            
            # 3. Stream
            async for chunk in self._stream_response(params):
                yield chunk
                
        finally:
            # 4. Release Slot
            slot_manager.release_slot(request_id)

    def _inject_thinking_prompt(self, messages: list[dict], suffix: str) -> list[dict]:
        """
        Inject thinking mode system prompt suffix.
        
        Appends the mode-specific instructions to the system message
        for Chain-of-Thought reasoning.
        """
        messages = messages.copy()  # Don't mutate original
        
        # Find existing system message
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                messages[i] = {
                    **msg,
                    "content": f"{msg.get('content', '')}\n\n{suffix}"
                }
                return messages
        
        # No system message found, prepend one
        messages.insert(0, {"role": "system", "content": suffix})
        return messages

    async def _enforce_rate_limit(self):
        """Enforce minimum interval between requests (P2 fix)."""
        import time
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()
    
    # Multi-pattern think tag detection for various reasoning models
    THINK_TAG_PATTERNS = [
        # (open_tag, close_tag) pairs
        ("<think>", "</think>"),           # DeepSeek R1, Qwen
        ("<thinking>", "</thinking>"),     # Claude-style
        ("<reasoning>", "</reasoning>"),   # Generic reasoning
        ("<reflection>", "</reflection>"), # Reflection models
    ]
    
    async def _stream_response(self, params: dict, _retry_count: int = 0) -> AsyncIterator[str]:
        """
        Stream response chunks with multi-pattern think tag filtering.

        Supports various reasoning models:
        - DeepSeek R1: <think>...</think>
        - Claude-style: <thinking>...</thinking>
        - Generic: <reasoning>...</reasoning>

        Uses buffering to handle tags split across chunk boundaries.
        Includes retry logic for empty responses (common with short questions).
        """
        import re
        from .logger import log

        MAX_RETRIES = 2  # Retry up to 2 times for empty responses

        # State machine
        in_think_block = False
        current_close_tag = ""
        pending_buffer = ""  # Buffer for potential partial tags
        think_content = ""   # Accumulated thinking content
        think_start_time = 0.0  # Timestamp when thinking started

        # Stats for logging
        chunk_count = 0
        total_chars_received = 0
        total_chars_yielded = 0
        total_chars_filtered = 0

        # Pre-compile patterns for efficiency
        open_pattern = re.compile(r'<(think|thinking|reasoning|reflection)>', re.IGNORECASE)

        model = params.get("model", "unknown")
        # log.lm_stream_start(model) is called by logger internally via events?
        # Actually log.lm_stream_start is a method of Logger.
        # The original code had print then log calls. We unify.
        log.lm(f"Starting stream for model={model}")
        log.lm_stream_start(model)

        try:
            log.lm("Creating chat completion...", model=model)
            stream = await self.client.chat.completions.create(**params)
            log.lm("Stream connection established ✓")
            
            async for chunk in stream:
                chunk_count += 1
                
                # Check for empty chunk
                if not chunk.choices:
                    # Silenced: Empty chunk log
                    continue
                
                delta = chunk.choices[0].delta
                if not delta.content:
                    # Log finish reason if present
                    finish_reason = chunk.choices[0].finish_reason
                    if finish_reason:
                        pass  # Silenced: Finish signal log
                    continue
                    
                content = delta.content
                total_chars_received += len(content)
                
                # Silenced: Raw chunk logs to reduce spam
                # preview = content.replace("\n", "\\n")[:40]
                # log.stream(f"[#{chunk_count:03d}] RAW CHUNK", 
                #           chars=len(content), 
                #           preview=f'"{preview}"',
                #           state="THINK" if in_think_block else "NORMAL")
                
                pending_buffer += content
                
                while pending_buffer:
                    if not in_think_block:
                        # Look for opening tag
                        match = open_pattern.search(pending_buffer)
                        
                        if match:
                            # Found opening tag
                            tag_name = match.group(1).lower()
                            current_close_tag = f"</{tag_name}>"
                            
                            log.think_block_start(f"<{tag_name}>")
                            
                            # Yield content before the tag
                            before_tag = pending_buffer[:match.start()]
                            if before_tag:
                                total_chars_yielded += len(before_tag)
                                # Silenced: Yield log
                                yield before_tag
                            
                            # Enter think mode
                            in_think_block = True
                            think_content = ""
                            pending_buffer = pending_buffer[match.end():]
                            log.think(f"  State: NORMAL → THINK", buffer_remaining=len(pending_buffer))
                            
                            # Emit thinking_start event
                            import time
                            think_start_time = time.time()
                            yield {"_meta": "thinking_start"}
                        else:
                            # Check for potential partial tag at end
                            if pending_buffer.endswith('<'):
                                # Keep '<' for next iteration
                                to_yield = pending_buffer[:-1]
                                if to_yield:
                                    total_chars_yielded += len(to_yield)
                                    # Silenced: Yield log
                                    yield to_yield
                                pending_buffer = '<'
                                break
                            elif '<' in pending_buffer[-15:]:
                                # Potential partial tag, check if it could be start of known tag
                                last_lt = pending_buffer.rfind('<')
                                potential = pending_buffer[last_lt:]
                                
                                is_partial_think_tag = any(
                                    tag[0].lower().startswith(potential.lower()) 
                                    for tag in self.THINK_TAG_PATTERNS
                                )
                                
                                if is_partial_think_tag:
                                    # Keep partial for next chunk
                                    to_yield = pending_buffer[:last_lt]
                                    if to_yield:
                                        total_chars_yielded += len(to_yield)
                                        # Silenced: Yield log
                                        yield to_yield
                                    pending_buffer = potential
                                    break
                                else:
                                    # Not a think tag, yield all
                                    total_chars_yielded += len(pending_buffer)
                                    log.stream(f"  → YIELD (not a think tag)", chars=len(pending_buffer))
                                    yield pending_buffer
                                    pending_buffer = ""
                            else:
                                # No potential tags, yield all
                                total_chars_yielded += len(pending_buffer)
                                # Silenced: Yield log
                                yield pending_buffer
                                pending_buffer = ""
                    else:
                        # Inside think block, look for closing tag
                        close_pos = pending_buffer.lower().find(current_close_tag.lower())
                        
                        if close_pos != -1:
                            # Found closing tag
                            think_content += pending_buffer[:close_pos]
                            total_chars_filtered += len(think_content)
                            
                            log.think_block_end(len(think_content))
                            log.think(f"  🧠 FILTERED CONTENT", chars=len(think_content))
                            
                            # Exit think mode
                            in_think_block = False
                            pending_buffer = pending_buffer[close_pos + len(current_close_tag):]
                            log.think(f"  State: THINK → NORMAL", buffer_remaining=len(pending_buffer))
                            
                            # Emit thinking_end event with duration and content
                            import time
                            duration_ms = int((time.time() - think_start_time) * 1000)
                            yield {
                                "_meta": "thinking_end",
                                "duration_ms": duration_ms,
                                "chars_filtered": len(think_content),
                                "think_content": think_content[:2000]  # Limit to 2000 chars for UI
                            }
                            
                            think_content = ""
                            current_close_tag = ""
                        else:
                            # Still in think block, accumulate
                            think_content += pending_buffer
                            # Silenced: Think accumulation log
                            pending_buffer = ""
                            break
            
            # Log final stats
            log.lm_stream_end(chunk_count)
            log.lm(f"📊 STREAM STATS",
                   received=total_chars_received,
                   yielded=total_chars_yielded,
                   filtered=total_chars_filtered)

            # P0 FIX: Retry logic for empty responses
            # This is common with short questions like "Как меня зовут?"
            if total_chars_yielded == 0 and _retry_count < MAX_RETRIES:
                log.warn(f"⚠️ Empty response detected, retrying ({_retry_count + 1}/{MAX_RETRIES})...")
                # Add a small delay before retry
                await asyncio.sleep(0.5)
                # Retry with slightly higher temperature to encourage response
                retry_params = params.copy()
                retry_params["temperature"] = min(params.get("temperature", 0.7) + 0.2, 1.0)
                async for chunk in self._stream_response(retry_params, _retry_count + 1):
                    yield chunk
                return

            # If still empty after all retries, yield a fallback message
            if total_chars_yielded == 0:
                log.error(f"❌ Model returned NO content after {_retry_count + 1} attempts")
                fallback_msg = "К сожалению, модель не смогла сгенерировать ответ. Попробуйте переформулировать вопрос или добавить больше контекста."
                yield fallback_msg

        except Exception as e:
            log.error(f"Stream exception: {type(e).__name__}: {e}")
            import traceback
            log.error(f"Traceback:\n{traceback.format_exc()}")
            yield f"\n[Error: {str(e)}]"
    
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_executor: Any,
        max_iterations: int = 10
    ) -> str:
        """
        Chat with automatic tool execution loop.
        
        Args:
            messages: Conversation messages
            tools: Available tools
            tool_executor: Object with execute(tool_name, args) method
            max_iterations: Max tool call iterations
            
        Returns:
            Final response after all tool calls
        """
        current_messages = messages.copy()
        
        for _ in range(max_iterations):
            response = await self.client.chat.completions.create(
                model=config.lm_studio.default_model,
                messages=current_messages,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # No tool calls, return final response
            if not message.tool_calls:
                return message.content or ""
            
            # Add assistant message with tool calls
            current_messages.append({
                "role": "assistant",
                "content": message.content,
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
            
            # Execute each tool call
            for tool_call in message.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments)
                    result = await tool_executor.execute(
                        tool_call.function.name,
                        args
                    )
                except Exception as e:
                    result = f"Error: {str(e)}"
                
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        
        return "Maximum iterations reached."
    
    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for text."""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-model",  # LM Studio embedding model
                input=text
            )
            return response.data[0].embedding
        except Exception:
            # Silent fail - embeddings are optional, system uses keyword fallback
            return []


# Global client instance
lm_client = LMStudioClient()
