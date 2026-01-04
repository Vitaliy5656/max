"""
Deep Research Audit Test.
Verifies if DeepResearchAgent researches and if the results are stored in memory.
"""

import asyncio
import sys
import os
from pathlib import Path
import logging

# Setup structured logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("ResearchTest")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.memory import memory
from src.core.research.deep_research import DeepResearchAgent, RunStatus
from src.core.embedding_service import embedding_service
from src.core.rag import RAGEngine
from src.core.lm_client import lm_client
import aiosqlite

async def test_deep_research():
    print("\n" + "="*60)
    print("      DEEP RESEARCH AUDIT TEST")
    print("="*60)
    
    # 1. Initialize Components
    print("[1] Initializing Core Systems...")
    
    # IMPORTANT: Ensure Client uses correct model (Mistral or default)
    from src.core.config import config
    config.lm_studio.default_model = "mistralai-mistral-nemo-instruct-2407-12b-mpoa-v1-i1"
    
    await embedding_service.initialize(lm_client)
    
    # Setup DB
    db_path = Path("data/test_audit_v2.db")
    if not db_path.exists():
        print("Creating new DB...")
    
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    
    # Create Agent
    agent = DeepResearchAgent(db)
    await agent.initialize(db)
    
    # Global memory initialization
    memory.db_path = db_path
    await memory.initialize()
    
    rag = RAGEngine(db)
    
    # 2. Set Research Goal
    query = "Find the latest version of Python released in 2025 (fake hypothetical check) or late 2024."
    print(f"\n[2] Setting Goal: '{query}'")
    
    await agent.set_goal(query, max_steps=5)
    
    # 3. Run Agent (Limited steps)
    print("\n[3] Running Deep Research (Max 5 steps)...")
    
    step_count = 0
    research_results_found = False
    
    async for step in agent.run_generator():
        step_count += 1
        # Safe print for Windows
        safe_result = ascii(step.result[:50])
        print(f"   > Step {step.step_number}: {step.action} ({safe_result}...)")
        
        if step.action == "web_search":
            research_results_found = True
            print(f"     [!] Web Search Triggered!")
            
        if step_count >= 5:
            print("   (Hitting step limit for test)")
            break
            
    # 4. Verification from Memory/RAG
    print("\n[4] Verifying Memory Persistence...")
    
    # Check Facts
    async with db.execute("SELECT count(*) as cnt FROM memory_facts") as c:
        row = await c.fetchone()
        facts_count = row['cnt']
    
    # Check Documents (RAG)
    async with db.execute("SELECT count(*) as cnt FROM documents") as c:
        row = await c.fetchone()
        docs_count = row['cnt']
        
    print(f"   - Total Facts in Memory: {facts_count}")
    print(f"   - Total Documents in RAG: {docs_count}")
    
    # Check if we have any facts related to 'Python'
    relevant_facts = await memory.get_relevant_facts(
        conversation_id="test_audit",
        category="research",
        query="Python version 2024 2025"
    )
    
    if relevant_facts:
        print(f"   [!] Found relevant facts in memory: {len(relevant_facts)}")
        for f in relevant_facts:
            print(f"      - {f.content}")
    else:
        print("   [x] No relevant facts found in memory.")

    print("\n" + "="*60)
    if research_results_found and not relevant_facts and docs_count == 0:
        print("RESULT: FAILURE - Search happened but data NOT stored in memory.")
    elif research_results_found:
        print("RESULT: SUCCESS - Search data found in memory/RAG.")
    else:
        print("RESULT: INCONCLUSIVE - Search did not trigger.")
    print("="*60)

    await memory.close()
    await db.close()

if __name__ == "__main__":
    asyncio.run(test_deep_research())
