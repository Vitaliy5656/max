"""
Deep Research Agent for Autonomous Task Execution.

Renamed from AutoGPT to reflect its specialized deep research focus.
Features:
- Multi-agent SOTA architecture (Planning, Execution, Verification)
- SOTA Stealth scraping with JA4 маскировкой
- Global multi-language research
- Fact credibility tracking
"""
import re
import uuid
import json
import asyncio
from datetime import datetime
from typing import Optional, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

import aiosqlite

from ..config import config
from ..lm_client import lm_client, TaskType
from ..tools import tools, TOOLS, DANGEROUS_TOOLS
from ..logger import log
from ..rag import rag
from .planner import ResearchPlanner
from .verifier import ResearchVerifier
from .synthesizer import ResearchSynthesizer
from .graph_memory import GraphMemory
from .workbench import ResearchWorkbench


class RunStatus(Enum):
    """Status of a Deep Research run."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"


class StepStatus(Enum):
    """Status of a single step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Step:
    """Single step in Research execution."""
    id: Optional[int] = None
    run_id: str = ""
    step_number: int = 0
    action: str = ""
    action_input: Optional[dict] = None
    result: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    created_at: Optional[str] = None


@dataclass
class Task:
    """Planned task from goal decomposition."""
    description: str
    completed: bool = False
    queries: list[str] = field(default_factory=list) # Planned search queries
    steps: list[Step] = field(default_factory=list)


