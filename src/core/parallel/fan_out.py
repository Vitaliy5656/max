"""
Async Fan-Out Pattern for Parallel LLM Execution.

Uses Ollama's continuous batching (OLLAMA_NUM_PARALLEL) to execute
multiple LLM calls concurrently while respecting VRAM limits.
"""
import asyncio
from typing import List, Callable, Any, Optional, AsyncGenerator
from dataclasses import dataclass

from ..logger import log
from .slot_manager import slot_manager, BusyError
from .types import SlotPriority


@dataclass
class FanOutResult:
    """Result of a single task in fan-out execution."""
    index: int
    success: bool
    result: Any = None
    error: Optional[str] = None


async def fan_out_tasks(
    tasks: List[Callable[[], Any]],
    max_parallel: int = 2,
    priority: SlotPriority = SlotPriority.STANDARD,
    timeout: float = 60.0
) -> List[FanOutResult]:
    """
    Execute multiple async tasks in parallel using Ollama slots.
    
    Each task should be an async function that calls LMStudioClient.
    Ollama's continuous batching handles the actual parallelism.
    
    Args:
        tasks: List of async callables to execute
        max_parallel: Max concurrent executions (should match OLLAMA_NUM_PARALLEL)
        priority: Priority level for slot acquisition
        timeout: Timeout per task in seconds
        
    Returns:
        List of FanOutResult with success/failure for each task
        
    Example:
        async def generate_response(prompt: str):
            return await lm_client.chat([{"role": "user", "content": prompt}])
            
        tasks = [
            lambda: generate_response("Question 1"),
            lambda: generate_response("Question 2"),
            lambda: generate_response("Question 3"),
        ]
        results = await fan_out_tasks(tasks, max_parallel=2)
    """
    semaphore = asyncio.Semaphore(max_parallel)
    results: List[FanOutResult] = []
    
    async def bounded_task(index: int, task: Callable) -> FanOutResult:
        """Execute single task with semaphore and timeout."""
        async with semaphore:
            try:
                log.parallel(f"Fan-out task {index + 1}/{len(tasks)} starting")
                
                # Execute with timeout
                result = await asyncio.wait_for(task(), timeout=timeout)
                
                log.parallel(f"Fan-out task {index + 1} completed")
                return FanOutResult(index=index, success=True, result=result)
                
            except asyncio.TimeoutError:
                log.warn(f"Fan-out task {index + 1} timed out after {timeout}s")
                return FanOutResult(index=index, success=False, error="Timeout")
                
            except Exception as e:
                log.error(f"Fan-out task {index + 1} failed: {e}")
                return FanOutResult(index=index, success=False, error=str(e))
    
    # Execute all tasks concurrently
    log.parallel(f"Starting fan-out: {len(tasks)} tasks, max_parallel={max_parallel}")
    
    gathered = await asyncio.gather(
        *[bounded_task(i, task) for i, task in enumerate(tasks)],
        return_exceptions=True
    )
    
    # Process results
    for item in gathered:
        if isinstance(item, FanOutResult):
            results.append(item)
        elif isinstance(item, Exception):
            # Should not happen due to try/except in bounded_task, but safety net
            results.append(FanOutResult(index=len(results), success=False, error=str(item)))
    
    # Sort by original order
    results.sort(key=lambda r: r.index)
    
    success_count = sum(1 for r in results if r.success)
    log.parallel(f"Fan-out complete: {success_count}/{len(tasks)} succeeded")
    
    return results


async def fan_out_with_slots(
    tasks: List[Callable[[], Any]],
    priority: SlotPriority = SlotPriority.STANDARD,
    timeout: float = 60.0
) -> AsyncGenerator[FanOutResult, None]:
    """
    Execute tasks with SlotManager integration.
    Yields results as they complete (streaming pattern).
    
    This version properly integrates with SlotManager for
    queue management and heartbeats.
    """
    async def execute_with_slot(index: int, task: Callable) -> FanOutResult:
        request_id = f"fanout-{index}-{id(task)}"
        
        try:
            # Acquire slot (with heartbeats)
            async for status in slot_manager.acquire_slot(request_id, priority):
                if status == "acquired":
                    break
                # Could yield heartbeat events here if needed
            
            # Execute task
            result = await asyncio.wait_for(task(), timeout=timeout)
            return FanOutResult(index=index, success=True, result=result)
            
        except BusyError as e:
            return FanOutResult(index=index, success=False, error=f"Queue full: {e}")
        except asyncio.TimeoutError:
            return FanOutResult(index=index, success=False, error="Timeout")
        except Exception as e:
            return FanOutResult(index=index, success=False, error=str(e))
        finally:
            slot_manager.release_slot(request_id)
    
    # Create all task coroutines
    coros = [execute_with_slot(i, task) for i, task in enumerate(tasks)]
    
    # Yield results as they complete
    for coro in asyncio.as_completed(coros):
        result = await coro
        yield result
