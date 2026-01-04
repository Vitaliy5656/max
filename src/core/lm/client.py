"""
LM Studio Client — Core API interactions.

Slim client class that uses modular components:
- cli.py for LMS CLI operations
- routing.py for task type detection
- streaming.py for SSE streaming
"""
import asyncio
import json
from typing import AsyncIterator, Optional, Any

from openai import AsyncOpenAI

from ..config import config
from ..logger import log
from .types import TaskType, ThinkingMode, ModelInfo
from . import cli, routing, streaming


class LMStudioClient:
    """
    Client for LM Studio's OpenAI-compatible API.

    Supports:
    - Chat completions with streaming
    - Model switching via CLI
    - Smart routing based on task
    - Auto-unload after TTL
    - Rate limiting
    """

    # Rate limiting configuration
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
        # Rate limiting via semaphore
        self._request_semaphore = asyncio.Semaphore(config.lm_studio.max_concurrent_requests)
        self._last_request_time: float = 0
        
        # Race Condition Lock
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
        real_models = await cli.scan_models_cli()
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
            loaded = await self.get_loaded_model()
            if loaded:
                if self._current_model != loaded:
                    log.lm(f"🧩 State healing: {self._current_model} -> {loaded}")
                    self._current_model = loaded
                return loaded
                
            self._current_model = None
            return None
        except Exception:
            return None

    async def get_loaded_model(self) -> Optional[str]:
        """Get currently loaded model (API check)."""
        try:
            models = await self.list_models()
            return models[0].id if models else None
        except:
            return None
    
    async def load_model(self, model_key: str, ttl: Optional[int] = None) -> bool:
        """Safe thread-locked model loading."""
        async with self._lock:
            loaded = await self.get_loaded_model()
            if loaded == model_key:
                self._current_model = model_key
                return True
                
            log.lm(f"🔄 Loading model: {model_key}...")
            
            success = await cli.load_model_impl(model_key, ttl)
            if success:
                self._current_model = model_key
                await asyncio.sleep(0.5)
                await self.get_loaded_model()
            return success

    async def unload_model(self, model_key: Optional[str] = None) -> bool:
        """Safe thread-locked unload."""
        async with self._lock:
            success = await cli.unload_model_impl(model_key)
            if success:
                if not model_key or model_key == self._current_model:
                    self._current_model = None
            return success
    
    async def ensure_model_loaded(self, required_model: str) -> bool:
        """
        Hot-swap: ensure the required model is loaded (Thread-safe).
        
        Smart matching: if loaded model contains required model name, 
        consider it a match (e.g., 'mistralai/ministral-3b' matches 'ministral-3b').
        """
        # Fast optimistic check outside lock
        if self._current_model == required_model:
            return True
        
        async with self._lock:
            # Re-check after acquiring lock
            current = await self.get_loaded_model()
            
            # Exact match
            if current == required_model:
                self._current_model = required_model
                return True
            
            # Fuzzy match
            if current and required_model:
                req_lower = required_model.lower()
                cur_lower = current.lower()
                if req_lower in cur_lower or cur_lower.endswith(req_lower):
                    log.lm(f"✓ Model already loaded (fuzzy match): {current}")
                    self._current_model = current
                    return True
            
            # If ANY model is loaded and we're not explicitly switching, use it
            if current and (required_model == "auto" or not required_model):
                log.lm(f"✓ Using currently loaded model: {current}")
                self._current_model = current
                return True
            
            log.lm(f"🔄 Hot-swap needed: {current or 'none'} → {required_model}")
            
            # Unload current model if different
            if current:
                await cli.unload_model_impl(current)
            
            # Load required model
            success = await cli.load_model_impl(required_model, ttl=config.lm_studio.auto_unload_ttl)
            if success:
                self._current_model = required_model
            return success

    def get_mode_config(self, thinking_mode: ThinkingMode):
        """Get configuration for a thinking mode."""
        from ..config import ThinkingModeConfig
        mode_config = config.lm_studio.thinking_modes.get(thinking_mode.value)
        if mode_config:
            return mode_config
        return config.lm_studio.thinking_modes["standard"]
    
    async def get_model_for_task(self, task_type: TaskType) -> str:
        """Smart routing: get best model for task type."""
        return await routing.get_model_for_task(task_type, config)
    
    def detect_task_type(self, message: str, has_image: bool = False) -> TaskType:
        """Auto-detect task type from message content."""
        return routing.detect_task_type(message, has_image)
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_type: Optional[TaskType] = None,
        thinking_mode: ThinkingMode = ThinkingMode.STANDARD,
        has_image: bool = False,
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str] | str:
        """
        Send chat completion request with thinking mode support.
        
        Args:
            messages: OpenAI-format messages list
            model: Model to use (overrides thinking_mode if specified)
            stream: Enable streaming response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
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
        
        # Model Selection Logic
        if config.lm_studio.model_selection_mode == "manual":
            if not model:
                loaded = await self.get_loaded_model()
                model = loaded if loaded else config.lm_studio.default_model
                log.lm(f"🎯 MANUAL mode: using {'loaded' if loaded else 'default'} model: {model}")
            else:
                log.lm(f"🎯 MANUAL mode: explicit model selection: {model}")
            
            if temperature is None:
                temperature = mode_config.temperature
            if max_tokens is None:
                max_tokens = mode_config.max_tokens
        else:
            if not model:
                model = mode_config.model
                log.lm(f"🧠 AUTO mode: thinking mode selected model: {model}")
            
            if temperature is None:
                temperature = mode_config.temperature
            if max_tokens is None:
                max_tokens = mode_config.max_tokens
        
        # Inject system prompt suffix for Chain-of-Thought
        if mode_config.system_prompt_suffix:
            messages = self._inject_thinking_prompt(messages, mode_config.system_prompt_suffix)
        
        # Apply thinking time for DEEP mode
        if thinking_mode == ThinkingMode.DEEP and config.lm_studio.min_thinking_time > 0:
            await asyncio.sleep(config.lm_studio.min_thinking_time)
        
        # Debug payload size
        log.lm(f"📦 Payload: {len(messages)} messages, max_tokens={max_tokens}, temp={temperature}")
        # log.debug(f"Payload detail: {json.dumps(messages, ensure_ascii=False)}") # Uncomment for deep debug
        
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

        # Track which model is being used
        self._current_model = model

        if stream:
            return streaming.stream_response(self.client, params)
        else:
            async with self._request_semaphore:
                await self._enforce_rate_limit()
                response = await self.client.chat.completions.create(**params)
                return response.choices[0].message.content or ""

    def _inject_thinking_prompt(self, messages: list[dict], suffix: str) -> list[dict]:
        """Inject thinking mode system prompt suffix."""
        messages = messages.copy()
        
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                messages[i] = {
                    **msg,
                    "content": f"{msg.get('content', '')}\n\n{suffix}"
                }
                return messages
        
        messages.insert(0, {"role": "system", "content": suffix})
        return messages

    async def _enforce_rate_limit(self):
        """Enforce minimum interval between requests."""
        import time
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()
    
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
            
            if not message.tool_calls:
                return message.content or ""
            
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
                model="text-embedding-bge-m3",
                input=text
            )
            return response.data[0].embedding
        except Exception:
            return []
