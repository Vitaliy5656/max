"""
Ensemble Cognitive Loop v2 — Main Orchestrator.

Multi-path reasoning with hierarchical synthesis and CPO.
Uses 2+2 parallelism to avoid overloading LM Studio.
"""
import asyncio
import re
import time
from typing import AsyncGenerator, Optional

from ..lm_client import lm_client
from ..config import config
from ..parallel.fan_out import fan_out_tasks
from ..logger import log

from .ensemble_types import (
    EnsembleConfig,
    EnsembleState,
    EnsembleResult,
    GenerationResult,
    SynthesisResult,
    VerificationResult,
    AxisResults,
    ThinkingStep,
)
from .ensemble_prompts import (
    PERSONA_PROMPTS,
    SYNTHESIS_PROMPT,
    DEBATE_PROMPT_CRITIQUE,
    DEBATE_PROMPT_RESPOND,
    MEGA_SYNTHESIS_PROMPT,
    VERIFIER_PROMPT,
    MUTATION_PROMPT,
    STEP_NAMES,
)
from .cpo_engine import cpo_engine


# Default configuration
_config = EnsembleConfig()


async def record_thinking_trace(result: EnsembleResult, log_entries: list[dict]):
    """
    Record execution trace for debugging and analysis.
    
    Args:
        result: Final result of ensemble process
        log_entries: List of thinking steps/events
    """
    import json
    from pathlib import Path
    from datetime import datetime
    
    try:
        # Create traces directory
        trace_dir = Path("logs/traces")
        trace_dir.mkdir(parents=True, exist_ok=True)
        
        # Format trace entry
        trace = {
            "timestamp": datetime.now().isoformat(),
            "question": result.answer[:50] + "..." if result.answer else "unknown", # approximate
            "duration_ms": result.elapsed_ms,
            "score": result.final_score,
            "steps": log_entries,
            "winner_axis": "unknown" # Could parse from meta
        }
        
        # Save to daily log file
        filename = f"trace_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        filepath = trace_dir / filename
        
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")
            
    except Exception as e:
        log.error(f"Failed to record trace: {e}")



