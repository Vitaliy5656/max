"""
Deep Research Benchmark Test
- Different topic: "Space exploration 2025"  
- Target: 5-6 sites
- Detailed metrics: timing, fact counts, content quality
"""
import asyncio
import time
from pathlib import Path
import aiosqlite

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.lm_client import lm_client
from src.core.embedding_service import embedding_service
from src.core.research.deep_research import DeepResearchAgent
from src.core.memory import memory  # Use global memory (AppData)

class BenchmarkMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.searches = []  # (query, duration, result_count)
        self.page_reads = []  # (url, duration, chars, tier_used)
        self.fact_saves = []  # (fact_preview, duration)
        self.errors = []
        
    def log_search(self, query, duration, count):
        self.searches.append((query, duration, count))
        
    def log_page_read(self, url, duration, chars, tier):
        self.page_reads.append((url, duration, chars, tier))
        
    def log_fact_save(self, preview, duration):
        self.fact_saves.append((preview, duration))
        
    def total_time(self):
        return time.time() - self.start_time
        
    def print_report(self):
        print("\n" + "=" * 70)
        print("        DEEP RESEARCH BENCHMARK REPORT")
        print("=" * 70)
        
        print(f"\n⏱️  TOTAL TIME: {self.total_time():.2f} seconds")
        
        print(f"\n🔍 SEARCHES ({len(self.searches)} total):")
        for query, dur, count in self.searches:
            print(f"   [{dur:.2f}s] '{query[:40]}...' → {count} results")
        avg_search = sum(d for _, d, _ in self.searches) / len(self.searches) if self.searches else 0
        print(f"   Average: {avg_search:.2f}s per search")
        
        print(f"\n📄 PAGE READS ({len(self.page_reads)} total):")
        for url, dur, chars, tier in self.page_reads:
            domain = url.split('/')[2] if '/' in url else url[:30]
            print(f"   [{dur:.2f}s] {domain} → {chars:,} chars (Tier {tier})")
        avg_read = sum(d for _, d, _, _ in self.page_reads) / len(self.page_reads) if self.page_reads else 0
        total_chars = sum(c for _, _, c, _ in self.page_reads)
        print(f"   Average: {avg_read:.2f}s per page, {total_chars:,} total chars")
        
        print(f"\n💾 FACTS SAVED ({len(self.fact_saves)} total):")
        for preview, dur in self.fact_saves[:5]:  # Show first 5
            print(f"   [{dur:.3f}s] '{preview[:60]}...'")
        if len(self.fact_saves) > 5:
            print(f"   ... and {len(self.fact_saves) - 5} more")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Sites visited:     {len(self.page_reads)}")
        print(f"   Unique domains:    {len(set(u.split('/')[2] for u, _, _, _ in self.page_reads if '/' in u))}")
        print(f"   Facts extracted:   {len(self.fact_saves)}")
        print(f"   Chars per fact:    {total_chars // len(self.fact_saves) if self.fact_saves else 0}")
        print(f"   Throughput:        {len(self.fact_saves) / self.total_time():.1f} facts/sec")
        
        if self.errors:
            print(f"\n⚠️  ERRORS ({len(self.errors)}):")
            for err in self.errors[:3]:
                print(f"   {err}")


async def run_benchmark():
    metrics = BenchmarkMetrics()
    
    print("=" * 70)
    print("   DEEP RESEARCH BENCHMARK: Space Exploration 2025")
    print("=" * 70)
    
    # Initialize
    print("\n[1] Initializing systems...")
    db_path = memory.db_path  # Use global memory's DB path
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    
    # Create Research Agent
    agent = DeepResearchAgent(db)
    await agent.initialize(db)
    await memory.initialize()
    await embedding_service.initialize(lm_client)
    
    # Count facts before
    async with db.execute("SELECT COUNT(*) FROM memory_facts") as cursor:
        facts_before = (await cursor.fetchone())[0]
    print(f"   Facts in DB before: {facts_before}")
    
    # Set goal with higher step limit for more sites
    query = "Research: What are the major space missions and discoveries planned for 2025? Find launch dates, missions, agencies involved. Save all facts."
    print(f"\n[2] Goal: '{query[:60]}...'")
    
    # Run with 30 steps to allow visiting more sites
    print("\n[3] Running research agent (30 steps max)...")
    await agent.set_goal(query, max_steps=30)
    
    run_start = time.time()
    run = await agent.run()
    run_duration = time.time() - run_start
    
    # Count facts after  
    async with db.execute("SELECT COUNT(*) FROM memory_facts") as cursor:
        facts_after = (await cursor.fetchone())[0]
    
    # Analyze steps for metrics
    for step in run.steps:
        if step.action == "web_search" and step.result:
            # Count URLs in result
            url_count = step.result.count("URL:")
            metrics.log_search(
                step.action_input.get("query", "?"),
                1.0,  # Estimated
                url_count
            )
        elif step.action == "read_webpage" and step.result:
            url = step.action_input.get("url", "?")
            chars = len(step.result)
            tier = "1-http" if "httpx" in str(step.result) else "3-nodriver"
            metrics.log_page_read(url, 2.0, chars, tier)
        elif step.action == "save_knowledge":
            preview = step.action_input.get("content", "?")[:80]
            metrics.log_fact_save(preview, 0.1)
    
    # Final report
    print(f"\n[4] Research complete in {run_duration:.1f}s")
    print(f"   Steps executed: {len(run.steps)}")
    print(f"   New facts: {facts_after - facts_before}")
    
    # Show sample of new facts
    print("\n[5] Sample of new facts:")
    async with db.execute(
        "SELECT id, content FROM memory_facts ORDER BY id DESC LIMIT 10"
    ) as cursor:
        rows = await cursor.fetchall()
        for row in rows:
            content = row["content"][:100] + "..." if len(row["content"]) > 100 else row["content"]
            print(f"   ID {row['id']}: {content}")
    
    await db.close()
    
    print("\n" + "=" * 70)
    print(f"BENCHMARK COMPLETE")
    print(f"Total time: {run_duration:.1f}s | Sites: {len([s for s in run.steps if s.action == 'read_webpage'])} | Facts: {facts_after - facts_before}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
