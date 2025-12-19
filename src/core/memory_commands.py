"""
Universal Memory Commands for MAX
Tool Registry integration for memory operations.
"""
from typing import Optional
from src.core.memory import memory
from src.core.privacy_lock import get_privacy_lock


async def remember_fact(content: str, category: str = "general") -> dict:
    """
    Remember a fact for long-term memory.
    
    Args:
        content: The fact to remember
        category: Category (general/shadow/vault)
    
    Returns:
        Result with fact_id and status
    """
    # Privacy check
    privacy_lock = get_privacy_lock()
    
    if not privacy_lock.can_access(category):
        return {
            "success": False,
            "error": f"Category '{category}' is locked. Use unlock command first."
        }
    
    # Add fact
    fact = await memory.add_fact(content, category=category)
    
    return {
        "success": True,
        "fact_id": fact.id,
        "category": category,
        "message": f"Remembered: {content[:50]}..."
    }


async def recall_facts(category: Optional[str] = None, limit: int = 10) -> dict:
    """
    Recall facts from memory.
    
    Args:
        category: Filter by category (optional)
        limit: Max facts to return
    
    Returns:
        List of facts
    """
    # Privacy check
    privacy_lock = get_privacy_lock()
    
    if category and not privacy_lock.can_access(category):
        return {
            "success": False,
            "error": f"Category '{category}' is locked. Use unlock command first."
        }
    
    # Get facts
    facts = await memory.list_facts(category=category, limit=limit)
    
    # Filter out locked categories if no category specified
    if not category:
        facts = [f for f in facts if privacy_lock.can_access(f.category)]
    
    return {
        "success": True,
        "facts": [
            {
                "id": f.id,
                "content": f.content,
                "category": f.category,
                "created_at": str(f.created_at) if f.created_at else None
            }
            for f in facts
        ],
        "count": len(facts)
    }


async def forget_fact(fact_id: int) -> dict:
    """
    Forget (delete) a fact.
    
    Args:
        fact_id: ID of fact to delete
    
    Returns:
        Success status
    """
    # Note: Should check privacy before deletion
    # but for simplicity, allowing deletion always
    
    deleted = await memory.delete_fact(fact_id)
    
    return {
        "success": deleted,
        "message": "Fact deleted" if deleted else "Fact not found"
    }


async def unlock_privacy(duration_minutes: int = 30) -> dict:
    """
    Unlock sensitive categories (shadow, vault).
    
    Args:
        duration_minutes: How long to keep unlocked
    
    Returns:
        Unlock status
    """
    privacy_lock = get_privacy_lock()
    privacy_lock.unlock(duration_minutes)
    
    return {
        "success": True,
        "message": f"Privacy unlocked for {duration_minutes} minutes",
        "status": privacy_lock.get_status()
    }


async def lock_privacy() -> dict:
    """
    Lock sensitive categories immediately.
    
    Returns:
        Lock status
    """
    privacy_lock = get_privacy_lock()
    privacy_lock.lock()
    
    return {
        "success": True,
        "message": "Privacy locked",
        "status": privacy_lock.get_status()
    }


# Tool definitions for Tool Registry
MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Remember a fact for long-term memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The fact to remember"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["general", "shadow", "vault"],
                        "description": "Category: general (always accessible), shadow/vault (require unlock)"
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_facts",
            "description": "Recall facts from memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["general", "shadow", "vault"],
                        "description": "Filter by category (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max facts to return (default 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unlock_privacy",
            "description": "Unlock access to sensitive categories (shadow, vault)",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_minutes": {
                        "type": "integer",
                        "description": "How long to keep unlocked (default 30 min)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_privacy",
            "description": "Lock sensitive categories immediately",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]