async def ensemble_thinking(
    question: str,
    context: str = "",
    config: Optional[EnsembleConfig] = None,
    cancel_event: Optional[asyncio.Event] = None,
    question_type: str = "general",
) -> AsyncGenerator[dict, None]:
    """
    Ensemble Cognitive Loop v2 — main entry point.
    
    Yields streaming events and finally the EnsembleResult.
    
    Args:
        question: User question
        context: Additional context
        config: Optional custom configuration
        cancel_event: Optional event to cancel mid-processing
        question_type: Category of question for CPO (e.g. "coding", "math")
    
    Yields:
        dict: Streaming events {"thinking": "step", ...} or {"result": EnsembleResult}
    """
    cfg = config or _config
    start_time = time.time()
    total_llm_calls = 0
    thinking_log = []
    
    def check_cancelled():
        if cancel_event and cancel_event.is_set():
            raise asyncio.CancelledError("User cancelled")
    
    def log_step(name: str, stage: int = 0, total: int = 0) -> dict:
        step = ThinkingStep(
            name=name,
            stage=stage,
            total=total,
            text=STEP_NAMES.get(name, name),
            elapsed_ms=(time.time() - start_time) * 1000
        )
        thinking_log.append(step.__dict__)
        return {"thinking": "step", **step.__dict__}
    
    try:
        # CPO Optimization Check
        if cfg.cpo_enabled:
            pref_axis, confidence = await cpo_engine.get_preference(question_type, cfg.cpo_min_observations)
            if confidence >= cfg.cpo_confidence_threshold:
                log.info(f"🧠 CPO Optimization: {question_type} -> prefers {pref_axis} ({confidence:.2f})")
                # Future: Implement axis skipping here
        
        # =================================================================
        # ROUND 1: Generate temperature variants (parallel)
        # =================================================================
        yield log_step("generating_temp", stage=1, total=4)
        check_cancelled()
        
        temp_results = await _generate_temperature_variants(
            question, context, cfg
        )
        total_llm_calls += 2
        
        # Check if we have enough responses
        valid_temp = [r for r in temp_results if r.success and len(r.content) >= cfg.min_response_length]
        
        if len(valid_temp) < 1:
            # Round 1 failed completely
            log.warn("Round 1 (temp) failed, will try Round 2 only")
        
        # =================================================================
        # ROUND 2: Generate persona variants (parallel)
        # =================================================================
        yield log_step("generating_prompt", stage=2, total=4)
        check_cancelled()
        
        prompt_results = await _generate_persona_variants(
            question, context, cfg
        )
        total_llm_calls += 2
        
        valid_prompt = [r for r in prompt_results if r.success and len(r.content) >= cfg.min_response_length]
        
        # Check combined validity
        all_valid = valid_temp + valid_prompt
        if len(all_valid) < 2:
            # Fallback to direct response
            log.warn(f"Only {len(all_valid)} valid responses, fallback to direct")
            yield log_step("fallback")
            
            direct = await _direct_response(question, context)
            total_llm_calls += 1
            
            result = EnsembleResult(
                answer=direct,
                final_score=5.0,
                state=EnsembleState.FALLBACK,
                elapsed_ms=(time.time() - start_time) * 1000,
                total_llm_calls=total_llm_calls,
                thinking_log=thinking_log,
            )
            yield {"result": result}
            return
        
        # =================================================================
        # SYNTHESIS: By axis
        # =================================================================
        yield log_step("synthesizing_temp", stage=3, total=4)
        check_cancelled()
        
        # Synthesize temperature axis (if we have results)
        if len(valid_temp) >= 2:
            synth_temp = await _synthesize(
                question, valid_temp[0].content, valid_temp[1].content, "temp", cfg
            )
        elif len(valid_temp) == 1:
            synth_temp = SynthesisResult(content=valid_temp[0].content, axis="temp")
        else:
            # Use one from prompt axis
            synth_temp = SynthesisResult(content=valid_prompt[0].content, axis="temp")
        total_llm_calls += 1
        
        yield log_step("synthesizing_prompt", stage=3, total=4)
        check_cancelled()
        
        # Synthesize persona axis
        if len(valid_prompt) >= 2:
            synth_prompt = await _synthesize(
                question, valid_prompt[0].content, valid_prompt[1].content, "prompt", cfg
            )
        elif len(valid_prompt) == 1:
            synth_prompt = SynthesisResult(content=valid_prompt[0].content, axis="prompt")
        else:
            synth_prompt = SynthesisResult(content=valid_temp[0].content, axis="prompt")
        total_llm_calls += 1
        
        # =================================================================
        # DEBATE: One round
        # =================================================================
        yield log_step("debating", stage=3, total=4)
        check_cancelled()
        
        debated_temp, debated_prompt = await _debate_round(
            question, synth_temp.content, synth_prompt.content, cfg
        )
        total_llm_calls += 4  # 2 critiques + 2 responses
        
        # =================================================================
        # MEGA SYNTHESIS
        # =================================================================
        yield log_step("mega_synth", stage=3, total=4)
        check_cancelled()
        
        mega_result, winner_axis = await _mega_synthesize(
            question, debated_temp, debated_prompt, cfg
        )
        total_llm_calls += 1
        
        # =================================================================
        # VERIFICATION: Two parallel verifiers
        # =================================================================
        yield log_step("verifying", stage=4, total=4)
        check_cancelled()
        
        score_a, score_b = await _verify_parallel(question, mega_result, cfg)
        total_llm_calls += 2
        
        final_score = _aggregate_scores(score_a.score, score_b.score, cfg)
        
        # Compute axis results for CPO (simplified for now, ideally verified separately)
        temp_axis_score = (score_a.score + score_b.score) / 2
        prompt_axis_score = (score_a.score + score_b.score) / 2
        
        axis_results = AxisResults(
            temp_axis_score=temp_axis_score,
            prompt_axis_score=prompt_axis_score,
        )
        
        # =================================================================
        # MUTATION if needed
        # =================================================================
        mutations_used = 0
        current_answer = mega_result
        current_score = final_score
        
        while current_score < cfg.mutation_threshold_1 and mutations_used < cfg.max_mutations:
            threshold = cfg.mutation_threshold_1 if mutations_used == 0 else cfg.mutation_threshold_2
            
            if current_score >= threshold:
                break
            
            yield log_step("mutating", stage=4, total=4)
            check_cancelled()
            
            mutations_used += 1
            log.cognitive(f"Mutation {mutations_used}: score {current_score} < {threshold}")
            
            current_answer = await _mutate(question, current_answer, current_score, cfg)
            total_llm_calls += 1
            
            # Re-verify
            score_a, score_b = await _verify_parallel(question, current_answer, cfg)
            total_llm_calls += 2
            current_score = _aggregate_scores(score_a.score, score_b.score, cfg)
        
        # Record CPO Preference (if we have a winner and score is good)
        if cfg.cpo_enabled and winner_axis != "equal":
             asyncio.create_task(cpo_engine.record_preference(question_type, winner_axis))

        # =================================================================
        # DONE
        # =================================================================
        result = EnsembleResult(
            answer=current_answer,
            final_score=current_score,
            mutations_used=mutations_used,
            axis_results=axis_results,
            state=EnsembleState.DONE,
            elapsed_ms=(time.time() - start_time) * 1000,
            total_llm_calls=total_llm_calls,
            thinking_log=thinking_log,
        )
        
        # Log trace (Phase 6 Telemetry)
        asyncio.create_task(record_thinking_trace(result, thinking_log))
        
        yield {"result": result.to_dict()}

    except asyncio.CancelledError:
        log.api("Ensemble cancelled by user")
        result = EnsembleResult(
            answer=mega_result if 'mega_result' in locals() else "",
            score=current_score if 'current_score' in locals() else 0.0,
            mutations_used=mutations_used if 'mutations_used' in locals() else 0,
            axis_results=None,
            state=EnsembleState.CANCELLED,
            elapsed_ms=(time.time() - start_time) * 1000,
            total_llm_calls=total_llm_calls,
            thinking_log=thinking_log,
        )
        yield {"result": result.to_dict()}
    
    except Exception as e:
        log.error(f"Ensemble error: {e}")
        # Try direct fallback
        try:
            direct = await _direct_response(question, context)
            result = EnsembleResult(
                answer=direct,
                final_score=5.0,
                state=EnsembleState.FALLBACK,
                elapsed_ms=(time.time() - start_time) * 1000,
                total_llm_calls=total_llm_calls + 1,
                thinking_log=thinking_log,
            )
        except Exception:
            result = EnsembleResult(
                answer=f"Произошла ошибка: {e}",
                final_score=0.0,
                state=EnsembleState.FALLBACK,
                elapsed_ms=(time.time() - start_time) * 1000,
                total_llm_calls=total_llm_calls,
                thinking_log=thinking_log,
            )
        yield {"result": result.to_dict()}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _generate_temperature_variants(
    question: str,
    context: str,
    cfg: EnsembleConfig,
) -> list[GenerationResult]:
    """Generate 2 responses with different temperatures (parallel)."""
    
    async def gen_temp(temp: float):
        try:
            response = await lm_client.chat(
                messages=[
                    {"role": "system", "content": context or "Ты полезный ассистент."},
                    {"role": "user", "content": question},
                ],
                model=config.lm_studio.default_model,
                temperature=temp,
                stream=False,
            )
            content = response if response else ""
            return GenerationResult(content=content, temperature=temp)
        except Exception as e:
            return GenerationResult(content="", temperature=temp, success=False, error=str(e))
    
    tasks = [
        lambda t=cfg.temperatures[0]: gen_temp(t),
        lambda t=cfg.temperatures[1]: gen_temp(t),
    ]
    
    raw_results = await fan_out_tasks(tasks, max_parallel=cfg.max_concurrent, timeout=cfg.timeout_generate)
    
    results = []
    for r in raw_results:
        if r.success:
            results.append(r.result)
        else:
            # Handle timeout/error from fan_out
            results.append(GenerationResult(content="", temperature=0.7, success=False, error=r.error or "Unknown error"))
    
    return results


