"""
Rate Limiter for SmartRouter.

Prevents overload and ensures fair resource usage.

Features:
    - Per-user rate limiting
    - Global rate limiting
    - Token bucket algorithm
    - Burst allowance
"""
import time
from typing import Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

from ..logger import log


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_in_seconds: float
    message: str


class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill bucket based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now
    
    @property
    def remaining(self) -> int:
        """Current remaining tokens."""
        self._refill()
        return int(self.tokens)
    
    @property
    def reset_time(self) -> float:
        """Time until bucket is full again."""
        if self.tokens >= self.capacity:
            return 0
        return (self.capacity - self.tokens) / self.refill_rate


class RateLimiter:
    """
    Rate limiter with per-user and global limits.
    """
    
    def __init__(
        self,
        global_rpm: int = 60,
        per_user_rpm: int = 20,
        burst_multiplier: float = 1.5
    ):
        """
        Args:
            global_rpm: Global requests per minute
            per_user_rpm: Per-user requests per minute
            burst_multiplier: Allow burst up to this multiplier
        """
        self.global_rpm = global_rpm
        self.per_user_rpm = per_user_rpm
        self.burst_multiplier = burst_multiplier
        
        # Global bucket
        self._global = TokenBucket(
            capacity=int(global_rpm * burst_multiplier),
            refill_rate=global_rpm / 60
        )
        
        # Per-user buckets
        self._users: Dict[str, TokenBucket] = {}
        
        # Stats
        self._allowed = 0
        self._blocked = 0
        
        log.debug(f"RateLimiter initialized (global={global_rpm}/min, user={per_user_rpm}/min)")
    
    def check(self, user_id: str = "anonymous") -> RateLimitResult:
        """Check if request is allowed."""
        
        # Check global limit first
        if not self._global.consume():
            self._blocked += 1
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_in_seconds=self._global.reset_time,
                message="Global rate limit exceeded"
            )
        
        # Check per-user limit
        if user_id not in self._users:
            self._users[user_id] = TokenBucket(
                capacity=int(self.per_user_rpm * self.burst_multiplier),
                refill_rate=self.per_user_rpm / 60
            )
        
        user_bucket = self._users[user_id]
        if not user_bucket.consume():
            self._blocked += 1
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_in_seconds=user_bucket.reset_time,
                message="User rate limit exceeded"
            )
        
        self._allowed += 1
        return RateLimitResult(
            allowed=True,
            remaining=min(self._global.remaining, user_bucket.remaining),
            reset_in_seconds=0,
            message="OK"
        )
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            "allowed": self._allowed,
            "blocked": self._blocked,
            "global_remaining": self._global.remaining,
            "active_users": len(self._users),
            "block_rate": self._blocked / max(self._allowed + self._blocked, 1) * 100
        }
    
    def clear_user(self, user_id: str) -> None:
        """Reset rate limit for a user."""
        if user_id in self._users:
            del self._users[user_id]


# Global instance
_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def check_rate_limit(user_id: str = "anonymous") -> RateLimitResult:
    """Quick helper for rate limit check."""
    return get_rate_limiter().check(user_id)
