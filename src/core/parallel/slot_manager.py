import asyncio
import time
import heapq
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from ..logger import log
from .types import SlotPriority, SlotConfig

@dataclass(order=True)
class QueueItem:
    priority: int
    entry_time: float
    event: asyncio.Event = field(compare=False)
    request_id: str = field(compare=False)

class BusyError(Exception):
    """Raised when queue is full."""
    pass

class SlotManager:
    """
    Manages access to limited LLM slots (VRAM focus).
    Uses a semaphore and a priority queue.
    """
    
    def __init__(self, config: SlotConfig = SlotConfig()):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_slots)
        self._queue: list[QueueItem] = []
        self._active_requests: set[str] = set()
        log.parallel(f"SlotManager initialized with {self.config.max_slots} slots (OLLAMA_NUM_PARALLEL)")
        
    async def acquire_slot(self, request_id: str, priority: SlotPriority) -> AsyncGenerator[str, None]:
        """
        Acquire a slot, yielding 'queue heartbeats' while waiting.
        """
        # 1. Fail Fast: Check Queue Size
        if len(self._queue) >= self.config.max_queue_size:
            raise BusyError(f"Queue full ({len(self._queue)}/{self.config.max_queue_size})")

        # 2. Check if slot available immediately
        if not self._semaphore.locked():
            await self._semaphore.acquire()
            self._active_requests.add(request_id)
            log.info(f"Slot acquired immediately: {request_id}")
            yield "acquired"
            return

        # 3. Add to Priority Queue
        entry = QueueItem(
            priority=-priority.value,  # Negative for max-heap behavior
            entry_time=time.time(),
            event=asyncio.Event(),
            request_id=request_id
        )
        heapq.heappush(self._queue, entry)
        log.info(f"Queued: {request_id} (Pos: {len(self._queue)})")
        
        # 4. Wait loop with Heartbeats
        start_wait = time.time()
        
        try:
            while not entry.event.is_set():
                # Check timeout
                if time.time() - start_wait > self.config.queue_timeout:
                    # Remove from queue if possible
                    if entry in self._queue:
                        self._queue.remove(entry)
                        heapq.heapify(self._queue) # Re-heapify is O(N) but queue is small
                    raise TimeoutError("Queue timeout")
                
                # Try to acquire semaphore if we are top priority
                # Note: asyncio.Semaphore doesn't support "check queue", so we manage it manually
                # Logic: If semaphore has capacity, pop best item.
                
                # Simplified Logic for Phase 1:
                # We wait for the semaphore release to trigger the event.
                # Actually, `release_slot` should trigger the event.
                
                # Heartbeat
                yield "waiting"
                try:
                    await asyncio.wait_for(entry.event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue # Loop and yield heartbeat
            
            # 5. Acquired via Event
            self._active_requests.add(request_id)
            log.info(f"Slot acquired from queue: {request_id}")
            yield "acquired"
            
        except Exception as e:
            # Cleanup if cancelled/failed
            if entry in self._queue:
                self._queue.remove(entry)
                heapq.heapify(self._queue)
            raise e

    def release_slot(self, request_id: str):
        """Release the slot and notify next in queue."""
        if request_id in self._active_requests:
            self._active_requests.remove(request_id)
            
            # If queue has items, wake up the highest priority one
            if self._queue:
                next_item = heapq.heappop(self._queue)
                # Instead of releasing semaphore, we pass the token to the next item
                # Effectively, semaphore count stays same (0 if full), but ownership transfers.
                # BUT: `acquire` above waits on `event`.
                # If we just set event, that coroutine will proceed.
                # It does NOT need to call `semaphore.acquire()` again because we transferred ownership.
                next_item.event.set()
            else:
                # No one waiting, actually release semaphore
                try:
                    self._semaphore.release()
                except ValueError:
                    pass # Already released
            
            log.info(f"Slot released: {request_id}")

    @property
    def active_count(self) -> int:
        return len(self._active_requests)

    @property
    def queue_length(self) -> int:
        return len(self._queue)

# Global Instance
slot_manager = SlotManager()