async def _generate_persona_variants(
    question: str,
    context: str,
    cfg: EnsembleConfig,
) -> list[GenerationResult]:
    """Generate 2 responses with different personas (parallel)."""
    
    async def gen_persona(persona: str):
        try:
            system = PERSONA_PROMPTS.get(persona, "")
            if context:
                system = f"{context}\n\n{system}"
            
            response = await lm_client.chat(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": question},
                ],
                model=config.lm_studio.default_model,
                stream=False,
            )
            content = response if response else ""
            return GenerationResult(content=content, temperature=0.7, persona=persona)
        except Exception as e:
            return GenerationResult(content="", temperature=0.7, persona=persona, success=False, error=str(e))
    
    tasks = [
        lambda p=cfg.personas[0]: gen_persona(p),
        lambda p=cfg.personas[1]: gen_persona(p),
    ]
    
    raw_results = await fan_out_tasks(tasks, max_parallel=cfg.max_concurrent, timeout=cfg.timeout_generate)

    results = []
    for r in raw_results:
        if r.success:
            results.append(r.result)
        else:
            results.append(GenerationResult(content="", temperature=0.7, success=False, error=r.error or "Unknown error"))
    
    return results


async def _synthesize(
    question: str,
    answer_a: str,
    answer_b: str,
    axis: str,
    cfg: EnsembleConfig,
) -> SynthesisResult:
    """Synthesize two answers into one."""
    
    prompt = SYNTHESIS_PROMPT.format(
        question=question,
        answer_a=answer_a[:2000],  # Truncate for context
        answer_b=answer_b[:2000],
    )
    
    try:
        response = await asyncio.wait_for(
            lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model=config.lm_studio.default_model,
                stream=False,
            ),
            timeout=cfg.timeout_synthesis
        )
        content = response if response else ""
        return SynthesisResult(content=content, axis=axis, sources=[answer_a[:100], answer_b[:100]])
    except Exception as e:
        log.warn(f"Synthesis failed: {e}, using first answer")
        return SynthesisResult(content=answer_a, axis=axis)


