"""
Retry Handler for routing operations.

Provides resilient retry logic with exponential backoff.

Features:
    - Exponential backoff
    - Jitter for thundering herd prevention
    - Circuit breaker pattern
    - Configurable per-operation
"""
import asyncio
import random
from typing import Callable, Optional, Any, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import time

from ..logger import log


T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 0.1  # seconds
    max_delay: float = 5.0      # seconds
    exponential_base: float = 2.0
    jitter: float = 0.1         # Random jitter factor


class CircuitBreaker:
    """Circuit breaker to prevent cascade failures."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._successes = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current state, potentially transitioning."""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout passed
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                log.debug(f"Circuit {self.name}: OPEN -> HALF_OPEN")
        return self._state
    
    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        state = self.state  # This may transition state
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            return True  # Allow test request
        else:  # OPEN
            return False
    
    def record_success(self) -> None:
        """Record a successful operation."""
        self._failures = 0
        self._successes += 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            log.debug(f"Circuit {self.name}: HALF_OPEN -> CLOSED (recovered)")
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self._failures += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            log.debug(f"Circuit {self.name}: HALF_OPEN -> OPEN (still failing)")
        elif self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            log.warn(f"Circuit {self.name}: CLOSED -> OPEN (threshold reached)")
    
    def get_stats(self) -> dict:
        """Get circuit breaker stats."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failures": self._failures,
            "successes": self._successes,
            "threshold": self.failure_threshold
        }


class RetryHandler:
    """
    Retry handler with exponential backoff and circuit breaker.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._circuits: dict[str, CircuitBreaker] = {}
        
        log.debug("RetryHandler initialized")
    
    def get_circuit(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker by name."""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name)
        return self._circuits[name]
    
    async def execute(
        self,
        operation: Callable[[], Any],
        circuit_name: Optional[str] = None,
        config: Optional[RetryConfig] = None
    ) -> Any:
        """
        Execute operation with retries and circuit breaker.
        
        Args:
            operation: Async callable to execute
            circuit_name: Name for circuit breaker (None to disable)
            config: Override default config
        """
        cfg = config or self.config
        circuit = self.get_circuit(circuit_name) if circuit_name else None
        
        # Check circuit breaker
        if circuit and not circuit.allow_request():
            raise Exception(f"Circuit {circuit_name} is OPEN")
        
        last_exception = None
        
        for attempt in range(cfg.max_retries + 1):
            try:
                result = await operation()
                
                if circuit:
                    circuit.record_success()
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if circuit:
                    circuit.record_failure()
                
                if attempt == cfg.max_retries:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(
                    cfg.initial_delay * (cfg.exponential_base ** attempt),
                    cfg.max_delay
                )
                
                # Add jitter
                delay *= (1 + random.uniform(-cfg.jitter, cfg.jitter))
                
                log.debug(f"Retry {attempt + 1}/{cfg.max_retries} after {delay:.2f}s")
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def get_all_circuits(self) -> list:
        """Get stats for all circuits."""
        return [c.get_stats() for c in self._circuits.values()]


# Global instance
_handler: Optional[RetryHandler] = None


def get_retry_handler() -> RetryHandler:
    """Get or create global retry handler."""
    global _handler
    if _handler is None:
        _handler = RetryHandler()
    return _handler


async def with_retry(operation: Callable, circuit_name: str = None) -> Any:
    """Quick helper for retry execution."""
    return await get_retry_handler().execute(operation, circuit_name)
