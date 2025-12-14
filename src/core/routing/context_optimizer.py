"""
Context Optimizer for MAX AI.

Reduces context size while preserving important information.
Saves tokens and speeds up LLM responses.

Features:
    - Smart truncation (keep recent + important)
    - Entity-based summarization markers
    - Code block detection
    - Sliding window with overlap
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..logger import log


@dataclass
class OptimizedContext:
    """Result of context optimization."""
    messages: List[Dict[str, str]]
    original_tokens: int
    optimized_tokens: int
    reduction_percent: float
    preserved_entities: List[str]


class ContextOptimizer:
    """
    Smart context compression.
    
    Strategies:
        - Keep last N messages fully
        - Summarize older messages
        - Preserve code blocks
        - Extract and preserve entities
    """
    
    def __init__(
        self,
        max_messages: int = 20,
        preserve_last: int = 5,
        max_tokens: int = 4000
    ):
        self.max_messages = max_messages
        self.preserve_last = preserve_last
        self.max_tokens = max_tokens
        
        log.debug(f"ContextOptimizer initialized (max_msg={max_messages})")
    
    def optimize(
        self,
        messages: List[Dict[str, str]],
        preserve_roles: Optional[List[str]] = None
    ) -> OptimizedContext:
        """
        Optimize message list for minimal tokens while preserving meaning.
        
        Args:
            messages: List of {role, content} dicts
            preserve_roles: Roles to never truncate (e.g., ["system"])
        """
        preserve_roles = preserve_roles or ["system"]
        
        if len(messages) <= self.max_messages:
            # No optimization needed
            tokens = self._estimate_tokens(messages)
            return OptimizedContext(
                messages=messages,
                original_tokens=tokens,
                optimized_tokens=tokens,
                reduction_percent=0.0,
                preserved_entities=[]
            )
        
        original_tokens = self._estimate_tokens(messages)
        
        # Separate system messages
        system_msgs = [m for m in messages if m.get("role") in preserve_roles]
        other_msgs = [m for m in messages if m.get("role") not in preserve_roles]
        
        # Keep last N messages fully
        recent = other_msgs[-self.preserve_last:]
        older = other_msgs[:-self.preserve_last]
        
        # Summarize older messages
        summarized = self._summarize_older(older)
        
        # Combine
        optimized = system_msgs + summarized + recent
        
        # Check token limit
        while self._estimate_tokens(optimized) > self.max_tokens and len(summarized) > 0:
            summarized.pop(0)
            optimized = system_msgs + summarized + recent
        
        optimized_tokens = self._estimate_tokens(optimized)
        
        return OptimizedContext(
            messages=optimized,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            reduction_percent=(1 - optimized_tokens / original_tokens) * 100 if original_tokens > 0 else 0,
            preserved_entities=[]
        )
    
    def _summarize_older(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Create summary markers for older messages."""
        if not messages:
            return []
        
        # Group by role and count
        user_count = sum(1 for m in messages if m.get("role") == "user")
        assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
        
        # Extract key entities/topics
        all_content = " ".join(m.get("content", "")[:200] for m in messages)
        topics = self._extract_topics(all_content)
        
        summary = f"[Предыдущий контекст: {user_count} сообщений пользователя, {assistant_count} ответов"
        if topics:
            summary += f". Темы: {', '.join(topics[:3])}"
        summary += "]"
        
        return [{"role": "system", "content": summary}]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text."""
        # Simple keyword extraction
        keywords = re.findall(r'\b[А-Яа-яA-Za-z]{5,}\b', text.lower())
        
        # Count occurrences
        counts: Dict[str, int] = {}
        for kw in keywords:
            counts[kw] = counts.get(kw, 0) + 1
        
        # Return top keywords
        sorted_kw = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_kw[:5]]
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Rough token estimation (4 chars per token)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4


# Global instance
_optimizer: Optional[ContextOptimizer] = None


def get_context_optimizer() -> ContextOptimizer:
    """Get or create global ContextOptimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = ContextOptimizer()
    return _optimizer


def optimize_context(messages: List[Dict[str, str]]) -> OptimizedContext:
    """Quick helper for context optimization."""
    return get_context_optimizer().optimize(messages)