async def _debate_round(
    question: str,
    synth_temp: str,
    synth_prompt: str,
    cfg: EnsembleConfig,
) -> tuple[str, str]:
    """One round of debate: each critiques the other, then responds."""
    
    # Step 1: Each critiques the other
    async def critique(answer: str):
        prompt = DEBATE_PROMPT_CRITIQUE.format(question=question, answer=answer[:2000])
        response = await lm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=config.lm_studio.default_model,
            stream=False,
        )
        return response if response else ""
    
    critique_tasks = [
        lambda a=synth_prompt: critique(a),  # temp critiques prompt
        lambda a=synth_temp: critique(a),    # prompt critiques temp
    ]
    
    crit_results = await fan_out_tasks(critique_tasks, max_parallel=cfg.max_concurrent, timeout=cfg.timeout_debate)
    critiques = [r.result if r.success else "" for r in crit_results]
    
    critique_of_prompt, critique_of_temp = critiques[0], critiques[1]
    
    # Step 2: Each responds to critique
    async def respond(original: str, crit: str):
        prompt = DEBATE_PROMPT_RESPOND.format(
            question=question,
            original=original[:1500],
            critique=crit[:500],
        )
        response = await lm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=config.lm_studio.default_model,
            stream=False,
        )
        return response if response else original
    
    respond_tasks = [
        lambda o=synth_temp, c=critique_of_temp: respond(o, c),
        lambda o=synth_prompt, c=critique_of_prompt: respond(o, c),
    ]
    
    resp_results = await fan_out_tasks(respond_tasks, max_parallel=cfg.max_concurrent, timeout=cfg.timeout_debate)
    improved = [r.result if r.success else "" for r in resp_results]
    
    # Fallback to original if debate failed
    out1 = improved[0] if improved[0] else synth_temp
    out2 = improved[1] if improved[1] else synth_prompt
    
    return out1, out2


