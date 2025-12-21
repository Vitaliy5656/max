
import asyncio
import sys
import json
from pathlib import Path
import logging

# Setup structured logging
logging.basicConfig(level=logging.ERROR)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.lm_client import lm_client
from src.core.embedding_service import embedding_service
from src.core.memory import memory
from src.core.research.deep_research import DeepResearchAgent
import aiosqlite

async def run_live_research():
    print("\n" + "="*60)
    print("      LIVE DEEP RESEARCH: LGBTQ+ in Russia 2025")
    print("="*60)
    
    # 1. Initialize
    print("[1] Initializing Core Systems...")
    db_path = Path("data/max.db") # Use main DB for this real task
    
    # Ensure DB exists
    if not db_path.exists():
        print("Creating new DB...")
        
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    
    # Initialize global memory object
    await memory.initialize(db_path=db_path)
    
    # 3. Create agent
    agent = DeepResearchAgent(memory._db)
    await agent.initialize(memory._db)
    await embedding_service.initialize(lm_client)
    
    # Inject memory into tools (just in case global update is needed)
    from src.core.tools import tools
    # tools code imports global memory, which points to default DB location. 
    # Since we use default location "data/max.db", it should be fine.
    
    # 2. Set Goal - Use English for better DuckDuckGo results
    query = "Research topic: 'Artificial Intelligence trends 2025'. Find statistics, new developments, industry applications. Save all discovered facts to memory."
    print(f"\n[2] Setting Goal: '{query[:50]}...'")
    
    # Increased steps for deep research
    await autogpt.set_goal(query, max_steps=15)
    
    # 3. Execution & Metrics
    print("\n[3] Running Agent (Max 15 steps)...")
    
    stats = {
        "steps": 0,
        "searches": 0,
        "sites_visited": [], # list of URLs
        "facts_saved": [],   # list of fact content
        "errors": 0
    }
    
    async for step in autogpt.run_generator():
        stats["steps"] += 1
        safe_result = ascii(step.result[:100])
        print(f" > Step {step.step_number}: {step.action}")
        
        if step.action == "web_search":
            stats["searches"] += 1
            print(f"   [Search] Query sent...")
            
        elif step.action == "read_webpage":
            url = step.action_input.get("url")
            if not url:
                url = f"unknown (keys: {list(step.action_input.keys())})"
            
            if url not in stats["sites_visited"]:
                stats["sites_visited"].append(url)
            
            # Log result length and snippet to see what we got
            content_len = len(step.result)
            snippet = ascii(step.result[:100])
            print(f"   [Visit] {url}")
            print(f"           -> Got {content_len} chars. Snippet: {snippet}...")
            
        elif step.action == "save_knowledge":
            content = step.action_input.get("content", "")
            stats["facts_saved"].append(content)
            print(f"   [SAVE] Saved knowledge: {len(content)} chars")
            
        elif "error" in step.result.lower() or "fail" in step.result.lower():
            stats["errors"] += 1
            
    # 4. Final Report
    print("\n" + "="*60)
    print("      RESEARCH COMPLETION REPORT")
    print("="*60)
    
    print(f"Total Steps Executed: {stats['steps']}")
    print(f"Total Searches:       {stats['searches']}")
    print(f"Sites Visited:        {len(stats['sites_visited'])}")
    for url in stats["sites_visited"]:
        print(f"  - {url}")
        
    print(f"Facts Saved to Memory: {len(stats['facts_saved'])}")
    print("-" * 30)
    for i, fact in enumerate(stats['facts_saved'], 1):
        safe_fact = ascii(fact[:100])
        print(f"{i}. {safe_fact}...")
        
    await memory.close()
    await db.close()

if __name__ == "__main__":
    asyncio.run(run_live_research())
