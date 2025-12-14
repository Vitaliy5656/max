from ..types import CognitiveState, CognitiveConfig
from ..prompts import EXECUTOR_SYSTEM_PROMPT, format_past_failures
from ...lm import lm_client, ThinkingMode
from ...logger import log

async def execute_with_cot(state: CognitiveState, config: CognitiveConfig = None) -> dict:
    """
    Executor Node: Generates a solution using Chain of Thought.
    Injects past failures to avoid repetition.
    P1 FIX: Now also injects user_context for personalized responses.
    """
    # Empty state handling: use sensible defaults
    plan = state.get("plan") or "No plan provided - answer the user's question directly"
    failures_text = format_past_failures(state.get("past_failures", []))
    user_context = state.get("user_context") or ""
    user_input = state.get("input") or "No input provided"
    current_attempt = state.get("iterations", 0) + 1
    total_attempts = state.get("total_iterations", 0) + 1

    # Construct prompt with injected memory
    system_prompt = EXECUTOR_SYSTEM_PROMPT.format(
        plan=plan,
        past_failures=failures_text
    )

    # P1 FIX: Inject user context if available
    if user_context:
        system_prompt += f"\n\nUSER CONTEXT/PREFERENCES:\n{user_context}"

    prompt = f"Original Request: {user_input}"

    log.cognitive(f"EXECUTING: Attempt {current_attempt} (total: {total_attempts})", plan_len=len(plan))

    # Call core LM in Deep Thinking mode
    response = await lm_client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        thinking_mode=ThinkingMode.DEEP,
        stream=False,
        max_tokens=2000
    )

    # Handle empty or error responses
    draft = response if isinstance(response, str) and response.strip() else ""
    if not draft:
        draft = "Не удалось сгенерировать ответ. Попробуйте переформулировать вопрос."
        log.warn("EXECUTING: Empty response from LLM, using fallback")

    log.cognitive(f"EXECUTING: Draft generated", length=len(draft))

    return {
        "draft_answer": draft,
        "status": "verifying",
        "step_name": "Executor",
        "step_content": f"Attempt {current_attempt}: Generated {len(draft)} chars"
    }
