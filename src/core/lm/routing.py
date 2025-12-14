"""
LM Client Routing — Task detection and model selection.

Provides:
- detect_task_type: Auto-detect task type from message
- get_model_for_task: Get best model for task type
"""
from .types import TaskType


def detect_task_type(message: str, has_image: bool = False) -> TaskType:
    """
    Auto-detect task type from message content.
    
    Args:
        message: User message text
        has_image: Whether the message contains an image
        
    Returns:
        Detected TaskType
    """
    if has_image:
        return TaskType.VISION
    
    # Keywords for reasoning tasks
    reasoning_keywords = [
        "почему", "объясни", "проанализируй", "сравни", "подумай",
        "рассуждай", "логика", "вывод", "докажи", "аргумент",
        "why", "explain", "analyze", "compare", "think", "reason"
    ]
    
    # Keywords for quick tasks
    quick_keywords = [
        "да или нет", "кратко", "быстро", "одним словом",
        "yes or no", "briefly", "quick", "short"
    ]
    
    message_lower = message.lower()
    
    if any(kw in message_lower for kw in quick_keywords):
        return TaskType.QUICK
    
    if any(kw in message_lower for kw in reasoning_keywords):
        return TaskType.REASONING
    
    # Additional heuristics beyond keywords
    # 1. Multiple question marks suggest complex inquiry
    question_marks = message.count('?')
    if question_marks >= 2:
        return TaskType.REASONING
    
    # 2. Math symbols often need reasoning
    has_math = any(c in message for c in ['=', '+', '*', '/', '^', '√', '∫', 'π'])
    if has_math and len(message) > 30:
        return TaskType.REASONING
    
    # 3. Question with significant length
    if question_marks >= 1 and len(message) > 100:
        return TaskType.REASONING
    
    # Default based on message length
    if len(message) > 200:
        return TaskType.REASONING
    
    return TaskType.DEFAULT


async def get_model_for_task(task_type: TaskType, config) -> str:
    """
    Smart routing: get best model for task type.
    
    Args:
        task_type: The type of task
        config: Application config object
        
    Returns:
        Model name/key to use
    """
    if task_type == TaskType.VISION:
        return config.lm_studio.vision_model
    elif task_type == TaskType.REASONING:
        return config.lm_studio.reasoning_model
    elif task_type == TaskType.QUICK:
        return config.lm_studio.quick_model
    else:
        return config.lm_studio.default_model
