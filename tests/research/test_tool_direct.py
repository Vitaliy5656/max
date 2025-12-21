
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.tools import tools

async def test_direct_search():
    print("Testing direct web_search tool execution...")
    
    # 1. Test Search
    query = "Python 3.13 release date"
    print(f"Query: {query}")
    
    result = await tools.execute("web_search", {"query": query, "max_results": 3})
    
    print(f"Result (ascii): {ascii(result)}")
    
    if "Python" in result and "http" in result:
        print("\n[OK] Search Tool validation passed.")
    else:
        print("\n[FAIL] Search Tool validation failed.")

if __name__ == "__main__":
    asyncio.run(test_direct_search())
