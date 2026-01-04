"""
Deep Search Diagnostic Script.
Isolates and tests each component of the deep search pipeline.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def diagnose():
    print("=" * 70)
    print("DEEP SEARCH DIAGNOSTIC REPORT")
    print("=" * 70)
    
    issues_found = []
    
    # 1. Test DuckDuckGo Search
    print("\n[1] Testing DuckDuckGo Search...")
    try:
        from src.core.web_search import web_searcher
        results = await web_searcher.search("Python 3.13 release date", max_results=3)
        if results:
            print(f"    OK: Search returned {len(results)} results")
            for i, r in enumerate(results, 1):
                print(f"        {i}. {r.url[:60]}...")
        else:
            print("    FAIL: Search returned NO results")
            issues_found.append("DuckDuckGo returns empty results")
    except Exception as e:
        print(f"    ERROR: {e}")
        issues_found.append(f"DuckDuckGo search exception: {e}")

    # 2. Test URL Validator (isolated)
    print("\n[2] Testing URL Validator...")
    try:
        from src.core.url_validator import url_validator
        
        # Test with known working URLs
        test_urls = [
            "https://www.python.org",
            "https://docs.python.org/3/whatsnew/3.13.html",
            "https://en.wikipedia.org/wiki/Python_(programming_language)",
        ]
        
        for url in test_urls:
            result = await url_validator.validate_url(url)
            status = "VALID" if result.valid else f"INVALID ({result.error_reason})"
            print(f"    {url[:50]}... -> {status}")
            if not result.valid:
                issues_found.append(f"URL validator blocks valid URL: {url}")
                
    except Exception as e:
        print(f"    ERROR: {e}")
        issues_found.append(f"URL validator exception: {e}")
    
    # 3. Test if validator blocks search results
    print("\n[3] Testing URL Validator on Search Results...")
    try:
        for r in results:
            result = await url_validator.validate_url(r.url)
            status = "VALID" if result.valid else f"BLOCKED ({result.error_reason})"
            print(f"    {r.url[:50]}... -> {status}")
            if not result.valid:
                issues_found.append(f"Validator blocks search result: {r.url[:50]}")
    except Exception as e:
        print(f"    ERROR: {e}")

    # 4. Test Page Reading
    print("\n[4] Testing Page Reader (httpx + playwright fallback)...")
    try:
        test_url = "https://www.python.org"
        content = await web_searcher.read_page(test_url, max_length=500)
        if content and not content.startswith("Error"):
            print(f"    OK: Got {len(content)} chars from {test_url}")
            print(f"    Snippet: {content[:100]}...")
        else:
            print(f"    FAIL: {content[:100]}")
            issues_found.append(f"Page reader failed: {content[:100]}")
    except Exception as e:
        print(f"    ERROR: {e}")
        issues_found.append(f"Page reader exception: {e}")

    # 5. Test Memory Save
    print("\n[5] Testing Memory Save...")
    try:
        from src.core.tools import tools
        from src.core.memory import memory
        import aiosqlite
        
        # Initialize memory with temp DB
        db_path = Path("data/diagnostic_test.db")
        db = await aiosqlite.connect(str(db_path))
        db.row_factory = aiosqlite.Row
        memory._db = db  # Inject DB
        
        # Ensure tables exist
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS memory_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                embedding BLOB,
                source_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        
        result = await tools.execute("save_knowledge", {
            "content": "Test fact for diagnostic", 
            "category": "research"
        })
        
        if "Saved" in result or "ID" in result:
            print(f"    OK: {result}")
        else:
            print(f"    FAIL: {result}")
            issues_found.append(f"Memory save returned: {result}")
            
        await db.close()
    except Exception as e:
        print(f"    ERROR: {e}")
        issues_found.append(f"Memory save exception: {e}")
    
    # SUMMARY
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    if issues_found:
        print(f"\nFOUND {len(issues_found)} ISSUES:\n")
        for i, issue in enumerate(issues_found, 1):
            print(f"  {i}. {issue}")
    else:
        print("\nNO ISSUES FOUND - All components work correctly!")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(diagnose())
