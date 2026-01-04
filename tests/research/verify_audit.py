
import asyncio
import sys
from pathlib import Path
import aiosqlite
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.research.deep_research import DeepResearchAgent, Task, RunStatus
from src.core.lm_client import lm_client
from src.core.memory import memory

async def verify_fixes():
    print("\n" + "="*60)
    print("      VERIFYING AUDIT FIXES: RESEARCH BLOCK")
    print("="*60)
    
    import time
    db_path = Path(f"data/max_test_{int(time.time())}.db")
    
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    memory.db_path = db_path
    await memory.initialize()
    
    agent = DeepResearchAgent(db)
    await agent.initialize(db)
    
    # 1. TEST TASK MARKING & TRACEABILITY
    print("\n[1] Testing Task Marking & Traceability...")
    goal = "Who is the current CEO of Google?"
    run = await agent.set_goal(goal, max_steps=5)
    
    # Manually mark tasks in plan
    run.plan = [Task(description="Find CEO name", completed=False)]
    
    # Simulate a step with empty result
    await agent._mark_task_progress("read_webpage", "Error: 404")
    print(f"  - Empty result test: Task completed = {run.plan[0].completed} (Expected: False)")
    
    # Simulate a step with good result
    good_result = "Sundar Pichai is the CEO of Google. He joined in 2004."
    await agent._mark_task_progress("read_webpage", good_result)
    print(f"  - Good result test: Task completed = {run.plan[0].completed} (Expected: True)")

    # 2. TEST TRACEABILITY (Linkage)
    print("\n[2] Testing Traceability (run_id linkage)...")
    from src.core.tools import ToolExecutor
    executor = ToolExecutor()
    await executor.execute("save_knowledge", {"content": "Sundar Pichai is CEO", "run_id": run.id})
    
    facts = await agent._get_run_facts(run.id)
    print(f"  - Facts linked to run: {len(facts)} (Expected: 1)")
    if facts:
        print(f"  - Linked Fact ID: {facts[0]['id']}")

    # 3. TEST TRIANGULATION
    print("\n[3] Testing Triangulation Logic...")
    from src.core.research.workbench import WorkbenchChunk
    agent._workbench = agent._workbench or (lambda: None)() # Ensure workbench
    agent._workbench.chunks = [
        WorkbenchChunk(content="Apple releases new iPhone with 5G.", source_url="https://techcrunch.com/1"),
        WorkbenchChunk(content="The latest iPhone features 5G connectivity.", source_url="https://theverge.com/2")
    ]
    # Manually set embeddings for test
    emb = [0.1] * 1024
    agent._workbench.chunks[0].embedding = emb
    agent._workbench.chunks[1].embedding = emb
    
    gold_facts = await agent._workbench.triangulate_facts("iPhone features")
    print(f"  - Triangulated Gold Facts: {len(gold_facts)} (Expected: >0)")
    if gold_facts:
        print(f"  - Sample Fact: {gold_facts[0]}")

    # 4. TEST STORM PLANNING
    print("\n[4] Testing Perspective-Guided Planning (STORM)...")
    storm_plan = await agent._planner.create_initial_plan("The impact of AI on farming")
    print(f"  - Plan stages: {[s['stage'] for s in storm_plan]}")
    has_personas = any(s['stage'] != "Обзор" for s in storm_plan)
    print(f"  - Has Personas: {has_personas} (Expected: True)")

    # 4. TEST SOURCE TRACKING IN SYNTHESIS
    print("\n[4] Testing Source Tracking in Synthesis...")
    test_facts = [
        {"content": "Fact A", "tag": "верифицировано", "url": "https://google.com"},
        {"content": "Fact B", "tag": "слухи", "url": "https://reddit.com"}
    ]
    report = await agent._synthesizer.generate_report("CEO Search", test_facts)
    print("  - Report sample (first 100 chars):")
    print(f"    {report[:100]}...")
    has_sources = "google.com" in report or "src1" in report
    print(f"  - Report has sources: {has_sources} (Expected: True)")

    await memory.close()
    await db.close()
    if db_path.exists(): db_path.unlink()
    print("\nVerification Complete.")

if __name__ == "__main__":
    asyncio.run(verify_fixes())
