from ..types import CognitiveState, CognitiveConfig
from ..prompts import VERIFIER_SYSTEM_PROMPT
from ...lm import lm_client, ThinkingMode
from ...logger import log
import re

async def verify_answer(state: CognitiveState, config: CognitiveConfig = None) -> dict:
    """
    Verifier Node: Scores the answer.
    Must return valid JSON.
    P1 FIX: Now also considers user_context for personalized verification.
    """
    draft = state.get("draft_answer") or ""
    plan = state.get("plan") or "No plan"
    user_context = state.get("user_context") or ""
    original_request = state.get("input") or "No request"

    # Handle empty draft - automatic low score
    if not draft.strip():
        log.warn("VERIFYING: Empty draft answer, assigning low score")
        return {
            "score": 0.1,
            "critique": "Draft answer is empty. Cannot verify.",
            "status": "deciding",
            "step_name": "Verifier",
            "step_content": "Score: 0.10 (Критическая ошибка)\nCritique: Empty draft"
        }

    # P1 FIX: Include original request and user context in verification
    prompt_parts = [
        f"Original User Request: {original_request}",
        f"Plan: {plan}",
        f"Draft Answer: {draft}",
    ]

    # P1 FIX: Add user preferences to verification criteria
    if user_context:
        prompt_parts.append(f"User Preferences: {user_context}")
        prompt_parts.append("(Consider if the answer matches user's preferences and style)")

    prompt_parts.append("\nCritique and Score.")
    prompt = "\n\n".join(prompt_parts)

    log.cognitive(f"VERIFYING: Assessing draft", draft_len=len(draft))

    # Call core LM
    response = await lm_client.chat(
        messages=[
            {"role": "system", "content": VERIFIER_SYSTEM_PROMPT + "\nIMPORTANT: Return ONLY valid JSON with keys 'score' (float 0.0-1.0) and 'critique' (string)."},
            {"role": "user", "content": prompt}
        ],
        thinking_mode=ThinkingMode.STANDARD,
        stream=False,
        max_tokens=1000
        # response_format={"type": "json_object"} # Removed: LM Studio error 400
    )

    response_text = response if isinstance(response, str) else ""

    try:
        import json
        # Clean potential markdown fences
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)

        score = float(data.get("score", 0.5))
        critique = data.get("critique", "No critique provided.")

    except (json.JSONDecodeError, ValueError) as e:
        log.warn(f"Verifier output JSON parse failed: {e}")
        # Fallback to regex - try multiple patterns
        score_match = re.search(r"[Ss]core[:\s]*([0-9.]+)", response_text)
        if not score_match:
            # Try finding any decimal between 0 and 1
            score_match = re.search(r"\b(0\.\d+|1\.0?)\b", response_text)

        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                score = 0.75  # Optimistic fallback - assume answer is decent
        else:
            # If no score found at all, be optimistic rather than pessimistic
            # This prevents endless refine loops when LLM doesn't return JSON
            score = 0.75  # P2 FIX: Optimistic fallback instead of 0.5
            log.warn("No score found in response, using optimistic fallback 0.75")

        critique = response_text or "Could not parse critique from LLM response"

    # Clamp score to valid range
    score = max(0.0, min(1.0, score))

    # Interpret score for human readability
    def interpret_score(s: float) -> str:
        if s >= 0.9:
            return "Отлично"
        elif s >= 0.75:
            return "Хорошо"
        elif s >= 0.6:
            return "Приемлемо"
        elif s >= 0.3:
            return "Требует доработки"
        else:
            return "Критическая ошибка"

    score_label = interpret_score(score)
    log.cognitive(f"VERIFICATION RESULT: Score={score} ({score_label})", critique_len=len(critique))

    # Determine if this will be the final iteration (for status)
    # Note: actual routing happens in graph.py, but we can predict
    from ..types import DEFAULT_COGNITIVE_CONFIG
    will_accept = score >= DEFAULT_COGNITIVE_CONFIG.accept_threshold

    return {
        "score": score,
        "critique": critique,
        "status": "completed" if will_accept else "deciding",
        "step_name": "Verifier",
        "step_content": f"Score: {score:.2f} ({score_label})\nCritique: {critique[:300]}..."
    }
