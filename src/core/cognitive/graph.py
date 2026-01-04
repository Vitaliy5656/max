# Strict Dependency Check (Audit Requirement: Fail hard if missing)
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    raise ImportError("❌ CRITICAL: 'langgraph' library not found. Please install it: pip install langgraph")


from .types import CognitiveState, CognitiveConfig, DEFAULT_COGNITIVE_CONFIG
from .nodes import planner, executor, verifier, memory

# Module-level config (can be overridden)
_config = DEFAULT_COGNITIVE_CONFIG


def set_cognitive_config(config: CognitiveConfig):
    """Set the cognitive loop configuration."""
    global _config
    _config = config


def interpret_score(score: float) -> str:
    """Convert numeric score to human-readable interpretation."""
    if score >= 0.9:
        return "Отлично"
    elif score >= 0.75:
        return "Хорошо"
    elif score >= 0.6:
        return "Приемлемо"
    elif score >= 0.3:
        return "Требует доработки"
    else:
        return "Критическая ошибка"


def route_verification(state: CognitiveState) -> str:
    """
    Decides the next step after verification.
    Uses total_iterations as hard limit to prevent infinite loops.
    Now uses CognitiveConfig for all thresholds (P1 FIX).
    """
    score = state.get("score", 0.0)
    iterations = state.get("iterations", 0)
    total_iterations = state.get("total_iterations", 0)

    # P0 FIX: Hard limit on TOTAL iterations (never resets, prevents infinite loop)
    if total_iterations >= _config.max_total_iterations:
        # Accept best effort after max total attempts
        return "accept" if score >= 0.5 else "abort"

    # 1. Success - using config threshold
    if score >= _config.accept_threshold:
        return "accept"

    # 2. Hard Failure (Max Iterations per plan reached)
    if iterations >= _config.max_iterations_per_plan:
        # If we have a decent score, accept it rather than abort
        if score >= _config.abort_threshold:
            return "accept"
        return "abort"

    # 3. Critical Failure -> Re-Plan
    # P0 FIX: Also check total_iterations to prevent replan loop
    if score < _config.replan_threshold and iterations < 3 and total_iterations < 6:
        return "replan"

    # 4. Retry (Refinement) -> Executor
    return "refine"

def build_cognitive_graph() -> StateGraph:
    """
    Builds the Cognitive Loop Graph:
    Planner -> Executor -> Verifier -> {Accept/Refine/Abort}
    """
    builder = StateGraph(CognitiveState)
    
    # Add Nodes
    builder.add_node("planner", planner.plan_task)
    builder.add_node("executor", executor.execute_with_cot)
    builder.add_node("verifier", verifier.verify_answer)
    builder.add_node("memory", memory.summarize_failure)
    
    # Define Edges
    builder.set_entry_point("planner")
    
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "verifier")
    
    # Conditional Logic
    builder.add_conditional_edges(
        "verifier",
        route_verification,
        {
            "accept": END,
            "abort": END,
            "refine": "memory",
            "replan": "planner" # 3. Critical Failure -> Re-Plan
        }
    )
    
    builder.add_edge("memory", "executor")
    
    return builder.compile()
