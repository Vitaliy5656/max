"""
Persistent Deep Research Orchestrator
- Crash-resistant: saves after EACH step
- Resumable: can continue from last checkpoint
- Multi-topic: processes list of research topics
- Bilingual: searches in Russian and English
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import aiosqlite
from src.core.lm_client import lm_client
from src.core.embedding_service import embedding_service
from src.core.memory import memory
from src.core.research.deep_research import RunStatus, DeepResearchAgent
from src.core.rag import rag
from src.core.web_search import web_searcher


# ============== RESEARCH CONFIGURATION ==============

RESEARCH_PROJECT = "LGBTQ_CIS_2025"

TOPICS = [
    # Психология
    "ЛГБТ психология каминг аут СНГ Россия",
    "психологические проблемы геев СНГ",
    "ЛГБТ психотерапия Россия Казахстан",
    "гомофобия влияние на психику СНГ",
    
    # Социология  
    "ЛГБТ сообщество СНГ статистика 2024 2025",
    "геи лесбиянки Россия Казахстан Украина сообщества",
    "права ЛГБТ СНГ законодательство",
    "дискриминация ЛГБТ на работе СНГ",
    
    # Здоровье
    "ЛГБТ секс СНГ",
    "секс геев в СНГ",
    "как происходит секс у геев",
    "секс геев в русской среде проблемы",
    "секс русских однополых пар как",
    "русские геи и сексуальная жизнь",
    
    # Отношения
    "однополые отношения СНГ проблемы",
    "ЛГБТ семьи дети СНГ",
    
    # English sources for comparison
    "LGBT psychology CIS Russia",
    "gay rights Central Asia 2024",
    "LGBTQ mental health post-Soviet countries",
]

# ============== STATE PERSISTENCE ==============

STATE_FILE = Path(__file__).parent / f"research_state_{RESEARCH_PROJECT}.json"

def load_state():
    """Load research state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "project": RESEARCH_PROJECT,
        "started_at": datetime.now().isoformat(),
        "completed_topics": [],
        "current_topic_index": 0,
        "total_facts_saved": 0,
        "total_pages_visited": 0,
        "last_checkpoint": None
    }

def save_state(state):
    """Save research state to file."""
    state["last_checkpoint"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"[CHECKPOINT] State saved to {STATE_FILE.name}")


# ============== RESEARCH ENGINE ==============

async def research_topic(topic: str, state: dict, agent: DeepResearchAgent, max_steps: int = 20):
    """Research a single topic with crash-resistant saving."""
    print(f"\n{'='*60}")
    print(f"  RESEARCHING: {topic}")
    print(f"{'='*60}")
    
    # Set goal
    goal = f"Глубокое исследование: {topic}. Найди факты, статистику, исследования. Сохрани ВСЕ найденные факты."
    await agent.set_goal(goal, max_steps=max_steps)
    
    facts_before = state["total_facts_saved"]
    pages_before = state["total_pages_visited"]
    
    try:
        run = await agent.run()
        
        # Count results
        pages_visited = sum(1 for s in run.steps if s.action == "read_webpage")
        
        # Update state
        state["total_pages_visited"] += pages_visited
        
        # Count new facts in DB
        async with memory._db.execute("SELECT COUNT(*) FROM memory_facts") as cursor:
            total_facts = (await cursor.fetchone())[0]
        
        new_facts = total_facts - facts_before
        state["total_facts_saved"] = total_facts
        
        print(f"\n[RESULT] Topic complete:")
        print(f"   Pages visited: {pages_visited}")
        print(f"   New facts: {new_facts}")
        print(f"   Total facts in DB: {total_facts}")
        
        return {
            "topic": topic,
            "pages": pages_visited,
            "new_facts": new_facts,
            "success": True
        }
        
    except Exception as e:
        print(f"[ERROR] Topic failed: {e}")
        return {
            "topic": topic,
            "error": str(e),
            "success": False
        }


async def run_research():
    """Main research orchestrator with resume capability."""
    print("=" * 70)
    print("  PERSISTENT DEEP RESEARCH ORCHESTRATOR")
    print("  " + "=" * 66)
    print(f"  Project: {RESEARCH_PROJECT}")
    print(f"  Topics: {len(TOPICS)}")
    print("=" * 70)
    
    # Load state (resume if exists)
    state = load_state()
    start_index = state["current_topic_index"]
    
    if start_index > 0:
        print(f"\n[RESUME] Continuing from topic {start_index + 1}/{len(TOPICS)}")
        print(f"[RESUME] Previously saved: {state['total_facts_saved']} facts, {state['total_pages_visited']} pages")
    
    # Initialize systems
    print("\n[INIT] Initializing systems...")
    await memory.initialize()
    await rag.initialize(memory._db)
    # Init Research Agent
    agent = DeepResearchAgent(memory._db)
    await agent.initialize(memory._db)
    await embedding_service.initialize(lm_client)
    
    print(f"[INIT] Database: {memory.db_path}")
    
    # Process topics
    for i, topic in enumerate(TOPICS[start_index:], start=start_index):
        state["current_topic_index"] = i
        save_state(state)  # Save BEFORE starting (crash-resistant)
        
        print(f"\n[PROGRESS] Topic {i + 1}/{len(TOPICS)}")
        
        result = await research_topic(topic, state)
        
        # Mark completed
        state["completed_topics"].append({
            "index": i,
            "topic": topic,
            "result": result,
            "completed_at": datetime.now().isoformat()
        })
        
        save_state(state)  # Save AFTER completing
        
        # Brief pause between topics to avoid rate limits
        if i < len(TOPICS) - 1:
            print("[PAUSE] Waiting 5 seconds before next topic...")
            await asyncio.sleep(5)
    
    # Final report
    print("\n" + "=" * 70)
    print("  RESEARCH COMPLETE")
    print("=" * 70)
    print(f"  Topics processed: {len(state['completed_topics'])}/{len(TOPICS)}")
    print(f"  Total facts saved: {state['total_facts_saved']}")
    print(f"  Total pages visited: {state['total_pages_visited']}")
    print(f"  State file: {STATE_FILE}")
    print("=" * 70)
    
    # Show sample of saved facts
    print("\n[SAMPLE] Recent facts saved:")
    async with memory._db.execute(
        "SELECT id, substr(content, 1, 100) FROM memory_facts ORDER BY id DESC LIMIT 10"
    ) as cursor:
        rows = await cursor.fetchall()
        for row in rows:
            print(f"   [{row[0]}] {row[1]}...")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  Press Ctrl+C to stop at any time - progress will be saved!")
    print("=" * 70)
    
    try:
        asyncio.run(run_research())
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Research interrupted by user")
        print("[STOPPED] Progress has been saved - run again to resume")
