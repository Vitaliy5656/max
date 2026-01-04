"""
LM Response Streaming — SSE streaming with think-tag filtering.

Handles streaming responses from LM Studio with:
- Multi-pattern think tag detection (DeepSeek, Claude, etc.)
- Buffering for tags split across chunks
- Thinking events emission for UI
"""
import asyncio
import re
import time
from typing import AsyncIterator

from ..logger import log


# Multi-pattern think tag detection for various reasoning models
THINK_TAG_PATTERNS = [
    # (open_tag, close_tag) pairs
    ("<think>", "</think>"),           # DeepSeek R1, Qwen
    ("<thinking>", "</thinking>"),     # Claude-style
    ("<reasoning>", "</reasoning>"),   # Generic reasoning
    ("<reflection>", "</reflection>"), # Reflection models
]


async def stream_response(
    client, 
    params: dict
) -> AsyncIterator[str | dict]:
    """
    Stream response chunks with multi-pattern think tag filtering.
    
    Supports various reasoning models:
    - DeepSeek R1: <think>...</think>
    - Claude-style: <thinking>...</thinking>
    - Generic: <reasoning>...</reasoning>
    
    Uses buffering to handle tags split across chunk boundaries.
    
    Args:
        client: AsyncOpenAI client instance
        params: Parameters for chat.completions.create
        
    Yields:
        Text chunks or metadata dicts (e.g., {"_meta": "thinking_start"})
    """
    # State machine
    in_think_block = False
    current_close_tag = ""
    pending_buffer = ""  # Buffer for potential partial tags
    think_content = ""   # Accumulated thinking content
    think_start_time = 0.0
    
    # Stats for logging
    chunk_count = 0
    total_chars_received = 0
    total_chars_yielded = 0
    total_chars_filtered = 0
    
    # Pre-compile patterns for efficiency
    open_pattern = re.compile(r'<(think|thinking|reasoning|reflection)>', re.IGNORECASE)
    
    model = params.get("model", "unknown")
    log.lm(f"Starting stream for model={model}")
    log.lm_stream_start(model)
    
    # Heartbeat configuration
    last_yield_time = time.time()
    HEARTBEAT_INTERVAL = 0.5  # Emit pulse every 500ms if silence
    
    try:
        log.lm("Creating chat completion...", model=model)
        stream = await client.chat.completions.create(**params)
        log.lm("Stream connection established ✓")
        
        chunk_iterator = stream.__aiter__()
        
        while True:
            try:
                # Wait for next chunk with timeout
                chunk = await asyncio.wait_for(chunk_iterator.__anext__(), timeout=HEARTBEAT_INTERVAL)
                last_yield_time = time.time()
            except asyncio.TimeoutError:
                # No chunk received within interval -> Emit Pulse
                yield {"_meta": "pulse", "model": model}
                continue
            except StopAsyncIteration:
                break
            
            chunk_count += 1

            
            # Check for empty chunk
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            if not delta.content:
                finish_reason = chunk.choices[0].finish_reason
                if finish_reason:
                    pass  # Silenced: Finish signal
                continue
                
            content = delta.content
            total_chars_received += len(content)
            
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
                            yield before_tag
                        
                        # Enter think mode
                        in_think_block = True
                        think_content = ""
                        pending_buffer = pending_buffer[match.end():]
                        log.think(f"  State: NORMAL → THINK", buffer_remaining=len(pending_buffer))
                        
                        # Emit thinking_start event
                        think_start_time = time.time()
                        yield {"_meta": "thinking_start"}
                    else:
                        # Check for potential partial tag at end
                        if pending_buffer.endswith('<'):
                            to_yield = pending_buffer[:-1]
                            if to_yield:
                                total_chars_yielded += len(to_yield)
                                yield to_yield
                            pending_buffer = '<'
                            break
                        elif '<' in pending_buffer[-15:]:
                            last_lt = pending_buffer.rfind('<')
                            potential = pending_buffer[last_lt:]
                            
                            is_partial_think_tag = any(
                                tag[0].lower().startswith(potential.lower()) 
                                for tag in THINK_TAG_PATTERNS
                            )
                            
                            if is_partial_think_tag:
                                to_yield = pending_buffer[:last_lt]
                                if to_yield:
                                    total_chars_yielded += len(to_yield)
                                    yield to_yield
                                pending_buffer = potential
                                break
                            else:
                                total_chars_yielded += len(pending_buffer)
                                yield pending_buffer
                                pending_buffer = ""
                        else:
                            total_chars_yielded += len(pending_buffer)
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
                        duration_ms = int((time.time() - think_start_time) * 1000)
                        yield {
                            "_meta": "thinking_end",
                            "duration_ms": duration_ms,
                            "chars_filtered": len(think_content),
                            "think_content": think_content[:2000]  # Limit for UI
                        }
                        
                        think_content = ""
                        current_close_tag = ""
                    else:
                        # Still in think block, accumulate
                        think_content += pending_buffer
                        pending_buffer = ""
                        break
        
        # Log final stats
        log.lm_stream_end(chunk_count)
        log.lm(f"📊 STREAM STATS", 
               received=total_chars_received,
               yielded=total_chars_yielded,
               filtered=total_chars_filtered)

        # Check for empty stream (P0 Fix)
        if total_chars_yielded == 0 and not in_think_block:
             log.error("❌ Model returned NO content (0 chars yielded)")
             yield "\n[Error: No content received from model]"
                    
    except Exception as e:
        log.error(f"Stream exception: {type(e).__name__}: {e}")
        import traceback
        log.error(f"Traceback:\n{traceback.format_exc()}")
        yield f"\n[Error: {str(e)}]"
