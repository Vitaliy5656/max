# -*- coding: utf-8 -*-
"""
Soul Limits — Governance constraints for soul.json.

Single-user mode (The Architect) — relaxed but still bounded.
Prevents chaotic growth while allowing rich personality modeling.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SoulLimits:
    """
    Schema governance limits.
    
    Designed for single-user mode (no multi-tenancy concerns).
    More generous than default, but still prevents runaway growth.
    """
    # Depth: 6 levels allows rich nested structures
    # e.g., user_model.creative_spectrum.gaming.tetris.mechanics.rotation
    max_depth: int = 6
    
    # Siblings: 20 items per level (generous for categorization)
    max_siblings: int = 20
    
    # Lists: 50 items max (e.g., insights, learned patterns)
    max_list_items: int = 50
    
    # Total keys: 500 (room for growth, but bounded)
    max_total_keys: int = 500
    
    # File size: 500 KB (large enough for rich data)
    max_file_size_kb: int = 500
    
    # Access tracking: archive after N days of no access
    stale_threshold_days: int = 30
    
    # Gardening: how often to run consolidation (seconds)
    gardening_interval: int = 600  # 10 minutes


# Default instance for single-user mode
SOUL_LIMITS = SoulLimits()


# Forgetting strategy
ForgettingStrategy = Literal["aggressive", "conservative", "llm_guided"]

# User's choice: Conservative — archive but never delete
FORGETTING_STRATEGY: ForgettingStrategy = "conservative"


# Protected paths — NEVER archived, core identity
PROTECTED_PATHS = frozenset([
    "meta",
    "user_model",
    "identity", 
    "axioms",
    "bdi_state",
    "current_focus",
])


def is_protected_path(path: str) -> bool:
    """Check if path is protected from archiving."""
    root = path.split(".")[0]
    return root in PROTECTED_PATHS


def validate_depth(path: str) -> tuple[bool, str]:
    """
    Check if path depth is within limits.
    
    Returns:
        (is_valid, error_message)
    """
    depth = len(path.split("."))
    if depth > SOUL_LIMITS.max_depth:
        return False, f"Depth {depth} exceeds limit {SOUL_LIMITS.max_depth}"
    return True, ""


def validate_siblings(parent_dict: dict) -> tuple[bool, str]:
    """
    Check if sibling count is within limits.
    
    Returns:
        (is_valid, error_message)
    """
    count = len(parent_dict)
    if count > SOUL_LIMITS.max_siblings:
        return False, f"Siblings {count} exceeds limit {SOUL_LIMITS.max_siblings}"
    return True, ""


def validate_list_size(items: list) -> tuple[bool, str]:
    """
    Check if list size is within limits.
    
    Returns:
        (is_valid, error_message)
    """
    count = len(items)
    if count > SOUL_LIMITS.max_list_items:
        return False, f"List size {count} exceeds limit {SOUL_LIMITS.max_list_items}"
    return True, ""


def count_keys(obj, depth: int = 0) -> int:
    """Recursively count all keys in nested structure."""
    if depth > 20:  # Safety limit
        return 0
    
    if isinstance(obj, dict):
        total = len(obj)
        for v in obj.values():
            total += count_keys(v, depth + 1)
        return total
    elif isinstance(obj, list):
        total = 0
        for item in obj:
            total += count_keys(item, depth + 1)
        return total
    return 0


def validate_total_keys(soul_dict: dict) -> tuple[bool, str]:
    """
    Check if total key count is within limits.
    
    Returns:
        (is_valid, error_message)
    """
    total = count_keys(soul_dict)
    if total > SOUL_LIMITS.max_total_keys:
        return False, f"Total keys {total} exceeds limit {SOUL_LIMITS.max_total_keys}"
    return True, ""
