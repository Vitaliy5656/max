from ..types import CognitiveState, CognitiveConfig
from ..prompts import PLANNER_SYSTEM_PROMPT
from ...lm import lm_client, ThinkingMode
from ...logger import log

async def plan_task(state: CognitiveState, config: CognitiveConfig = None) -> dict:
    """
    Planner Node: Decomposes the input into a structured plan.
    """
    user_input = state["input"]
    
    # Check if plan already exists (re-planning support)
    # If there are past failures and we routed back here, it means we need a NEW plan.
    is_replanning = len(state.get("past_failures", [])) > 0
    
    if state.get("plan") and not is_replanning:
        return {"status": "planning_update"}

    context = ""
    if is_replanning:
        failures = state.get("past_failures", [])
        last_failure = failures[-1] if failures else "Unknown"
        context = f"\n\nPREVIOUS PLAN FAILED. \nLast Critique: {last_failure}\n\nTASK: Generate a BETTER plan that avoids these mistakes."
        log.cognitive(f"RE-PLANNING: Generating new plan due to failure")

    # Inject User Context if available
    user_profile_txt = state.get("user_context", "")
    if user_profile_txt:
        context += f"\n\nUser Context/Preferences:\n{user_profile_txt}"

    prompt = f"User Request: {user_input}{context}"
    
    log.cognitive(f"PLANNING: Decomposing task", input=user_input[:50])
    
    # Call core LM
    response = await lm_client.chat(
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        thinking_mode=ThinkingMode.STANDARD,
        stream=False,
        max_tokens=1000
    )
    
    # Handle empty response
    plan_text = response if isinstance(response, str) and response.strip() else ""
    if not plan_text:
        plan_text = f"1. Analyze the user request: {user_input[:100]}\n2. Generate appropriate response\n3. Verify completeness"
        log.warn("PLANNING: Empty response from LLM, using default plan")

    log.cognitive(f"PLANNING: Plan generated", length=len(plan_text))

    # P0 FIX: total_iterations is NEVER reset (prevents infinite replan loop)
    # iterations resets for new plan, but total_iterations keeps counting
    current_total = state.get("total_iterations", 0)

    # Determine step content based on whether this is initial or re-planning
    if is_replanning:
        step_content = f"Re-planning (attempt {current_total + 1}):\n{plan_text[:500]}..."
    else:
        step_content = f"Initial Plan:\n{plan_text[:500]}..."

    return {
        "plan": plan_text,
        "status": "executing",
        "steps": [],
        "iterations": 0,  # Reset iterations for new plan
        "total_iterations": current_total + 1 if is_replanning else current_total,  # Increment only on replan
        "step_name": "Planner",
        "step_content": step_content
    }
