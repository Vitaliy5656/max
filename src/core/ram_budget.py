"""
RAM Budget Coordinator for MAX
Centralized RAM allocation for all caches with priority-based distribution.
"""
import psutil
import logging
from typing import Dict, Optional

log = logging.getLogger(__name__)


class RAMBudget:
    """
    Global RAM budget coordinator for all caches.
    
    Features:
    - Priority-based allocation
    - Graceful degradation (low-priority caches disabled first)
    - Real-time RAM stats
    - Prevents RAM exhaustion
    """
    
    def __init__(self, max_cache_ram_mb: int = 500):
        self.max_ram = max_cache_ram_mb * 1024 * 1024  # Convert to bytes
        self.allocations: Dict[str, int] = {}
        self.priorities: Dict[str, int] = {}
        self.enabled: Dict[str, bool] = {}
        self._initialized = False
    
    def register_cache(
        self,
        cache_id: str,
        estimated_size_mb: int,
        priority: int
    ):
        """
        Register a cache with budget coordinator.
        
        Args:
            cache_id: Unique cache identifier (e.g., "db_pool", "embedding_cache")
            estimated_size_mb: Estimated RAM usage in MB
            priority: Priority 1-10 (10 = highest priority, critical)
        """
        self.allocations[cache_id] = estimated_size_mb * 1024 * 1024
        self.priorities[cache_id] = priority
        self.enabled[cache_id] = False
        
        log.debug(
            f"Registered cache '{cache_id}': "
            f"{estimated_size_mb}MB, priority={priority}"
        )
    
    def allocate(self) -> Dict[str, bool]:
        """
        Allocate RAM to caches based on priority and available RAM.
        
        Returns:
            Dict of cache_id -> enabled status
        """
        # Get available RAM
        available_ram = psutil.virtual_memory().available
        
        # Budget = min(max configured, 50% of available RAM)
        budget = min(self.max_ram, available_ram * 0.5)
        
        log.info(
            f"RAM Budget allocation: {budget / 1024 / 1024:.0f}MB available "
            f"(sys: {available_ram / 1024 / 1024:.0f}MB free)"
        )
        
        # Sort caches by priority (highest first)
        sorted_caches = sorted(
            self.allocations.keys(),
            key=lambda x: self.priorities[x],
            reverse=True
        )
        
        # Allocate to caches in priority order
        allocated = 0
        for cache_id in sorted_caches:
            size = self.allocations[cache_id]
            
            if allocated + size <= budget:
                self.enabled[cache_id] = True
                allocated += size
                log.info(
                    f"  ✅ {cache_id}: "
                    f"{size / 1024 / 1024:.0f}MB (priority {self.priorities[cache_id]})"
                )
            else:
                self.enabled[cache_id] = False
                log.warning(
                    f"  ❌ {cache_id}: "
                    f"{size / 1024 / 1024:.0f}MB DISABLED (budget exceeded)"
                )
        
        self._initialized = True
        
        log.info(
            f"Total allocated: {allocated / 1024 / 1024:.0f}MB / "
            f"{budget / 1024 / 1024:.0f}MB budget"
        )
        
        return self.enabled.copy()
    
    def is_enabled(self, cache_id: str) -> bool:
        """Check if cache is enabled."""
        if not self._initialized:
            log.warning("RAM budget not allocated yet, assuming cache enabled")
            return True
        
        return self.enabled.get(cache_id, False)
    
    def get_stats(self) -> dict:
        """Get allocation statistics."""
        total_allocated = sum(
            size for cid, size in self.allocations.items()
            if self.enabled.get(cid, False)
        )
        
        available_ram = psutil.virtual_memory().available
        
        return {
            "total_budget_mb": self.max_ram / 1024 / 1024,
            "allocated_mb": total_allocated / 1024 / 1024,
            "available_system_mb": available_ram / 1024 / 1024,
            "caches": {
                cid: {
                    "enabled": self.enabled.get(cid, False),
                    "size_mb": self.allocations[cid] / 1024 / 1024,
                    "priority": self.priorities[cid]
                }
                for cid in self.allocations
            }
        }


# Global instance
ram_budget = RAMBudget(max_cache_ram_mb=500)
