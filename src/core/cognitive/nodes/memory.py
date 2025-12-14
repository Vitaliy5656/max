from ..types import CognitiveState, CognitiveConfig
from ..prompts import MEMORY_SYSTEM_PROMPT
from ...logger import log

async def summarize_failure(state: CognitiveState, config: CognitiveConfig = None) -> dict:
    """
    Memory Node: Summarizes verification failure.
    Increments both iterations and total_iterations counters.
    Creates a concise, actionable summary of what went wrong.
    """
    critique = state.get("critique", "Unknown error")
    score = state.get("score", 0.0)
    old_failures = state.get("past_failures", [])
    current_iterations = state.get("iterations", 0)
    current_total = state.get("total_iterations", 0)

    # Extract key points from critique (first 300 chars, same as verifier)
    # Focus on actionable information
    critique_clean = critique.strip()

    # Create structured summary with attempt number, score, and key issue
    summary = f"[Attempt {current_iterations + 1}, Score {score:.2f}]: {critique_clean[:300]}"

    log.cognitive(f"MEMORY: Recording failure", summary=summary[:80])

    # Append to failure history (Rolling window of 3 most recent)
    new_failures = old_failures + [summary]
    if len(new_failures) > 3:
        new_failures = new_failures[-3:]

    return {
        "past_failures": new_failures,
        "iterations": current_iterations + 1,
        "total_iterations": current_total + 1,  # P0 FIX: Global counter never resets
        "status": "executing",  # Loop back to executor
        "step_name": "Memory",
        "step_content": f"Recorded failure #{current_iterations + 1}: {summary[:150]}..."
    }