async def _mega_synthesize(
    question: str,
    synth_temp: str,
    synth_prompt: str,
    cfg: EnsembleConfig,
) -> tuple[str, str]:
    """Final mega synthesis of the two axis results. Returns (answer, winner_axis)."""
    
    prompt = MEGA_SYNTHESIS_PROMPT.format(
        question=question,
        synth_temp=synth_temp[:2000],
        synth_prompt=synth_prompt[:2000],
    )
    
    content = synth_temp # default
    winner = "equal"
    
    try:
        response = await asyncio.wait_for(
            lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model=config.lm_studio.default_model,
                stream=False,
            ),
            timeout=cfg.timeout_synthesis
        )
        content = response if response else synth_temp
        
        # Parse winner
        if "[WINNER: TEMP]" in content:
            winner = "temp"
            content = content.replace("[WINNER: TEMP]", "")
        elif "[WINNER: PROMPT]" in content:
            winner = "prompt"
            content = content.replace("[WINNER: PROMPT]", "")
        elif "[WINNER: EQUAL]" in content:
            winner = "equal"
            content = content.replace("[WINNER: EQUAL]", "")
            
        return content.strip(), winner
        
    except Exception as e:
        log.warn(f"Mega synthesis failed: {e}")
        return synth_temp, "equal"


async def _verify_parallel(
    question: str,
    answer: str,
    cfg: EnsembleConfig,
) -> tuple[VerificationResult, VerificationResult]:
    """Two parallel verifiers for robustness."""
    
    async def verify():
        prompt = VERIFIER_PROMPT.format(
            question=question[:500],
            answer=answer[:2000],
        )
        response = await lm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=config.lm_studio.default_model,
            stream=False,
            temperature=0.1,  # Low temp for consistency
        )
        raw = response if response else ""
        score = _parse_score(raw, cfg.verifier_fallback_score)
        return VerificationResult(score=score, raw_response=raw, is_fallback=(score == cfg.verifier_fallback_score))
    
    tasks = [verify, verify]
    raw_results = await fan_out_tasks(tasks, max_parallel=cfg.max_concurrent, timeout=cfg.timeout_verify)
    
    results = []
    for r in raw_results:
        if r.success:
            results.append(r.result)
        else:
            results.append(VerificationResult(score=cfg.verifier_fallback_score, raw_response="Timeout", is_fallback=True))
            
    return results[0], results[1]


def _parse_score(response: str, fallback: float) -> float:
    """Parse numeric score from verifier response."""
    # Try to find a number 1-10
    match = re.search(r'\b([1-9]|10)\b', response.strip())
    if match:
        return float(match.group(1))
    
    # Try to parse as float
    try:
        score = float(response.strip())
        if 1 <= score <= 10:
            return score
    except ValueError:
        pass
    
    log.warn(f"Could not parse score from: {response[:50]}, using fallback {fallback}")
    return fallback


def _aggregate_scores(score_a: float, score_b: float, cfg: EnsembleConfig) -> float:
    """Aggregate two verifier scores (conservative if disagreement)."""
    disagreement = abs(score_a - score_b)
    
    if disagreement > cfg.score_disagreement_threshold:
        log.warn(f"Verifier disagreement: {score_a} vs {score_b}, using min")
        return min(score_a, score_b)
    
    return (score_a + score_b) / 2


async def _mutate(
    question: str,
    previous: str,
    score: float,
    cfg: EnsembleConfig,
) -> str:
    """Generate improved version based on low score."""
    
    prompt = MUTATION_PROMPT.format(
        question=question,
        previous_answer=previous[:2000],
        score=score,
    )
    
    try:
        response = await asyncio.wait_for(
            lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model=config.lm_studio.default_model,
                stream=False,
            ),
            timeout=cfg.timeout_generate
        )
        return response if response else previous
    except Exception as e:
        log.warn(f"Mutation failed: {e}")
        return previous


async def _direct_response(question: str, context: str) -> str:
    """Direct response fallback."""
    response = await lm_client.chat(
        messages=[
            {"role": "system", "content": context or "Ты полезный ассистент."},
            {"role": "user", "content": question},
        ],
        model=config.lm_studio.default_model,
        stream=False,
    )
    return response if response else "Не удалось сгенерировать ответ."