@dataclass
class DeepResearchRun:
    """Represents a full Deep Research run."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    status: RunStatus = RunStatus.RUNNING
    max_steps: int = 20
    current_step: int = 0
    use_editable_cot: bool = True  # New field for user intervention
    plan: list[Task] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    burst_executed: bool = False  # Prevent multiple bursts on resume
    result: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    stats: dict = field(default_factory=lambda: {
        "articles_read": 0,
        "sites_visited": 0,
        "total_symbols": 0,
        "facts_saved": 0,
        "saved_symbols": 0
    })


class DeepResearchAgent:
    """
    Autonomous agent for deep multi-perspective research.
    
    Renamed from AutoGPT to reflect specialized research capabilities.
    """

    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
        self._current_run: Optional[DeepResearchRun] = None
        self._paused = False
        self._pending_confirmation: Optional[dict] = None
        self._on_step_callback = None
        self._on_confirmation_needed = None
        # P2 fix: CancellationToken for stopping long operations
        self._cancel_event: asyncio.Event = asyncio.Event()
        # P1 fix: Global lock to prevent race conditions (Singleton safety)
        self._run_lock = asyncio.Lock()
        # SOTA: Planner agent
        self._planner = ResearchPlanner()
        self._verifier = ResearchVerifier()
        self._synthesizer = ResearchSynthesizer()
        self._verification_semaphore = asyncio.Semaphore(2) # Limit parallel verification
        self._graph = None # Will be initialized per session
        self._workbench = None  # Ephemeral workbench for batch analysis
        self._forager: Optional[Any] = None # Information Forager
        self._discovery_stack: List[Any] = [] # Stack of high-scent leads
        
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        # P2-1 Fix: Schema migration for existing databases
        try:
            await self._db.execute("ALTER TABLE autogpt_runs ADD COLUMN plan TEXT")
            await self._db.commit()
            log.research("Added 'plan' column to autogpt_runs")
        except: pass # Column already exists
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS research_facts (
                run_id TEXT NOT NULL REFERENCES autogpt_runs(id) ON DELETE CASCADE,
                fact_id INTEGER NOT NULL REFERENCES memory_facts(id) ON DELETE CASCADE,
                PRIMARY KEY (run_id, fact_id)
            )
        """)
        await self._db.commit()
        
        # Initialize RAG for web context storage
        await rag.initialize(db)
        
    def set_callbacks(
        self,
        on_step=None,
        on_confirmation_needed=None
    ):
        """Set callback functions for UI integration."""
        self._on_step_callback = on_step
        self._on_confirmation_needed = on_confirmation_needed
    
    async def set_goal(self, goal: str, max_steps: int = 20, use_editable_cot: bool = False, curiosity_intensity: float = 0.7, saturation_threshold: float = 0.8) -> DeepResearchRun:
        """
        Set a new goal and create a run.
        """
        self.reset_cancel()
        
        # SOTA: Store cognitive parameters
        self._curiosity_intensity = curiosity_intensity
        self._saturation_threshold = saturation_threshold
        self._last_saturation = 0.0 # Reset for new run

        run = DeepResearchRun(
            goal=goal,
            max_steps=max_steps,
            status=RunStatus.RUNNING,
            use_editable_cot=use_editable_cot,
            created_at=datetime.now().isoformat()
        )
        
        # Initialize runtime attributes
        run._pending_facts = []  # Facts awaiting verification/storage
        
        # Initialize Graph Memory
        self._graph = GraphMemory(self._db)
        await self._graph.initialize()
        
        # Initialize Workbench for batch analysis
        # Low threshold (3) for faster accumulation during testing
        self._workbench = ResearchWorkbench(threshold=3, chunk_size=500)
        
        # Initialize Forager
        from ..quantum.forager import InformationForager
        self._forager = InformationForager(goal)
        self._discovery_stack = []
        
        # Keep old table names for data continuity
        await self._db.execute(
            """INSERT INTO autogpt_runs (id, goal, status, max_steps, plan, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (run.id, run.goal, run.status.value, run.max_steps, json.dumps([t.description for t in run.plan]), run.created_at)
        )
        
        # Ensure linkage table exists
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS research_facts (
                run_id TEXT,
                fact_id INTEGER,
                FOREIGN KEY(fact_id) REFERENCES memory_facts(id)
            )
        """)
        await self._db.commit()
        
        self._current_run = run
        return run
    
    async def run(self, max_steps: Optional[int] = None) -> list[Step]:
        """Execute the goal autonomously."""
        steps = []
        async for step in self.run_generator(max_steps):
            steps.append(step)
        return steps

    async def run_generator(self, max_steps: Optional[int] = None) -> AsyncIterator[Step]:
        """Execute the goal autonomously (Generator version)."""
        if not self._current_run:
            raise ValueError("No goal set. Call set_goal() first.")
        
        if self._run_lock.locked():
             raise RuntimeError("Agent is busy with another task")
             
        async with self._run_lock:
            run = self._current_run
            steps_limit = max_steps or run.max_steps
            
            # Phase 0: Goal Enhancement (SOTA Optimization)
            # Short goals produce vague queries. Detailed goals produce precise queries.
            # Auto-enhance if goal is short (<200 chars) and doesn't contain a plan structure.
            if len(run.goal) < 200 and "план" not in run.goal.lower() and "1." not in run.goal:
                enhanced_goal = await self._enhance_goal(run.goal)
                if enhanced_goal and len(enhanced_goal) > len(run.goal):
                    log.research(f"[GOAL ENHANCER] Expanded goal from {len(run.goal)} to {len(enhanced_goal)} chars")
                    run.goal = enhanced_goal
                    run._original_goal = run.goal  # Keep original for reference
                    # Update Forager with enhanced goal for better scent matching
                    if self._forager:
                        self._forager.goal = enhanced_goal
            
            # Phase 1: Plan
            if not run.plan:
                await self._create_plan()
                log.debug(f"Plan created. use_editable_cot={run.use_editable_cot}")
                if run.use_editable_cot:
                    run.status = RunStatus.WAITING_CONFIRMATION
                    yield Step(
                        run_id=run.id,
                        step_number=0,
                        action="plan_created",
                        result="План исследования создан. Ожидание подтверждения пользователя.",
                        status=StepStatus.COMPLETED
                    )
                    return # Stop and wait for user to resume
            
            # Phase 1.5: Query Bank (SOTA Optimization)
            # Generate ALL queries upfront to avoid on-the-fly drift
            if not hasattr(run, '_query_bank') or not run._query_bank:
                run._query_bank = await self._generate_query_bank(run.goal, num_queries=15)
                log.research(f"[QUERY BANK] Loaded {len(run._query_bank)} pre-generated queries")
            
            # Phase 1.6: PARALLEL SEARCH BURST (TURBO MODE)
            # Execute 5 searches in parallel to quickly gather initial data
            if not run.burst_executed and hasattr(run, '_query_bank') and len(run._query_bank) >= 5:
                log.research("(Burst) Launching parallel search burst (5 concurrent searches)...")
                run.burst_executed = True
                from ..web_search import web_searcher
                
                # Take 5 queries for parallel execution
                burst_queries = [run._query_bank.pop(0) for _ in range(5)]
                
                async def search_one(query: str, idx: int):
                    """Execute single search and return results."""
                    try:
                        # Translate to English for better Serper results
                        en_query = await self._translate_query(query) or query
                        results = await web_searcher.search(en_query, max_results=5, goal=run.goal)
                        log.research(f"(Burst) Search {idx+1}/5 complete: {query[:30]}... -> {len(results)} results")
                        return results
                    except Exception as e:
                        log.error(f"(Burst) Search {idx+1}/5 failed: {e}")
                        return []
                
                # Execute all 5 searches in PARALLEL
                burst_results = await asyncio.gather(*[
                    search_one(q, i) for i, q in enumerate(burst_queries)
                ])
                
                # Combine all results into pending URLs for processing
                all_urls = []
                for results in burst_results:
                    for r in results:
                        if r.url not in all_urls:
                            all_urls.append(r.url)
                
                # Store URLs for agent to process
                if not hasattr(run, '_pending_urls'):
                    run._pending_urls = []
                run._pending_urls.extend(all_urls[:20])  # Cap at 20 URLs
                
                log.research(f"(Burst) complete! {len(all_urls)} unique URLs queued for processing")
                run._search_count = 5  # Account for burst searches
            
            # Phase 2: Execute
            consecutive_failures = 0
            saturation_steps = 0
            MAX_SATURATION_STEPS = 5 # Stop after 5 steps of near-zero surprise
            
            while (
                (run.current_step < steps_limit or steps_limit == 0) and
                run.status == RunStatus.RUNNING and
                not self._paused and
                not self._cancel_event.is_set()
            ):
                log.debug(f"Entering execution loop. Step {run.current_step}/{steps_limit}")
                try:
                    # CHECK FOR SATURATION (Omni-Sponge Exit Condition)
                    if hasattr(self, '_last_saturation') and self._last_saturation > self._saturation_threshold:
                        saturation_steps += 1
                        if saturation_steps >= MAX_SATURATION_STEPS:
                            log.research(f"[OMNI-SPONGE] Knowledge Saturation reached ({self._last_saturation:.2f}). Ending research.")
                            run.status = RunStatus.COMPLETED
                            break
                    else:
                        saturation_steps = 0

                    print("[DEBUG] creating step_task...")
                    step_task = asyncio.create_task(self._execute_next_step())
                    cancel_wait = asyncio.create_task(self._cancel_event.wait())
                    log.debug("waiting for tasks...")
                    
                    done, pending = await asyncio.wait(
                        [step_task, cancel_wait], 
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    log.debug(f"wait finished. Done: {len(done)}")
                    
                    if cancel_wait in done:
                        log.research("Cancellation requested. Stopping current step...")
                        step_task.cancel()
                        try:
                            await step_task
                        except asyncio.CancelledError:
                            print("[AGENT] Step cancelled.")
                        run.status = RunStatus.FAILED # Or CANCELLED if you add it
                        break
                        
                    try:
                        step = step_task.result()
                    except asyncio.CancelledError:
                        log.research("Step cancelled unexpectedly.")
                        break
                    except Exception as e:
                        log.error(f"Step Task crashed with Exception: {e}")
                        import traceback
                        traceback.print_exc()
                        run.status = RunStatus.FAILED
                        run.result = f"Error: {e}"
                        break
                    except BaseException as e:
                        log.error(f"Step Task crashed with BaseException: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                    
                    if step:
                        run.steps.append(step)
                        run.current_step += 1
                        
                        # If the step was 'save_knowledge' and it returned facts, process them
                        if step.action == "save_knowledge" and step.result and "Сохранено" in step.result:
                            # Assuming step.action_input['batch'] contains the facts
                            facts = step.action_input.get("batch", [])
                            if facts:
                                for f in facts:
                                    # Update Graph Memory
                                    if self._graph:
                                        await self._graph.add_extraction(f, run.id)
                        
                        if step.status == StepStatus.FAILED:
                            consecutive_failures += 1
                            if consecutive_failures >= 3:
                                run.status = RunStatus.FAILED
                                run.result = "Aborted: Too many consecutive failures (3)."
                                step.result += "\n[System] Aborting run due to repeated failures."
                                await self._save_step(step)
                                break
                        else:
                            consecutive_failures = 0
                        
                        yield step
                        
                        if self._on_step_callback:
                            await self._on_step_callback(step)
                    else:
                        print("[AGENT] Step execution returned None. Ending run.")
                        break
                    
                    if await self._check_goal_completed():
                        log.debug(f"Goal completed check: True (steps={run.current_step})")
                        run.status = RunStatus.COMPLETED
                        break
                    else:
                        log.debug(f"Goal completed check: False (tasks left: {len([t for t in run.plan if not t.completed])})")
                    
                    log.debug(f"End of loop iter. Steps={run.current_step}/{steps_limit}, Status={run.status}")

                except Exception as e:
                    run.status = RunStatus.FAILED
                    run.result = f"Error: {str(e)}"
                    break
            
            # Post-loop Finalization
            if run.status == RunStatus.RUNNING:
                # If we exited due to steps limit, mark as completed if we have results
                run.status = RunStatus.COMPLETED
            
            if run.status == RunStatus.COMPLETED:
                # WORKBENCH: Flush remaining data before synthesis
                if self._workbench and self._workbench.chunks:
                    print(f"[WORKBENCH] Flushing {len(self._workbench.chunks)} remaining chunks...")
                    remaining_facts = await self._workbench.quick_extract_facts(run.goal)
                    if remaining_facts:
                        # Save remaining facts
                        from ..tools import tools
                        result = await tools._tool_save_knowledge(
                            content=remaining_facts[0],
                            batch=remaining_facts,
                            category="research"
                        )
                        print(f"[WORKBENCH] Saved remaining: {result.output}")
                        
                        # Link facts to this run
                        import re as regex
                        ids_match = regex.search(r'IDs:\s*\[([^\]]+)\]', result.output)
                        if ids_match:
                            ids_str = ids_match.group(1)
                            fact_ids = [int(x.strip()) for x in ids_str.split(',') if x.strip().isdigit()]
                            for fid in fact_ids:
                                await self._link_fact_to_run(run.id, fid)
                            log.research(f"[WORKBENCH] Linked {len(fact_ids)} facts to run {run.id}")
                    self._workbench.clear()
                
                # SOTA: Final Synthesis Phase
                log.research("Generating final report...")
                # Fetch all facts linked to this run from DB
                run_facts = await self._get_run_facts(run.id)
                
                # Prepare facts for synthesizer (extract URL from tags)
                typed_facts = []
                for f in run_facts:
                    content = f.get('content', '')
                    url = ""
                    # Extract URL from metadata if present
                    if f.get('metadata'):
                        try:
                            meta = json.loads(f['metadata'])
                            url = meta.get('url', '')
                        except: pass
                    
                    if not url and " [Tags: url:" in content:
                        parts = content.split(" [Tags: url:")
                        content = parts[0]
                        url = parts[1].rstrip("]")
                    
                    typed_facts.append({
                        "content": content,
                        "tag": f.get('category', 'research'),
                        "url": url
                    })

                if typed_facts:
                    report = await self._synthesizer.generate_report(run.goal, typed_facts)
                    run.result = report
                    log.research(f"Report generated ({len(report)} chars) with {len(typed_facts)} facts.")
                else:
                    run.result = "Research finished, but no relevant facts were found for the final report."
            
            await self._db.execute(
                """UPDATE autogpt_runs 
                   SET status = ?, current_step = ?, result = ?, completed_at = ?
                   WHERE id = ?""",
                (run.status.value, run.current_step, run.result, 
                 datetime.now().isoformat() if run.status != RunStatus.RUNNING else None,
                 run.id)
            )
            await self._db.commit()
    
    async def _create_plan(self):
        """Create a plan by decomposing the goal using ResearchPlanner."""
        run = self._current_run
        plan_items = await self._planner.create_initial_plan(run.goal)
        
        run.plan = [
            Task(
                description=f"{item['stage']}: {item['description']}",
                queries=item.get('queries', [])
            )
            for item in plan_items
        ]
        
        # Save plan to metadata if needed, for now just update memory
        log.debug(f"plan_items type: {type(plan_items)}")
        log.research(f"Created {len(run.plan)} tasks: {[t.description for t in run.plan]}")

    async def _enhance_goal(self, short_goal: str) -> str:
        """
        Goal Enhancer: Transforms a short goal into a detailed research plan.
        
        This leverages the observation that detailed goals produce precise search queries,
        while short goals often lead to drift and hallucinations.
        """
        prompt = f"""Ты — Эксперт по Планированию Исследований.
Пользователь дал короткий запрос: "{short_goal}"

Твоя задача: Расширить этот запрос в ДЕТАЛЬНЫЙ план исследования.

Формат ОТВЕТА (строго):
Цель исследования: [Развёрнутая версия цели]

Ключевые аспекты для изучения:
1. [Конкретный аспект с 2-3 ключевыми словами для поиска]
2. [Еще один аспект с ключевыми словами]
3. [Третий аспект]
4. [Четвёртый аспект, если применимо]

Основные поисковые термины:
- [Термин 1]
- [Термин 2]
- [Термин 3]

ВАЖНО: Включи КОНКРЕТНЫЕ термины и ключевые слова, которые должны использоваться в поисковых запросах.
НЕ добавляй сроки, методологию или оргструктуру — только содержательную часть."""

        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=TaskType.REASONING,  # Use strong model for critical goal expansion
                stream=False,
                max_tokens=800
            )
            
            # Strict validation: response must have expected structure
            has_goal = "Цель исследования" in response or "цель" in response.lower()[:100]
            has_aspects = "Ключевые аспекты" in response or "1." in response
            is_longer = len(response.strip()) > len(short_goal) * 1.5  # At least 50% longer
            
            if has_goal and has_aspects and is_longer:
                log.research(f"[GOAL ENHANCER] [OK] Validated. Length: {len(short_goal)} -> {len(response)}")
                return response.strip()
            else:
                log.warn(f"[GOAL ENHANCER] Invalid format (goal={has_goal}, aspects={has_aspects}, longer={is_longer})")
            
        except Exception as e:
            print(f"[GOAL ENHANCER] Error: {e}")
        
        return short_goal  # Fallback to original

    async def _generate_query_bank(self, goal: str, num_queries: int = 15) -> list[str]:
        """
        Query Bank: Generate ALL search queries upfront.
        
        This eliminates on-the-fly query generation which causes drift.
        Produces 10-20 diverse, specific search queries covering all aspects of the goal.
        """
        prompt = f"""Ты — Генератор Поисковых Запросов для исследования.
Тема исследования: {goal}

Сгенерируй {num_queries} ТОЧНЫХ поисковых запросов для полного изучения этой темы.

КРИТИЧЕСКИ ВАЖНО:
1. КАЖДЫЙ запрос ОБЯЗАТЕЛЬНО должен содержать ключевые слова из темы!
   - Если тема "история клавиатуры", каждый запрос должен содержать "клавиатура" или "keyboard"
   - НЕ СОЗДАВАЙ общие запросы типа "key milestones" — поисковик НЕ поймёт контекст!
2. Запросы должны быть КОНКРЕТНЫМИ и ОДНОЗНАЧНЫМИ
3. Покрывать РАЗНЫЕ аспекты темы (история, статистика, изобретатели, технологии)
4. Включать как русские, так и английские запросы

Ответь ТОЛЬКО списком JSON:
["запрос 1", "запрос 2", ...]

Пример для "История клавиатуры":
["история компьютерной клавиатуры", "keyboard invention history", "QWERTY keyboard layout history", "кто изобрел клавиатуру", "mechanical keyboard history Cherry MX", "эргономичные клавиатуры история", "keyboard timeline 1800s to 2000s"]"""

        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=TaskType.REASONING,  # Strong model for quality
                stream=False,
                max_tokens=1500
            )
            
            # Extract JSON array
            import json
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                queries = json.loads(response[json_start:json_end])
                if isinstance(queries, list) and len(queries) >= 5:
                    log.research(f"[QUERY BANK] Generated {len(queries)} queries:")
                    for i, q in enumerate(queries[:num_queries], 1):
                        log.research(f"  {i}. {q}")
                    return queries[:num_queries]  # Cap at requested number
                    
        except Exception as e:
            print(f"[QUERY BANK] Error: {e}")
        
        # Fallback: generate basic queries from goal keywords
        import re
        keywords = re.findall(r'\w+', goal)[:5]
        fallback = [goal] + [f"{goal} {kw}" for kw in keywords if len(kw) > 3]
        print(f"[QUERY BANK] [WARN] Using fallback: {len(fallback)} queries")
        return fallback

    async def update_plan(self, tasks: list[str]):
        """Manually update the current research plan (Editable CoT)."""
        if not self._current_run: return
        self._current_run.plan = [Task(description=t) for t in tasks]
        self._current_run.status = RunStatus.RUNNING
        # Log update?
    
    async def _execute_next_step(self) -> Optional[Step]:
        """Execute the next step towards the goal."""
        log.debug("_execute_next_step STARTED")
        run = self._current_run
        
        # ========== TURBO: PROCESS PENDING URLS FROM BURST ==========
        # If we have URLs queued from parallel burst, process them directly
        while hasattr(run, '_pending_urls') and run._pending_urls:
            pending_url = run._pending_urls.pop(0)
            
            # Track URL to avoid duplicates
            if not hasattr(run, '_visited_urls'):
                run._visited_urls = set()
            
            if pending_url in run._visited_urls:
                log.research(f"(Skip) Skipping already visited URL: {pending_url[:40]}...")
                continue
            
            log.research(f"(Read) Processing queued URL ({len(run._pending_urls)} left): {pending_url[:50]}...")
            run._visited_urls.add(pending_url)
            
            # Create step for reading this URL
            run.current_step += 1
            step = Step(
                run_id=run.id,
                step_number=run.current_step,
                action="read_webpage",
                action_input={"url": pending_url, "goal": run.goal}, # Better input
                status=StepStatus.RUNNING
            )
            # Thought for logging
            step.thought = f"Processing URL from TURBO burst: {pending_url[:30]}"
            
            # Execute the read action directly
            try:
                from ..tools import tools
                # Fix: Use tools.execute for consistency
                step.result = await tools.execute("read_webpage", step.action_input)
                step.status = StepStatus.COMPLETED
                
                # Add to workbench for batch processing
                if self._workbench and "Content from" in step.result:
                    content = step.result.replace("Content from", "").strip()
                    await self._workbench.add_page(pending_url, content)
                
                # We return here to yield the step in the main loop
                return step
            except Exception as e:
                print(f"[TURBO] [FAIL] Failed to read {pending_url}: {e}")
                step.result = f"Error: {e}"
                step.status = StepStatus.FAILED
                return step
        
        # ========== NORMAL: ASK LLM FOR NEXT ACTION ==========
        context = f"Goal: {run.goal}\n\n"
        
        if run.plan:
            context += "Plan:\n"
            for i, task in enumerate(run.plan, 1):
                status = "[DONE]" if task.completed else "[ ]"
                context += f"  {status} {i}. {task.description}\n"
                if not task.completed and task.queries:
                    context += f"     Suggested queries: {task.queries}\n"
            context += "\n"
        
        if run.steps:
            context += "Previous Steps:\n"
            for step in run.steps[-5:]:
                result_preview = step.result[:500] if step.result else 'OK'
                context += f"  - {step.action}: {result_preview}...\n"
            context += "\n"
        
        next_action_prompt = f"""{context}
Ты - Deep Research Agent. Что нужно сделать следующим шагом?

СТАНДАРТ ИССЛЕДОВАНИЯ (Строго следуй подписям инструментов):

1. web_search(query: str) - Поиск информации.
   Пример: {{"action": "web_search", "action_input": {{"query": "актуальные данные о..."}}}}

2. read_webpage(url: str) - Чтение конкретной страницы.
   Пример: {{"action": "read_webpage", "action_input": {{"url": "https://..."}}}}

3. save_knowledge(content: str) - Сохранение важного факта.
   Пример: {{"action": "save_knowledge", "action_input": {{"content": "Найденный факт..."}}}}

Важно: Не повторяй одни и те же действия. Если ты уже нашел ссылки, читай их.

[System] [WARN] CRITICAL REQUIREMENT [WARN]
ИСПОЛЬЗУЙ ТОЛЬКО ЭТИ 3 ИНСТРУМЕНТА:
- web_search
- read_webpage  
- save_knowledge

НЕ ПРИДУМЫВАЙ ДРУГИХ ИНСТРУМЕНТОВ! define_key_entities, serpapi_search, analyze и т.д. НЕ СУЩЕСТВУЮТ!
Если не знаешь что делать - используй web_search.

Обязательно используй JSON формат:
{{
  "thought": "reasoning",
  "action": "tool_name",
  "action_input": {{...}},
  "is_final": false
}}"""

        # OMNI-SPONGE: Prioritize Discovery Stack for autonomous branching
        # ONLY if plan is exhausted OR we are deep in research (step > 4) and want to explore
        if self._discovery_stack and (not run.plan or all(t.completed for t in run.plan) or (run.current_step > 4 and run.current_step % 3 == 0)):
            print(f"[DEBUG] Priority Stack Branching: Stack={len(self._discovery_stack)}, Plan Empty/Done={not run.plan}")
            lead = self._discovery_stack.pop()
            if self._forager:
                self._forager.visited_urls.add(lead.url)
            
            log.research(f"(Rocket) Curiosity Branching: Visiting {lead.url}")
            return Step(
                run_id=run.id,
                step_number=run.current_step + 1,
                action="read_webpage",
                action_input={"url": lead.url, "goal": run.goal},
                status=StepStatus.PENDING
            )

        print(f"[DEBUG] Requesting next action from LLM... (Step {run.current_step})")
        response = await lm_client.chat(
            messages=[{"role": "user", "content": next_action_prompt}],
            stream=False,
            task_type=TaskType.REASONING,
            max_tokens=500
        )
        print(f"[DEBUG] LLM Response received ({len(response)} chars)")
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            action_data = json.loads(response[json_start:json_end])
        except:
            # FALLBACK: Use Query Bank if JSON parsing fails (not hardcoded goal!)
            fallback_query = None
            
            # Priority 1: Query Bank
            if hasattr(run, '_query_bank') and run._query_bank:
                fallback_query = run._query_bank.pop(0)
                print(f"[FALLBACK] JSON failed, using Query Bank ({len(run._query_bank)} left): {fallback_query[:40]}...")
            # Priority 2: Adaptive queries  
            elif hasattr(run, '_adaptive_queries') and run._adaptive_queries:
                fallback_query = run._adaptive_queries.pop(0)
                print(f"[FALLBACK] JSON failed, using Adaptive Query: {fallback_query[:40]}...")
            # Priority 3: Goal (last resort)
            else:
                fallback_query = run.goal[:100]
                print(f"[FALLBACK] JSON failed, no queries left, using goal: {fallback_query[:40]}...")
            
            action_data = {
                "action": "web_search", 
                "action_input": {"query": fallback_query},
                "is_final": False
            }
        
        if action_data.get("is_final") or action_data.get("action") == "finish":
            log.research(f"LLM decided to finish. Reason: {action_data.get('thought', 'No thought provided')}")
            run.status = RunStatus.COMPLETED
            
            # SOTA: Automatic Synthesis
            async with self._db.execute(
                "SELECT content, tag FROM research_facts_view WHERE run_id = ?",
                (run.id,)
            ) as cursor:
                # Assuming we have a view or similar
                # Let's just use recent memory for now
                pass
            
            # Fetch all saved facts for this run
            facts = []
            async with self._db.execute(
                "SELECT content, metadata FROM memory_facts WHERE id IN (SELECT fact_id FROM research_facts WHERE run_id = ?)",
                (run.id,)
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    meta = json.loads(row[1])
                    facts.append({"content": row[0], "tag": meta.get("tag", "н/д")})
            
            if facts:
                report = await self._synthesizer.generate_report(run.goal, facts)
                run.result = report
            else:
                run.result = action_data.get("result", "Research completed but no facts extracted.")
                
            return None
        
        action = action_data.get("action", "think")
        action_input = action_data.get("action_input", {})
        
        # AGGRESSIVE FALLBACK: If action is 'think' or empty, force web_search
        if action in ["think", ""] or not action_input:
            incomplete_task = None
            if run.plan:
                for task in run.plan:
                    if not task.completed:
                        incomplete_task = task
                        break
            if incomplete_task:
                fallback_query = run.goal
                action = "web_search"
                action_input = {"query": fallback_query}
                log.research(f"[FALLBACK] 'think' replaced with web_search: {fallback_query}")
        
        # ============= RESEARCH FLOW STATE MACHINE =============
        if run.steps:
            last_step = run.steps[-1]
            last_action = last_step.action
            last_result = last_step.result or ""
            
            if hasattr(run, '_pending_facts') and run._pending_facts:
                next_fact = run._pending_facts.pop(0)
                action = "save_knowledge"
                action_input = {"content": next_fact, "category": "research", "run_id": run.id}
            elif last_action == "web_search" and "URL:" in last_result:
                url_match = re.search(r'URL:\s*(https?://[^\s\n]+)', last_result)
                if url_match:
                    forced_url = url_match.group(1)
                    action = "read_webpage"
                    action_input = {"url": forced_url, "goal": run.goal}
                    run._last_url = forced_url
            elif last_action == "read_webpage" and len(last_result) > 200 and not last_result.startswith("Error"):
                content = last_result.replace("Content from", "").strip()
                if content.startswith("http"):
                    content = content.split("\n", 1)[1] if "\n" in content else content
                
                # Basic quality/error filters
                error_indicators = ["404", "403", "captcha", "verify you are human"]
                is_error = any(err in content.lower() for err in error_indicators)
                
                if not is_error:
                    last_url = run._last_url if hasattr(run, '_last_url') else 'unknown'
                    
                        # WORKBENCH FLOW: Add to ephemeral store
                    if self._workbench:
                        workbench_ready = await self._workbench.add_page(last_url, content)
                        
                        # Trigger Batch Analysis and TRIANGULATION if ready
                        if workbench_ready:
                            log.research("Workbench Threshold reached! Triggering Triangulation & Analysis...")
                            
                            # 1. TRIANGULATION: Find "Gold Facts" across sources
                            gold_facts = await self._workbench.triangulate_facts(run.goal)
                            if gold_facts:
                                log.research(f"[TRIANGULATION] Found {len(gold_facts)} GOLD facts. Injecting to memory...")
                                if not hasattr(run, '_pending_facts'):
                                     run._pending_facts = []
                                run._pending_facts.extend(gold_facts)
                            
                            # 2. General Analysis (Gaps, Next Queries)
                            analysis = await self._workbench.analyze(run.goal)
                            
                            # Update Plan with new facts/insights (Regular ones)
                            if analysis.quality_facts:
                                if not hasattr(run, '_pending_facts'):
                                     run._pending_facts = []
                                run._pending_facts.extend(analysis.quality_facts)
                                log.research(f"[WORKBENCH] Added {len(analysis.quality_facts)} quality facts to pending queue")
                            
                            # Update Discovery Stack with next queries
                            if analysis.next_queries:
                                log.research(f"[WORKBENCH] Injecting {len(analysis.next_queries)} adaptive queries")
                                if not hasattr(run, '_adaptive_queries'):
                                    run._adaptive_queries = []
                                run._adaptive_queries.extend(analysis.next_queries)

                            # 3. GRAPH EXTRACTION: Batch process workbench content for graph
                            # This is more efficient than individual extractions
                            if self._graph:
                                workbench_text = "\n\n".join([c.content[:400] for c in self._workbench.chunks[:5]])
                                await self._graph.add_extraction(workbench_text, run.id)

                            # 4. Clear workbench for next batch
                            self._workbench.clear()

                        # === DEEP DIVE: Crawl internal links on relevant sites ===
                        try:
                            if await self._workbench.should_deep_dive(last_url, content, run.goal):
                                from ..web_search import web_searcher
                                # Get raw HTML for link extraction
                                extra_pages = await web_searcher.deep_dive(
                                    start_url=last_url,
                                    html=last_result,  # Use original HTML
                                    goal=run.goal,
                                    max_pages=3
                                )
                                # Add all deep dive pages to workbench
                                if extra_pages:
                                    log.research(f"[DEEP DIVE] Found {len(extra_pages)} internal pages")
                                    for sub_url, sub_content in extra_pages:
                                        await self._workbench.add_page(sub_url, sub_content)
                        except Exception as e:
                            log.debug(f"[DEEP DIVE] Error: {e}")
                        
                        # === OMNI-SPONGE: Forage for new leads (Discovery Stack) ===
                        if self._forager:
                            new_leads = await self._forager.forage_links(last_result, getattr(run, '_current_depth', 0))
                            if new_leads:
                                log.research(f"[OMNI-SPONGE] Found {len(new_leads)} potential leads. Ranking...")
                                ranked = await self._forager.rank_by_llm(new_leads)
                                for lead in reversed(ranked): # Add to stack
                                    if lead.url not in self._forager.visited_urls:
                                        self._discovery_stack.append(lead)
                                        log.debug(f"  + Added to stack: {lead.text[:40]}...")
                    else:
                        # Fallback: old individual extraction
                        try:
                            await rag.add_web_context(content, last_url, run.goal)
                        except: pass
                        
                        facts_to_save = await self._extract_facts_with_llm(content, run.goal)
                        if facts_to_save:
                            action_input = {
                                "content": facts_to_save[0],
                                "batch": facts_to_save,
                                "category": "research",
                                "run_id": run.id,
                                "tags": f"url:{last_url}"
                            }
        
        if action == "web_search":
            # === GLOBAL MULTI-LANGUAGE SEARCH ===
            original_query = action_input.get("query", "")
            if isinstance(original_query, list):
                original_query = original_query[0] if original_query else ""
                action_input["query"] = original_query
            
            action_input["goal"] = run.goal  # Pass goal for filtering
            
            # === PRIORITY 1: USE QUERY BANK (Pre-generated, no drift) ===
            if hasattr(run, '_query_bank') and run._query_bank:
                bank_query = run._query_bank.pop(0)
                log.research(f"(Target) Using pre-generated query ({len(run._query_bank)} left): {bank_query[:50]}...")
                action_input["query"] = bank_query
                original_query = bank_query
            # === PRIORITY 2: USE ADAPTIVE QUERIES (Gap-filling) ===
            elif hasattr(run, '_adaptive_queries') and run._adaptive_queries:
                adaptive_query = run._adaptive_queries.pop(0)
                log.research(f"(Target) Using gap-filling query: {adaptive_query[:50]}...")
                action_input["query"] = adaptive_query
                original_query = adaptive_query
            
            # Initialize search counter if not exists
            if not hasattr(run, '_search_count'):
                run._search_count = 0
            run._search_count += 1
            
            # Use global search every 2nd search for diversity (2, 4, 6...)
            use_global = (run._search_count % 2 == 0)
            
            if use_global:
                log.research(f"🌍 Multi-language search #{run._search_count}: {original_query[:40]}...")
                action_input["use_global"] = True
                action_input["translate_to"] = 3  # Translate to 3 random languages
            else:
                log.research(f"Standard search #{run._search_count}: {original_query[:40]}...")
            
            # Still translate Russian queries to English
            if re.search('[а-яА-Я]', original_query):
                translated = await self._translate_query(original_query)
                if translated:
                    action_input["query"] = f"{translated} (original: {original_query})"
                    log.research(f"Searching in English: {translated}")

        step = Step(
            run_id=run.id,
            step_number=run.current_step + 1,
            action=action,
            action_input=action_input,
            status=StepStatus.RUNNING
        )
        
        if action in DANGEROUS_TOOLS:
            confirmed = False
            if self._on_confirmation_needed:
                confirmed = await self._on_confirmation_needed(action, action_input)
            if not confirmed:
                step.status = StepStatus.SKIPPED
                step.result = "Blocked: User confirmation required."
                await self._save_step(step)
                return step
        
        try:
            if action == "think":
                step.result = action_data.get("thought", "Thinking...")
            else:
                step.result = await tools.execute(action, action_input)
            
            step.status = StepStatus.COMPLETED
            
            # HARVEST METRICS
            if action == "read_webpage" and "Error" not in step.result:
                run.stats["articles_read"] += 1
                run.stats["total_symbols"] += len(step.result)
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(action_input.get("url")).netloc
                    if not hasattr(run, "_visited_domains"):
                        run._visited_domains = set()
                    if domain not in run._visited_domains:
                        run._visited_domains.add(domain)
                        run.stats["sites_visited"] = len(run._visited_domains)
                except: pass
            
            if action == "save_knowledge" and step.status == StepStatus.COMPLETED:
                run.stats["facts_saved"] += 1
                run.stats["saved_symbols"] += len(str(action_input.get("content", "")))
                # If batch save, increment more
                batch = action_input.get("batch", [])
                if batch:
                    run.stats["facts_saved"] = run.stats["facts_saved"] - 1 + len(batch)
                    for b in batch:
                        run.stats["saved_symbols"] += len(str(b))
            
            # SOTA: Link facts to run
            if action == "save_knowledge" and step.status == StepStatus.COMPLETED:
                # Result looks like "[OK] Saved to memory (ID: 123)"
                # OR "[OK] Batch saved 10 facts (IDs: [1, 2, ...])"
                if "IDs: [" in step.result:
                    try:
                        ids_str = re.search(r'IDs:\s*\[(.*?)\]', step.result).group(1)
                        saved_ids = [int(i.strip()) for i in ids_str.split(",") if i.strip()]
                        for fact_id in saved_ids:
                            await self._link_fact_to_run(run.id, fact_id)
                    except Exception as e:
                        print(f"Error parsing batch IDs: {e}")
                elif "(ID: " in step.result:
                    try:
                        found_id = re.search(r'ID:\s*(\d+)', step.result)
                        if found_id:
                            fact_id = int(found_id.group(1))
                            await self._link_fact_to_run(run.id, fact_id)
                    except: pass

            await self._mark_task_progress(action, step.result)
        except Exception as e:
            step.result = f"Error: {str(e)}"
            step.status = StepStatus.FAILED

        await self._save_step(step)
        run.steps.append(step)
        run.current_step += 1

        # OMNI-SPONGE: Titans TTT on extracted knowledge
        if action == "save_knowledge" and step.status == StepStatus.COMPLETED:
            await self._trigger_titans_ttt(action_input.get("batch", []))

        return step

    async def _trigger_titans_ttt(self, facts: list[str]):
        """Force Titans Neural Memory to learn from extracted facts."""
        if not facts: return
        
        from ..memory import memory
        for fact in facts:
            # Get embedding for the fact
            emb = await lm_client.get_embedding(fact)
            if emb:
                # Update Titans with the fact
                res = await memory.titans.process_signal(emb)
                self._last_saturation = res.get("saturation", 0.0)
                if res.get("is_stored"):
                    # Use research logger
                    log.research(f"Curious insight absorbed! Surprise: {res['surprise']:.4f}, Saturation: {self._last_saturation:.2f}")

    async def _mark_task_progress(self, action: str, result: str):
        """Mark planned tasks as completed based on executed actions."""
        run = self._current_run
        if not run or not run.plan:
            return

        # P1 fix: Only mark as done if result is substantial AND actually contains info
        # Avoid marking as done on errors, short responses, or "no facts found"
        if not result or len(result) < 100 or "error" in result.lower():
            return
            
        useless_phrases = ["no facts", "nothing found", "could not find", "unavailable"]
        if any(phrase in result.lower() for phrase in useless_phrases):
            return

        for task in run.plan:
            if task.completed:
                continue
            task_lower = task.description.lower()
            
            # Check if this action matches the task intent
            action_match = any(kw in task_lower for kw in [
                "поиск", "search", "read", "читать", "сохранить", 
                "save_knowledge", "find", "who", "get", "extract"
            ]) or action.lower() in task_lower
            
            if action_match:
                task.completed = True
                log.research(f"Task marked as completed: {task.description[:40]}...")
                break

    async def _link_fact_to_run(self, run_id: str, fact_id: int):
        """Link a single fact to a research run."""
        await self._db.execute(
            "INSERT INTO research_facts (run_id, fact_id) VALUES (?, ?)",
            (run_id, fact_id)
        )
        await self._db.commit()


    async def _translate_query(self, query: str) -> Optional[str]:
        """Translate query to English for Global Search."""
        try:
            prompt = f"""Translate to English. Output ONLY the translated text, nothing else.
NO explanations. NO notes. NO parentheses. JUST the translation.

Input: {query}
Output:"""
            result = await lm_client.chat([{"role": "user", "content": prompt}], task_type=TaskType.QUICK, stream=False, max_tokens=100)
            # Clean any remaining garbage
            clean = result.strip().split('\n')[0].strip()  # Take only first line
            if '(' in clean:  # Remove any parenthetical notes
                clean = clean.split('(')[0].strip()
            return clean if len(clean) > 3 else None
        except: return None

    async def _extract_facts_with_llm(self, content: str, goal: str) -> list[str]:
        """Extract and VERIFY facts using LLM (Phi 3.5 optimized)."""
        try:
            content_chunk = content[:6000]
            # Use large model for extraction to get better nuance
            prompt = f"Extract all research facts related to: {goal}\n\nContent:\n{content_chunk}\n\nReturn as numbered list."
            messages = [
                {"role": "system", "content": "You are a Research Fact Extractor."},
                {"role": "user", "content": prompt}
            ]
            response = await lm_client.chat(messages=messages, stream=False, task_type=TaskType.REASONING)
            raw_facts = [line.lstrip("0123456789.-•) ").strip() for line in response.split("\n") if len(line.strip()) > 20]
            
            # QUALITY FILTER: Remove garbage before verification
            quality_facts = [f for f in raw_facts if self._is_quality_fact(f)]
            
            if not quality_facts:
                return []
            
            # SOTA: Parallel Verification and Tagging (with Semaphore)
            async def semaphore_verify(fact):
                async with self._verification_semaphore:
                    return await self._verifier.verify_fact(fact, goal)

            verification_tasks = [semaphore_verify(fact) for fact in quality_facts[:10]]
            verification_results = await asyncio.gather(*verification_tasks)
            
            # Filter: Only keep verified and rumor facts, skip "не подтверждено"
            verified_facts = []
            for i, (tag, conf) in enumerate(verification_results):
                if tag in ["верифицировано", "слухи/мнения"] and conf >= 0.3:
                    verified_facts.append(f"[{tag}] {quality_facts[i]}")
                
            return verified_facts
        except Exception as e:
            print(f"Extraction error: {e}")
            return []
    
    def _is_quality_fact(self, fact: str) -> bool:
        """Filter out garbage facts before saving to memory."""
        fact_lower = fact.lower()
        
        # Blacklist: Error messages and garbage
        garbage_keywords = [
            "unavailable", "inaccessible", "404", "403", "error", 
            "dns_probe", "nxdomain", "timeout", "captcha", "verify you are human",
            "cannot be extracted", "could not resolve", "connection refused",
            "website is currently", "page not found", "access denied",
            "please enable javascript", "cloudflare", "bot detection"
        ]
        
        if any(kw in fact_lower for kw in garbage_keywords):
            return False
        
        # Too short = likely garbage
        if len(fact) < 50:
            return False
        
        # Too many special characters = encoding issues
        special_count = sum(1 for c in fact if ord(c) > 65535 or c in '\ufffd\x00')
        if special_count > len(fact) * 0.1:
            return False
        
        return True
    
    async def _save_step(self, step: Step):
        """Save step to database."""
        await self._db.execute(
            """INSERT INTO autogpt_steps 
               (run_id, step_number, action, action_input, result, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (step.run_id, step.step_number, step.action,
             json.dumps(step.action_input) if step.action_input else None,
             step.result, step.status.value)
        )
        await self._db.commit()
    
    async def _check_goal_completed(self) -> bool:
        """Check if research goal achieved."""
        run = self._current_run
        if run.steps and run.steps[-1].action == "finish":
            return True
        if run.plan and all(t.completed for t in run.plan):
            return True
        return False
    
    def pause(self):
        self._paused = True
        if self._current_run: self._current_run.status = RunStatus.PAUSED

    def resume(self):
        self._paused = False
        if self._current_run: self._current_run.status = RunStatus.RUNNING

    async def cancel(self):
        self._cancel_event.set()
        if self._current_run:
            self._current_run.status = RunStatus.FAILED
            self._current_run.result = "Cancelled by user"
            await self._db.execute(
                "UPDATE autogpt_runs SET status = ?, result = ?, completed_at = ? WHERE id = ?",
                (RunStatus.FAILED.value, "Cancelled by user", datetime.now().isoformat(), self._current_run.id)
            )
            await self._db.commit()

    def is_running(self) -> bool:
        return self._current_run is not None and self._current_run.status == RunStatus.RUNNING

    def is_paused(self) -> bool:
        return self._paused or (self._current_run is not None and self._current_run.status == RunStatus.PAUSED)

    def reset_cancel(self):
        self._cancel_event.clear()
    
    async def get_run(self, run_id: str) -> Optional[DeepResearchRun]:
        """Get a run by ID."""
        async with self._db.execute(
            "SELECT * FROM autogpt_runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        return DeepResearchRun(
            id=row["id"],
            goal=row["goal"],
            status=RunStatus(row["status"]),
            max_steps=row["max_steps"],
            current_step=row["current_step"],
            result=row["result"],
            created_at=row["created_at"],
            completed_at=row["completed_at"]
        )
    async def _get_run_facts(self, run_id: str) -> list[dict]:
        """Get all facts linked to this research run."""
        facts = []
        async with self._db.execute(
            """SELECT mf.* FROM memory_facts mf
               JOIN research_facts rf ON mf.id = rf.fact_id
               WHERE rf.run_id = ?""",
            (run_id,)
        ) as cursor:
            async for row in cursor:
                facts.append(dict(row))
        return facts

    async def _link_fact_to_run(self, run_id: str, fact_id: int):
        """Link a fact to a specific research run."""
        await self._db.execute(
            "INSERT OR IGNORE INTO research_facts (run_id, fact_id) VALUES (?, ?)",
            (run_id, fact_id)
        )
        await self._db.commit()
